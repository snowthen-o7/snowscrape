"""
Redis caching module for SnowScrape.

Supports both Upstash (serverless, for Lambda) and standard Redis (local dev).
All operations are fail-safe: if Redis is unavailable, operations return None/False
instead of raising exceptions.
"""

import json
import os
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

_redis_client = None


def get_redis_client():
    """Get or create Redis client singleton. Returns None if Redis unavailable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    redis_url = os.environ.get('REDIS_URL')
    if not redis_url:
        return None

    try:
        import redis
        _redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=2,
            socket_connect_timeout=2,
            retry_on_timeout=True,
        )
        _redis_client.ping()
        logger.info("Redis connected successfully")
        return _redis_client
    except Exception as e:
        logger.warning("Failed to connect to Redis: %s", e)
        _redis_client = None
        return None


PREFIX = "snowscrape:"


def cache_get(key: str) -> Optional[Any]:
    """Get value from cache. Returns None on miss or error."""
    client = get_redis_client()
    if not client:
        return None
    try:
        raw = client.get(f"{PREFIX}{key}")
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.warning("Cache get error for %s: %s", key, e)
        return None


def cache_set(key: str, value: Any, ttl: int = 60) -> bool:
    """Set value in cache with TTL in seconds. Returns success."""
    client = get_redis_client()
    if not client:
        return False
    try:
        client.setex(f"{PREFIX}{key}", ttl, json.dumps(value, default=str))
        return True
    except Exception as e:
        logger.warning("Cache set error for %s: %s", key, e)
        return False


def cache_delete(key: str) -> bool:
    """Delete key from cache. Returns success."""
    client = get_redis_client()
    if not client:
        return False
    try:
        client.delete(f"{PREFIX}{key}")
        return True
    except Exception as e:
        logger.warning("Cache delete error for %s: %s", key, e)
        return False


def cache_delete_pattern(pattern: str) -> bool:
    """Delete all keys matching a pattern. Returns success."""
    client = get_redis_client()
    if not client:
        return False
    try:
        cursor = 0
        while True:
            cursor, keys = client.scan(cursor, match=f"{PREFIX}{pattern}", count=100)
            if keys:
                client.delete(*keys)
            if cursor == 0:
                break
        return True
    except Exception as e:
        logger.warning("Cache delete pattern error for %s: %s", pattern, e)
        return False


def cache_get_or_set(key: str, factory: Callable[[], Any], ttl: int = 60) -> Any:
    """Get from cache, or call factory and cache result."""
    cached = cache_get(key)
    if cached is not None:
        return cached
    value = factory()
    cache_set(key, value, ttl)
    return value
