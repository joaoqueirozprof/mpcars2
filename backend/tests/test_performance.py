import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class TestCacheService:
    """Tests for Redis cache service."""

    def test_generate_key(self):
        """Test cache key generation."""
        from app.core.cache import CacheService

        service = CacheService()
        key = service._generate_key("test", arg1="value1", arg2="value2")
        assert key.startswith("mpcars2:")
        assert "test" in key

    @patch("app.core.cache.redis")
    def test_cache_get_miss(self, mock_redis):
        """Test cache miss."""
        from app.core.cache import CacheService

        mock_client = MagicMock()
        mock_client.get.return_value = None
        mock_redis.from_url.return_value = mock_client

        service = CacheService()
        service._client = mock_client
        result = service.get("test_key")

        assert result is None

    @patch("app.core.cache.redis")
    def test_cache_set(self, mock_redis):
        """Test cache set."""
        from app.core.cache import CacheService

        mock_client = MagicMock()
        mock_client.setex.return_value = True
        mock_redis.from_url.return_value = mock_client

        service = CacheService()
        service._client = mock_client
        result = service.set("test_key", {"data": "value"}, ttl=300)

        assert result is True
        mock_client.setex.assert_called_once()

    @patch("app.core.cache.redis")
    def test_cache_delete(self, mock_redis):
        """Test cache delete."""
        from app.core.cache import CacheService

        mock_client = MagicMock()
        mock_client.delete.return_value = 1
        mock_redis.from_url.return_value = mock_client

        service = CacheService()
        service._client = mock_client
        result = service.delete("test_key")

        assert result is True

    @patch("app.core.cache.redis")
    def test_cache_invalidate_related(self, mock_redis):
        """Test cache invalidation by pattern."""
        from app.core.cache import CacheService

        mock_client = MagicMock()
        mock_client.keys.return_value = ["key1", "key2"]
        mock_client.delete.return_value = 2
        mock_redis.from_url.return_value = mock_client

        service = CacheService()
        service._client = mock_client
        result = service.invalidate_related("contrato", 1)

        assert result == 2


class TestDatabasePool:
    """Tests for database connection pool."""

    def test_pool_settings_development(self, monkeypatch):
        """Test pool settings for development."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("SECRET_KEY", "a" * 32)

        from app.core import database
        settings = database._get_pool_settings()

        assert settings["pool_size"] == 5
        assert settings["max_overflow"] == 10

    def test_pool_settings_staging(self, monkeypatch):
        """Test pool settings for staging."""
        monkeypatch.setenv("ENVIRONMENT", "staging")
        monkeypatch.setenv("SECRET_KEY", "a" * 32)

        from app.core import database
        settings = database._get_pool_settings()

        assert settings["pool_size"] == 15
        assert settings["max_overflow"] == 20

    def test_pool_settings_production(self, monkeypatch):
        """Test pool settings for production."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "a" * 32)

        from app.core import database
        settings = database._get_pool_settings()

        assert settings["pool_size"] == 20
        assert settings["max_overflow"] == 30
        assert settings["pool_recycle"] == 1800
        assert settings["pool_timeout"] == 30

    def test_pool_echo_in_development(self, monkeypatch):
        """Test that SQL echo is enabled in development."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("SECRET_KEY", "a" * 32)

        from app.core import database
        settings = database._get_pool_settings()

        assert settings["echo"] is True

    def test_pool_echo_disabled_in_production(self, monkeypatch):
        """Test that SQL echo is disabled in production."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "a" * 32)

        from app.core import database
        settings = database._get_pool_settings()

        assert settings["echo"] is False


class TestPagination:
    """Tests for pagination functionality."""

    def test_pagination_calculation(self):
        """Test pagination calculations."""
        from app.core.pagination import paginate
        from sqlalchemy.orm import Query

        mock_query = MagicMock(spec=Query)
        mock_query.count.return_value = 100

        result = paginate(mock_query, page=2, limit=10)

        assert result["total"] == 100
        assert result["page"] == 2
        assert result["limit"] == 10
        assert result["totalPages"] == 10
        mock_query.offset.assert_called_with(10)
        mock_query.limit.assert_called_with(10)

    def test_pagination_first_page(self):
        """Test first page calculation."""
        from app.core.pagination import paginate
        from sqlalchemy.orm import Query

        mock_query = MagicMock(spec=Query)
        mock_query.count.return_value = 50

        result = paginate(mock_query, page=1, limit=25)

        assert result["page"] == 1
        assert result["totalPages"] == 2
        mock_query.offset.assert_called_with(0)

    def test_pagination_default_limit(self):
        """Test default limit."""
        from app.core.pagination import paginate
        from sqlalchemy.orm import Query

        mock_query = MagicMock(spec=Query)
        mock_query.count.return_value = 10

        result = paginate(mock_query)

        assert result["limit"] == 50
        assert result["page"] == 1
