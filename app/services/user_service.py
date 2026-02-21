"""
User Service - Smart Caching with Redis Hashes & Arq Write-Behind

✅ HIGH PERFORMANCE ARCHITECTURE (REFACTORED):
1. Single Source of Truth: Redis Hash `user:{id}` (hearts, xp, streak)
2. Atomic Operations: Lua scripts for concurrency safety
3. Reliable Write-Behind: Arq Queue (Redis-backed) for DB sync
4. No Auto-Regen: Hearts only via AdMob (strict)

Key Patterns:
- HINCRBY atomic operations
- Arq for reliability (retries on crash)
- Strict business logic (Max 5 hearts)
"""

import json
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

# =====================================================
# CACHE KEY PATTERNS & TTL CONSTANTS
# =====================================================

# TTL values (in seconds)
CACHE_TTL_LEVELS = 3600       # 1 hour for user-specific level progress
CACHE_TTL_STATIC = 86400      # 24 hours for static content (sections, paths)

class CacheKeys:
    """Centralized Redis cache key patterns for the application."""
    
    @staticmethod
    def training_sections() -> str:
        return "training:sections"
    
    @staticmethod
    def learning_path(section_id: str) -> str:
        return f"training:path:{section_id}"
    
    @staticmethod
    def levels(user_id: str) -> str:
        return f"user:{user_id}:levels"
    
    @staticmethod
    def map_progress(user_id: str) -> str:
        return f"user:{user_id}:map_progress"

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import BackgroundTasks, Request

from app.core.redis import get_redis
from app.core.logging import get_logger
from app.core.redis_service import RedisService

logger = get_logger(__name__)

# =====================================================
# CACHE KEYS & CONFIGURATION
# =====================================================

MAX_HEARTS = 5
CACHE_TTL_USER = None  # Persistent (User request: "Redis hearts state jangan pakai TTL")

# =====================================================
# CORE: READ OPERATIONS (Redis Hash)
# =====================================================

