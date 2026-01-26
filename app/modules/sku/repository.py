"""
SKU Repository

Database access layer for SKU module.
All database queries are isolated here using SQLAlchemy.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List, Dict, Any

from app.modules.sku.models import (
    SkuLevel,
    SkuPoint,
    SkuProgress,
    SpecialMission,
    MissionTask
)


class SkuRepository:
    """Repository for SKU module database operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== SKU POINT METHODS ====================
    async def get_points_by_level(self, level: SkuLevel) -> List[SkuPoint]:
        stmt = select(SkuPoint).where(SkuPoint.level == level).order_by(SkuPoint.number)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_point_by_id(self, point_id: str) -> Optional[SkuPoint]:
        stmt = select(SkuPoint).where(SkuPoint.id == point_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_progress_for_user(self, user_id: int) -> List[SkuProgress]:
        stmt = select(SkuProgress).where(SkuProgress.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_progress_for_point(self, user_id: int, point_id: str) -> Optional[SkuProgress]:
        stmt = select(SkuProgress).where(
            SkuProgress.user_id == user_id,
            SkuProgress.sku_point_id == point_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_progress(self, user_id: int, point_id: str, score: int, is_completed: bool) -> None:
        progress = await self.get_progress_for_point(user_id, point_id)
        if progress:
            progress.score = score
            progress.is_completed = is_completed
            return
        self.db.add(
            SkuProgress(
                user_id=user_id,
                sku_point_id=point_id,
                score=score,
                is_completed=is_completed
            )
        )

    # ==================== MISSION METHODS (Legacy) ====================
    
    async def get_all_missions(self) -> List[SpecialMission]:
        """
        Get all special missions with their tasks.
        Equivalent to: SELECT * FROM khasyaraka_special_missions 
                      JOIN khasyaraka_mission_tasks
        """
        stmt = (
            select(SpecialMission)
            .options(
                selectinload(SpecialMission.tasks)
            )
            .order_by(SpecialMission.id)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_mission_by_id(self, mission_id: int) -> Optional[SpecialMission]:
        """Get a specific mission by ID with tasks"""
        stmt = (
            select(SpecialMission)
            .where(SpecialMission.id == mission_id)
            .options(
                selectinload(SpecialMission.tasks)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ==================== TASK METHODS (Legacy) ====================

    async def get_mission_task_by_id(self, task_id: int) -> Optional[MissionTask]:
        """
        Get a specific mission task by ID.
        Used for answer verification.
        """
        stmt = (
            select(MissionTask)
            .where(MissionTask.id == task_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_task_by_id(self, task_id: int, is_mission: bool) -> Optional[Dict[str, Any]]:
        """
        Get task data by ID (either SKU task or Mission task).
        Returns a dictionary with task data for answer verification.
        
        Args:
            task_id: Task ID
            is_mission: True for mission task, False for SKU task
        
        Returns:
            Dictionary with: type, correct_index, options, explanation, correct_text
            None if task not found
        """
        if is_mission:
            task = await self.get_mission_task_by_id(task_id)
        else:
            return None
        
        if not task:
            return None
        
        return {
            'type': task.type,
            'correct_index': task.correct_index,
            'options': task.options or [],
            'explanation': task.explanation,
            'correct_text': task.correct_text or '',
        }
