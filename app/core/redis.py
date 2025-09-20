import asyncio
import json
import time
from typing import Any, Optional, Union, Dict, List
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

import redis.asyncio as redis
from redis.asyncio import ConnectionPool
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.redis")


class RedisManager:
    """
    Redis connection manager with connection pooling, health monitoring,
    and session management capabilities.

    Provides optimized Redis operations for caching, sessions, and real-time data.
    """

    def __init__(self):
        self.pool: Optional[ConnectionPool] = None
        self.client: Optional[redis.Redis] = None
        self._connection_stats = {}
        self._last_health_check = None
        self._is_connected = False

    async def initialize(self):
        """Initialize Redis connection pool."""
        try:
            # Parse Redis URL for connection parameters
            redis_url = settings.get_redis_url()

            # Create connection pool with optimized settings
            self.pool = ConnectionPool.from_url(
                redis_url,
                max_connections=settings.REDIS_POOL_SIZE,
                socket_timeout=settings.REDIS_TIMEOUT,
                socket_connect_timeout=settings.REDIS_TIMEOUT,
                socket_keepalive=True,
                socket_keepalive_options={},
                retry_on_timeout=settings.REDIS_RETRY_ON_TIMEOUT,
                health_check_interval=30,
                decode_responses=True,
                encoding='utf-8'
            )

            # Create Redis client
            self.client = redis.Redis(
                connection_pool=self.pool,
                decode_responses=True
            )

            # Test connection
            await self.client.ping()
            self._is_connected = True

            logger.info(
                "Redis connection initialized",
                pool_size=settings.REDIS_POOL_SIZE,
                timeout=settings.REDIS_TIMEOUT
            )

        except Exception as e:
            logger.error("Failed to initialize Redis connection", error=str(e))
            self._is_connected = False
            raise

    async def close(self):
        """Close Redis connections."""
        try:
            if self.client:
                await self.client.close()
            if self.pool:
                await self.pool.disconnect()

            self._is_connected = False
            logger.info("Redis connections closed")

        except Exception as e:
            logger.error("Error closing Redis connections", error=str(e))

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive Redis health check.

        Returns:
            dict: Health check results with performance metrics
        """
        health_data = {
            "healthy": False,
            "timestamp": time.time(),
            "checks": {}
        }

        try:
            if not self.client:
                await self.initialize()

            # Connectivity check
            start_time = time.time()
            pong = await self.client.ping()
            ping_time = (time.time() - start_time) * 1000

            health_data["checks"]["connectivity"] = {
                "status": "healthy" if pong else "unhealthy",
                "response_time_ms": ping_time,
                "ping_response": pong
            }

            # Performance check with set/get operations
            test_key = f"health_check_{int(time.time())}"
            test_value = "health_check_value"

            start_time = time.time()
            await self.client.set(test_key, test_value, ex=60)
            retrieved = await self.client.get(test_key)
            await self.client.delete(test_key)
            operation_time = (time.time() - start_time) * 1000

            health_data["checks"]["operations"] = {
                "status": "healthy" if retrieved == test_value else "unhealthy",
                "response_time_ms": operation_time,
                "set_get_test": retrieved == test_value
            }

            # Memory and connection info
            info = await self.client.info()
            connected_clients = info.get("connected_clients", 0)
            used_memory = info.get("used_memory", 0)
            max_memory = info.get("maxmemory", 0)

            memory_usage_percent = (
                (used_memory / max_memory * 100) if max_memory > 0 else 0
            )

            health_data["checks"]["resources"] = {
                "status": "healthy" if memory_usage_percent < 90 else "degraded",
                "connected_clients": connected_clients,
                "memory_usage_percent": memory_usage_percent,
                "used_memory_mb": used_memory / (1024 * 1024),
                "max_memory_mb": max_memory / (1024 * 1024) if max_memory > 0 else None
            }

            # Overall health determination
            all_checks_healthy = all(
                check.get("status") == "healthy"
                for check in health_data["checks"].values()
            )

            health_data["healthy"] = all_checks_healthy
            self._last_health_check = time.time()

        except Exception as e:
            logger.error("Redis health check failed", error=str(e))
            health_data["checks"]["error"] = {
                "status": "unhealthy",
                "error": str(e)
            }

        return health_data

    @asynccontextmanager
    async def get_client(self):
        """Get Redis client with automatic reconnection."""
        if not self.client or not self._is_connected:
            await self.initialize()

        try:
            yield self.client
        except RedisConnectionError:
            logger.warning("Redis connection lost, attempting reconnection")
            await self.initialize()
            yield self.client


class CacheManager:
    """
    High-level caching interface with serialization, compression,
    and advanced caching patterns.
    """

    def __init__(self, redis_manager: RedisManager):
        self.redis_manager = redis_manager
        self.key_prefix = settings.CACHE_KEY_PREFIX
        self.default_ttl = settings.CACHE_TTL

    def _make_key(self, key: str) -> str:
        """Create cache key with prefix."""
        return f"{self.key_prefix}:{key}"

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache with automatic deserialization.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            async with self.redis_manager.get_client() as client:
                cache_key = self._make_key(key)
                value = await client.get(cache_key)

                if value is None:
                    return None

                # Try to deserialize JSON
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value

        except Exception as e:
            logger.warning("Cache get error", key=key, error=str(e))
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """
        Set value in cache with automatic serialization.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: settings.CACHE_TTL)
            nx: Only set if key doesn't exist
            xx: Only set if key exists

        Returns:
            True if successful, False otherwise
        """
        try:
            async with self.redis_manager.get_client() as client:
                cache_key = self._make_key(key)
                ttl = ttl or self.default_ttl

                # Serialize value if not string
                if not isinstance(value, str):
                    value = json.dumps(value, default=str)

                result = await client.set(cache_key, value, ex=ttl, nx=nx, xx=xx)
                return bool(result)

        except Exception as e:
            logger.error("Cache set error", key=key, error=str(e))
            return False

    async def delete(self, *keys: str) -> int:
        """
        Delete keys from cache.

        Args:
            *keys: Keys to delete

        Returns:
            Number of keys deleted
        """
        try:
            async with self.redis_manager.get_client() as client:
                cache_keys = [self._make_key(key) for key in keys]
                return await client.delete(*cache_keys)

        except Exception as e:
            logger.error("Cache delete error", keys=keys, error=str(e))
            return 0

    async def exists(self, *keys: str) -> int:
        """
        Check if keys exist in cache.

        Args:
            *keys: Keys to check

        Returns:
            Number of existing keys
        """
        try:
            async with self.redis_manager.get_client() as client:
                cache_keys = [self._make_key(key) for key in keys]
                return await client.exists(*cache_keys)

        except Exception as e:
            logger.error("Cache exists error", keys=keys, error=str(e))
            return 0

    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration time for a key.

        Args:
            key: Cache key
            ttl: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            async with self.redis_manager.get_client() as client:
                cache_key = self._make_key(key)
                return await client.expire(cache_key, ttl)

        except Exception as e:
            logger.error("Cache expire error", key=key, error=str(e))
            return False

    async def mget(self, *keys: str) -> List[Optional[Any]]:
        """
        Get multiple values from cache.

        Args:
            *keys: Keys to retrieve

        Returns:
            List of values (None for missing keys)
        """
        try:
            async with self.redis_manager.get_client() as client:
                cache_keys = [self._make_key(key) for key in keys]
                values = await client.mget(cache_keys)

                results = []
                for value in values:
                    if value is None:
                        results.append(None)
                    else:
                        try:
                            results.append(json.loads(value))
                        except (json.JSONDecodeError, TypeError):
                            results.append(value)

                return results

        except Exception as e:
            logger.error("Cache mget error", keys=keys, error=str(e))
            return [None] * len(keys)

    async def mset(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Set multiple key-value pairs in cache.

        Args:
            mapping: Dictionary of key-value pairs
            ttl: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            async with self.redis_manager.get_client() as client:
                # Prepare cache keys and values
                cache_mapping = {}
                for key, value in mapping.items():
                    cache_key = self._make_key(key)
                    if not isinstance(value, str):
                        value = json.dumps(value, default=str)
                    cache_mapping[cache_key] = value

                # Set all keys
                result = await client.mset(cache_mapping)

                # Set TTL if specified
                if ttl and result:
                    expire_tasks = [
                        client.expire(cache_key, ttl)
                        for cache_key in cache_mapping.keys()
                    ]
                    await asyncio.gather(*expire_tasks, return_exceptions=True)

                return bool(result)

        except Exception as e:
            logger.error("Cache mset error", mapping_size=len(mapping), error=str(e))
            return False

    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment a numeric value in cache.

        Args:
            key: Cache key
            amount: Amount to increment by

        Returns:
            New value after increment, or None on error
        """
        try:
            async with self.redis_manager.get_client() as client:
                cache_key = self._make_key(key)
                return await client.incrby(cache_key, amount)

        except Exception as e:
            logger.error("Cache increment error", key=key, error=str(e))
            return None

    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching a pattern.

        Args:
            pattern: Key pattern (supports wildcards)

        Returns:
            Number of keys deleted
        """
        try:
            async with self.redis_manager.get_client() as client:
                cache_pattern = self._make_key(pattern)

                # Use SCAN for memory-efficient iteration
                keys = []
                async for key in client.scan_iter(match=cache_pattern):
                    keys.append(key)

                if keys:
                    return await client.delete(*keys)
                return 0

        except Exception as e:
            logger.error("Cache clear pattern error", pattern=pattern, error=str(e))
            return 0


class SessionManager:
    """
    Session management using Redis for scalable session storage.
    """

    def __init__(self, redis_manager: RedisManager):
        self.redis_manager = redis_manager
        self.session_prefix = "session"
        self.default_ttl = 86400  # 24 hours

    def _make_session_key(self, session_id: str) -> str:
        """Create session key."""
        return f"{self.session_prefix}:{session_id}"

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data.

        Args:
            session_id: Session identifier

        Returns:
            Session data or None if not found
        """
        try:
            async with self.redis_manager.get_client() as client:
                session_key = self._make_session_key(session_id)
                data = await client.get(session_key)

                if data:
                    return json.loads(data)
                return None

        except Exception as e:
            logger.error("Session get error", session_id=session_id, error=str(e))
            return None

    async def set_session(
        self,
        session_id: str,
        data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set session data.

        Args:
            session_id: Session identifier
            data: Session data
            ttl: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            async with self.redis_manager.get_client() as client:
                session_key = self._make_session_key(session_id)
                ttl = ttl or self.default_ttl

                serialized_data = json.dumps(data, default=str)
                result = await client.set(session_key, serialized_data, ex=ttl)
                return bool(result)

        except Exception as e:
            logger.error("Session set error", session_id=session_id, error=str(e))
            return False

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete session.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False otherwise
        """
        try:
            async with self.redis_manager.get_client() as client:
                session_key = self._make_session_key(session_id)
                result = await client.delete(session_key)
                return bool(result)

        except Exception as e:
            logger.error("Session delete error", session_id=session_id, error=str(e))
            return False

    async def refresh_session(self, session_id: str, ttl: Optional[int] = None) -> bool:
        """
        Refresh session TTL.

        Args:
            session_id: Session identifier
            ttl: New time to live in seconds

        Returns:
            True if refreshed, False otherwise
        """
        try:
            async with self.redis_manager.get_client() as client:
                session_key = self._make_session_key(session_id)
                ttl = ttl or self.default_ttl
                result = await client.expire(session_key, ttl)
                return bool(result)

        except Exception as e:
            logger.error("Session refresh error", session_id=session_id, error=str(e))
            return False


# Global Redis manager and cache instances
redis_manager = RedisManager()
cache_manager = CacheManager(redis_manager)
session_manager = SessionManager(redis_manager)


# Convenience functions
async def get_cache() -> CacheManager:
    """Get cache manager instance."""
    return cache_manager


async def get_session_manager() -> SessionManager:
    """Get session manager instance."""
    return session_manager


async def initialize_redis():
    """Initialize Redis connection."""
    await redis_manager.initialize()


async def close_redis():
    """Close Redis connections."""
    await redis_manager.close()


async def get_redis_health() -> Dict[str, Any]:
    """Get Redis health status."""
    return await redis_manager.health_check()


# Redis middleware for automatic connection management
class RedisMiddleware:
    """Middleware for Redis connection lifecycle management."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Ensure Redis is initialized
        if not redis_manager._is_connected:
            try:
                await redis_manager.initialize()
            except Exception as e:
                logger.error("Failed to initialize Redis in middleware", error=str(e))

        await self.app(scope, receive, send)