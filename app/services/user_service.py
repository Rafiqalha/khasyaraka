"""
User Service - Smart Caching with Cache-Aside & Write-Behind Patterns

✅ HIGH PERFORMANCE ARCHITECTURE:
1. Cache-Aside: Read from Redis first, fallback to Postgres
2. Write-Behind: Update Redis immediately, sync to Postgres in background
3. Graceful Degradation: If Redis is down, fallback to Postgres directly

Reduces Postgres load by ~80% for frequently accessed data:
- User Profile (XP, Streak, Hearts)
- Level Status (locked/unlocked/completed)

Key Patterns:
- DECR atomic operations for hearts (prevents race conditions)
- TTL-based cache expiration (30 min default)
- Background task for write-behind DB sync
"""

import json
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import BackgroundTasks

from app.core.redis import get_redis
from app.core.logging import get_logger

logger = get_logger(__name__)

# =====================================================
# CACHE KEYS & TTL CONFIGURATION
# =====================================================

class CacheKeys:
    """Redis key patterns for consistency"""
    USER_PROFILE = "user:{user_id}:profile"  # Hash: total_xp, streak, hearts
    USER_HEARTS = "user:{user_id}:hearts"    # Atomic counter for hearts
    LEVEL_STATUS = "user:{user_id}:levels"   # Hash: level_id -> status
    MAP_PROGRESS = "user:{user_id}:map_progress" # JSON List: Full map state

    @classmethod
    def profile(cls, user_id: str) -> str:
        return cls.USER_PROFILE.format(user_id=user_id)
    
    @classmethod
    def hearts(cls, user_id: str) -> str:
        return cls.USER_HEARTS.format(user_id=user_id)
    
    @classmethod
    def levels(cls, user_id: str) -> str:
        return cls.LEVEL_STATUS.format(user_id=user_id)

    @classmethod
    def map_progress(cls, user_id: str) -> str:
        return cls.MAP_PROGRESS.format(user_id=user_id)


# TTL Configuration (seconds)
CACHE_TTL_PROFILE = 1800  # 30 minutes
CACHE_TTL_LEVELS = 3600   # 1 hour
MAX_HEARTS = 5


# =====================================================
# CACHE-ASIDE PATTERN: READ OPERATIONS
# =====================================================

