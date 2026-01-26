"""
Auth Repository

Database access layer for Auth module.
All database queries are isolated here using SQLAlchemy.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.modules.users.models import User


class AuthRepository:
    """Repository for Auth module database operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            email: User email address
        
        Returns:
            User object if found, None otherwise
        """
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalars().first()

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
        
        Returns:
            User object if found, None otherwise
        """
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_user(
        self,
        email: str,
        hashed_password: str,
        full_name: str,
        picture_url: Optional[str] = None,
        is_active: bool = True
    ) -> User:
        """
        Create a new user in the database.
        
        Args:
            email: User email address
            hashed_password: Hashed password
            full_name: User's full name
            picture_url: Optional profile picture URL
            is_active: Whether user is active
        
        Returns:
            Created User object
        
        Raises:
            ValueError: If email already exists (should be checked before calling)
        """
        db_user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            picture_url=picture_url,
            is_active=is_active
        )
        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)
        return db_user
