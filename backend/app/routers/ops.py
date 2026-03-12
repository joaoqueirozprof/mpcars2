import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_admin_user, get_ops_user
from app.core.security import verify_password
from app.models.user import User


router = APIRouter(prefix="/ops", tags=["Operacao"])

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


def _format_file_size(total_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(max(total_bytes, 0))
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024
    return f"{int(size)} B"


def _list_backups(limit: int = 10) -> List[Dict[str, Any]]:
    backup_root = Path(settings.BACKUP_DIRECTORY)
    if not backup_root.exists() or not backup_root.is_dir():
        return []

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


@router.get("/readiness")
def get_readiness(
    _: User = Depends(get_admin_user), db: Session = Depends(get_db)
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
    _: User = Depends(get_ops_user),
) -> Dict[str, Any]:
    script_path = _resolve_path(settings.BACKUP_SCRIPT_PATH, "ops/backup_mpcars2.sh")
    restore_path = _resolve_path(settings.RESTORE_SCRIPT_PATH, "ops/restore_mpcars2.sh")

    return {
        "enabled": settings.BACKUP_ENABLED,
        "directory": settings.BACKUP_DIRECTORY,
        "storage_label": settings.BACKUP_STORAGE_LABEL,
        "retention_days": settings.BACKUP_RETENTION_DAYS,
        "backup_script_exists": script_path.exists(),
        "restore_script_exists": restore_path.exists(),
        "backup_script": str(script_path),
        "restore_script": str(restore_path),
        "items": _list_backups(),
    }


@router.post("/backups/run")
def run_backup_now(
    _: User = Depends(get_ops_user),
) -> Dict[str, Any]:
    script_path = _resolve_path(settings.BACKUP_SCRIPT_PATH, "ops/backup_mpcars2.sh")
    if not script_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Script de backup nao encontrado em {script_path}",
        )

    result = _run_command(["bash", str(script_path)], _project_root())
    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=(result.stderr or result.stdout or "Falha ao executar backup.").strip(),
        )

    items = _list_backups(limit=1)
    return {
        "status": "backup_executado",
        "message": "Backup solicitado com sucesso.",
        "output": (result.stdout or "").strip(),
        "latest_backup": items[0] if items else None,
    }


@router.get("/version")
def get_version_status(
    _: User = Depends(get_admin_user),
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
