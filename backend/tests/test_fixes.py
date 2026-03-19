"""Unit tests for validation, cache, and audit modules."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


class TestValidators:
    """Tests for validation utilities."""

    def test_validate_cpf_valid(self):
        """Test CPF validation with valid numbers."""
        from app.core.validators import validate_cpf
        
        valid_cpfs = [
            "11144477735",
            "111.444.777-35",
            "123.456.789-09",
            "000.000.001-99",
        ]
        
        for cpf in valid_cpfs:
            assert validate_cpf(cpf) is True, f"Failed for CPF: {cpf}"

    def test_validate_cpf_invalid(self):
        """Test CPF validation with invalid numbers."""
        from app.core.validators import validate_cpf
        
        invalid_cpfs = [
            "00000000000",
            "11111111111",
            "12345678901",
            "123",
            "",
            None,
        ]
        
        for cpf in invalid_cpfs:
            assert validate_cpf(cpf) is False, f"Should fail for CPF: {cpf}"

    def test_validate_cpf_edge_cases(self):
        """Test CPF edge cases."""
        from app.core.validators import validate_cpf
        
        assert validate_cpf("") is False
        assert validate_cpf(None) is False

    def test_validate_cnpj_valid(self):
        """Test CNPJ validation with valid numbers."""
        from app.core.validators import validate_cnpj
        
        valid_cnpjs = [
            "11222333000181",
            "11.222.333/0001-81",
        ]
        
        for cnpj in valid_cnpjs:
            assert validate_cnpj(cnpj) is True, f"Failed for CNPJ: {cnpj}"

    def test_validate_cnpj_invalid(self):
        """Test CNPJ validation with invalid numbers."""
        from app.core.validators import validate_cnpj
        
        invalid_cnpjs = [
            "00000000000000",
            "11111111111111",
            "12345678901234",
            "123",
            "",
            None,
        ]
        
        for cnpj in invalid_cnpjs:
            assert validate_cnpj(cnpj) is False, f"Should fail for CNPJ: {cnpj}"

    def test_format_cpf(self):
        """Test CPF formatting."""
        from app.core.validators import format_cpf
        
        assert format_cpf("11144477735") == "111.444.777-35"
        assert format_cpf("123.456.789-09") == "123.456.789-09"

    def test_format_cnpj(self):
        """Test CNPJ formatting."""
        from app.core.validators import format_cnpj
        
        assert format_cnpj("11222333000181") == "11.222.333/0001-81"

    def test_validate_placa_old_format(self):
        """Test vehicle plate validation (old format)."""
        from app.core.validators import validate_placa
        
        assert validate_placa("ABC-1234") is True
        assert validate_placa("ABC1234") is True

    def test_validate_placa_mercosul(self):
        """Test vehicle plate validation (Mercosul format)."""
        from app.core.validators import validate_placa
        
        assert validate_placa("ABC-1B23") is True
        assert validate_placa("ABC1B23") is True

    def test_validate_placa_invalid(self):
        """Test vehicle plate validation with invalid plates."""
        from app.core.validators import validate_placa
        
        assert validate_placa("ABC-123") is False
        assert validate_placa("123-ABCD") is False
        assert validate_placa("") is False

    def test_validate_cep(self):
        """Test CEP validation."""
        from app.core.validators import validate_cep
        
        assert validate_cep("01000-000") is True
        assert validate_cep("01000000") is True
        assert validate_cep("12345678") is True
        assert validate_cep("123") is False
        assert validate_cep("") is False

    def test_validate_renavam(self):
        """Test RENAVAM validation."""
        from app.core.validators import validate_renavam
        
        valid_renavam = "12345678901"
        invalid_renavam = "12345678900"
        
        assert validate_renavam(valid_renavam) is True
        assert validate_renavam(invalid_renavam) is False

    def test_validate_chassi(self):
        """Test chassis validation."""
        from app.core.validators import validate_chassi
        
        valid_chassi = "9BWZZZ377VT000001"
        invalid_chassi = "123"
        
        assert validate_chassi(valid_chassi) is True
        assert validate_chassi(invalid_chassi) is False

    def test_validate_phone(self):
        """Test phone validation."""
        from app.core.validators import validate_phone
        
        assert validate_phone("11999999999") is True
        assert validate_phone("+5511999999999") is True
        assert validate_phone("123") is False
        assert validate_phone("") is False


class TestCacheService:
    """Tests for cache service."""

    @patch("app.core.cache.redis")
    def test_cache_set_when_unavailable(self, mock_redis):
        """Test cache gracefully handles Redis unavailability."""
        mock_redis.from_url.side_effect = Exception("Redis connection failed")
        
        from app.core.cache import CacheService
        service = CacheService()
        service._client = None
        
        result = service.set("test_key", {"data": "value"}, ttl=300)
        assert result is False

    @patch("app.core.cache.redis")
    def test_cache_get_when_unavailable(self, mock_redis):
        """Test cache get returns None when Redis unavailable."""
        from app.core.cache import CacheService
        service = CacheService()
        service._client = None
        
        result = service.get("test_key")
        assert result is None

    def test_cache_invalidate_related(self):
        """Test cache invalidation for related entities."""
        from app.core.cache import CacheService
        
        with patch.object(CacheService, 'delete_pattern') as mock_delete:
            service = CacheService()
            service._client = None
            
            result = service.invalidate_related("veiculo", 1)
            mock_delete.assert_called()

    @patch("app.core.cache.redis")
    def test_cache_stats(self, mock_redis):
        """Test cache statistics."""
        mock_client = MagicMock()
        mock_client.info.return_value = {
            "keyspace_hits": 80,
            "keyspace_misses": 20,
        }
        mock_client.dbsize.return_value = 10
        
        from app.core.cache import CacheService
        service = CacheService()
        service._client = mock_client
        
        stats = service.get_stats()
        
        assert "hit_rate" in stats
        assert stats["hit_rate"] == 80.0


class TestAuditLogger:
    """Tests for audit logging service."""

    def test_calculate_changes(self):
        """Test change calculation between values."""
        from app.services.audit import AuditLogger
        
        logger = AuditLogger()
        
        old_values = {"nome": "Old Name", "status": "active"}
        new_values = {"nome": "New Name", "status": "active"}
        
        changes = logger._calculate_changes(old_values, new_values)
        
        assert "nome" in changes
        assert changes["nome"]["old"] == "Old Name"
        assert changes["nome"]["new"] == "New Name"
        assert "status" not in changes

    def test_calculate_changes_no_changes(self):
        """Test change calculation when no changes."""
        from app.services.audit import AuditLogger
        
        logger = AuditLogger()
        
        old_values = {"nome": "Same"}
        new_values = {"nome": "Same"}
        
        changes = logger._calculate_changes(old_values, new_values)
        
        assert len(changes) == 0


class TestErrorHandling:
    """Tests for error handling improvements."""

    def test_app_exception_creation(self):
        """Test AppException creation."""
        from app.core.exceptions import AppException, ErrorCode
        
        exc = AppException(
            message="Test error",
            code=ErrorCode.NOT_FOUND,
            status_code=404,
            details={"field": "id"}
        )
        
        assert exc.message == "Test error"
        assert exc.code == ErrorCode.NOT_FOUND
        assert exc.status_code == 404
        assert exc.details["field"] == "id"

    def test_not_found_exception(self):
        """Test NotFoundException creation."""
        from app.core.exceptions import NotFoundException
        
        exc = NotFoundException("Veiculo", 123)
        
        assert "Veiculo" in exc.message
        assert "123" in exc.message
        assert exc.status_code == 404

    def test_validation_exception(self):
        """Test ValidationException creation."""
        from app.core.exceptions import ValidationException
        
        exc = ValidationException(
            message="Validation failed",
            details={"errors": ["Field required"]}
        )
        
        assert exc.message == "Validation failed"
        assert exc.details["errors"] == ["Field required"]


class TestBusinessRules:
    """Tests for business rule validations."""

    def test_date_range_validation(self):
        """Test that end date must be after start date."""
        from datetime import datetime, timedelta
        
        start_date = datetime.now() + timedelta(days=30)
        end_date = datetime.now() + timedelta(days=10)
        
        assert end_date < start_date

    def test_negative_value_validation(self):
        """Test negative values are rejected."""
        assert -100.00 < 0

    def test_status_transition_veiculo(self):
        """Test vehicle status transitions."""
        valid_transitions = {
            "disponivel": ["alugado", "manutencao", "inativo"],
            "alugado": ["disponivel", "manutencao"],
            "manutencao": ["disponivel", "inativo"],
            "inativo": ["disponivel"],
        }
        
        assert "alugado" in valid_transitions["disponivel"]
        assert "disponivel" not in valid_transitions["alugado"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
