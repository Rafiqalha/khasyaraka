from sqlalchemy import String, Integer, ForeignKey, Enum, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from sqlalchemy.sql import func
import enum

from app.db.base import Base


class ToolTypeEnum(enum.Enum):
    """Enum for survival tool types"""
    compass = "compass"
    clinometer = "clinometer"
    pedometer = "pedometer"
    morse = "morse"
    leveler = "leveler"
    gps_tracker = "gps_tracker"


class SurvivalMastery(Base):
    """
    Tracks user's endless progression for each survival tool.
    
    XP accumulates infinitely, levels scale using: level = floor(sqrt(xp / 100)) + 1
    """
    __tablename__ = "survival_mastery"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    tool_type: Mapped[ToolTypeEnum] = mapped_column(
        Enum(ToolTypeEnum, name="tooltype"), 
        nullable=False
    )
    current_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    total_actions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    highest_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_altitude: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_distance_tracked: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )
    
    # Unique constraint: one record per user per tool
    __table_args__ = (
        {"schema": None},
    )
