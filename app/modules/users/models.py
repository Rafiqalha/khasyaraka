from sqlalchemy import Column, String, Boolean, Integer, DateTime, Date
from sqlalchemy.sql import func
from app.db.base import Base # Import dari base yang tadi kita buat

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    picture_url = Column(String, nullable=True)  # For Google profile picture
    total_xp = Column(Integer, default=0)
    streak = Column(Integer, default=0, nullable=False)  # Daily streak counter
    longest_streak = Column(Integer, default=0, nullable=False)  # All-time longest streak
    hearts = Column(Integer, default=5, nullable=False)  # Lives system (max 5)
    last_active_date = Column(Date, nullable=True)  # Last date user was active (for streak calculation)
    timezone = Column(String, default="Asia/Jakarta", nullable=False)  # User timezone (IANA)
    hack_level = Column(String, default="Script Kiddie")
    decrypted_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())