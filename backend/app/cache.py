"""
Redis Cache Module for Nuvie Backend.

Provides:
- Connection management with health checks
- Typed cache operations with TTL
- Recommendation caching (5 min TTL)
- Movie metadata caching (1 hour TTL)
- Graceful fallback when Redis unavailable
"""

import json
import logging
import os
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar

import redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

# Type variable for generic cache functions
T = TypeVar("T")

# -----------------------
# Configuration
# -----------------------
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() == "true"

# TTL constants (in seconds)
TTL_RECOMMENDATIONS = int(os.getenv("CACHE_TTL_RECOMMENDATIONS", "300"))  # 5 minutes
TTL_MOVIE_METADATA = int(os.getenv("CACHE_TTL_MOVIE_METADATA", "3600"))  # 1 hour
TTL_USER_PROFILE = int(os.getenv("CACHE_TTL_USER_PROFILE", "600"))  # 10 minutes
TTL_TRENDING = int(os.getenv("CACHE_TTL_TRENDING", "900"))  # 15 minutes


# -----------------------
# Redis Connection
# -----------------------
class RedisCache:
    """Redis cache client with connection pooling and health checks."""

    _instance: Optional["RedisCache"] = None
    _client: Optional[redis.Redis] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None and REDIS_ENABLED:
            self._connect()

    def _connect(self) -> None:
        """Establish connection to Redis."""
        try:
            self._client = redis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            # Test connection
            self._client.ping()
            logger.info(f"Redis connected: {REDIS_URL.split('@')[-1]}")
        except RedisConnectionError as e:
            logger.warning(f"Redis connection failed: {e}")
            self._client = None
        except Exception as e:
            logger.error(f"Redis initialization error: {e}")
            self._client = None

    @property
    def client(self) -> Optional[redis.Redis]:
        return self._client

    @property
    def is_available(self) -> bool:
        """Check if Redis is available."""
        if not self._client:
            return False
        try:
            self._client.ping()
            return True
        except RedisError:
            return False

    def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        if not self._client:
            return None
        try:
            return self._client.get(key)
        except RedisError as e:
            logger.warning(f"Redis get error for {key}: {e}")
            return None

    def set(self, key: str, value: str, ttl: int = 300) -> bool:
        """Set value in cache with TTL."""
        if not self._client:
            return False
        try:
            return self._client.setex(key, ttl, value)
        except RedisError as e:
            logger.warning(f"Redis set error for {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self._client:
            return False
        try:
            return bool(self._client.delete(key))
        except RedisError as e:
            logger.warning(f"Redis delete error for {key}: {e}")
            return False

    def get_json(self, key: str) -> Optional[Any]:
        """Get JSON value from cache."""
        value = self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None

    def set_json(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set JSON value in cache."""
        try:
            return self.set(key, json.dumps(value), ttl)
        except (TypeError, ValueError) as e:
            logger.warning(f"JSON serialization error for {key}: {e}")
            return False

    def health_check(self) -> Dict[str, Any]:
        """Return health status of Redis connection."""
        if not REDIS_ENABLED:
            return {"status": "disabled", "enabled": False}

        if not self._client:
            return {"status": "disconnected", "enabled": True, "connected": False}

        try:
            info = self._client.info("server")
            return {
                "status": "healthy",
                "enabled": True,
                "connected": True,
                "redis_version": info.get("redis_version"),
                "used_memory_human": info.get("used_memory_human", "unknown"),
            }
        except RedisError as e:
            return {"status": "error", "enabled": True, "connected": False, "error": str(e)}


# Global cache instance
cache = RedisCache()


# -----------------------
# Cache Key Generators
# -----------------------
def recommendations_key(user_id: str, limit: int, offset: int) -> str:
    """Generate cache key for user recommendations."""
    return f"recs:{user_id}:{limit}:{offset}"


def movie_key(movie_id: int) -> str:
    """Generate cache key for movie metadata."""
    return f"movie:{movie_id}"


def trending_key(limit: int, offset: int) -> str:
    """Generate cache key for trending movies."""
    return f"trending:{limit}:{offset}"


def user_profile_key(user_id: str) -> str:
    """Generate cache key for user profile."""
    return f"user:{user_id}"


# -----------------------
# Cache Decorators
# -----------------------
def cached(key_func: Callable[..., str], ttl: int = 300, skip_cache: bool = False):
    """
    Decorator for caching function results.

    Args:
        key_func: Function that generates cache key from function arguments
        ttl: Time to live in seconds
        skip_cache: If True, always bypass cache (useful for testing)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            if skip_cache or not cache.is_available:
                return func(*args, **kwargs)

            # Generate cache key
            cache_key = key_func(*args, **kwargs)

            # Try to get from cache
            cached_value = cache.get_json(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value

            # Execute function and cache result
            result = func(*args, **kwargs)

            if result is not None:
                cache.set_json(cache_key, result, ttl)
                logger.debug(f"Cache set: {cache_key}")

            return result

        return wrapper

    return decorator


def invalidate_user_cache(user_id: str) -> None:
    """Invalidate all cache entries for a user."""
    if cache.is_available:
        # Delete recommendation cache (we don't know all keys, so use pattern)
        # In production, use Redis SCAN with pattern matching
        cache.delete(user_profile_key(user_id))
        logger.info(f"Invalidated cache for user: {user_id}")


# -----------------------
# Convenience Functions
# -----------------------
def get_cached_recommendations(user_id: str, limit: int, offset: int) -> Optional[List[Dict[str, Any]]]:
    """Get cached recommendations for a user."""
    key = recommendations_key(user_id, limit, offset)
    return cache.get_json(key)


def set_cached_recommendations(user_id: str, limit: int, offset: int, items: List[Dict[str, Any]]) -> bool:
    """Cache recommendations for a user."""
    key = recommendations_key(user_id, limit, offset)
    return cache.set_json(key, items, TTL_RECOMMENDATIONS)


def get_cached_movie(movie_id: int) -> Optional[Dict[str, Any]]:
    """Get cached movie metadata."""
    key = movie_key(movie_id)
    return cache.get_json(key)


def set_cached_movie(movie_id: int, data: Dict[str, Any]) -> bool:
    """Cache movie metadata."""
    key = movie_key(movie_id)
    return cache.set_json(key, data, TTL_MOVIE_METADATA)


def get_cached_trending(limit: int, offset: int) -> Optional[List[Dict[str, Any]]]:
    """Get cached trending movies."""
    key = trending_key(limit, offset)
    return cache.get_json(key)


def set_cached_trending(limit: int, offset: int, items: List[Dict[str, Any]]) -> bool:
    """Cache trending movies."""
    key = trending_key(limit, offset)
    return cache.set_json(key, items, TTL_TRENDING)
