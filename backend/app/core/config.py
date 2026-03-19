import json
import os
import secrets
from pathlib import Path
from typing import Annotated, List, Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _load_secret(secret_name: str, default: Optional[str] = None) -> Optional[str]:
    """Load secret from Docker secrets file or environment variable."""
    secrets_path = f"/run/secrets/{secret_name}"
    if Path(secrets_path).exists():
        return Path(secrets_path).read_text().strip()
    return os.getenv(secret_name, default)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        env_file_encoding="utf-8",
    )

    PROJECT_NAME: str = "MPCARS"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    TESTING: bool = False

    SECRET_KEY: Optional[str] = None

    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    PASSWORD_MIN_LENGTH: int = 8
    ALLOW_PUBLIC_REGISTRATION: bool = False
    SEED_ON_STARTUP: bool = True
    RUN_LEGACY_COLUMN_MIGRATIONS: bool = True
    ENABLE_API_DOCS: bool = True
    SECURITY_HEADERS_ENABLED: bool = True
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60

    DATABASE_URL: str = "postgresql://mpcars2:ClE7dmebNoSbfv2xTBiAKxrfDwxA3L@mpcars2-db:5432/mpcars2"
    TEST_DATABASE_URL: Optional[str] = None
    REDIS_URL: str = "redis://mpcars2-redis:6379/0"

    POSTGRES_PASSWORD: Optional[str] = None

    BACKUP_ENABLED: bool = False
    BACKUP_DIRECTORY: str = "/backups"
    BACKUP_STORAGE_LABEL: str = "Drive dedicado da VPS"
    BACKUP_RETENTION_DAYS: int = 14
    BACKUP_SCRIPT_PATH: str = "ops/backup_mpcars2.sh"
    RESTORE_SCRIPT_PATH: str = "ops/restore_mpcars2.sh"
    BACKUP_COMMAND_TIMEOUT_SECONDS: int = 300
    GOOGLE_DRIVE_BACKUP_ENABLED: bool = False
    GOOGLE_DRIVE_SYNC_ON_BACKUP: bool = True
    GOOGLE_DRIVE_FOLDER_ID: Optional[str] = None
    GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON: Optional[str] = None
    GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE: Optional[str] = None
    GIT_REPOSITORY_PATH: Optional[str] = None
    PASSWORD_RESET_BASE_URL: Optional[str] = None
    PASSWORD_RESET_TOKEN_TTL_MINUTES: int = 30

    CORS_ORIGINS: Annotated[List[str], NoDecode] = [
        "http://72.61.129.78:3002",
        "http://localhost:3002",
        "http://localhost:5173",
    ]
    TRUSTED_HOSTS: Annotated[List[str], NoDecode] = [
        "72.61.129.78",
        "localhost",
        "127.0.0.1",
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._resolve_secrets()

    def _resolve_secrets(self):
        """Resolve secrets from Docker secrets files or environment."""
        if not self.SECRET_KEY:
            self.SECRET_KEY = _load_secret("SECRET_KEY")

        if not self.POSTGRES_PASSWORD:
            self.POSTGRES_PASSWORD = _load_secret("POSTGRES_PASSWORD")

        if self.ENVIRONMENT in {"production", "staging"} and not self.SECRET_KEY:
            raise ValueError("SECRET_KEY deve ser configurado via secrets em produção")
        if not self.SECRET_KEY:
            import secrets as _secrets
            self.SECRET_KEY = _secrets.token_hex(32)

    @field_validator("CORS_ORIGINS", "TRUSTED_HOSTS", mode="before")
    @classmethod
    def parse_list_env(cls, value):
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                return []
            if normalized.startswith("["):
                return json.loads(normalized)
            return [item.strip() for item in normalized.split(",") if item.strip()]
        return value

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized not in {"development", "staging", "production", "test"}:
            raise ValueError("ENVIRONMENT invalido")
        return normalized

    @model_validator(mode="after")
    def validate_security_settings(self):
        if self.PASSWORD_MIN_LENGTH < 8:
            raise ValueError("PASSWORD_MIN_LENGTH deve ser no minimo 8")

        if self.BACKUP_RETENTION_DAYS < 1:
            raise ValueError("BACKUP_RETENTION_DAYS deve ser no minimo 1")

        if self.BACKUP_COMMAND_TIMEOUT_SECONDS < 30:
            raise ValueError("BACKUP_COMMAND_TIMEOUT_SECONDS deve ser no minimo 30")

        if self.PASSWORD_RESET_TOKEN_TTL_MINUTES < 5:
            raise ValueError("PASSWORD_RESET_TOKEN_TTL_MINUTES deve ser no minimo 5")

        if self.ENVIRONMENT == "production":
            if len(self.SECRET_KEY or "") < 32:
                raise ValueError("SECRET_KEY deve ter ao menos 32 caracteres em producao")

            if self.RUN_LEGACY_COLUMN_MIGRATIONS:
                raise ValueError("RUN_LEGACY_COLUMN_MIGRATIONS deve ser False em producao")

            if self.SEED_ON_STARTUP:
                raise ValueError("SEED_ON_STARTUP deve ser False em producao")

            if self.ENABLE_API_DOCS:
                raise ValueError("ENABLE_API_DOCS deve ser False em producao")

        if self.GOOGLE_DRIVE_BACKUP_ENABLED and not self.GOOGLE_DRIVE_FOLDER_ID:
            raise ValueError("GOOGLE_DRIVE_FOLDER_ID deve ser informado quando o sync do Google Drive estiver ativo")

        if self.GOOGLE_DRIVE_BACKUP_ENABLED and not (
            self.GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON or self.GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE
        ):
            raise ValueError(
                "Informe GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON ou GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE para usar backup no Google Drive"
            )

        return self

    @property
    def database_url_for_runtime(self) -> str:
        if self.TESTING and self.TEST_DATABASE_URL:
            return self.TEST_DATABASE_URL

        if self.POSTGRES_PASSWORD:
            db_user = "mpcars2"
            db_host = "mpcars2-db"
            db_port = "5432"
            db_name = "mpcars2"
            return f"postgresql://{db_user}:{self.POSTGRES_PASSWORD}@{db_host}:{db_port}/{db_name}"

        return self.DATABASE_URL

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_staging(self) -> bool:
        return self.ENVIRONMENT == "staging"

    @property
    def should_enable_docs(self) -> bool:
        return self.ENABLE_API_DOCS and not self.is_production


settings = Settings()
