from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.permissions import require_tier
from app.modules.users.models import User
from app.modules.survival.repository import SurvivalRepository
from app.modules.survival.service import SurvivalService
from app.modules.survival.schemas import (
    AllMasteryResponse,
    RecordActionRequest,
    RecordActionResponse
)

router = APIRouter()


@router.get("/mastery", response_model=AllMasteryResponse)
async def get_user_mastery(
    current_user: dict = Depends(get_current_user),
    _tier = Depends(require_tier("pro")),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all survival tool mastery stats for the current user.
    
    Returns levels, XP, and progress for all 6 tools.
    """
    repository = SurvivalRepository(db)
    service = SurvivalService(repository)
    
    user_id = int(current_user.get("sub"))
    return await service.get_all_mastery(user_id)


@router.post("/action", response_model=RecordActionResponse)
async def record_tool_action(
    request: RecordActionRequest,
    current_user: dict = Depends(get_current_user),
    _tier = Depends(require_tier("pro")),
    db: AsyncSession = Depends(get_db)
):
    """
    Record a successful survival tool action.
    
    Called when user:
    - Locks a compass target
    - Reads an angle with clinometer
    - Completes a step milestone with pedometer
    - Sends a morse signal
    - Levels a surface
    - Locks a GPS coordinate
    
    Grants XP and updates mastery level.
    """
    repository = SurvivalRepository(db)
    service = SurvivalService(repository)
    
    try:
        user_id = int(current_user.get("sub"))
        result = await service.record_action(
            user_id=user_id,
            tool_type=request.tool_type,
            xp_gained=request.xp_gained,
            metadata=request.action_metadata
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record action: {str(e)}"
        )
