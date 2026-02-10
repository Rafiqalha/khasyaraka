"""
User Cache API Endpoints

FastAPI routes demonstrating Cache-Aside and Write-Behind patterns.
Uses dependency injection for database sessions and background tasks.

Routes:
- GET /users/{user_id}/profile - Get user profile (cached)
- POST /users/{user_id}/hearts/decrement - Decrement hearts (instant response)
- GET /users/{user_id}/levels/{level_id}/status - Get level status (cached)
- POST /users/{user_id}/levels/{level_id}/status - Update level status (write-behind)
"""

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional

from app.core.database import get_db
from app.core.response import success, error
from app.core.logging import get_logger
from app.services.user_service import (
    get_user_data,
    decrement_hearts,
    get_level_status,
    update_level_status,
    invalidate_user_cache,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/users", tags=["User Cache"])


# =====================================================
# SCHEMAS
# =====================================================

class HeartsDecrementRequest(BaseModel):
    """Request body for hearts decrement"""
    amount: int = Field(default=1, ge=1, le=5, description="Number of hearts to decrement")


class LevelStatusUpdateRequest(BaseModel):
    """Request body for level status update"""
    status: str = Field(..., pattern="^(locked|unlocked|completed|active)$")


class UserProfileResponse(BaseModel):
    """User profile data"""
    user_id: str
    total_xp: int
    streak: int
    hearts: int
    last_active_date: Optional[str] = None


class HeartsResponse(BaseModel):
    """Hearts update response"""
    user_id: str
    hearts: int
    max_hearts: int
    synced: bool


class LevelStatusResponse(BaseModel):
    """Level status response"""
    user_id: str
    level_id: str
    status: str
    synced: Optional[bool] = None


# =====================================================
# ENDPOINTS
# =====================================================

@router.get(
    "/{user_id}/profile",
    response_model=None,
    summary="Get User Profile (Cached)",
    description="""
    Fetch user profile with Cache-Aside pattern.
    
    **Performance:**
    - Redis Hit: ~5ms (instant)
    - Redis Miss: ~50-100ms (Postgres query + cache write)
    
    **Caching:**
    - TTL: 30 minutes
    - Background revalidation (SWR) at 50% TTL
    """,
)
async def get_user_profile(
    user_id: str,
    force_refresh: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Get user profile with caching"""
    try:
        user_data = await get_user_data(user_id, db, force_refresh=force_refresh)
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )
        
        # Remove internal cache metadata before returning
        user_data.pop("_cached_at", None)
        
        return success(
            data=user_data,
            message="User profile retrieved successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user profile"
        )


@router.post(
    "/{user_id}/hearts/decrement",
    response_model=None,
    summary="Decrement Hearts (Instant)",
    description="""
    Decrement user hearts with Write-Behind pattern.
    
    **Performance:**
    - Response: ~5ms (instant from Redis DECR)
    - DB Sync: Background task (user doesn't wait)
    
    **Race Condition Safety:**
    - Uses Redis DECR (atomic operation)
    - Multiple concurrent decrements are handled safely
    
    **Fallback:**
    - If Redis is down, falls back to direct DB update
    """,
)
async def decrement_user_hearts(
    user_id: str,
    request: HeartsDecrementRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Decrement hearts with instant response and background sync"""
    try:
        result = await decrement_hearts(
            user_id=user_id,
            db=db,
            background_tasks=background_tasks,
            amount=request.amount,
        )
        
        return success(
            data=result,
            message=f"Hearts decremented by {request.amount}"
        )
        
    except Exception as e:
        logger.error(f"Error decrementing hearts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrement hearts"
        )


@router.get(
    "/{user_id}/levels/{level_id}/status",
    response_model=None,
    summary="Get Level Status (Cached)",
    description="""
    Get level completion status with Cache-Aside pattern.
    
    **Returns:**
    - `locked`: Level not yet accessible
    - `unlocked`: Level accessible but not started
    - `active`: Level in progress
    - `completed`: Level completed
    """,
)
async def get_user_level_status(
    user_id: str,
    level_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get level status with caching"""
    try:
        status_value = await get_level_status(user_id, level_id, db)
        
        return success(
            data={
                "user_id": user_id,
                "level_id": level_id,
                "status": status_value,
            },
            message="Level status retrieved"
        )
        
    except Exception as e:
        logger.error(f"Error fetching level status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch level status"
        )


@router.post(
    "/{user_id}/levels/{level_id}/status",
    response_model=None,
    summary="Update Level Status (Write-Behind)",
    description="""
    Update level status with Write-Behind pattern.
    
    **Performance:**
    - Response: ~5ms (instant from Redis)
    - DB Sync: Background task (user doesn't wait)
    
    **Use Cases:**
    - Mark level as `unlocked` after completing previous level
    - Mark level as `completed` after finishing quiz
    """,
)
async def update_user_level_status(
    user_id: str,
    level_id: str,
    request: LevelStatusUpdateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Update level status with instant response and background sync"""
    try:
        result = await update_level_status(
            user_id=user_id,
            level_id=level_id,
            status=request.status,
            db=db,
            background_tasks=background_tasks,
        )
        
        return success(
            data=result,
            message=f"Level status updated to {request.status}"
        )
        
    except Exception as e:
        logger.error(f"Error updating level status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update level status"
        )


@router.post(
    "/{user_id}/cache/invalidate",
    response_model=None,
    summary="Invalidate User Cache",
    description="""
    Force invalidate all cached data for a user.
    
    **Use Cases:**
    - User logout (clear all data)
    - Force refresh after admin modification
    - Debug/troubleshooting
    """,
)
async def invalidate_cache(user_id: str):
    """Invalidate all cached data for user"""
    try:
        await invalidate_user_cache(user_id)
        
        return success(
            data={"user_id": user_id, "invalidated": True},
            message="Cache invalidated successfully"
        )
        
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to invalidate cache"
        )
