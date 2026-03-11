from typing import List, Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
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

    DATABASE_URL: str = "postgresql://mpcars2:mpcars2pass@mpcars2-db:5432/mpcars2"
    TEST_DATABASE_URL: Optional[str] = None
    REDIS_URL: str = "redis://mpcars2-redis:6379/0"

    CORS_ORIGINS: List[str] = [
        "http://72.61.129.78:3002",
        "http://localhost:3002",
        "http://localhost:5173",
    ]

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

        if self.ENVIRONMENT == "production" and len(self.SECRET_KEY or "") < 32:
            raise ValueError("SECRET_KEY deve ter ao menos 32 caracteres em producao")

        return self

    @property
    def database_url_for_runtime(self) -> str:
        if self.TESTING and self.TEST_DATABASE_URL:
            return self.TEST_DATABASE_URL
        return self.DATABASE_URL

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
