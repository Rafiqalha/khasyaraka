from sqlalchemy import Column, Integer, String, ForeignKey, Enum, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum

class TKKLevel(str, enum.Enum):
    PURWA = "purwa"
    MADYA = "madya"
    UTAMA = "utama"

class UserTKK(Base):
    __tablename__ = "user_tkk"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tkk_slug = Column(String, nullable=False, index=True)
    level = Column(Enum(TKKLevel), nullable=False)
    attained_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to User model
    # user = relationship("User", back_populates="tkks") # Assuming back_populates is added to User model, user side needs update if we want bidirectional

    __table_args__ = (
        UniqueConstraint('user_id', 'tkk_slug', 'level', name='uq_user_tkk_level'),
    )

    def __repr__(self):
        return f"<UserTKK(user_id={self.user_id}, tkk={self.tkk_slug}, level={self.level})>"
