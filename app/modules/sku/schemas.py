from typing import List, Optional, Any
from pydantic import BaseModel, Field

from app.modules.sku.models import SkuLevel


class SkuOverviewResponse(BaseModel):
    bantara_progress: float = Field(..., description="Progress Bantara (0-100)")
    is_laksana_unlocked: bool = Field(..., description="Whether Laksana is unlocked")


class SkuPointStatus(BaseModel):
    id: str
    number: int
    title: str
    category: str
    is_completed: bool
    score: int


class SkuPointsResponse(BaseModel):
    level: SkuLevel
    total: int
    points: List[SkuPointStatus]


class SkuPointDetailResponse(BaseModel):
    id: str
    level: SkuLevel
    number: int
    title: str
    description: str
    category: str
    quiz_content: dict
    is_completed: bool
    score: int


class SkuSubmitRequest(BaseModel):
    sku_point_id: str
    answers: List[int]


class SkuSubmitResponse(BaseModel):
    sku_point_id: str
    score: int
    correct_count: int
    total_questions: int
    is_completed: bool
