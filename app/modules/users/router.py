"""
Users Module Router

API endpoints for user operations.
"""

from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime, date

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.response import success
from app.modules.auth.repository import AuthRepository

router = APIRouter(prefix="/users", tags=["Users"])


class UpdateUserStatsRequest(BaseModel):
    """Request model for updating user stats (streak and last_active_date only)"""
    streak: int = 0
    last_active_date: date | None = None  # Optional: if not provided, use current date
    # NOTE: total_xp is NOT updated through this endpoint
    # XP is ONLY updated through POST /training/progress/submit (single source of truth)


@router.get("/me")
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current authenticated user information including stats.
    
    Args:
        current_user: JWT payload from get_current_user dependency
        db: Database session
    
    Returns:
        Standard API response with user data including total_xp, streak, and last_active_date
    """
    user_id = int(current_user.get("sub"))
    repository = AuthRepository(db)
    user = await repository.get_user_by_id(user_id)
    
    if not user:
        from app.core.errors import AppException
        raise AppException(
            message="User not found",
            error_code="USER_NOT_FOUND",
            status_code=404
        )
    
    return success(
        data={
            "id": user.id,
            "name": user.full_name,
            "username": user.email,  # Using email as username for now
            "is_pro": False,
            "gugus_depan": None,  # TODO: Add gugus_depan field to User model
            "total_xp": user.total_xp or 0,  # Include total_xp from database
            "streak": user.streak or 0,  # Include streak from database
            "last_active_date": user.last_active_date.isoformat() if user.last_active_date else None,  # Include last_active_date
        },
        message="User information retrieved successfully"
    )


@router.put("/me/stats")
async def update_user_stats(
    request: UpdateUserStatsRequest = Body(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user's stats (streak and last_active_date ONLY).
    
    **IMPORTANT:** XP is NOT updated through this endpoint.
    XP is ONLY updated through POST /training/progress/submit (single source of truth).
    
    This endpoint is used for:
    - Updating daily streak
    - Updating last_active_date
    
    Args:
        request: UpdateUserStatsRequest with streak and optional last_active_date
        current_user: JWT payload from get_current_user dependency
        db: Database session
    
    Returns:
        Standard API response with updated user stats (including current total_xp from DB)
    """
    user_id = int(current_user.get("sub"))
    repository = AuthRepository(db)
    user = await repository.get_user_by_id(user_id)
    
    if not user:
        from app.core.errors import AppException
        raise AppException(
            message="User not found",
            error_code="USER_NOT_FOUND",
            status_code=404
        )
    
    # ✅ Update ONLY streak and last_active_date (NOT total_xp)
    user.streak = request.streak
    
    # Update last_active_date: use provided date or current date
    if request.last_active_date:
        user.last_active_date = request.last_active_date
    else:
        user.last_active_date = date.today()
    
    await db.commit()
    await db.refresh(user)
    
    # ✅ Update Redis leaderboard with CURRENT total_xp (not from request)
    # This ensures Redis stays in sync with PostgreSQL
    try:
        from app.modules.gamification.service import LeaderboardService
        leaderboard_service = LeaderboardService(db)
        await leaderboard_service.update_user_score(
            user_id=str(user_id),
            total_xp=user.total_xp or 0  # ✅ Use current total_xp from DB
        )
    except Exception as e:
        # Don't fail the request if Redis update fails
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        logger.warning(f"⚠️ Failed to update Redis leaderboard: {e}")
    
    return success(
        data={
            "id": user.id,
            "total_xp": user.total_xp,  # ✅ Return current total_xp from DB (not updated)
            "streak": user.streak,
            "last_active_date": user.last_active_date.isoformat() if user.last_active_date else None,
        },
        message="User stats updated successfully"
    )
