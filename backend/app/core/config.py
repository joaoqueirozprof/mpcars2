import json
from typing import List, Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        enable_decoding=False,
    )

    PROJECT_NAME: str = "MPCARS"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    TESTING: bool = False
    SECRET_KEY: str = "mpcars2-secret-key-change-in-production-2024"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    PASSWORD_MIN_LENGTH: int = 8
    ALLOW_PUBLIC_REGISTRATION: bool = False
    SEED_ON_STARTUP: bool = True
    RUN_LEGACY_COLUMN_MIGRATIONS: bool = True
    ENABLE_API_DOCS: bool = True
    SECURITY_HEADERS_ENABLED: bool = True

    DATABASE_URL: str = "postgresql://mpcars2:mpcars2pass@mpcars2-db:5432/mpcars2"
    TEST_DATABASE_URL: Optional[str] = None
    REDIS_URL: str = "redis://mpcars2-redis:6379/0"
    BACKUP_ENABLED: bool = False
    BACKUP_DIRECTORY: str = "/backups"
    BACKUP_STORAGE_LABEL: str = "Drive dedicado da VPS"
    BACKUP_RETENTION_DAYS: int = 14
    BACKUP_SCRIPT_PATH: str = "ops/backup_mpcars2.sh"
    RESTORE_SCRIPT_PATH: str = "ops/restore_mpcars2.sh"
    BACKUP_COMMAND_TIMEOUT_SECONDS: int = 300
    GIT_REPOSITORY_PATH: Optional[str] = None
    PASSWORD_RESET_BASE_URL: Optional[str] = None
    PASSWORD_RESET_TOKEN_TTL_MINUTES: int = 30

    CORS_ORIGINS: List[str] = [
        "http://72.61.129.78:3002",
        "http://localhost:3002",
        "http://localhost:5173",
    ]
    TRUSTED_HOSTS: List[str] = [
        "72.61.129.78",
        "localhost",
        "127.0.0.1",
    ]

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

        if self.ENVIRONMENT == "production" and len(self.SECRET_KEY or "") < 32:
            raise ValueError("SECRET_KEY deve ter ao menos 32 caracteres em producao")

        return self

    @property
    def database_url_for_runtime(self) -> str:
        if self.TESTING and self.TEST_DATABASE_URL:
            return self.TEST_DATABASE_URL
        return self.DATABASE_URL

settings = Settings()
