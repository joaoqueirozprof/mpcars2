import os
import shutil
import subprocess
import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_ops_user, get_platform_admin_user
from app.core.security import verify_password
from app.models.user import User
from app.services.google_drive_backup import (
    GoogleDriveBackupError,
    disconnect_google_drive_oauth,
    get_google_drive_account_email,
    get_google_drive_folder_url,
    get_google_drive_overview,
    is_google_drive_configured,
    is_google_drive_enabled,
    is_google_drive_sync_on_backup,
    poll_google_drive_device_authorization,
    start_google_drive_device_authorization,
    sync_backup_directory,
)


router = APIRouter(prefix="/ops", tags=["Operacao"])


class GoogleDriveOAuthStartRequest(BaseModel):
    client_id: str
    client_secret: str
    folder_name: Optional[str] = None

DEFAULT_SECRET_MARKERS = {
    "change-in-production",
    "mpcars2-secret-key-production-2024",
    "mpcars2-secret-key-change-in-production-2024",
}
DEFAULT_PASSWORD_MARKERS = {"mpcars2pass", "postgres", "admin", "123456"}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_path(value: Optional[str], default_relative: str) -> Path:
    if value:
        candidate = Path(value)
        if candidate.is_absolute():
            return candidate
        return (_project_root() / candidate).resolve()
    return (_project_root() / default_relative).resolve()


def _resolve_existing_path(value: Optional[str], default_relative: str) -> Path:
    candidates: List[Path] = []
    if value:
        configured = Path(value)
        if configured.is_absolute():
            candidates.append(configured)
            stripped = Path(str(value).lstrip("/\\"))
            candidates.append((_project_root() / stripped).resolve())
        else:
            candidates.append((_project_root() / configured).resolve())

    candidates.append((_project_root() / default_relative).resolve())

    seen: set[str] = set()
    unique_candidates: List[Path] = []
    for candidate in candidates:
        serialized = str(candidate)
        if serialized in seen:
            continue
        seen.add(serialized)
        unique_candidates.append(candidate)

    for candidate in unique_candidates:
        if candidate.exists():
            return candidate

    return unique_candidates[0]


def _backup_root() -> Path:
    candidate = Path(settings.BACKUP_DIRECTORY)
    if candidate.is_absolute():
        return candidate
    return (_project_root() / candidate).resolve()


def _build_check(
    check_id: str,
    title: str,
    status: str,
    severity: str,
    details: str,
    action: str,
) -> Dict[str, str]:
    return {
        "id": check_id,
        "title": title,
        "status": status,
        "severity": severity,
        "details": details,
        "action": action,
    }


def _database_password_is_default() -> bool:
    try:
        password = (make_url(settings.DATABASE_URL).password or "").strip()
    except Exception:
        return True
    return password.lower() in DEFAULT_PASSWORD_MARKERS


def _secret_is_default() -> bool:
    secret = (settings.SECRET_KEY or "").strip().lower()
    return not secret or any(marker in secret for marker in DEFAULT_SECRET_MARKERS)


def _parse_manifest(manifest_path: Path) -> Dict[str, str]:
    data: Dict[str, str] = {}
    if not manifest_path.exists():
        return data

    for line in manifest_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def _manifest_path(backup_dir: Path) -> Path:
    return backup_dir / "manifest.txt"


def _serialize_manifest_value(value: Any) -> str:
    return str(value if value is not None else "").replace("\n", " ").strip()


def _write_manifest(manifest_path: Path, data: Dict[str, Any]) -> None:
    lines = [
        f"{key}={_serialize_manifest_value(value)}"
        for key, value in data.items()
        if value is not None
    ]
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _update_manifest(
    backup_dir: Path,
    updates: Dict[str, Any],
    *,
    remove_keys: Optional[List[str]] = None,
) -> Dict[str, str]:
    manifest = _parse_manifest(_manifest_path(backup_dir))
    for key in remove_keys or []:
        manifest.pop(key, None)

    for key, value in updates.items():
        if value is None:
            manifest.pop(key, None)
            continue
        manifest[key] = _serialize_manifest_value(value)

    _write_manifest(_manifest_path(backup_dir), manifest)
    return manifest