async def get_user_data(
    user_id: str,
    db: AsyncSession,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Get user data from Redis Hash (Single Source of Truth).
    Fallback to DB if missing.
    """
    try:
        # ✅ Step 1: Try Redis Hash
        if not force_refresh:
            user_data = await RedisService.get_user_data(user_id)
            if user_data:
                # Type conversion (Redis returns strings)
                return {
                    "user_id": user_id,
                    "hearts": int(user_data.get("hearts", MAX_HEARTS)),
                    "total_xp": int(user_data.get("total_xp", 0)),
                    "streak": int(user_data.get("streak", 0)),
                    "last_active_date": user_data.get("last_active_date"),
                }

        # ✅ Step 2: DB Fallback
        logger.debug(f"📊 [CACHE MISS] Fetching user {user_id} from DB")
        result = await db.execute(
            text("""
                SELECT id, total_xp, streak, COALESCE(hearts, :max) AS hearts, last_active_date
                FROM users WHERE id = :uid
            """),
            {"uid": int(user_id), "max": MAX_HEARTS}
        )
        row = result.fetchone()
        
        if not row:
            return {}

        data = {
            "hearts": row.hearts,
            "total_xp": row.total_xp or 0,
            "streak": row.streak or 0,
            "last_active_date": row.last_active_date.isoformat() if row.last_active_date else None
        }

        # ✅ Step 3: Populate Redis Hash
        await RedisService.set_user_data(user_id, data, ttl=CACHE_TTL_USER)
        data["user_id"] = str(row.id)
        return data

    except Exception as e:
        logger.error(f"❌ Error getting user data: {e}", exc_info=True)
        # Fallback to empty/default if critical failure
        return {"user_id": user_id, "hearts": MAX_HEARTS, "total_xp": 0}

# =====================================================
# CORE: WRITE OPERATIONS (Atomic + Queue)
# =====================================================

async def decrement_hearts(
    request: Request,
    user_id: str,
    amount: int = 1
) -> Dict[str, Any]:
    """
    Atomic decrement using Lua script + Arq Queue.
    """
    try:
        # ✅ 1. Atomic Decrement (Min 0) via RedisService
        # This uses the Lua script we defined
        new_hearts = await RedisService.atomic_decrement_hearts(user_id)
        
        logger.info(f"💔 [HEARTS] User {user_id}: {new_hearts + 1} -> {new_hearts}")

        # ✅ 2. Reliable Write-Behind (Arq)
        # We access the pool from app.state
        if hasattr(request.app.state, "arq_pool"):
            await request.app.state.arq_pool.enqueue_job(
                "sync_hearts_db",
                user_id=int(user_id),
                hearts=new_hearts
            )
        else:
            logger.error("🚨 Arq pool not available! Data might be lost if server crashes.")
            # Fallback could go here, but we rely on Arq for now

        return {
            "user_id": user_id,
            "hearts": new_hearts,
            "max": MAX_HEARTS
        }

    except Exception as e:
        logger.error(f"❌ Decrement failed: {e}")
        raise

async def increment_hearts(
    request: Request,
    user_id: str,
    amount: int = 1
) -> Dict[str, Any]:
    """
    Atomic increment (Max 5) - Strictly for AdMob rewards.
    """
    try:
        # ✅ 1. Atomic Increment (Max 5)
        new_hearts = await RedisService.atomic_add_heart(user_id)
        
        logger.info(f"💚 [HEARTS] User {user_id}: Reward! -> {new_hearts}")

        # ✅ 2. Enqueue Job
        if hasattr(request.app.state, "arq_pool"):
            await request.app.state.arq_pool.enqueue_job(
                "sync_hearts_db",
                user_id=int(user_id),
                hearts=new_hearts
            )

        return {
            "user_id": user_id,
            "hearts": new_hearts,
            "max": MAX_HEARTS
        }

    except Exception as e:
        logger.error(f"❌ Increment failed: {e}")
        raise


async def sync_hearts_db(ctx, user_id: int, hearts: int):
    """
    Background task: Sync hearts from Redis to Postgres.
    
    ✅ Write-Behind: User already got response, this is async sync.
    ARQ JOB: Requires ctx as first argument.
    """
    from app.core.database import get_db_context
    
    try:
        async with get_db_context() as db:
            await db.execute(
                text("""
                    UPDATE users
                    SET hearts = GREATEST(0, :hearts)
                    WHERE id = :user_id
                """),
                {"user_id": int(user_id), "hearts": hearts}
            )
            await db.commit()
            logger.debug(f"✅ [SYNC] Hearts synced to DB: user={user_id}, hearts={hearts}")
    except Exception as e:
        logger.error(f"❌ Background hearts sync failed for user {user_id}: {e}", exc_info=True)


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
    """
    # ... logic using RedisService or get_redis directly ...
    # For now, simplistic implementation to restore functionality
    try:
        result = await db.execute(
            text("SELECT status FROM user_progress WHERE user_id = :uid AND level_id = :lid"),
            {"uid": int(user_id), "lid": level_id}
        )
        row = result.fetchone()
        return row.status if row else "locked"
    except Exception:
        return "locked"

async def update_level_status(
    user_id: str,
    level_id: str,
    status: str,
    db: AsyncSession,
    background_tasks: BackgroundTasks = None
) -> Dict[str, Any]:
    """
    Update level status (Simpler version for now)
    """
    # Direct DB update for safety until full restore
    await db.execute(
        text("""
            INSERT INTO user_progress (user_id, level_id, status, updated_at)
            VALUES (:uid, :lid, :stat, NOW())
            ON CONFLICT (user_id, level_id) DO UPDATE SET status = :stat, updated_at = NOW()
        """),
        {"uid": int(user_id), "lid": level_id, "stat": status}
    )
    await db.commit()
    return {"status": status}

async def invalidate_user_cache(user_id: str):
    """Invalidate cache"""
    try:
        redis = await get_redis()
        await redis.delete(f"user:{user_id}:profile", f"user:{user_id}:hearts")
    except Exception:
        pass
