"""
Admin Module Router

Protected endpoints for administrative operations.
⚠️ DANGER ZONE: These endpoints can destroy data.
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import os

from app.db.session import get_db
from app.core.redis import get_redis
from app.core.response import success
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

# Secret key for admin operations (set in environment)
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "your-super-secret-key-change-in-production")


def verify_admin_key(x_admin_key: str = Header(..., description="Admin secret key for protected operations")):
    """Verify admin secret key from header"""
    if x_admin_key != ADMIN_SECRET_KEY:
        logger.warning(f"❌ [ADMIN] Invalid admin key attempted")
        raise HTTPException(status_code=403, detail="Invalid admin key")
    return True


@router.post("/reset-world")
async def reset_world(
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """
    ⚠️ DANGER: Reset all user data.
    
    Deletes in FK-safe order:
    1. user_progress (training)
    2. user_solved_challenges, cyber_level_progress, encryption_logs (cyber)
    3. sku_progress (sku)
    4. survival_mastery (survival)
    5. users
    
    Requires X-Admin-Key header with valid secret.
    """
    logger.warning("🔥 [ADMIN] reset-world endpoint called - DELETING ALL USER DATA")
    
    deleted_counts = {}
    
    # Tables to delete in FK-safe order (children before parents)
    # Format: (table_name, has_user_fk)
    tables_to_clear = [
        # Training module
        "user_progress",
        # Cyber module (user-related)
        "user_solved_challenges",
        "cyber_level_progress", 
        "encryption_logs",
        # SKU module
        "sku_progress",
        # Survival module
        "survival_mastery",
        # Finally: users
        "users",
    ]
    
    try:
        for table in tables_to_clear:
            try:
                result = await db.execute(text(f"DELETE FROM {table}"))
                deleted_counts[table] = result.rowcount
                logger.info(f"🗑️ [ADMIN] Deleted {result.rowcount} records from {table}")
            except Exception as table_error:
                # Table might not exist, log and continue
                logger.warning(f"⚠️ [ADMIN] Could not delete from {table}: {table_error}")
                deleted_counts[table] = f"error: {str(table_error)[:50]}"
        
        # Commit PostgreSQL changes
        await db.commit()
        logger.info("✅ [ADMIN] PostgreSQL commit successful")
        
        # Flush Redis cache
        deleted_keys = 0
        try:
            redis = await get_redis()
            
            # Delete user-related keys
            cursor = 0
            while True:
                cursor, keys = await redis.scan(cursor, match="user:*", count=100)
                if keys:
                    await redis.delete(*keys)
                    deleted_keys += len(keys)
                if cursor == 0:
                    break
            
            # Also delete leaderboard
            await redis.delete("leaderboard:global")
            deleted_keys += 1
            
            logger.info(f"🗑️ [ADMIN] Deleted {deleted_keys} Redis keys")
            
        except Exception as redis_error:
            logger.warning(f"⚠️ [ADMIN] Redis flush failed: {redis_error}")
        
        logger.warning("🔥 [ADMIN] World reset complete!")
        
        return success(
            data={
                "postgres": deleted_counts,
                "redis_keys_deleted": deleted_keys,
            },
            message="🔥 World reset complete. All user data purged."
        )
        
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ [ADMIN] Reset failed: {e}")
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")


@router.post("/reset-progress/{user_id}")
async def reset_user_progress(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """
    Reset a single user's training progress.
    
    GLOBAL LINEAR PROGRESSION:
    1. Delete ALL user_progress records for this user
    2. Find the FIRST level globally (Section order=1, Unit order=1, Level number=1)
    3. Create UNLOCKED record for that level only
    4. Invalidate Redis cache
    """
    logger.info(f"🔄 [ADMIN] Resetting progress for user {user_id}")
    
    try:
        # Step 1: Delete all progress for user
        result = await db.execute(
            text("DELETE FROM user_progress WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        deleted_count = result.rowcount
        logger.info(f"🗑️ [ADMIN] Deleted {deleted_count} progress records for user {user_id}")
        
        # Step 2: Find first level globally (Section 1, Unit 1, Level 1)
        first_level_query = text("""
            SELECT tl.id 
            FROM training_levels tl
            JOIN training_units tu ON tl.unit_id = tu.id
            JOIN training_sections ts ON tu.section_id = ts.id
            WHERE ts.is_active = true 
              AND tu.is_active = true 
              AND tl.is_active = true
            ORDER BY ts.order ASC, tu.order ASC, tl.level_number ASC
            LIMIT 1
        """)
        first_level_result = await db.execute(first_level_query)
        first_level_row = first_level_result.fetchone()
        
        first_level_id = None
        if first_level_row:
            first_level_id = first_level_row[0]
            
            # Step 3: Create UNLOCKED record for first level
            # Include ALL NOT NULL fields
            await db.execute(
                text("""
                    INSERT INTO user_progress 
                        (user_id, level_id, status, score, total_questions, correct_answers, 
                         xp_earned, time_spent_seconds, completed_at, created_at, updated_at)
                    VALUES 
                        (:user_id, :level_id, 'UNLOCKED', 0, 0, 0, 0, 0, NULL, NOW(), NOW())
                """),
                {"user_id": user_id, "level_id": first_level_id}
            )
            logger.info(f"🔓 [ADMIN] Unlocked first level {first_level_id} for user {user_id}")
        
        await db.commit()
        
        # Step 4: Invalidate Redis cache
        try:
            redis = await get_redis()
            await redis.delete(f"user:{user_id}:map_progress")
            await redis.delete(f"user:{user_id}:levels")
            await redis.delete(f"user:{user_id}:profile")
            logger.info(f"🗑️ [ADMIN] Invalidated cache for user {user_id}")
        except Exception as redis_error:
            logger.warning(f"⚠️ [ADMIN] Redis cache invalidation failed: {redis_error}")
        
        return success(
            data={
                "user_id": user_id,
                "deleted_records": deleted_count,
                "first_level_unlocked": first_level_id,
            },
            message=f"Progress reset! User {user_id} starts fresh with level {first_level_id}"
        )
        
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ [ADMIN] Reset progress failed: {e}")
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")


@router.get("/health")
async def admin_health():
    """Health check for admin module"""
    return success(
        data={"status": "ok", "module": "admin"},
        message="Admin module is healthy"
    )
