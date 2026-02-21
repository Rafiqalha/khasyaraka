"""
Subscription Schemas

Pydantic models for subscription API requests/responses.
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class SubscriptionResponse(BaseModel):
    """Response for GET /user/subscription — enriched with computed fields"""
    tier: str
    status: str
    features: List[str]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    expires_in_days: Optional[int] = None
    auto_renew: bool = False
    billing_provider: Optional[str] = None

    class Config:
        from_attributes = True


class SubscriptionUpgradeRequest(BaseModel):
    """Request for POST /user/subscription/upgrade"""
    tier: str
    payment_reference: Optional[str] = None
    billing_provider: Optional[str] = None
    duration_days: int = 30


class SubscriptionRenewRequest(BaseModel):
    """Request for POST /user/subscription/renew"""
    payment_reference: Optional[str] = None
    duration_days: int = 30


class SubscriptionUpgradeResponse(BaseModel):
    """Response for subscription upgrade/renew"""
    success: bool
    tier: str
    status: str
    features: List[str]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    expires_in_days: Optional[int] = None
    message: str
