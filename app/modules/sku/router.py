"""
SKU Module Router

FastAPI endpoints for SKU (Buku Saku) and Mission (SKK) operations.
Router only handles HTTP layer: request parsing, service calls, response formatting.
All business logic is in service layer.
All database access is in repository layer.
Exceptions are handled by global exception handler in main.py.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import get_current_user
from app.modules.sku.service import SkuService
from app.modules.sku.schemas import (
    SkuOverviewResponse,
    SkuPointsResponse,
    SkuPointDetailResponse,
    SkuSubmitRequest,
    SkuSubmitResponse
)
from app.core.response import success
from app.modules.sku.models import SkuLevel

router = APIRouter()


def get_service(db: AsyncSession = Depends(get_db)) -> SkuService:
    """Dependency injection for SkuService"""
    return SkuService(db)


# ==========================================
# Twin Pillars Endpoints
# ==========================================
@router.get("/overview", response_model=SkuOverviewResponse)
async def get_overview(
    current_user: dict = Depends(get_current_user),
    service: SkuService = Depends(get_service)
):
    user_id = int(current_user.get("sub")) if current_user.get("sub") else None
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user session")
    return await service.get_overview(user_id)


@router.get("/{level}/points", response_model=SkuPointsResponse)
async def get_points(
    level: SkuLevel,
    current_user: dict = Depends(get_current_user),
    service: SkuService = Depends(get_service)
):
    user_id = int(current_user.get("sub")) if current_user.get("sub") else None
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user session")
    return await service.get_points(user_id, level)


@router.get("/points/{point_id}", response_model=SkuPointDetailResponse)
async def get_point_detail(
    point_id: str,
    current_user: dict = Depends(get_current_user),
    service: SkuService = Depends(get_service)
):
    user_id = int(current_user.get("sub")) if current_user.get("sub") else None
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user session")
    return await service.get_point_detail(user_id, point_id)


@router.post("/submit", response_model=SkuSubmitResponse)
async def submit_sku(
    payload: SkuSubmitRequest,
    current_user: dict = Depends(get_current_user),
    service: SkuService = Depends(get_service)
):
    user_id = int(current_user.get("sub")) if current_user.get("sub") else None
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user session")
    return await service.submit_answers(user_id, payload)