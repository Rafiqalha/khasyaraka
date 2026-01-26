"""
Cyber Module Models

Database models for CyberScout challenges.
"""

from enum import Enum
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, Enum as SqlEnum, JSON, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CyberCategory(str, Enum):
    morse = "morse"
    semaphore = "semaphore"
    caesar_cipher = "caesar_cipher"
    rail_fence = "rail_fence"
    atbash = "atbash"
    binary = "binary"
    reverse = "reverse"


class CyberChallenge(Base):
    """Challenge for CyberScout missions"""
    __tablename__ = "cyber_challenges"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    module_id: Mapped[str] = mapped_column(String(50), ForeignKey("cyber_modules.id"), nullable=False, index=True)
    level: Mapped[int] = mapped_column(Integer, default=1)
    category: Mapped[CyberCategory] = mapped_column(
        SqlEnum(CyberCategory, name="cyber_category"),
        nullable=False,
        index=True
    )
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    encrypted_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    decrypted_answer: Mapped[str] = mapped_column(String(200), nullable=False)
    xp_reward: Mapped[int] = mapped_column(Integer, default=5)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CyberModule(Base):
    """CyberScout learning module (chapter)"""
    __tablename__ = "cyber_modules"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    original_title: Mapped[str] = mapped_column(String(200), nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    min_read_seconds: Mapped[int] = mapped_column(Integer, default=20)
    intel_content: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserSolvedChallenge(Base):
    """Track solved challenges to prevent XP farming"""
    __tablename__ = "user_solved_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    challenge_id: Mapped[str] = mapped_column(String(50), ForeignKey("cyber_challenges.id"), nullable=False, index=True)
    solved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "challenge_id", name="uq_user_challenge"),
    )


class CyberLevelProgress(Base):
    """Progress per module level with stars"""
    __tablename__ = "cyber_level_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    module_id: Mapped[str] = mapped_column(String(50), ForeignKey("cyber_modules.id"), nullable=False, index=True)
    level: Mapped[int] = mapped_column(Integer, default=1)
    stars: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[int] = mapped_column(Integer, default=0)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "module_id", "level", name="uq_user_module_level"),
    )
