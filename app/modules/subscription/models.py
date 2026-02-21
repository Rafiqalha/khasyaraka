"""
Subscription Models

Database models for the subscription system.
Supports subscription history (no UNIQUE on user_id).
Active subscription = status='active' AND end_date > NOW().
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tier = Column(String, nullable=False, default="free")
    status = Column(String, nullable=False, default="active")
    start_date = Column(DateTime(timezone=True), server_default=func.now())
    end_date = Column(DateTime(timezone=True), nullable=True)
    payment_reference = Column(String, nullable=True)
    billing_provider = Column(String, nullable=True)
    provider_subscription_id = Column(String, nullable=True)
    auto_renew = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
