import json
import hashlib
import logging
from typing import Any, Optional, Callable, TypeVar, Union
from functools import wraps
import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


class CacheService:
    """Redis cache service for API responses with automatic invalidation."""

    CACHE_TTL = {
        'dashboard': 300,
        'list': 60,
        'detail': 120,
        'search': 180,
    }

    def __init__(self):
        self._client: Optional[redis.Redis] = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            try:
                self._client = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                )
                self._client.ping()
            except redis.RedisError as e:
                logger.warning(f"Redis unavailable, caching disabled: {e}")
                self._client = None
        return self._client

    @property
    def is_available(self) -> bool:
        """Check if Redis is available."""
        return self.client is not None

    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a cache key from prefix and arguments."""
        key_parts = [prefix]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        key_str = ":".join(key_parts)
        return f"mpcars2:{hashlib.md5(key_str.encode()).hexdigest()}:{prefix}"

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.is_available:
            return None
            
        try:
            value = self.client.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)
            logger.debug(f"Cache MISS: {key}")
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Cache get error: {e}")
        return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: int = 300
    ) -> bool:
        """Set value in cache with TTL in seconds."""
        if not self.is_available:
            return False
            
        try:
            serialized = json.dumps(value, default=str)
            result = self.client.setex(key, ttl, serialized)
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return result
        except (redis.RedisError, TypeError) as e:
            logger.warning(f"Cache set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.is_available:
            return False
            
        try:
            result = self.client.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return bool(result)
        except redis.RedisError as e:
            logger.warning(f"Cache delete error: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        if not self.is_available:
            return 0
            
        try:
            keys = self.client.keys(f"mpcars2:*{pattern}*")
            if keys:
                result = self.client.delete(*keys)
                logger.debug(f"Cache DELETE pattern: {pattern} ({result} keys)")
                return result
        except redis.RedisError as e:
            logger.warning(f"Cache delete pattern error: {e}")
        return 0

    def invalidate_list(self, entity: str) -> int:
        """Invalidate all list caches for an entity."""
        return self.delete_pattern(f"list:{entity}")

    def invalidate_detail(self, entity: str, entity_id: int) -> int:
        """Invalidate detail cache for a specific entity."""
        return self.delete_pattern(f"detail:{entity}:{entity_id}")

    def invalidate_related(self, entity_type: str, entity_id: int) -> int:
        """Invalidate all cache entries related to an entity."""
        count = 0
        count += self.delete_pattern(f"detail:{entity_type}:{entity_id}")
        count += self.delete_pattern(f"list:{entity_type}")
        count += self.delete_pattern(f"search:{entity_type}")
        logger.info(f"Invalidated {count} cache entries for {entity_type}:{entity_id}")
        return count

    def invalidate_dashboard(self) -> int:
        """Invalidate all dashboard caches."""
        return self.delete_pattern("dashboard")

    def invalidate_all(self) -> int:
        """Invalidate all application caches."""
        if not self.is_available:
            return 0
            
        try:
            keys = self.client.keys("mpcars2:*")
            if keys:
                result = self.client.delete(*keys)
                logger.info(f"Invalidated all caches: {result} keys")
                return result
        except redis.RedisError as e:
            logger.warning(f"Cache invalidate all error: {e}")
        return 0

    def cached(self, prefix: str, ttl: int = 300):
        """Decorator for caching function results."""
        def decorator(func: F) -> F:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not self.is_available:
                    return await func(*args, **kwargs)
                    
                key = self._generate_key(prefix, *args, **kwargs)
                cached_value = self.get(key)
                if cached_value is not None:
                    return cached_value
                    
                result = await func(*args, **kwargs)
                self.set(key, result, ttl)
                return result

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                if not self.is_available:
                    return func(*args, **kwargs)
                    
                key = self._generate_key(prefix, *args, **kwargs)
                cached_value = self.get(key)
                if cached_value is not None:
                    return cached_value
                    
                result = func(*args, **kwargs)
                self.set(key, result, ttl)
                return result

            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper
        return decorator

    def get_stats(self) -> dict:
        """Get cache statistics."""
        if not self.is_available:
            return {"status": "unavailable"}
            
        try:
            info = self.client.info("stats")
            memory_info = self.client.info("memory")
            return {
                "status": "available",
                "keys": self.client.dbsize(),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(info),
                "memory_used": memory_info.get("used_memory_human", "unknown"),
            }
        except redis.RedisError as e:
            return {"status": "error", "message": str(e)}

    def _calculate_hit_rate(self, info: dict) -> float:
        """Calculate cache hit rate percentage."""
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)


cache_service = CacheService()
