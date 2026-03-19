"""API Versioning utilities."""
from typing import Optional, Callable
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from functools import wraps
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class APIVersion:
    """API Version constants."""

    V1 = "v1"
    V2 = "v2"
    CURRENT = V1


class DeprecationWarning:
    """Deprecation warning helper."""

    def __init__(self, message: str, remove_in: str = "v2.0.0"):
        self.message = message
        self.remove_in = remove_in


def create_versioned_router(prefix: str, version: str = APIVersion.CURRENT) -> APIRouter:
    """Create a versioned API router."""
    return APIRouter(prefix=f"/{version}{prefix}", tags=[f"{version}{prefix}"])


def deprecate_endpoint(
    message: str = "This endpoint will be removed in a future version",
    remove_in: str = "v2.0.0",
):
    """Decorator to mark endpoints as deprecated."""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            response = await func(*args, **kwargs)

            if isinstance(response, JSONResponse):
                headers = dict(response.headers)
                headers["Deprecation"] = "true"
                headers["Sunset"] = remove_in
                headers["Link"] = f'<{settings.API_V1_PREFIX}/docs>; rel="alternate"'

                return JSONResponse(
                    status_code=response.status_code,
                    content=response.body.decode(),
                    headers=headers,
                )

            return response

        return wrapper

    return decorator


async def version_middleware(request: Request, call_next):
    """Middleware to handle API versioning headers."""
    response = await call_next(request)

    api_version = request.headers.get("Accept-Version", APIVersion.CURRENT)

    if api_version != APIVersion.CURRENT:
        response.headers["API-Version"] = APIVersion.CURRENT
        response.headers["Deprecated"] = "false"

    return response


def get_version_info() -> dict:
    """Get current API version information."""
    return {
        "version": APIVersion.CURRENT,
        "status": "stable",
        "endpoints": {
            "v1": {
                "status": "stable",
                "deprecation_date": None,
            },
            "v2": {
                "status": "planned",
                "estimated_release": "Q3 2026",
            },
        },
    }
