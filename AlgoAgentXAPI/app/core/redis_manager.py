"""
Redis connection manager with health checks and fallback support.
"""

import logging
import redis.asyncio as aioredis
from typing import Optional, Any
from contextlib import asynccontextmanager
from .config import settings

logger = logging.getLogger(__name__)


class RedisManager:
    """Manages Redis connections with health checks and fallback logic."""

    def __init__(self):
        self._redis_client: Optional[aioredis.Redis] = None
        self._is_connected = False
        self._connection_error = None

    async def initialize(self) -> bool:
        """
        Initialize Redis connection with health check.
        
        Returns:
            bool: True if Redis is available, False otherwise
        """
        try:
            # Parse Redis URL from environment
            redis_url = self._get_redis_url()
            logger.info(f"Initializing Redis connection with URL: {redis_url}")
            
            # Create Redis client
            self._redis_client = aioredis.from_url(
                redis_url,
                decode_responses=False,  # Keep binary for Celery compatibility
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            
            # Test connection
            await self._redis_client.ping()
            self._is_connected = True
            self._connection_error = None
            logger.info("Redis connection established successfully")
            return True
            
        except Exception as e:
            self._is_connected = False
            self._connection_error = str(e)
            logger.warning(f"Redis connection failed: {e}")
            logger.warning("Redis is unavailable - will use fallback background execution")
            return False

    def _get_redis_url(self) -> str:
        """Get Redis URL from environment variables with fallback logic."""
        # Try REDIS_URL first (most specific)
        redis_url = getattr(settings, 'redis_url', None)
        if redis_url and redis_url != "redis://localhost:6379/0":
            return redis_url
            
        # Try individual components
        redis_host = getattr(settings, 'redis_host', 'localhost')
        redis_port = getattr(settings, 'redis_port', 6379)
        redis_db = getattr(settings, 'redis_db', 0)
        
        return f"redis://{redis_host}:{redis_port}/{redis_db}"

    @property
    def is_available(self) -> bool:
        """Check if Redis is available and connected."""
        return self._is_connected and self._redis_client is not None

    @property
    def client(self) -> Optional[aioredis.Redis]:
        """Get Redis client if available."""
        if not self.is_available:
            return None
        return self._redis_client

    async def health_check(self) -> dict:
        """
        Perform Redis health check.
        
        Returns:
            dict: Health status with connection details
        """
        status = {
            "redis_available": self.is_available,
            "connection_error": self._connection_error,
            "redis_url": self._get_redis_url()
        }
        
        if self.is_available:
            try:
                info = await self._redis_client.info()
                status.update({
                    "redis_version": info.get("redis_version"),
                    "used_memory_human": info.get("used_memory_human"),
                    "connected_clients": info.get("connected_clients")
                })
            except Exception as e:
                status["health_check_error"] = str(e)
                status["redis_available"] = False
        
        return status

    async def close(self):
        """Close Redis connection."""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None
            self._is_connected = False


# Global Redis manager instance
redis_manager = RedisManager()


@asynccontextmanager
async def get_redis_client():
    """
    Context manager for Redis client with automatic cleanup.
    
    Usage:
        async with get_redis_client() as redis:
            await redis.ping()
    """
    if not redis_manager.is_available:
        raise RuntimeError("Redis is not available")
    
    try:
        yield redis_manager.client
    except Exception as e:
        logger.error(f"Redis operation failed: {e}")
        raise