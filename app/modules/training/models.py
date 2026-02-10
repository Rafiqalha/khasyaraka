import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Text, Integer, ForeignKey, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional

from app.db.base import Base


class TrainingSection(Base):
    """Section/Bagian (e.g., Pengetahuan Umum Kepramukaan)"""
    __tablename__ = "training_sections"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g., "puk"
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tier: Mapped[str] = mapped_column(String(20), default="free")  # "free" or "premium"
    order: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    units: Mapped[list["TrainingUnit"]] = relationship(back_populates="section", cascade="all, delete-orphan")


class TrainingUnit(Base):
    """Unit (e.g., Sejarah dan Trivia Kepramukaan)"""
    __tablename__ = "training_units"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g., "puk_unit_1"
    section_id: Mapped[str] = mapped_column(String(50), ForeignKey("training_sections.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=1)
    total_levels: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    section: Mapped["TrainingSection"] = relationship(back_populates="units")
    levels: Mapped[list["TrainingLevel"]] = relationship(back_populates="unit", cascade="all, delete-orphan")


class TrainingLevel(Base):
    """Level/Lesson dalam sebuah Unit"""
    __tablename__ = "training_levels"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g., "puk_u1_l1"
    unit_id: Mapped[str] = mapped_column(String(50), ForeignKey("training_units.id"), nullable=False)
    level_number: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), default="easy")  # very_easy, easy, medium, hard
    total_questions: Mapped[int] = mapped_column(Integer, default=5)
    min_correct: Mapped[int] = mapped_column(Integer, default=4)
    xp_reward: Mapped[int] = mapped_column(Integer, default=10)
    unlock_rule: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # {"type": "start", "value": true}
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    unit: Mapped["TrainingUnit"] = relationship(back_populates="levels")
    questions: Mapped[list["TrainingQuestion"]] = relationship(back_populates="level", cascade="all, delete-orphan")


class TrainingQuestion(Base):
    """Pertanyaan dalam sebuah Level"""
    __tablename__ = "training_questions"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g., "q_puk_u1_l1_01"
    level_id: Mapped[str] = mapped_column(String(50), ForeignKey("training_levels.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)  # multiple_choice, matching, fill_blank, etc.
    question: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)  # Question-specific data (options, pairs, etc.)
    xp: Mapped[int] = mapped_column(Integer, default=2)
    order: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    level: Mapped["TrainingLevel"] = relationship(back_populates="questions")


class UserProgress(Base):
    """Progress user untuk setiap level"""
    __tablename__ = "user_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    level_id: Mapped[str] = mapped_column(String(50), ForeignKey("training_levels.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="LOCKED")  # LOCKED, UNLOCKED, COMPLETED
    score: Mapped[int] = mapped_column(Integer, default=0)
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0)
    xp_earned: Mapped[int] = mapped_column(Integer, default=0)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint: one progress record per user per level
    __table_args__ = (
        {"comment": "User progress for training levels"},
    )


# Legacy model - kept for backward compatibility
class TrainingPath(Base):
    __tablename__ = "khasyaraka_training_paths"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )

    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
