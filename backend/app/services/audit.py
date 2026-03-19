"""Audit logging service for tracking all system events."""
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from functools import wraps

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import AuditLog

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """Audit action types."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGE = "password_change"
    ACCESS_DENIED = "access_denied"
    EXPORT = "export"
    IMPORT = "import"
    API_CALL = "api_call"


class AuditEntity(str, Enum):
    """Audit entity types."""
    USER = "user"
    EMPRESA = "empresa"
    CLIENTE = "cliente"
    VEICULO = "veiculo"
    CONTRATO = "contrato"
    RESERVA = "reserva"
    SEGURO = "seguro"
    MULTA = "multa"
    MANUTENCAO = "manutencao"
    FINANCEIRO = "financeiro"
    IPVA = "ipva"
    DESPESA = "despesa"
    CONFIGURACAO = "configuracao"
    BACKUP = "backup"
    SYSTEM = "system"


class AuditLogger:
    """Service for logging audit events."""

    def __init__(self):
        self._session: Optional[Session] = None

    @property
    def session(self) -> Session:
        if self._session is None:
            self._session = SessionLocal()
        return self._session

    def close(self):
        """Close the database session."""
        if self._session:
            self._session.close()
            self._session = None

    def log(
        self,
        action: AuditAction,
        entity_type: AuditEntity,
        entity_id: Optional[int] = None,
        user_id: Optional[int] = None,
        user_email: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Log an audit event.
        
        Args:
            action: Type of action performed
            entity_type: Type of entity affected
            entity_id: ID of the entity (if applicable)
            user_id: ID of the user who performed the action
            user_email: Email of the user
            details: Additional details about the action
            old_values: Previous values (for updates)
            new_values: New values (for updates/creates)
            ip_address: Client IP address
            user_agent: Client user agent
        """
        try:
            changes = None
            if old_values and new_values:
                changes = self._calculate_changes(old_values, new_values)

            audit_log = AuditLog(
                timestamp=datetime.utcnow(),
                action=action.value,
                entity_type=entity_type.value,
                entity_id=entity_id,
                user_id=user_id,
                user_email=user_email,
                details=json.dumps(details) if details else None,
                old_values=json.dumps(old_values) if old_values else None,
                new_values=json.dumps(new_values) if new_values else None,
                changes=json.dumps(changes) if changes else None,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            self.session.add(audit_log)
            self.session.commit()

            logger.info(
                f"Audit: {action.value} on {entity_type.value}:{entity_id} "
                f"by user:{user_email or user_id}"
            )

            return audit_log

        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
            self.session.rollback()
            raise

    def _calculate_changes(
        self,
        old_values: Dict[str, Any],
        new_values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate what changed between old and new values."""
        changes = {}
        
        all_keys = set(old_values.keys()) | set(new_values.keys())
        
        for key in all_keys:
            old = old_values.get(key)
            new = new_values.get(key)
            
            if old != new:
                changes[key] = {
                    "old": old,
                    "new": new,
                }
        
        return changes

    def get_entity_history(
        self,
        entity_type: AuditEntity,
        entity_id: int,
        limit: int = 50,
    ) -> list[AuditLog]:
        """Get audit history for a specific entity."""
        return (
            self.session.query(AuditLog)
            .filter(
                AuditLog.entity_type == entity_type.value,
                AuditLog.entity_id == entity_id,
            )
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
            .all()
        )

    def get_user_activity(
        self,
        user_id: int,
        limit: int = 100,
    ) -> list[AuditLog]:
        """Get activity history for a specific user."""
        return (
            self.session.query(AuditLog)
            .filter(AuditLog.user_id == user_id)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
            .all()
        )

    def search(
        self,
        action: Optional[AuditAction] = None,
        entity_type: Optional[AuditEntity] = None,
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        """Search audit logs with filters."""
        query = self.session.query(AuditLog)

        if action:
            query = query.filter(AuditLog.action == action.value)
        if entity_type:
            query = query.filter(AuditLog.entity_type == entity_type.value)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)

        return (
            query
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
            .all()
        )


audit_logger = AuditLogger()


def audit(
    action: AuditAction,
    entity_type: AuditEntity,
    entity_id_param: str = "id",
):
    """
    Decorator for automatic audit logging.
    
    Usage:
        @audit(AuditAction.CREATE, AuditEntity.VEICULO)
        def create_veiculo(veiculo_data: dict):
            ...
    """
    def decorator(func):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            entity_id = kwargs.get(entity_id_param) or (
                result.id if hasattr(result, 'id') else None
            )

            try:
                audit_logger.log(
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                )
            except Exception as e:
                logger.warning(f"Audit logging failed: {e}")

            return result

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            entity_id = kwargs.get(entity_id_param) or (
                result.id if hasattr(result, 'id') else None
            )

            try:
                audit_logger.log(
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                )
            except Exception as e:
                logger.warning(f"Audit logging failed: {e}")

            return result

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def log_auth_event(
    action: AuditAction,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    success: bool = True,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
):
    """Log authentication events."""
    return audit_logger.log(
        action=action,
        entity_type=AuditEntity.USER,
        entity_id=user_id,
        user_id=user_id,
        user_email=user_email,
        details=details,
        ip_address=ip_address,
    )
