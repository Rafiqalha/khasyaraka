"""
Cyber Module Repository

Database access layer for CyberScout.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.modules.cyber.models import (
    CyberChallenge, CyberCategory, UserSolvedChallenge, CyberModule, CyberLevelProgress,
    SandiType, SandiQuestion, EncryptionLog, SandiCategory
)


class CyberRepository:
    """Repository for Cyber module database operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_random_challenge(self, category: CyberCategory) -> Optional[CyberChallenge]:
        stmt = (
            select(CyberChallenge)
            .where(CyberChallenge.category == category)
            .order_by(func.random())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_challenge_by_id(self, challenge_id: str) -> Optional[CyberChallenge]:
        stmt = select(CyberChallenge).where(CyberChallenge.id == challenge_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_challenges_by_module_level(self, module_id: str, level: int) -> list[CyberChallenge]:
        stmt = (
            select(CyberChallenge)
            .where(
                CyberChallenge.module_id == module_id,
                CyberChallenge.level == level
            )
            .order_by(CyberChallenge.id)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_random_challenge_by_module(self, module_id: str) -> Optional[CyberChallenge]:
        stmt = (
            select(CyberChallenge)
            .where(CyberChallenge.module_id == module_id)
            .order_by(func.random())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_modules(self) -> list[CyberModule]:
        stmt = select(CyberModule).order_by(CyberModule.difficulty, CyberModule.title)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_module_by_id(self, module_id: str) -> Optional[CyberModule]:
        stmt = select(CyberModule).where(CyberModule.id == module_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_level_progress(self, user_id: int, module_id: str, level: int) -> Optional[CyberLevelProgress]:
        stmt = (
            select(CyberLevelProgress)
            .where(
                CyberLevelProgress.user_id == user_id,
                CyberLevelProgress.module_id == module_id,
                CyberLevelProgress.level == level
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_level_progress(
        self,
        user_id: int,
        module_id: str,
        level: int,
        stars: int,
        score: int,
        is_completed: bool
    ) -> CyberLevelProgress:
        existing = await self.get_level_progress(user_id, module_id, level)
        if existing:
            existing.stars = max(existing.stars, stars)
            existing.score = max(existing.score, score)
            existing.is_completed = existing.is_completed or is_completed
            return existing

        progress = CyberLevelProgress(
            user_id=user_id,
            module_id=module_id,
            level=level,
            stars=stars,
            score=score,
            is_completed=is_completed
        )
        self.db.add(progress)
        return progress

    async def has_user_solved(self, user_id: int, challenge_id: str) -> bool:
        stmt = (
            select(UserSolvedChallenge)
            .where(
                UserSolvedChallenge.user_id == user_id,
                UserSolvedChallenge.challenge_id == challenge_id
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def mark_solved(self, user_id: int, challenge_id: str) -> None:
        solved = UserSolvedChallenge(user_id=user_id, challenge_id=challenge_id)
        self.db.add(solved)

    # ============ SANDI PRAMUKA METHODS ============

    async def get_all_sandi_types(self) -> list[SandiType]:
        """Get all Sandi types"""
        stmt = select(SandiType).order_by(SandiType.difficulty, SandiType.name)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_sandi_by_codename(self, codename: str) -> Optional[SandiType]:
        """Get Sandi type by codename"""
        stmt = select(SandiType).where(SandiType.codename == codename)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_sandi_by_id(self, sandi_id: int) -> Optional[SandiType]:
        """Get Sandi type by ID"""
        stmt = select(SandiType).where(SandiType.id == sandi_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_random_sandi_questions(self, sandi_id: int, limit: int = 5) -> list[SandiQuestion]:
        """Get random questions for a Sandi type"""
        stmt = (
            select(SandiQuestion)
            .where(SandiQuestion.sandi_id == sandi_id)
            .order_by(func.random())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create_encryption_log(
        self,
        user_id: int,
        sandi_id: int,
        input_hash: str,
        operation_mode: str
    ) -> EncryptionLog:
        """Create encryption log entry"""
        log = EncryptionLog(
            user_id=user_id,
            sandi_id=sandi_id,
            input_hash=input_hash,
            operation_mode=operation_mode
        )
        self.db.add(log)
        return log
