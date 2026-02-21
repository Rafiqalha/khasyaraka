"""
Users Module Router

API endpoints for user operations.
"""

from fastapi import APIRouter, Depends, Body, UploadFile, File
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
import os
import uuid
from sqlalchemy import select

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.response import success
from app.core.logging import get_logger
from app.modules.auth.repository import AuthRepository
from app.services.user_service import get_user_data as get_cached_user_data

logger = get_logger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])

from app.modules.users.schemas import PublicUserResponse
from app.modules.tkk.models import UserTKK


class UpdateUserStatsRequest(BaseModel):
    """Request model for updating user stats (streak and last_active_date only)"""
    streak: int = 0
    last_active_date: date | None = None  # Optional: if not provided, use current date
    # NOTE: total_xp is NOT updated through this endpoint
    # XP is ONLY updated through POST /training/progress/submit (single source of truth)


class UpdateProfileRequest(BaseModel):
    """Request model for updating user profile (display name)"""
    full_name: Optional[str] = None


async def _invalidate_profile_cache(user_id: int):
    """Invalidate Redis profile cache so leaderboard shows fresh data"""
    try:
        from app.core.redis import get_redis
        redis = await get_redis()
        cache_key = f"user:profile:{user_id}"
        await redis.delete(cache_key)
        logger.info(f"🧹 [PROFILE] Invalidated Redis cache for user {user_id}")
    except Exception as e:
        logger.warning(f"⚠️ [PROFILE] Failed to invalidate Redis cache: {e}")


@router.get("/me/avatar/{filename}")
async def get_avatar(filename: str):
    """Redirect to ImageKit CDN URL for backward compatibility.
    
    Old avatars stored as /api/v1/users/me/avatar/<filename> will 
    redirect to ImageKit CDN. If CDN is not configured or the file
    doesn't exist on CDN, returns 404.
    """
    from app.core.config import settings
    if settings.IMAGEKIT_URL_ENDPOINT:
        # Redirect to ImageKit CDN
        cdn_url = f"{settings.IMAGEKIT_URL_ENDPOINT}/avatars/{filename}"
        logger.info(f"🔄 [AVATAR] Redirecting {filename} -> {cdn_url}")
        return RedirectResponse(url=cdn_url, status_code=302)
    
    logger.warning(f"⚠️ [AVATAR] CDN not configured, cannot serve avatar: {filename}")
    from app.core.errors import AppException
    raise AppException(
        message="Avatar not found — CDN not configured",
        error_code="AVATAR_NOT_FOUND",
        status_code=404
    )


@router.patch("/me/profile")
async def update_profile(
    request_body: UpdateProfileRequest = Body(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user's display profile (name).
    Invalidates Redis profile cache so leaderboard reflects changes immediately.
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

    if request_body.full_name is not None:
        user.full_name = request_body.full_name.strip()

    await db.commit()
    await db.refresh(user)

    # Invalidate Redis profile cache
    await _invalidate_profile_cache(user_id)

    return success(
        data={
            "id": user.id,
            "name": user.full_name,
            "picture_url": user.picture_url,
        },
        message="Profile updated successfully"
    )


@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a new profile avatar to ImageKit CDN.
    Stores permanent CDN URL in DB, invalidates Redis cache.
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

    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed_types:
        from app.core.errors import AppException
        raise AppException(
            message=f"Invalid file type: {file.content_type}. Allowed: JPEG, PNG, WebP",
            error_code="INVALID_FILE_TYPE",
            status_code=400
        )

    # Read file contents
    contents = await file.read()
    ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
    filename = f"{user_id}_{uuid.uuid4().hex[:8]}.{ext}"

    # Upload to ImageKit CDN
    from app.core.imagekit_service import upload_avatar as ik_upload
    
    # Extract old ImageKit file_id if stored
    old_file_id = None
    if user.picture_url and "imagekit.io" in (user.picture_url or ""):
        # We don't store file_id separately, so skip deletion for now
        pass

    result = await ik_upload(
        file_bytes=contents,
        filename=filename,
        user_id=user_id,
        old_file_id=old_file_id,
    )

    # Store full ImageKit CDN URL in DB (permanent, survives deploys)
    user.picture_url = result["url"]

    await db.commit()
    await db.refresh(user)

    # Invalidate Redis profile cache
    await _invalidate_profile_cache(user_id)

    logger.info(f"✅ [AVATAR] Uploaded to ImageKit for user {user_id}: {result['url']}")

    return success(
        data={
            "id": user.id,
            "picture_url": user.picture_url,
        },
        message="Avatar uploaded successfully"
    )

@router.get("/{user_id}/public", response_model=dict)
async def get_public_profile(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get public read-only profile for any user.
    Does not require authentication. Never returns sensitive data.
    """
    repository = AuthRepository(db)
    user = await repository.get_user_by_id(user_id)
    
    if not user or not user.is_active:
        from app.core.errors import AppException
        raise AppException(
            message="User not found or inactive",
            error_code="USER_NOT_FOUND",
            status_code=404
        )
        
    # Fetch TKK badges for the user
    tkk_query = await db.execute(
        select(UserTKK.tkk_slug)
        .where(UserTKK.user_id == user_id)
    )
    tkk_badges = [row[0] for row in tkk_query.fetchall()]
    
    response_data = PublicUserResponse(
        id=user.id,
        full_name=user.full_name,
        picture_url=user.picture_url,
        total_xp=user.total_xp or 0,
        streak=user.streak or 0,
        hack_level=user.hack_level or "Script Kiddie",
        tkk_badges=tkk_badges
    )
    
    return success(
        data=response_data.model_dump(),
        message="Public profile fetched successfully"
    )


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
    
    # ✅ Read hearts from Redis (Source of Truth) — same source AdMob SSV writes to
    # Falls back to PostgreSQL if Redis has no data
    try:
        cached_data = await get_cached_user_data(str(user_id), db)
        hearts_value = cached_data.get("hearts", user.hearts if user.hearts is not None else 5)
    except Exception as e:
        logger.warning(f"⚠️ [USERS/ME] Failed to get hearts from Redis: {e}")
        hearts_value = user.hearts if user.hearts is not None else 5

    return success(
        data={
            "id": user.id,
            "name": user.full_name,
            "username": user.email,  # Using email as username for now
            "picture_url": user.picture_url,
            "is_pro": False,
            "gugus_depan": None,  # TODO: Add gugus_depan field to User model
            "total_xp": user.total_xp or 0,  # Include total_xp from database
            "streak": user.streak or 0,  # Include streak from database
            "longest_streak": user.longest_streak or 0,
            "hearts": hearts_value,
            "max_hearts": 5,
            "last_active_date": user.last_active_date.isoformat() if user.last_active_date else None,
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
