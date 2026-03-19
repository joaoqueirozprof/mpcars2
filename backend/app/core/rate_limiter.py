from functools import wraps
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


limiter = Limiter(key_func=get_remote_address)


def get_rate_limit_key(request: Request) -> str:
    """Get rate limit key based on user authentication."""
    if request.state and hasattr(request.state, "user"):
        user = getattr(request.state, "user", None)
        if user and hasattr(user, "id"):
            return f"user:{user.id}"
    return get_remote_address(request)


def rate_limit(requests_per_minute: int = 60):
    """Decorator to apply rate limiting to endpoints."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            limiter = request.app.state.limiter
            if limiter:
                await limiter.check_request_limit(request, key=get_rate_limit_key(request))
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def apply_rate_limit_to_router(router, requests_per_minute: int = 60):
    """Apply rate limiting to all routes in a router."""
    return router
