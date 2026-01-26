"""
SKU Service

Business logic layer for SKU module.
Handles answer verification, scoring, and data transformation.
"""

import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sku.repository import SkuRepository
from app.modules.sku.models import SkuLevel
from app.modules.sku.schemas import (
    SkuOverviewResponse,
    SkuPointsResponse,
    SkuPointDetailResponse,
    SkuSubmitRequest,
    SkuSubmitResponse,
    SkuPointStatus
)

logger = logging.getLogger(__name__)


class SkuService:
    """Service for SKU module business logic"""
    
    def __init__(self, db: AsyncSession):
        self.repository = SkuRepository(db)

    async def get_overview(self, user_id: int) -> SkuOverviewResponse:
        bantara_points = await self.repository.get_points_by_level(SkuLevel.bantara)
        progress = await self.repository.get_progress_for_user(user_id)
        completed_ids = {p.sku_point_id for p in progress if p.is_completed}

        total = len(bantara_points)
        completed = sum(1 for p in bantara_points if p.id in completed_ids)
        progress_percent = 0.0 if total == 0 else round((completed / total) * 100, 2)
        is_laksana_unlocked = progress_percent >= 100

        return SkuOverviewResponse(
            bantara_progress=progress_percent,
            is_laksana_unlocked=is_laksana_unlocked
        )

    async def get_points(self, user_id: int, level: SkuLevel) -> SkuPointsResponse:
        points = await self.repository.get_points_by_level(level)
        progress = await self.repository.get_progress_for_user(user_id)
        progress_map = {p.sku_point_id: p for p in progress}

        point_status = []
        for point in points:
            prog = progress_map.get(point.id)
            point_status.append(
                SkuPointStatus(
                    id=point.id,
                    number=point.number,
                    title=point.title,
                    category=point.category,
                    is_completed=prog.is_completed if prog else False,
                    score=prog.score if prog else 0
                )
            )

        return SkuPointsResponse(
            level=level,
            total=len(point_status),
            points=point_status
        )

    async def get_point_detail(self, user_id: int, point_id: str) -> SkuPointDetailResponse:
        point = await self.repository.get_point_by_id(point_id)
        if not point:
            raise ValueError("Point not found")

        progress = await self.repository.get_progress_for_point(user_id, point_id)
        return SkuPointDetailResponse(
            id=point.id,
            level=point.level,
            number=point.number,
            title=point.title,
            description=point.description,
            category=point.category,
            quiz_content=point.quiz_content,
            is_completed=progress.is_completed if progress else False,
            score=progress.score if progress else 0
        )

    async def submit_answers(self, user_id: int, payload: SkuSubmitRequest) -> SkuSubmitResponse:
        point = await self.repository.get_point_by_id(payload.sku_point_id)
        if not point:
            raise ValueError("Point not found")

        questions = point.quiz_content.get("questions", [])
        total_questions = len(questions)
        if total_questions == 0:
            raise ValueError("No questions available")

        correct_count = 0
        for idx, question in enumerate(questions):
            correct_index = question.get("correct_index")
            user_answer = payload.answers[idx] if idx < len(payload.answers) else None
            if user_answer is not None and user_answer == correct_index:
                correct_count += 1

        score = round((correct_count / total_questions) * 100)
        is_completed = score >= 80

        await self.repository.upsert_progress(
            user_id=user_id,
            point_id=point.id,
            score=score,
            is_completed=is_completed
        )
        await self.repository.db.commit()

        return SkuSubmitResponse(
            sku_point_id=point.id,
            score=score,
            correct_count=correct_count,
            total_questions=total_questions,
            is_completed=is_completed
        )