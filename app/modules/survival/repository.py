from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.modules.survival.models import SurvivalMastery, ToolTypeEnum


class SurvivalRepository:
    """Repository for survival mastery database operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_user_mastery(self, user_id: int, tool_type: ToolTypeEnum) -> Optional[SurvivalMastery]:
        """Get mastery record for a specific user and tool"""
        result = await self.db.execute(
            select(SurvivalMastery)
            .where(
                SurvivalMastery.user_id == user_id,
                SurvivalMastery.tool_type == tool_type
            )
        )
        return result.scalar_one_or_none()
    
    async def get_all_user_masteries(self, user_id: int) -> List[SurvivalMastery]:
        """Get all mastery records for a user"""
        result = await self.db.execute(
            select(SurvivalMastery)
            .where(SurvivalMastery.user_id == user_id)
            .order_by(SurvivalMastery.current_level.desc())
        )
        return list(result.scalars().all())
    
    async def create_mastery(self, user_id: int, tool_type: ToolTypeEnum) -> SurvivalMastery:
        """Create a new mastery record"""
        mastery = SurvivalMastery(
            user_id=user_id,
            tool_type=tool_type,
            current_xp=0,
            current_level=1,
            total_actions=0,
            highest_streak=0
        )
        self.db.add(mastery)
        await self.db.commit()
        await self.db.refresh(mastery)
        return mastery
    
    async def update_mastery(
        self, 
        mastery: SurvivalMastery,
        xp_delta: int,
        new_level: int,
        action_count: int = 1,
        max_altitude: float | None = None,
        distance_delta: float = 0.0
    ) -> SurvivalMastery:
        """Update mastery stats"""
        mastery.current_xp += xp_delta
        mastery.current_level = new_level
        mastery.total_actions += action_count
        mastery.total_distance_tracked += distance_delta
        if max_altitude is not None and max_altitude > mastery.max_altitude:
            mastery.max_altitude = max_altitude
        
        await self.db.commit()
        await self.db.refresh(mastery)
        return mastery
    
    async def get_or_create_mastery(self, user_id: int, tool_type: ToolTypeEnum) -> SurvivalMastery:
        """Get existing mastery or create new one"""
        mastery = await self.get_user_mastery(user_id, tool_type)
        if not mastery:
            mastery = await self.create_mastery(user_id, tool_type)
        return mastery
