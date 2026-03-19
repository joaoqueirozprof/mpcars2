"""Centralized error handling for the application."""
import logging
import traceback
from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from jose.exceptions import JWTError
from pydantic import ValidationError as PydanticValidationError

from app.core.config import settings

logger = logging.getLogger(__name__)


class ErrorCode:
    """Standardized error codes."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    DUPLICATE_ENTRY = "DUPLICATE_ENTRY"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        code: str = ErrorCode.INTERNAL_ERROR,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundException(AppException):
    """Exception for not found resources."""

    def __init__(self, resource: str, resource_id: Any = None):
        message = f"{resource} not found"
        if resource_id:
            message = f"{resource} with id {resource_id} not found"
        super().__init__(
            message=message,
            code=ErrorCode.NOT_FOUND,
            status_code=status.HTTP_404_NOT_FOUND,
        )


class DuplicateEntryException(AppException):
    """Exception for duplicate entries."""

    def __init__(self, resource: str, field: str, value: Any):
        super().__init__(
            message=f"{resource} with {field} '{value}' already exists",
            code=ErrorCode.DUPLICATE_ENTRY,
            status_code=status.HTTP_409_CONFLICT,
            details={"field": field, "value": str(value)},
        )


class UnauthorizedException(AppException):
    """Exception for unauthorized access."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            code=ErrorCode.UNAUTHORIZED,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class ForbiddenException(AppException):
    """Exception for forbidden access."""

    def __init__(self, message: str = "Access denied"):
        super().__init__(
            message=message,
            code=ErrorCode.FORBIDDEN,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class ValidationException(AppException):
    """Exception for validation errors."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code=ErrorCode.VALIDATION_ERROR,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details or {},
        )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle application exceptions."""
    logger.warning(
        f"Application exception: {exc.code} - {exc.message}",
        extra={
            "path": str(request.url),
            "method": request.method,
            "code": exc.code,
            "details": exc.details,
        },
    )

    content = {
        "error": {
            "code": exc.code,
            "message": exc.message,
        }
    }

    if exc.details:
        content["error"]["details"] = exc.details

    return JSONResponse(
        status_code=exc.status_code,
        content=content,
    )


async def validation_exception_handler(
    request: Request, exc: (RequestValidationError, PydanticValidationError)
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    errors = []

    if isinstance(exc, RequestValidationError):
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })
    else:
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })

    logger.warning(
        f"Validation error on {request.method} {request.url.path}: {errors}",
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": ErrorCode.VALIDATION_ERROR,
                "message": "Validation failed",
                "details": errors,
            }
        },
    )


async def database_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle SQLAlchemy database errors."""
    logger.error(
        f"Database error: {str(exc)}",
        extra={
            "path": str(request.url),
            "method": request.method,
            "error_type": type(exc).__name__,
        },
    )

    if isinstance(exc, IntegrityError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": {
                    "code": ErrorCode.DUPLICATE_ENTRY,
                    "message": "A duplicate entry constraint was violated",
                }
            },
        )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": ErrorCode.DATABASE_ERROR,
                "message": "A database error occurred" if settings.is_production else str(exc),
            }
        },
    )


async def jose_exception_handler(request: Request, exc: JWTError) -> JSONResponse:
    """Handle JWT errors."""
    logger.warning(
        f"JWT error: {str(exc)}",
        extra={"path": str(request.url), "method": request.method},
    )

    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": {
                "code": ErrorCode.UNAUTHORIZED,
                "message": "Invalid or expired token",
            }
        },
        headers={"WWW-Authenticate": "Bearer"},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}\n{traceback.format_exc()}",
        extra={
            "path": str(request.url),
            "method": request.method,
            "error_type": type(exc).__name__,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": ErrorCode.INTERNAL_ERROR,
                "message": "An unexpected error occurred" if settings.is_production else str(exc),
            }
        },
    )


def register_exception_handlers(app):
    """Register all exception handlers with the FastAPI app."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(PydanticValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, database_exception_handler)
    app.add_exception_handler(JWTError, jose_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # Slowapi is optional in some deployments. If it's not installed, keep app online.
    try:
        from slowapi.errors import RateLimitExceeded  # type: ignore
    except Exception:
        RateLimitExceeded = None

    if RateLimitExceeded is not None:
        app.add_exception_handler(RateLimitExceeded, generic_exception_handler)

    return app
