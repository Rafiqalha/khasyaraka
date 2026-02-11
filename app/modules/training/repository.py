"""
Training Repository

Database access layer for Training module.
All database queries are isolated here using SQLAlchemy.
"""

from datetime import datetime
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional, List

from app.modules.training.models import (
    TrainingSection,
    TrainingUnit,
    TrainingLevel,
    TrainingQuestion,
    UserProgress
)


class TrainingRepository:
    """Repository for Training module database operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== SECTION METHODS ====================
    
    async def get_all_sections(self) -> List[TrainingSection]:
        """Get all active sections ordered by order"""
        stmt = (
            select(TrainingSection)
            .where(TrainingSection.is_active == True)
            .order_by(TrainingSection.order)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_section_by_id(self, section_id: str) -> Optional[TrainingSection]:
        """
        Get a specific section by ID.
        
        Returns None if section doesn't exist or is inactive.
        Logs warning for better debugging.
        """
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        
        # ✅ First check if section exists at all (even if inactive)
        stmt_exists = select(TrainingSection).where(TrainingSection.id == section_id)
        result_exists = await self.db.execute(stmt_exists)
        section_exists = result_exists.scalar_one_or_none()
        
        if not section_exists:
            logger.warning(f"⚠️ Section '{section_id}' does not exist in database")
            return None
        
        if not section_exists.is_active:
            logger.warning(f"⚠️ Section '{section_id}' exists but is_active = false")
            return None
        
        # ✅ Section exists and is active
        return section_exists

    async def get_section_with_units_and_levels(self, section_id: str) -> Optional[TrainingSection]:
        """
        Get section with eager-loaded units and levels.
        
        Returns None if section doesn't exist or is inactive.
        Logs warning for better debugging.
        """
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        
        # ✅ First check if section exists
        section = await self.get_section_by_id(section_id)
        if not section:
            return None
        
        # ✅ Load with relationships
        stmt = (
            select(TrainingSection)
            .where(
                TrainingSection.id == section_id,
                TrainingSection.is_active == True
            )
            .options(
                selectinload(TrainingSection.units).selectinload(TrainingUnit.levels)
            )
        )
        result = await self.db.execute(stmt)
        section_with_relations = result.scalar_one_or_none()
        
        if section_with_relations:
            units_count = len(section_with_relations.units) if section_with_relations.units else 0
            logger.info(f"✅ Loaded section '{section_id}' with {units_count} units")
        
        return section_with_relations

    # ==================== UNIT METHODS ====================
    
    async def get_units_by_section(self, section_id: str) -> List[TrainingUnit]:
        """Get all active units for a section"""
        stmt = (
            select(TrainingUnit)
            .where(
                TrainingUnit.section_id == section_id,
                TrainingUnit.is_active == True
            )
            .order_by(TrainingUnit.order)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_unit_by_id(self, unit_id: str) -> Optional[TrainingUnit]:
        """Get a specific unit by ID"""
        stmt = (
            select(TrainingUnit)
            .where(
                TrainingUnit.id == unit_id,
                TrainingUnit.is_active == True
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ==================== LEVEL METHODS ====================
    
    async def get_levels_by_unit(self, unit_id: str) -> List[TrainingLevel]:
        """Get all active levels for a unit"""
        stmt = (
            select(TrainingLevel)
            .where(
                TrainingLevel.unit_id == unit_id,
                TrainingLevel.is_active == True
            )
            .order_by(TrainingLevel.level_number)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_level_by_id(self, level_id: str) -> Optional[TrainingLevel]:
        """Get a specific level by ID"""
        stmt = (
            select(TrainingLevel)
            .where(
                TrainingLevel.id == level_id,
                TrainingLevel.is_active == True
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ==================== QUESTION METHODS ====================
    
    async def get_questions_by_unit(self, unit_id: str) -> List[TrainingQuestion]:
        """
        Get all questions from all levels in a unit.
        
        Args:
            unit_id: Unit ID (e.g., 'puk_u1')
        
        Returns:
            List of all questions from all active levels in this unit
            Ordered by level_number, then by question order
        """
        # Get all levels in this unit
        levels = await self.get_levels_by_unit(unit_id)
        
        # Get all questions from all levels
        all_questions = []
        for level in sorted(levels, key=lambda l: l.level_number):
            level_questions = await self.get_questions_by_level(level.id)
            all_questions.extend(level_questions)
        
        return all_questions

    async def get_questions_by_level(self, level_id: str) -> List[TrainingQuestion]:
        """Get all active questions for a level"""
        stmt = (
            select(TrainingQuestion)
            .where(
                TrainingQuestion.level_id == level_id,
                TrainingQuestion.is_active == True
            )
            .order_by(TrainingQuestion.order)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_question_by_id(self, question_id: str) -> Optional[TrainingQuestion]:
        """Get a specific question by ID"""
        stmt = (
            select(TrainingQuestion)
            .where(
                TrainingQuestion.id == question_id,
                TrainingQuestion.is_active == True
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ==================== USER PROGRESS METHODS ====================
    
    async def get_user_progress(self, user_id: int, level_id: str) -> Optional[UserProgress]:
        """Get user progress for a specific level"""
        stmt = (
            select(UserProgress)
            .where(
                UserProgress.user_id == user_id,
                UserProgress.level_id == level_id
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_progress_by_section(self, user_id: int, section_id: Optional[str] = None) -> List[UserProgress]:
        """
        Get all user progress for levels.
        If section_id is provided, filter by section.
        If section_id is None, return all progress (Global).
        """
        # First get relevant level IDs
        stmt = (
            select(TrainingLevel.id)
            .join(TrainingUnit)
            .join(TrainingSection)
        )
        
        if section_id:
            stmt = stmt.where(TrainingSection.id == section_id)
            
        # Ensure we only get progress for active content
        stmt = stmt.where(
            TrainingSection.is_active == True,
            TrainingUnit.is_active == True,
            TrainingLevel.is_active == True
        )
            
        level_ids_result = await self.db.execute(stmt)
        level_ids = [row[0] for row in level_ids_result.all()]
        
        if not level_ids:
            return []
        
        # Get progress for these levels
        stmt = (
            select(UserProgress)
            .where(
                UserProgress.user_id == user_id,
                UserProgress.level_id.in_(level_ids)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def upsert_user_progress(
        self,
        user_id: int,
        level_id: str,
        status: str,
        score: int = 0,
        total_questions: int = 0,
        correct_answers: int = 0,
        xp_earned: int = 0,
        time_spent_seconds: int = 0,
        commit: bool = False,  # ✅ NEW: Allow caller to control commit
    ) -> UserProgress:
        """
        Create or update user progress for a level.
        
        Args:
            commit: If True, commit transaction. If False, caller must commit.
                   Default False to allow atomic transactions with XP updates.
        """
        existing = await self.get_user_progress(user_id, level_id)
        
        if existing:
            # Update existing
            existing.status = status
            existing.score = score
            existing.total_questions = total_questions
            existing.correct_answers = correct_answers
            existing.xp_earned = xp_earned
            existing.time_spent_seconds = time_spent_seconds
            existing.updated_at = datetime.utcnow()
            if status.upper() == "COMPLETED":
                existing.completed_at = datetime.utcnow()
            if commit:
                await self.db.commit()
                await self.db.refresh(existing)
            return existing
        else:
            # Create new
            new_progress = UserProgress(
                user_id=user_id,
                level_id=level_id,
                status=status,
                score=score,
                total_questions=total_questions,
                correct_answers=correct_answers,
                xp_earned=xp_earned,
                time_spent_seconds=time_spent_seconds,
            )
            if status.upper() == "COMPLETED":
                new_progress.completed_at = datetime.utcnow()
            self.db.add(new_progress)
            if commit:
                await self.db.commit()
                await self.db.refresh(new_progress)
            return new_progress