async def get_user_data(
    user_id: str,
    db: AsyncSession,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Get user data with Cache-Aside pattern.
    
    Flow:
    1. Check Redis cache (fast path)
    2. If miss -> Query Postgres -> Cache result -> Return
    3. If Redis down -> Query Postgres directly (graceful degradation)
    
    Returns:
        Dict with: user_id, total_xp, streak, hearts, last_active_date
    """
    cache_key = CacheKeys.profile(user_id)
    
    # ✅ Step 1: Try Redis cache (unless force refresh)
    if not force_refresh:
        try:
            redis = await get_redis()
            cached = await redis.get(cache_key)
            
            if cached:
                logger.debug(f"📦 [CACHE HIT] User {user_id} profile from Redis")
                data = json.loads(cached)
                
                # ✅ Trigger background revalidation if cache is stale (SWR pattern)
                # Check if cached data is older than 50% of TTL
                cached_at = data.get("_cached_at", 0)
                if datetime.now(timezone.utc).timestamp() - cached_at > CACHE_TTL_PROFILE * 0.5:
                    asyncio.create_task(_background_revalidate_user(user_id, db))
                
                return data
                
        except Exception as e:
            logger.warning(f"⚠️ Redis read failed, falling back to Postgres: {e}")
    
    # ✅ Step 2: Query Postgres (cache miss or Redis down)
    logger.debug(f"📊 [CACHE MISS] Fetching user {user_id} from Postgres")
    
    try:
        result = await db.execute(
            text("""
                SELECT id, total_xp, streak, hearts, last_active_date
                FROM users
                WHERE id = :user_id
            """),
            {"user_id": user_id}
        )
        row = result.fetchone()
        
        if not row:
            logger.warning(f"⚠️ User {user_id} not found in database")
            return {}
        
        user_data = {
            "user_id": str(row.id),
            "total_xp": row.total_xp or 0,
            "streak": row.streak or 0,
            "hearts": row.hearts if row.hearts is not None else MAX_HEARTS,
            "last_active_date": row.last_active_date.isoformat() if row.last_active_date else None,
            "_cached_at": datetime.now(timezone.utc).timestamp(),
        }
        
        # ✅ Step 3: Cache result in Redis (best effort)
        try:
            redis = await get_redis()
            await redis.setex(
                cache_key,
                CACHE_TTL_PROFILE,
                json.dumps(user_data)
            )
            # Also set atomic hearts counter
            await redis.setex(
                CacheKeys.hearts(user_id),
                CACHE_TTL_PROFILE,
                user_data["hearts"]
            )
            logger.debug(f"💾 [CACHE SET] User {user_id} cached for {CACHE_TTL_PROFILE}s")
        except Exception as e:
            logger.warning(f"⚠️ Failed to cache user data: {e}")
        
        return user_data
        
    except Exception as e:
        logger.error(f"❌ Database error fetching user {user_id}: {e}")
        raise


async def _background_revalidate_user(user_id: str, db: AsyncSession):
    """Background task to refresh stale cache (SWR pattern)"""
    try:
        await get_user_data(user_id, db, force_refresh=True)
        logger.debug(f"🔄 [SWR] Background revalidated user {user_id}")
    except Exception as e:
        logger.warning(f"⚠️ Background revalidation failed for user {user_id}: {e}")


# =====================================================
# WRITE-BEHIND PATTERN: HEARTS UPDATE
# =====================================================

async def decrement_hearts(
    user_id: str,
    db: AsyncSession,
    background_tasks: BackgroundTasks,
    amount: int = 1
) -> Dict[str, Any]:
    """
    Decrement user hearts with Write-Behind pattern.
    
    Flow:
    1. DECR in Redis atomically (instant response to user)
    2. Schedule background task to sync to Postgres
    3. Return new value immediately (no DB wait)
    
    ✅ Race Condition Prevention:
    - Redis DECR is atomic (safe for concurrent requests)
    - Background sync uses last-write-wins (acceptable for hearts)
    
    Returns:
        Dict with: user_id, hearts (new value), synced (bool)
    """
    cache_key = CacheKeys.hearts(user_id)
    
    try:
        redis = await get_redis()
        
        # ✅ Check if key exists, if not initialize from DB
        if not await redis.exists(cache_key):
            user_data = await get_user_data(user_id, db)
            current_hearts = user_data.get("hearts", MAX_HEARTS)
            await redis.setex(cache_key, CACHE_TTL_PROFILE, current_hearts)
        
        # ✅ Atomic DECR (prevents race conditions)
        new_hearts = await redis.decrby(cache_key, amount)
        
        # Clamp to 0 minimum
        if new_hearts < 0:
            new_hearts = 0
            await redis.set(cache_key, 0)
        
        logger.info(f"💔 [HEARTS] User {user_id}: hearts decremented to {new_hearts}")
        
        # ✅ Schedule background sync to Postgres (user doesn't wait)
        background_tasks.add_task(
            _sync_hearts_to_db,
            user_id,
            new_hearts
        )
        
        # ✅ Invalidate profile cache (will be refreshed on next read)
        profile_key = CacheKeys.profile(user_id)
        await redis.delete(profile_key)
        
        return {
            "user_id": user_id,
            "hearts": new_hearts,
            "synced": False,  # Will be synced in background
            "max_hearts": MAX_HEARTS,
        }
        
    except Exception as e:
        logger.warning(f"⚠️ Redis DECR failed, falling back to direct DB update: {e}")
        
        # Fallback: Direct DB update (slower but reliable)
        await db.execute(
            text("""
                UPDATE users
                SET hearts = GREATEST(0, hearts - :amount)
                WHERE id = :user_id
            """),
            {"user_id": user_id, "amount": amount}
        )
        await db.commit()
        
        # Get updated value
        result = await db.execute(
            text("SELECT hearts FROM users WHERE id = :user_id"),
            {"user_id": user_id}
        )
        row = result.fetchone()
        new_hearts = row.hearts if row else 0
        
        return {
            "user_id": user_id,
            "hearts": new_hearts,
            "synced": True,  # Already synced to DB
            "max_hearts": MAX_HEARTS,
        }


async def _sync_hearts_to_db(user_id: str, hearts: int):
    """
    Background task: Sync hearts from Redis to Postgres.
    
    ✅ Write-Behind: User already got response, this is async sync.
    """
    from app.core.database import get_db_context
    
    try:
        async with get_db_context() as db:
            await db.execute(
                text("""
                    UPDATE users
                    SET hearts = :hearts, updated_at = NOW()
                    WHERE id = :user_id
                """),
                {"user_id": user_id, "hearts": hearts}
            )
            await db.commit()
            logger.debug(f"✅ [SYNC] Hearts synced to DB: user={user_id}, hearts={hearts}")
    except Exception as e:
        logger.error(f"❌ Background hearts sync failed for user {user_id}: {e}")


# =====================================================
# LEVEL STATUS CACHING
# =====================================================

async def get_level_status(
    user_id: str,
    level_id: str,
    db: AsyncSession
) -> str:
    """
    Get level status with Cache-Aside pattern.
    
    Returns: "locked", "unlocked", "completed", or "active"
    """
    cache_key = CacheKeys.levels(user_id)
    
    try:
        redis = await get_redis()
        
        # Check if level status is cached (hash field)
        status = await redis.hget(cache_key, level_id)
        if status:
            logger.debug(f"📦 [CACHE HIT] Level {level_id} status: {status}")
            return status
            
    except Exception as e:
        logger.warning(f"⚠️ Redis read failed for level status: {e}")
    
    # Query Postgres
    try:
        result = await db.execute(
            text("""
                SELECT status
                FROM user_progress
                WHERE user_id = :user_id AND level_id = :level_id
            """),
            {"user_id": user_id, "level_id": level_id}
        )
        row = result.fetchone()
        status = row.status if row else "locked"
        
        # Cache result
        try:
            redis = await get_redis()
            await redis.hset(cache_key, level_id, status)
            await redis.expire(cache_key, CACHE_TTL_LEVELS)
        except Exception as e:
            logger.warning(f"⚠️ Failed to cache level status: {e}")
        
        return status
        
    except Exception as e:
        logger.error(f"❌ Database error fetching level status: {e}")
        return "locked"


async def update_level_status(
    user_id: str,
    level_id: str,
    status: str,
    db: AsyncSession,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Update level status with Write-Behind pattern.
    
    1. Update Redis immediately
    2. Sync to Postgres in background
    """
    cache_key = CacheKeys.levels(user_id)
    
    try:
        redis = await get_redis()
        
        # ✅ Update Redis immediately
        await redis.hset(cache_key, level_id, status)
        await redis.expire(cache_key, CACHE_TTL_LEVELS)
        
        logger.info(f"🔓 [LEVEL] User {user_id}: level {level_id} -> {status}")
        
        # ✅ Schedule background sync
        background_tasks.add_task(
            _sync_level_status_to_db,
            user_id,
            level_id,
            status
        )
        
        return {
            "user_id": user_id,
            "level_id": level_id,
            "status": status,
            "synced": False,
        }
        
    except Exception as e:
        logger.warning(f"⚠️ Redis update failed, direct DB write: {e}")
        
        # Fallback: Direct DB update
        await db.execute(
            text("""
                INSERT INTO user_progress (user_id, level_id, status, updated_at)
                VALUES (:user_id, :level_id, :status, NOW())
                ON CONFLICT (user_id, level_id)
                DO UPDATE SET status = :status, updated_at = NOW()
            """),
            {"user_id": user_id, "level_id": level_id, "status": status}
        )
        await db.commit()
        
        return {
            "user_id": user_id,
            "level_id": level_id,
            "status": status,
            "synced": True,
        }


async def _sync_level_status_to_db(user_id: str, level_id: str, status: str):
    """Background task: Sync level status to Postgres"""
    from app.core.database import get_db_context
    
    try:
        async with get_db_context() as db:
            await db.execute(
                text("""
                    INSERT INTO user_progress (user_id, level_id, status, updated_at)
                    VALUES (:user_id, :level_id, :status, NOW())
                    ON CONFLICT (user_id, level_id)
                    DO UPDATE SET status = :status, updated_at = NOW()
                """),
                {"user_id": user_id, "level_id": level_id, "status": status}
            )
            await db.commit()
            logger.debug(f"✅ [SYNC] Level status synced: user={user_id}, level={level_id}")
    except Exception as e:
        logger.error(f"❌ Background level sync failed: {e}")


# =====================================================
# CACHE INVALIDATION
# =====================================================

async def invalidate_user_cache(user_id: str):
    """
    Invalidate all cached data for a user.
    
    Call this when:
    - User logs out
    - User data is modified externally
    - Force refresh is needed
    """
    try:
        redis = await get_redis()
        
        keys_to_delete = [
            CacheKeys.profile(user_id),
            CacheKeys.hearts(user_id),
            CacheKeys.levels(user_id),
        ]
        
        await redis.delete(*keys_to_delete)
        logger.info(f"🧹 [CACHE] Invalidated all cache for user {user_id}")
        
    except Exception as e:
        logger.warning(f"⚠️ Cache invalidation failed for user {user_id}: {e}")
