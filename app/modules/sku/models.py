"""
SKU Module Models

SQLAlchemy models for SKU (Buku Saku) and Mission (SKK) tables.
"""

from enum import Enum
from sqlalchemy import String, Boolean, Integer, ForeignKey, JSON, Text, Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List

from app.db.base import Base


class SkuLevel(str, Enum):
    """SKU Level Enum (Twin Pillars)"""
    bantara = "bantara"
    laksana = "laksana"


class SkuPoint(Base):
    """SKU Point (Kwarnas Intellectual/Cognitive)"""
    __tablename__ = "sku_points"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    level: Mapped[SkuLevel] = mapped_column(SqlEnum(SkuLevel), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    quiz_content: Mapped[dict] = mapped_column(JSON, nullable=False)

    progress: Mapped[List["SkuProgress"]] = relationship(
        back_populates="point",
        cascade="all, delete-orphan"
    )


class SkuProgress(Base):
    """SKU Progress per user per point"""
    __tablename__ = "sku_progress"

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        primary_key=True
    )
    sku_point_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("sku_points.id"),
        primary_key=True
    )
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    point: Mapped["SkuPoint"] = relationship(back_populates="progress")


class SpecialMission(Base):
    """Special Mission (SKK - Syarat Kecakapan Khusus)"""
    __tablename__ = "khasyaraka_special_missions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mission_title: Mapped[str] = mapped_column(String(200), nullable=False)
    level_category: Mapped[str] = mapped_column(String(50), nullable=False)
    badge_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationships
    tasks: Mapped[List["MissionTask"]] = relationship(
        back_populates="mission",
        cascade="all, delete-orphan",
        order_by="MissionTask.id"
    )


class MissionTask(Base):
    """Mission Task (Tugas dalam sebuah Mission)"""
    __tablename__ = "khasyaraka_mission_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mission_id: Mapped[int] = mapped_column(Integer, ForeignKey("khasyaraka_special_missions.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)  # multiple_choice, text, reorder
    question: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)  # List of options/answers
    correct_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # For multiple_choice
    correct_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # For reorder/text
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    mission: Mapped["SpecialMission"] = relationship(back_populates="tasks")
