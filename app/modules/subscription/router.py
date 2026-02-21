"""
Subscription Router (Hardened)

API endpoints:
- GET  /user/subscription        — effective tier + features + expires_in_days
- POST /user/subscription/upgrade — upgrade tier (creates new history row)
- POST /user/subscription/renew   — renew existing paid tier
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import get_current_user
from app.modules.subscription.service import SubscriptionService
from app.modules.subscription.schemas import (
    SubscriptionResponse,
    SubscriptionUpgradeRequest,
    SubscriptionRenewRequest,
    SubscriptionUpgradeResponse,
)

router = APIRouter()


def get_service(db: AsyncSession = Depends(get_db)) -> SubscriptionService:
    return SubscriptionService(db)


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    current_user: dict = Depends(get_current_user),
    service: SubscriptionService = Depends(get_service),
):
    """
    Get current user's effective subscription.

    Returns computed effective tier (based on active, non-expired sub),
    feature list, expires_in_days, auto_renew, and billing_provider.
    """
    user_id = int(current_user.get("sub"))
    return await service.get_effective_subscription(user_id)


@router.post("/subscription/upgrade", response_model=SubscriptionUpgradeResponse)
async def upgrade_subscription(
    request: SubscriptionUpgradeRequest,
    current_user: dict = Depends(get_current_user),
    service: SubscriptionService = Depends(get_service),
):
    """
    Upgrade user's subscription tier.
    Creates a new subscription row; old one preserved as history.
    """
    user_id = int(current_user.get("sub"))
    try:
        return await service.upgrade_subscription(
            user_id=user_id,
            new_tier=request.tier,
            payment_reference=request.payment_reference,
            billing_provider=request.billing_provider,
            duration_days=request.duration_days,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/subscription/renew", response_model=SubscriptionUpgradeResponse)
async def renew_subscription(
    request: SubscriptionRenewRequest,
    current_user: dict = Depends(get_current_user),
    service: SubscriptionService = Depends(get_service),
):
    """
    Renew an existing paid subscription.
    Extends end_date atomically. Returns updated subscription state.
    """
    user_id = int(current_user.get("sub"))
    try:
        return await service.renew_subscription(
            user_id=user_id,
            payment_reference=request.payment_reference,
            duration_days=request.duration_days,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
