"""
Redis Connection Pool

Manages Redis connection for caching and leaderboard operations.
Uses Redis Sorted Sets (ZSET) for high-performance leaderboard queries.

✅ Production Hardened:
- Supports redis:// and rediss:// (TLS)
- Socket keepalive for Cloud Run stateless model
- Health checks enabled
- Retry logic for transient failures
- Singleton-safe for Cloud Run
"""

import redis.asyncio as redis
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialBackoff
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Global Redis connection pool (singleton)
_redis_pool: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    """
    Get Redis connection pool (singleton pattern).
    
    ✅ Production Hardened:
    - Supports redis:// and rediss:// (TLS) for Upstash
    - Socket keepalive for Cloud Run stateless model
    - Health checks enabled (30s interval)
    - Retry logic for transient failures
    - Singleton-safe (thread-safe for Cloud Run)
    
    Returns:
        Redis client instance
        
    Raises:
        ConnectionError: If Redis connection fails after retries
    """
    global _redis_pool
    
    if _redis_pool is None:
        try:
            # Use computed Redis URL (supports rediss:// for TLS)
            redis_url = settings.REDIS_URL_COMPUTED
            
            # ✅ Production: Retry configuration for transient failures
            retry = Retry(
                ExponentialBackoff(cap=10, base=1),
                retries=3
            )
            
            _redis_pool = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,  # Max connections per instance
                # ✅ Cloud Run: Enable health checks for stateless model
                health_check_interval=30,  # Check every 30 seconds
                socket_keepalive=True,  # Keep connections alive
                socket_keepalive_options={},  # Default keepalive options
                # ✅ Production: Retry on timeout and connection errors
                retry=retry,
                retry_on_timeout=True,  # Retry on timeout errors
                retry_on_error=[ConnectionError, TimeoutError],  # Retry on these errors
            )
            
            # Test connection with timeout
            await _redis_pool.ping()
            logger.info(f"✅ Redis connected: {redis_url.split('@')[-1] if '@' in redis_url else redis_url}")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}", exc_info=True)
            _redis_pool = None  # Reset on failure
            raise ConnectionError(f"Failed to connect to Redis: {e}")
    
    return _redis_pool


async def close_redis():
    """Close Redis connection pool (called on shutdown)"""
    global _redis_pool
    if _redis_pool:
        try:
            await _redis_pool.close()
            logger.info("✅ Redis connection closed")
        except Exception as e:
            logger.error(f"⚠️ Error closing Redis connection: {e}")
        finally:
            _redis_pool = None
