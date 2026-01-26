"""
Auth Service

Business logic layer for Auth module.
Handles authentication, password hashing, token generation, and Google OAuth.
Uses repository for all database access.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.users.models import User
from app.modules.auth.schemas import UserCreate
from app.modules.auth.repository import AuthRepository
from app.core.errors import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    InvalidTokenError,
    UserInactiveError
)
from app.core.logging import get_logger
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import jwt
from app.core.config import settings
from typing import Optional, Dict, Any, Tuple
from google.auth.transport import requests
from google.oauth2 import id_token

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
logger = get_logger(__name__)


class AuthService:
    """Service for Auth module business logic"""
    
    def __init__(self, db: AsyncSession):
        self.repository = AuthRepository(db)

    async def create_user(self, user_in: UserCreate) -> User:
        """
        Create a new user with email and hashed password.
        
        Args:
            user_in: UserCreate schema with username, password, name/full_name
        
        Returns:
            User object if created successfully
        
        Raises:
            UserAlreadyExistsError: If email already exists
        """
        # Get email from username
        email = user_in.get_email()
        full_name = user_in.get_full_name()
        
        if not full_name:
            from app.core.errors import AppException
            raise AppException(
                message="Name is required",
                error_code="VALIDATION_ERROR",
                status_code=422
            )
        
        # 1. Check if email already exists
        existing_user = await self.repository.get_user_by_email(email)
        if existing_user:
            logger.warning(f"Registration attempt with existing email: {email}")
            raise UserAlreadyExistsError(email)
        
        # 2. Hash password
        hashed_password = pwd_context.hash(user_in.password)
        
        # 3. Create user via repository
        db_user = await self.repository.create_user(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            is_active=True
        )
        
        logger.info(f"User created successfully: {db_user.email} (ID: {db_user.id})")
        return db_user


    def create_access_token(self, user_id: int, expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token for the user.
        
        Args:
            user_id: The user's ID
            expires_delta: Custom expiration time (default: from settings)
        
        Returns:
            JWT token string
        """
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        to_encode = {
            "sub": str(user_id),
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm="HS256"
        )
        
        return encoded_jwt

    def verify_google_token(self, id_token_str: str) -> Dict[str, Any]:
        """
        Verify Google ID token and extract user information.
        
        Args:
            id_token_str: The ID token from Google Sign-In
        
        Returns:
            Dictionary containing user info (email, name, picture, sub)
        
        Raises:
            InvalidTokenError: If token is invalid
        """
        try:
            # Verify the token with Google's public certificates
            idinfo = id_token.verify_oauth2_token(
                id_token_str,
                requests.Request(),
                clock_skew_in_seconds=10  # Allow 10 second skew
            )
            
            # Token is valid
            return {
                "sub": idinfo.get("sub"),  # Google user ID
                "email": idinfo.get("email"),
                "name": idinfo.get("name"),
                "picture": idinfo.get("picture"),
            }
        except Exception as e:
            logger.warning(f"Google token verification failed: {str(e)}")
            raise InvalidTokenError(f"Invalid Google token: {str(e)}")

    async def google_sign_in(self, id_token_str: str) -> Tuple[User, str]:
        """
        Handle Google Sign-In: verify token, check/create user, return JWT.
        
        Args:
            id_token_str: Google ID token from frontend
        
        Returns:
            Tuple of (User object, access token)
        
        Raises:
            InvalidTokenError: If token verification fails
            UserInactiveError: If user account is disabled
        """
        # 1. Verify Google token
        user_info = self.verify_google_token(id_token_str)
        
        email = user_info.get("email")
        name = user_info.get("name", "Scout User")
        picture = user_info.get("picture")
        google_id = user_info.get("sub")
        
        # 2. Check if user exists via repository
        db_user = await self.repository.get_user_by_email(email)
        
        if db_user:
            # Check if user is active
            if not db_user.is_active:
                logger.warning(f"Google sign-in attempt for inactive user: {email}")
                raise UserInactiveError()
            
            # User exists: return user with new token
            access_token = self.create_access_token(db_user.id)
            logger.info(f"Google sign-in successful: {email} (ID: {db_user.id})")
            return db_user, access_token
        else:
            # User doesn't exist: create new user
            # Generate a random password (user logged in via Google, no traditional password)
            random_password = pwd_context.hash(google_id)
            
            db_user = await self.repository.create_user(
                email=email,
                hashed_password=random_password,
                full_name=name,
                picture_url=picture,
                is_active=True
            )
            
            # Create token for new user
            access_token = self.create_access_token(db_user.id)
            logger.info(f"New user created via Google sign-in: {email} (ID: {db_user.id})")
            return db_user, access_token

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain password against its hashed version.
        
        Args:
            plain_password: Plain text password from user
            hashed_password: Hashed password from database
        
        Returns:
            True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)

    async def login_with_email(self, email: str, password: str) -> Tuple[User, str]:
        """
        Handle email/password login: verify credentials, return JWT.
        
        Args:
            email: User email
            password: User password (plain text)
        
        Returns:
            Tuple of (User object, access token)
        
        Raises:
            InvalidCredentialsError: If email not found or password incorrect
            UserInactiveError: If user account is disabled
        """
        # 1. Find user by email via repository
        db_user = await self.repository.get_user_by_email(email)
        
        if not db_user:
            logger.warning(f"Login attempt with non-existent email: {email}")
            raise InvalidCredentialsError()
        
        # 2. Verify password
        if not self.verify_password(password, db_user.hashed_password):
            logger.warning(f"Login attempt with incorrect password for: {email}")
            raise InvalidCredentialsError()
        
        # 3. Check if user is active
        if not db_user.is_active:
            logger.warning(f"Login attempt for inactive user: {email}")
            raise UserInactiveError()
        
        # 4. Generate JWT token
        access_token = self.create_access_token(db_user.id)
        logger.info(f"Login successful: {email} (ID: {db_user.id})")
        
        return db_user, access_token