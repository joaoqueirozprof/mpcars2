import os
import pytest
from pydantic import ValidationError


class TestSecurityConfig:
    """Tests for security configuration."""

    def test_production_requires_secret_key(self, monkeypatch):
        """Test that production environment requires a valid SECRET_KEY."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "short")

        with pytest.raises(ValueError, match="SECRET_KEY deve ter ao menos 32 caracteres"):
            from app.core.config import Settings
            Settings()

    def test_production_block_legacy_migrations(self, monkeypatch):
        """Test that production blocks legacy migrations."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "a" * 32)
        monkeypatch.setenv("RUN_LEGACY_COLUMN_MIGRATIONS", "true")

        with pytest.raises(ValueError, match="RUN_LEGACY_COLUMN_MIGRATIONS deve ser False"):
            from app.core.config import Settings
            Settings()

    def test_production_block_seed_on_startup(self, monkeypatch):
        """Test that production blocks seed on startup."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "a" * 32)
        monkeypatch.setenv("SEED_ON_STARTUP", "true")

        with pytest.raises(ValueError, match="SEED_ON_STARTUP deve ser False"):
            from app.core.config import Settings
            Settings()

    def test_production_block_api_docs(self, monkeypatch):
        """Test that production blocks API docs."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "a" * 32)
        monkeypatch.setenv("ENABLE_API_DOCS", "true")

        with pytest.raises(ValueError, match="ENABLE_API_DOCS deve ser False"):
            from app.core.config import Settings
            Settings()

    def test_development_allows_legacy_migrations(self, monkeypatch):
        """Test that development allows legacy migrations."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("SECRET_KEY", "a" * 32)
        monkeypatch.setenv("RUN_LEGACY_COLUMN_MIGRATIONS", "true")

        from app.core.config import Settings
        settings = Settings()
        assert settings.RUN_LEGACY_COLUMN_MIGRATIONS is True

    def test_production_properties(self, monkeypatch):
        """Test production/staging properties."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "a" * 32)

        from app.core.config import Settings
        settings = Settings()

        assert settings.is_production is True
        assert settings.is_staging is False
        assert settings.should_enable_docs is False

    def test_staging_properties(self, monkeypatch):
        """Test staging properties."""
        monkeypatch.setenv("ENVIRONMENT", "staging")
        monkeypatch.setenv("SECRET_KEY", "a" * 32)

        from app.core.config import Settings
        settings = Settings()

        assert settings.is_production is False
        assert settings.is_staging is True
        assert settings.should_enable_docs is True

    def test_development_properties(self, monkeypatch):
        """Test development properties."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("SECRET_KEY", "a" * 32)

        from app.core.config import Settings
        settings = Settings()

        assert settings.is_production is False
        assert settings.is_staging is False
        assert settings.should_enable_docs is True


class TestCORSConfig:
    """Tests for CORS configuration."""

    def test_production_restricts_cors(self, monkeypatch):
        """Test that production restricts CORS origins."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "a" * 32)
        monkeypatch.setenv("CORS_ORIGINS", "http://any-origin.com")

        from app.core.config import Settings
        settings = Settings()

        assert "http://any-origin.com" not in settings.CORS_ORIGINS or all(
            o.startswith("https://") for o in settings.CORS_ORIGINS
        )

    def test_development_allows_localhost(self, monkeypatch):
        """Test that development allows localhost origins."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("SECRET_KEY", "a" * 32)

        from app.core.config import Settings
        settings = Settings()

        assert "http://localhost:3002" in settings.CORS_ORIGINS


class TestRateLimitConfig:
    """Tests for rate limiting configuration."""

    def test_default_rate_limit_enabled(self, monkeypatch):
        """Test that rate limiting is enabled by default."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "a" * 32)

        from app.core.config import Settings
        settings = Settings()

        assert settings.RATE_LIMIT_ENABLED is True
        assert settings.RATE_LIMIT_PER_MINUTE == 60

    def test_custom_rate_limit(self, monkeypatch):
        """Test custom rate limit configuration."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "a" * 32)
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "100")

        from app.core.config import Settings
        settings = Settings()

        assert settings.RATE_LIMIT_ENABLED is True
        assert settings.RATE_LIMIT_PER_MINUTE == 100