def _resolve_backup_directory(backup_id: str) -> Path:
    normalized = (backup_id or "").strip()
    if not normalized or normalized in {".", ".."} or "/" in normalized or "\\" in normalized:
        raise HTTPException(status_code=400, detail="Identificador de backup invalido.")

    backup_dir = _backup_root() / normalized
    if not backup_dir.exists() or not backup_dir.is_dir():
        raise HTTPException(status_code=404, detail="Backup nao encontrado.")

    return backup_dir


def _format_file_size(total_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(max(total_bytes, 0))
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024
    return f"{int(size)} B"


def _backup_downloads(backup_id: str) -> Dict[str, str]:
    return {
        "bundle": f"/ops/backups/{backup_id}/download/bundle",
        "database": f"/ops/backups/{backup_id}/download/database",
        "assets": f"/ops/backups/{backup_id}/download/assets",
        "manifest": f"/ops/backups/{backup_id}/download/manifest",
    }


def _google_drive_overview(db: Session) -> Dict[str, Any]:
    return get_google_drive_overview(db)


def _sync_backup_to_google_drive(
    backup_dir: Path,
    *,
    db: Optional[Session] = None,
    raise_on_error: bool = False,
) -> Optional[Dict[str, Any]]:
    if not is_google_drive_enabled(db):
        return None

    attempt_at = datetime.now(timezone.utc).isoformat()
    _update_manifest(
        backup_dir,
        {
            "google_drive_last_attempt_at": attempt_at,
            "google_drive_status": "syncing",
        },
    )

    try:
        sync_result = sync_backup_directory(backup_dir, db=db)
    except GoogleDriveBackupError as exc:
        _update_manifest(
            backup_dir,
            {
                "google_drive_status": "error",
                "google_drive_last_attempt_at": attempt_at,
                "google_drive_last_error": str(exc),
            },
        )
        if raise_on_error:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {
            "status": "error",
            "message": str(exc),
        }

    synced_at = datetime.now(timezone.utc).isoformat()
    _update_manifest(
        backup_dir,
        {
            "google_drive_status": "synced",
            "google_drive_last_attempt_at": attempt_at,
            "google_drive_synced_at": synced_at,
            "google_drive_root_folder_id": sync_result.get("root_folder_id"),
            "google_drive_root_folder_url": sync_result.get("root_folder_url"),
            "google_drive_backup_folder_id": sync_result.get("backup_folder_id"),
            "google_drive_backup_folder_url": sync_result.get("backup_folder_url"),
            "google_drive_account_email": sync_result.get("account_email"),
            "google_drive_service_account_email": sync_result.get("service_account_email"),
            "google_drive_database_file_url": sync_result.get("files", {}).get("database.sql", {}).get("url"),
            "google_drive_assets_file_url": sync_result.get("files", {}).get("assets.tar.gz", {}).get("url"),
            "google_drive_manifest_file_url": sync_result.get("files", {}).get("manifest.txt", {}).get("url"),
        },
        remove_keys=["google_drive_last_error"],
    )
    return sync_result


def _list_backups(limit: int = 10, db: Optional[Session] = None) -> List[Dict[str, Any]]:
    backup_root = _backup_root()
    if not backup_root.exists() or not backup_root.is_dir():
        return []

    google_drive_overview = get_google_drive_overview(db)
    backups: List[Dict[str, Any]] = []
    for directory in sorted(
        [item for item in backup_root.iterdir() if item.is_dir()],
        key=lambda item: item.name,
        reverse=True,
    )[:limit]:
        manifest = _parse_manifest(directory / "manifest.txt")
        total_bytes = sum(
            file.stat().st_size for file in directory.rglob("*") if file.is_file()
        )
        backups.append(
            {
                "id": directory.name,
                "timestamp": manifest.get("timestamp", directory.name),
                "directory": str(directory),
                "database_file": str(directory / "database.sql")
                if (directory / "database.sql").exists()
                else None,
                "assets_file": str(directory / "assets.tar.gz")
                if (directory / "assets.tar.gz").exists()
                else None,
                "size_bytes": total_bytes,
                "size_human": _format_file_size(total_bytes),
                "manifest": manifest,
                "downloads": _backup_downloads(directory.name),
                "google_drive": {
                    "enabled": google_drive_overview["enabled"],
                    "status": manifest.get(
                        "google_drive_status",
                        "pending" if google_drive_overview["enabled"] else "disabled",
                    ),
                    "last_attempt_at": manifest.get("google_drive_last_attempt_at"),
                    "synced_at": manifest.get("google_drive_synced_at"),
                    "last_error": manifest.get("google_drive_last_error"),
                    "root_folder_url": manifest.get("google_drive_root_folder_url")
                    or google_drive_overview.get("folder_url")
                    or get_google_drive_folder_url(),
                    "folder_url": manifest.get("google_drive_backup_folder_url"),
                    "account_email": manifest.get("google_drive_account_email")
                    or manifest.get("google_drive_service_account_email")
                    or get_google_drive_account_email(db),
                    "service_account_email": manifest.get("google_drive_service_account_email"),
                    "files": {
                        "database": manifest.get("google_drive_database_file_url"),
                        "assets": manifest.get("google_drive_assets_file_url"),
                        "manifest": manifest.get("google_drive_manifest_file_url"),
                    },
                },
            }
        )
    return backups


def _run_command(command: List[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=settings.BACKUP_COMMAND_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Comando indisponivel no ambiente atual: {command[0]}",
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(
            status_code=504,
            detail="O processo demorou mais do que o tempo limite configurado.",
        ) from exc


def _write_database_dump(target_file: Path) -> str:
    runtime_url = make_url(settings.database_url_for_runtime)
    driver = (runtime_url.drivername or "").lower()

    if driver.startswith("postgresql"):
        command = [
            "pg_dump",
            "--no-owner",
            "--no-privileges",
            "--clean",
            "--if-exists",
            "-h",
            runtime_url.host or "localhost",
            "-p",
            str(runtime_url.port or 5432),
            "-U",
            runtime_url.username or "postgres",
            "-d",
            (runtime_url.database or "").lstrip("/"),
        ]
        env = os.environ.copy()
        if runtime_url.password:
            env["PGPASSWORD"] = runtime_url.password

        try:
            with target_file.open("w", encoding="utf-8") as output_handle:
                result = subprocess.run(
                    command,
                    cwd=str(_project_root()),
                    env=env,
                    stdout=output_handle,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=settings.BACKUP_COMMAND_TIMEOUT_SECONDS,
                    check=False,
                )
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=500,
                detail="pg_dump nao esta disponivel no ambiente atual para gerar o backup.",
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(
                status_code=504,
                detail="O dump do banco demorou mais do que o tempo limite configurado.",
            ) from exc

        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=(result.stderr or "Falha ao gerar dump do banco.").strip(),
            )

        return f"Dump PostgreSQL gerado via pg_dump para {(runtime_url.database or '').lstrip('/')}"

    if driver.startswith("sqlite"):
        import sqlite3

        database_path = runtime_url.database or ""
        if not database_path or database_path == ":memory:":
            target_file.write_text("-- SQLite em memoria: dump indisponivel\n", encoding="utf-8")
            return "Ambiente de teste com SQLite em memoria registrado no manifesto."

        connection = sqlite3.connect(database_path)
        try:
            with target_file.open("w", encoding="utf-8") as output_handle:
                for line in connection.iterdump():
                    output_handle.write(f"{line}\n")
        finally:
            connection.close()

        return f"Dump SQLite salvo a partir de {database_path}"

    raise HTTPException(
        status_code=500,
        detail=f"Banco {runtime_url.drivername} ainda nao suportado pelo backup automatico.",
    )


def _write_assets_archive(target_file: Path) -> str:
    root = _project_root()
    included_paths: List[str] = []

    with tarfile.open(target_file, "w:gz") as archive:
        for relative in ("uploads", "pdfs"):
            source = root / relative
            if not source.exists():
                continue
            archive.add(source, arcname=relative)
            included_paths.append(relative)

    if not included_paths:
        return "Nenhum upload ou PDF encontrado; arquivo de assets criado vazio."

    return "Assets salvos com: " + ", ".join(included_paths)


def _cleanup_old_backups(backup_root: Path) -> int:
    if not backup_root.exists():
        return 0

    removed = 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.BACKUP_RETENTION_DAYS)

    for directory in backup_root.iterdir():
        if not directory.is_dir():
            continue
        modified_at = datetime.fromtimestamp(directory.stat().st_mtime, tz=timezone.utc)
        if modified_at < cutoff:
            shutil.rmtree(directory, ignore_errors=True)
            removed += 1

    return removed


def _run_native_backup() -> Dict[str, Any]:
    backup_root = _backup_root()
    backup_root.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_dir = backup_root / timestamp
    target_dir.mkdir(parents=True, exist_ok=True)

    database_file = target_dir / "database.sql"
    assets_file = target_dir / "assets.tar.gz"
    database_note = _write_database_dump(database_file)
    assets_note = _write_assets_archive(assets_file)
    removed_count = _cleanup_old_backups(backup_root)

    manifest = {
        "timestamp": timestamp,
        "backup_mode": "native-api",
        "database_note": database_note,
        "assets_note": assets_note,
        "backup_directory": str(target_dir),
        "retention_days": str(settings.BACKUP_RETENTION_DAYS),
        "removed_old_backups": str(removed_count),
    }
    _write_manifest(_manifest_path(target_dir), manifest)

    return {
        "target_dir": target_dir,
        "output": "\n".join(
            [
                f"Backup salvo em {target_dir}",
                database_note,
                assets_note,
                f"Backups antigos removidos: {removed_count}",
            ]
        ),
    }


@router.get("/readiness")
def get_readiness(
    _: User = Depends(get_platform_admin_user), db: Session = Depends(get_db)
) -> Dict[str, Any]:
    checks: List[Dict[str, str]] = []
    seeded_admin = db.query(User).filter(User.email == "admin@mpcars.com").first()
    default_admin_active = bool(
        seeded_admin
        and getattr(seeded_admin, "ativo", False)
        and verify_password("123456", seeded_admin.hashed_password)
    )

    checks.append(
        _build_check(
            "environment",
            "Ambiente configurado",
            "ok" if settings.ENVIRONMENT == "production" else "warning",
            "warning",
            "O sistema deve rodar com ENVIRONMENT=production para aplicar a politica correta de operacao."
            if settings.ENVIRONMENT != "production"
            else "Ambiente marcado como producao.",
            "Defina ENVIRONMENT=production no arquivo .env.production e reinicie os containers.",
        )
    )
    checks.append(
        _build_check(
            "secret_key",
            "Chave secreta forte",
            "ok" if not _secret_is_default() and len(settings.SECRET_KEY or "") >= 32 else "critical",
            "critical",
            "A SECRET_KEY ainda parece padrao ou curta demais."
            if _secret_is_default() or len(settings.SECRET_KEY or "") < 32
            else "A SECRET_KEY esta com tamanho adequado para producao.",
            "Gere uma chave longa e unica antes de expor o sistema para usuarios reais.",
        )
    )
    checks.append(
        _build_check(
            "database_password",
            "Senha do banco dedicada",
            "ok" if not _database_password_is_default() else "critical",
            "critical",
            "A senha do banco ainda parece padrao."
            if _database_password_is_default()
            else "A credencial do banco nao aparenta usar senha padrao.",
            "Altere POSTGRES_PASSWORD e DATABASE_URL para uma credencial exclusiva do ambiente real.",
        )
    )
    checks.append(
        _build_check(
            "api_docs",
            "Documentacao publica da API",
            "ok" if settings.ENVIRONMENT != "production" or not settings.ENABLE_API_DOCS else "warning",
            "warning",
            "Docs da API ainda estao publicos em producao."
            if settings.ENVIRONMENT == "production" and settings.ENABLE_API_DOCS
            else "Docs da API podem ser desabilitados quando o ambiente real estiver fechado.",
            "Defina ENABLE_API_DOCS=false em producao para reduzir superficie de exposicao.",
        )
    )
    checks.append(
        _build_check(
            "seed_startup",
            "Seed automatica no startup",
            "ok" if settings.ENVIRONMENT != "production" or not settings.SEED_ON_STARTUP else "warning",
            "warning",
            "SEED_ON_STARTUP ainda esta ativo para producao."
            if settings.ENVIRONMENT == "production" and settings.SEED_ON_STARTUP
            else "Seed automatica pode permanecer no ambiente de homologacao ou teste.",
            "Defina SEED_ON_STARTUP=false antes de operar com cadastros reais.",
        )
    )
    checks.append(
        _build_check(
            "legacy_migrations",
            "Migracoes legadas no startup",
            "ok" if settings.ENVIRONMENT != "production" or not settings.RUN_LEGACY_COLUMN_MIGRATIONS else "warning",
            "warning",
            "Compatibilidade legada ainda roda a cada subida da API."
            if settings.ENVIRONMENT == "production" and settings.RUN_LEGACY_COLUMN_MIGRATIONS
            else "As correcoes legadas podem ser desligadas apos estabilizar a base.",
            "Defina RUN_LEGACY_COLUMN_MIGRATIONS=false quando a base estiver alinhada com as migracoes.",
        )
    )
    checks.append(
        _build_check(
            "cors_hosts",
            "CORS e hosts confiaveis",
            "ok"
            if settings.CORS_ORIGINS and "*" not in settings.CORS_ORIGINS and settings.TRUSTED_HOSTS
            else "warning",
            "warning",
            "Revise dominios permitidos e hosts confiaveis antes de apontar o dominio final."
            if not settings.CORS_ORIGINS or "*" in settings.CORS_ORIGINS or not settings.TRUSTED_HOSTS
            else "CORS e trusted hosts estao configurados explicitamente.",
            "Cadastre apenas os dominios reais em CORS_ORIGINS e TRUSTED_HOSTS.",
        )
    )
    checks.append(
        _build_check(
            "backup_policy",
            "Rotina de backup configurada",
            "ok" if settings.BACKUP_ENABLED and settings.BACKUP_DIRECTORY else "critical",
            "critical",
            "Ainda nao existe sinalizacao de backup automatico configurado."
            if not settings.BACKUP_ENABLED
            else f"Backups apontados para {settings.BACKUP_DIRECTORY}.",
            "Ative BACKUP_ENABLED, defina BACKUP_DIRECTORY e use o script de backup em uma rotina automatica.",
        )
    )
    checks.append(
        _build_check(
            "default_admin",
            "Conta admin padrao",
            "critical" if default_admin_active else "ok",
            "critical",
            "A conta admin@mpcars.com com senha padrao ainda esta ativa."
            if default_admin_active
            else "Nao foi detectada conta admin padrao com senha fraca.",
            "Troque a senha do admin seeded ou remova a conta padrao antes do go-live.",
        )
    )
    checks.append(
        _build_check(
            "public_registration",
            "Cadastro publico desabilitado",
            "ok" if not settings.ALLOW_PUBLIC_REGISTRATION else "warning",
            "warning",
            "O cadastro publico esta habilitado."
            if settings.ALLOW_PUBLIC_REGISTRATION
            else "O cadastro publico segue bloqueado para producao.",
            "Mantenha ALLOW_PUBLIC_REGISTRATION=false para nao abrir criacao livre de contas.",
        )
    )

    critical_count = sum(1 for check in checks if check["status"] == "critical")
    warning_count = sum(1 for check in checks if check["status"] == "warning")
    ok_count = sum(1 for check in checks if check["status"] == "ok")

    return {
        "environment": settings.ENVIRONMENT,
        "ready_for_production": critical_count == 0 and settings.ENVIRONMENT == "production",
        "summary": {
            "ok": ok_count,
            "warning": warning_count,
            "critical": critical_count,
        },
        "checks": checks,
        "backup": {
            "enabled": settings.BACKUP_ENABLED,
            "directory": settings.BACKUP_DIRECTORY,
            "storage_label": settings.BACKUP_STORAGE_LABEL,
            "retention_days": settings.BACKUP_RETENTION_DAYS,
            "scripts": {
                "backup": settings.BACKUP_SCRIPT_PATH,
                "restore": settings.RESTORE_SCRIPT_PATH,
            },
        },
        "next_steps": [check["action"] for check in checks if check["status"] != "ok"][:6],
    }


@router.get("/backups")
def list_backups(
    db: Session = Depends(get_db),
    _: User = Depends(get_ops_user),
) -> Dict[str, Any]:
    script_path = _resolve_existing_path(settings.BACKUP_SCRIPT_PATH, "ops/backup_mpcars2.sh")
    restore_path = _resolve_existing_path(settings.RESTORE_SCRIPT_PATH, "ops/restore_mpcars2.sh")

    return {
        "enabled": settings.BACKUP_ENABLED,
        "directory": str(_backup_root()),
        "storage_label": settings.BACKUP_STORAGE_LABEL,
        "retention_days": settings.BACKUP_RETENTION_DAYS,
        "backup_script_exists": script_path.exists(),
        "restore_script_exists": restore_path.exists(),
        "backup_script": str(script_path),
        "restore_script": str(restore_path),
        "google_drive": _google_drive_overview(db),
        "items": _list_backups(db=db),
    }


@router.post("/backups/run")
def run_backup_now(
    db: Session = Depends(get_db),
    _: User = Depends(get_ops_user),
) -> Dict[str, Any]:
    if not settings.BACKUP_ENABLED:
        raise HTTPException(
            status_code=400,
            detail="Backups estao desabilitados neste ambiente.",
        )

    script_path = _resolve_existing_path(settings.BACKUP_SCRIPT_PATH, "ops/backup_mpcars2.sh")
    output = ""
    sync_result: Optional[Dict[str, Any]] = None

    if script_path.exists():
        result = _run_command(["bash", str(script_path)], _project_root())
        if result.returncode == 0:
            output = (result.stdout or "").strip()
        else:
            native_result = _run_native_backup()
            script_error = (result.stderr or result.stdout or "Falha ao executar backup.").strip()
            output = f"{native_result['output']}\nScript legado ignorado: {script_error}"
    else:
        native_result = _run_native_backup()
        output = native_result["output"]

    items = _list_backups(limit=1, db=db)
    if (
        items
        and is_google_drive_enabled(db)
        and is_google_drive_sync_on_backup(db)
        and items[0].get("google_drive", {}).get("status") != "synced"
    ):
        sync_result = _sync_backup_to_google_drive(_resolve_backup_directory(items[0]["id"]), db=db)
        if sync_result:
            sync_message = (
                f"Google Drive sincronizado: {sync_result.get('backup_folder_url')}"
                if sync_result.get("status") != "error"
                else f"Falha ao sincronizar no Google Drive: {sync_result.get('message')}"
            )
            output = "\n".join([part for part in [output, sync_message] if part])
            items = _list_backups(limit=1, db=db)

    return {
        "status": "backup_executado",
        "message": "Backup solicitado com sucesso.",
        "output": output,
        "google_drive": sync_result,
        "latest_backup": items[0] if items else None,
    }


def _cleanup_file(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


@router.post("/google-drive/oauth/device/start")
def start_google_drive_oauth_device_flow(
    payload: GoogleDriveOAuthStartRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_ops_user),
) -> Dict[str, Any]:
    try:
        return start_google_drive_device_authorization(
            payload.client_id,
            payload.client_secret,
            folder_name=payload.folder_name,
            db=db,
        )
    except GoogleDriveBackupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/google-drive/oauth/device/poll")
def poll_google_drive_oauth_device_flow(
    db: Session = Depends(get_db),
    _: User = Depends(get_ops_user),
) -> Dict[str, Any]:
    try:
        return poll_google_drive_device_authorization(db=db)
    except GoogleDriveBackupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/google-drive/oauth/disconnect")
def disconnect_google_drive_oauth_flow(
    db: Session = Depends(get_db),
    _: User = Depends(get_ops_user),
) -> Dict[str, Any]:
    try:
        return disconnect_google_drive_oauth(db=db)
    except GoogleDriveBackupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/backups/{backup_id}/download/{artifact}")
def download_backup_artifact(
    backup_id: str,
    artifact: str,
    _: User = Depends(get_ops_user),
):
    backup_dir = _resolve_backup_directory(backup_id)
    artifact_name = (artifact or "").strip().lower()

    artifact_map = {
        "database": ("database.sql", "application/sql"),
        "assets": ("assets.tar.gz", "application/gzip"),
        "manifest": ("manifest.txt", "text/plain; charset=utf-8"),
    }

    if artifact_name == "bundle":
        temp_handle = NamedTemporaryFile(
            prefix=f"mpcars2-backup-{backup_id}-",
            suffix=".tar.gz",
            delete=False,
        )
        temp_path = Path(temp_handle.name)
        temp_handle.close()
        with tarfile.open(temp_path, "w:gz") as archive:
            archive.add(backup_dir, arcname=backup_dir.name)

        return FileResponse(
            temp_path,
            media_type="application/gzip",
            filename=f"backup-{backup_id}.tar.gz",
            background=BackgroundTask(_cleanup_file, temp_path),
        )

    selected = artifact_map.get(artifact_name)
    if not selected:
        raise HTTPException(status_code=400, detail="Arquivo de backup invalido.")

    filename, media_type = selected
    file_path = backup_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado neste backup.")

    return FileResponse(
        file_path,
        media_type=media_type,
        filename=f"{backup_id}-{filename}",
    )


@router.post("/backups/{backup_id}/sync-google-drive")
def sync_backup_now(
    backup_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_ops_user),
) -> Dict[str, Any]:
    if not is_google_drive_enabled(db):
        raise HTTPException(
            status_code=400,
            detail="A sincronizacao com Google Drive esta desabilitada neste ambiente.",
        )

    backup_dir = _resolve_backup_directory(backup_id)
    sync_result = _sync_backup_to_google_drive(backup_dir, db=db, raise_on_error=True)
    latest = next((item for item in _list_backups(limit=30, db=db) if item["id"] == backup_id), None)

    return {
        "status": "sincronizado",
        "message": "Backup sincronizado com o Google Drive.",
        "google_drive": sync_result,
        "backup": latest,
    }


