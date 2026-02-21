"""
Subscription Tier Cache

Redis-backed cache for effective subscription tier lookups.
Eliminates DB query on every permission check.

Architecture:
    require_tier() → Redis GET → hit? return tier : DB query → Redis SET (60s TTL)
    upgrade/renew → Redis DEL (instant invalidation)

Key format: sub:tier:{user_id}
Value format: JSON {"tier": "pro", "sub_id": 42}
TTL: 60 seconds

Safety guarantees:
- Cache miss → always falls back to DB (never blocks)
- Redis down → graceful degradation to DB-only (no errors)
- Mutations → instant invalidation (no stale reads after upgrade/renew)
"""

import json
from typing import Optional
from app.core.logging import get_logger

logger = get_logger(__name__)

CACHE_TTL_SECONDS = 60
CACHE_PREFIX = "sub:tier:"


def _cache_key(user_id: int) -> str:
    return f"{CACHE_PREFIX}{user_id}"


async def get_cached_tier(user_id: int) -> Optional[dict]:
    """
    Get cached tier from Redis.
    Returns {"tier": str, "sub_id": int|None} or None on miss.
    Never raises — returns None on any Redis error.
    """
    try:
        from app.core.redis import get_redis
        redis_client = await get_redis()
        raw = await redis_client.get(_cache_key(user_id))
        if raw:
            data = json.loads(raw)
            logger.debug(f"⚡ [TIER_CACHE] HIT user={user_id} tier={data.get('tier')}")
            return data
        return None
    except Exception as e:
        logger.warning(f"⚠️ [TIER_CACHE] Redis read error (graceful fallback): {e}")
        return None


async def set_cached_tier(user_id: int, tier: str, sub_id: int | None = None):
    """
    Cache a tier lookup result in Redis with TTL.
    Never raises — silently fails on Redis error.
    """
    try:
        from app.core.redis import get_redis
        redis_client = await get_redis()
        payload = json.dumps({"tier": tier, "sub_id": sub_id})
        await redis_client.set(_cache_key(user_id), payload, ex=CACHE_TTL_SECONDS)
        logger.debug(f"📝 [TIER_CACHE] SET user={user_id} tier={tier} TTL={CACHE_TTL_SECONDS}s")
    except Exception as e:
        logger.warning(f"⚠️ [TIER_CACHE] Redis write error (non-critical): {e}")


async def invalidate_cached_tier(user_id: int):
    """
    Instantly invalidate a user's cached tier.
    Called on upgrade, renew, or any subscription mutation.
    Never raises — silently fails on Redis error.
    """
    try:
        from app.core.redis import get_redis
        redis_client = await get_redis()
        await redis_client.delete(_cache_key(user_id))
        logger.info(f"🗑️ [TIER_CACHE] INVALIDATED user={user_id}")
    except Exception as e:
        logger.warning(f"⚠️ [TIER_CACHE] Redis delete error (non-critical): {e}")
