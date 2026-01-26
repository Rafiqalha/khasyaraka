"""
Leaderboard Router

API endpoints for leaderboard operations.
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.db.session import get_db
from app.core.security import get_current_user, get_current_user_optional
from app.core.response import success
from app.modules.gamification.service import LeaderboardService
from app.modules.gamification.schemas import LeaderboardResponse
from app.modules.users.models import User
from app.core.logging import get_logger

logger = get_logger(__name__)

# Import LEADERBOARD_KEY from service
from app.modules.gamification.service import LEADERBOARD_KEY

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])


def get_service(db: AsyncSession = Depends(get_db)) -> LeaderboardService:
    """Dependency for LeaderboardService"""
    return LeaderboardService(db=db)


@router.get(
    "",
    summary="Get leaderboard",
    description="Get top users leaderboard with optional current user rank. Uses Redis for fast queries, falls back to PostgreSQL if Redis unavailable."
)
async def get_leaderboard(
    request: Request,
    limit: int = Query(50, ge=1, le=100, description="Number of top users to return"),
    service: LeaderboardService = Depends(get_service)
):
    """
    Get leaderboard with top users.
    
    **ARCHITECTURE:**
    - Primary: Redis ZSET (fast)
    - Fallback: PostgreSQL (if Redis empty/error)
    - PostgreSQL is SINGLE SOURCE OF TRUTH for users.total_xp
    
    **AUTHENTICATION:**
    - Optional: Works with or without JWT token
    - If authenticated: Returns my_rank
    - If not authenticated: Returns top_users only (no my_rank)
    
    Args:
        request: FastAPI Request object to get optional auth
        limit: Number of top users to return (default 50, max 100)
        
    Returns:
        LeaderboardResponse with top_users and my_rank (if authenticated)
    """
    # ✅ CRITICAL DEBUG: Log request path and auth header
    logger.info(f"🔍 [LEADERBOARD_ENDPOINT] Request path: {request.url.path}")
    
    authorization = request.headers.get("Authorization")
    has_auth = authorization is not None and authorization.startswith("Bearer ")
    logger.info(f"🔍 [LEADERBOARD_ENDPOINT] Authorization header present: {has_auth}")
    
    # ✅ CRITICAL FIX: Use optional auth instead of required auth
    # This allows endpoint to work with or without token
    current_user = get_current_user_optional(request)
    
    current_user_id = None
    if current_user:
        current_user_id = str(current_user.get("sub"))
        logger.info(f"✅ [LEADERBOARD_ENDPOINT] Authenticated user_id: {current_user_id}")
    else:
        logger.info("⚠️ [LEADERBOARD_ENDPOINT] No authenticated user (endpoint works without auth)")
    
    # ✅ CRITICAL DEBUG: Log before calling service
    logger.info(f"🔍 [LEADERBOARD_ENDPOINT] Calling service.get_leaderboard(limit={limit}, current_user_id={current_user_id})")
    
    leaderboard = await service.get_leaderboard(
        limit=limit,
        current_user_id=current_user_id
    )
    
    # ✅ CRITICAL DEBUG: Log response before returning
    logger.info(f"🔍 [LEADERBOARD_ENDPOINT] Service returned: top_users={len(leaderboard.top_users)}, my_rank={'present' if leaderboard.my_rank else 'null'}")
    
    if leaderboard.top_users:
        logger.info(f"   First user: {leaderboard.top_users[0].name} - {leaderboard.top_users[0].xp} XP (rank #{leaderboard.top_users[0].rank})")
    else:
        logger.warning("⚠️ [LEADERBOARD_ENDPOINT] WARNING: top_users is empty!")
    
    if leaderboard.my_rank:
        logger.info(f"   My rank: rank={leaderboard.my_rank.rank}, xp={leaderboard.my_rank.xp}")
    else:
        logger.warning("⚠️ [LEADERBOARD_ENDPOINT] WARNING: my_rank is null!")
    
    return success(
        data=leaderboard.dict(),
        message="Leaderboard retrieved successfully"
    )


@router.post(
    "/rebuild",
    summary="Rebuild leaderboard",
    description="Rebuild Redis leaderboard from PostgreSQL (admin/utility endpoint). Useful after Redis restart or data migration."
)
async def rebuild_leaderboard(
    current_user: dict = Depends(get_current_user),  # Require authentication
    service: LeaderboardService = Depends(get_service)
):
    """
    Rebuild Redis leaderboard from PostgreSQL (source of truth).
    
    **USE CASES:**
    - After Redis restart
    - After data migration
    - Manual admin trigger
    
    **SECURITY:** Requires authentication (admin-only in production)
    
    Returns:
        Number of users added to Redis
    """
    count = await service.rebuild_leaderboard()
    
    return success(
        data={"users_count": count},
        message=f"Leaderboard rebuilt successfully: {count} users"
    )


@router.get(
    "/debug/full",
    summary="Full debug leaderboard state",
    description="Comprehensive debug endpoint showing ALL system state. TEMPORARY - Remove in production."
)
async def debug_leaderboard_full(
    request: Request,
    service: LeaderboardService = Depends(get_service)
):
    """
    Full debug endpoint showing ALL system state.
    
    **TEMPORARY:** Remove this endpoint in production.
    
    Returns:
        Complete system state including:
        - Auth state
        - PostgreSQL stats
        - Redis state
        - My rank calculation
        - Final response
    """
    # ✅ SECURITY: Disable debug endpoint in production
    from app.core.config import settings
    if settings.ENVIRONMENT == "production":
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debug endpoint not available in production"
        )
    
    from app.modules.users.models import User
    from sqlalchemy import select, func
    from app.core.redis import get_redis
    
    debug_info = {
        "auth": {},
        "postgresql": {},
        "redis": {},
        "my_rank": {},
        "final_response": {}
    }
    
    # ✅ AUTH STATE
    authorization = request.headers.get("Authorization")
    has_auth = authorization is not None and authorization.startswith("Bearer ")
    
    current_user = get_current_user_optional(request)
    user_id = None
    user_found = False
    
    if current_user:
        user_id = str(current_user.get("sub"))
        # Check if user exists in DB
        try:
            stmt = select(User).where(User.id == int(user_id))
            result = await service.db.execute(stmt)
            user_obj = result.scalar_one_or_none()
            user_found = user_obj is not None
        except Exception as e:
            logger.error(f"Error checking user: {e}")
    
    debug_info["auth"] = {
        "token_present": has_auth,
        "user_id": user_id,
        "user_found": user_found,
        "current_user_payload": current_user if current_user else None
    }
    
    # ✅ POSTGRESQL STATE
    try:
        # Total users
        total_users_stmt = select(func.count(User.id))
        total_users_result = await service.db.execute(total_users_stmt)
        total_users = total_users_result.scalar() or 0
        
        # Users with XP
        users_with_xp_stmt = select(func.count(User.id)).where(User.total_xp > 0)
        users_with_xp_result = await service.db.execute(users_with_xp_stmt)
        users_with_xp = users_with_xp_result.scalar() or 0
        
        # Top 10 users raw
        top_users_stmt = (
            select(User)
            .where(User.total_xp > 0)
            .order_by(User.total_xp.desc())
            .limit(10)
        )
        top_users_result = await service.db.execute(top_users_stmt)
        top_users_raw = top_users_result.scalars().all()
        
        debug_info["postgresql"] = {
            "total_users": total_users,
            "users_with_xp": users_with_xp,
            "top_users_raw": [
                {
                    "id": user.id,
                    "name": user.full_name or "Unknown",
                    "total_xp": user.total_xp or 0
                }
                for user in top_users_raw
            ]
        }
        
        # Current user's PostgreSQL state
        if user_id:
            stmt = select(User).where(User.id == int(user_id))
            result = await service.db.execute(stmt)
            current_user_obj = result.scalar_one_or_none()
            
            if current_user_obj:
                stmt = select(func.count(User.id)).where(User.total_xp > (current_user_obj.total_xp or 0))
                result = await service.db.execute(stmt)
                rank_count = result.scalar() or 0
                
                debug_info["postgresql"]["current_user"] = {
                    "user_id": user_id,
                    "total_xp": current_user_obj.total_xp or 0,
                    "rank": rank_count + 1
                }
            else:
                debug_info["postgresql"]["current_user"] = {"error": "User not found"}
    except Exception as e:
        debug_info["postgresql"] = {"error": str(e)}
        import traceback
        logger.error(f"PostgreSQL debug error: {traceback.format_exc()}")
    
    # ✅ REDIS STATE
    try:
        redis_client = await get_redis()
        
        # Get all entries
        all_entries = await redis_client.zrevrange(
            LEADERBOARD_KEY,
            0,
            -1,
            withscores=True
        )
        
        zcard = await redis_client.zcard(LEADERBOARD_KEY)
        
        debug_info["redis"] = {
            "key": LEADERBOARD_KEY,
            "zcard": zcard,
            "entries": [
                {
                    "user_id": entry[0],
                    "xp": int(entry[1]),
                    "rank": idx + 1
                }
                for idx, entry in enumerate(all_entries)
            ]
        }
        
        # Current user's Redis state
        if user_id:
            user_score = await redis_client.zscore(LEADERBOARD_KEY, user_id)
            user_rank = await redis_client.zrevrank(LEADERBOARD_KEY, user_id)
            
            debug_info["redis"]["current_user"] = {
                "user_id": user_id,
                "score": int(user_score) if user_score is not None else None,
                "rank": int(user_rank) + 1 if user_rank is not None else None
            }
    except Exception as e:
        debug_info["redis"] = {"error": str(e)}
        import traceback
        logger.error(f"Redis debug error: {traceback.format_exc()}")
    
    # ✅ MY_RANK CALCULATION
    if user_id:
        try:
            # Try Redis first
            try:
                redis_client = await get_redis()
                score = await redis_client.zscore(LEADERBOARD_KEY, user_id)
                rank = await redis_client.zrevrank(LEADERBOARD_KEY, user_id)
                
                debug_info["my_rank"]["redis"] = {
                    "score": int(score) if score is not None else None,
                    "rank": int(rank) + 1 if rank is not None else None
                }
            except Exception as e:
                debug_info["my_rank"]["redis"] = {"error": str(e)}
            
            # Try PostgreSQL fallback
            my_rank_result = await service._get_my_rank_from_postgres(user_id)
            debug_info["my_rank"]["postgresql"] = {
                "rank": my_rank_result.rank if my_rank_result else None,
                "xp": my_rank_result.xp if my_rank_result else None
            }
            
            # Try service method
            my_rank_service = await service._get_my_rank(user_id)
            debug_info["my_rank"]["service"] = {
                "rank": my_rank_service.rank if my_rank_service else None,
                "xp": my_rank_service.xp if my_rank_service else None
            }
        except Exception as e:
            debug_info["my_rank"] = {"error": str(e)}
            import traceback
            logger.error(f"My rank debug error: {traceback.format_exc()}")
    
    # ✅ FINAL RESPONSE
    try:
        final_response = await service.get_leaderboard(
            limit=10,
            current_user_id=user_id
        )
        debug_info["final_response"] = {
            "top_users_count": len(final_response.top_users),
            "top_users": [
                {
                    "rank": user.rank,
                    "id": user.id,
                    "name": user.name,
                    "xp": user.xp
                }
                for user in final_response.top_users[:5]  # First 5 only
            ],
            "my_rank": {
                "rank": final_response.my_rank.rank if final_response.my_rank else None,
                "xp": final_response.my_rank.xp if final_response.my_rank else None
            }
        }
    except Exception as e:
        debug_info["final_response"] = {"error": str(e)}
        import traceback
        logger.error(f"Final response debug error: {traceback.format_exc()}")
    
    return success(
        data=debug_info,
        message="Full leaderboard debug information"
    )