@router.get("/version")
def get_version_status(
    _: User = Depends(get_platform_admin_user),
) -> Dict[str, Any]:
    repo_path = _resolve_path(settings.GIT_REPOSITORY_PATH, ".")
    if not repo_path.exists():
        raise HTTPException(status_code=500, detail="Repositorio git nao encontrado para leitura de versao.")

    branch = _run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo_path)
    if branch.returncode != 0:
        raise HTTPException(status_code=500, detail=(branch.stderr or "Falha ao consultar branch git").strip())

    commit = _run_command(["git", "rev-parse", "HEAD"], repo_path)
    short_commit = _run_command(["git", "rev-parse", "--short", "HEAD"], repo_path)
    message = _run_command(["git", "log", "-1", "--pretty=%s"], repo_path)
    recent = _run_command(
        ["git", "log", "-5", "--pretty=%h|%s|%cd", "--date=iso"],
        repo_path,
    )
    dirty = _run_command(["git", "status", "--porcelain"], repo_path)

    recent_commits = []
    for line in (recent.stdout or "").splitlines():
        short_hash, title, committed_at = (line.split("|", 2) + ["", "", ""])[:3]
        recent_commits.append(
            {
                "short_hash": short_hash,
                "title": title,
                "committed_at": committed_at,
            }
        )

    return {
        "repository": str(repo_path),
        "branch": (branch.stdout or "").strip(),
        "commit_hash": (commit.stdout or "").strip(),
        "short_hash": (short_commit.stdout or "").strip(),
        "last_message": (message.stdout or "").strip(),
        "dirty": bool((dirty.stdout or "").strip()),
        "recent_commits": recent_commits,
    }
