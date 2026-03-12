from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_admin_user
from app.core.security import verify_password
from app.models.user import User


router = APIRouter(prefix="/ops", tags=["Operacao"])

DEFAULT_SECRET_MARKERS = {
    "change-in-production",
    "mpcars2-secret-key-production-2024",
    "mpcars2-secret-key-change-in-production-2024",
}
DEFAULT_PASSWORD_MARKERS = {"mpcars2pass", "postgres", "admin", "123456"}


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
            "Ative BACKUP_ENABLED, defina BACKUP_DIRECTORY e use o script ops/backup_mpcars2.sh em cron.",
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

    next_steps = [check["action"] for check in checks if check["status"] != "ok"][:6]

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
            "retention_days": settings.BACKUP_RETENTION_DAYS,
            "scripts": {
                "backup": "ops/backup_mpcars2.sh",
                "restore": "ops/restore_mpcars2.sh",
            },
        },
        "next_steps": next_steps,
    }
