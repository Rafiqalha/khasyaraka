"""
Cyber Module Models

Database models for CyberScout challenges and Sandi Pramuka.
"""

from enum import Enum
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, Enum as SqlEnum, JSON, DateTime, ForeignKey, UniqueConstraint, Text
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


class SandiCategory(str, Enum):
    """Category for Sandi Pramuka types"""
    encoding = "encoding"
    substitution = "substitution"
    transposition = "transposition"
    visual = "visual"


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


class SandiType(Base):
    """Sandi Pramuka Type - Metadata for 15 cipher types"""
    __tablename__ = "sandi_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codename: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    difficulty: Mapped[int] = mapped_column(Integer, default=1)  # 1-4
    category: Mapped[SandiCategory] = mapped_column(
        SqlEnum(SandiCategory, name="sandi_category"),
        nullable=False,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SandiQuestion(Base):
    """Exam questions for Sandi Pramuka"""
    __tablename__ = "sandi_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sandi_id: Mapped[int] = mapped_column(Integer, ForeignKey("sandi_types.id"), nullable=False, index=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_text: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[str] = mapped_column(String(500), nullable=False)
    hint: Mapped[str] = mapped_column(Text, nullable=True)
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    xp_reward: Mapped[int] = mapped_column(Integer, default=10)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EncryptionLog(Base):
    """Audit trail for Tool Mode usage"""
    __tablename__ = "encryption_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    sandi_id: Mapped[int] = mapped_column(Integer, ForeignKey("sandi_types.id"), nullable=False, index=True)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # SHA-256 hash of input
    operation_mode: Mapped[str] = mapped_column(String(20), nullable=False)  # ENCRYPT or DECRYPT
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
