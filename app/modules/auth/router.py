"""
Auth Module Router

FastAPI endpoints for authentication operations.
Router only handles HTTP layer: request parsing, service calls, response formatting.
All business logic is in service layer.
All database access is in repository layer.
Exceptions are handled by global exception handler in main.py.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import get_current_user
from app.modules.auth.service import AuthService
from app.modules.auth import schemas
from app.core.response import success

router = APIRouter()


def get_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Dependency injection for AuthService"""
    return AuthService(db)


@router.post("/register")
async def register(
    user_in: schemas.UserCreate,
    service: AuthService = Depends(get_service)
):
    """
    Register a new user with username and password.
    
    Args:
        user_in: User registration data (name, username, password, optional gugus_depan)
        service: Injected AuthService
    
    Returns:
        Standard API response with access_token and user data
    
    Raises:
        UserAlreadyExistsError: If username already exists (handled by global handler)
    """
    user = await service.create_user(user_in)
    access_token = service.create_access_token(user.id)
    
    return success(
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "id": user.id,
            "name": user.full_name,
            "username": user.email,  # Using email as username for now
            "is_pro": False,
        },
        message="User registered successfully"
    )


@router.post("/google")
async def google_sign_in(
    request: schemas.GoogleTokenRequest,
    service: AuthService = Depends(get_service)
):
    """
    Google Sign-In endpoint.
    
    Verifies the Google ID token from frontend, then either:
    - Creates a new user (if email doesn't exist)
    - Returns existing user
    
    Both cases return JWT access token.
    
    Args:
        request: GoogleTokenRequest with id_token
        service: Injected AuthService
    
    Returns:
        Standard API response with GoogleAuthResponse data
    
    Raises:
        InvalidTokenError: If token verification fails (handled by global handler)
        UserInactiveError: If user account is disabled (handled by global handler)
    """
    user, access_token = await service.google_sign_in(request.id_token)
    
    return success(
        data=schemas.GoogleAuthResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            picture_url=getattr(user, 'picture_url', None),
            access_token=access_token,
            token_type="bearer"
        ),
        message="Google sign-in successful"
    )


@router.post("/login")
async def login_with_email(
    request: schemas.LoginRequest,
    service: AuthService = Depends(get_service)
):
    """
    Username/Password Login endpoint.
    
    Verifies user credentials and returns JWT access token.
    
    Args:
        request: LoginRequest with username and password
        service: Injected AuthService
    
    Returns:
        Standard API response with access_token and user data
    
    Raises:
        InvalidCredentialsError: If credentials are invalid (handled by global handler)
        UserInactiveError: If user account is disabled (handled by global handler)
    """
    user, access_token = await service.login_with_email(
        request.email, request.password
    )
    
    return success(
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "id": user.id,
            "name": user.full_name,
            "username": user.email,  # Using email as username for now
            "is_pro": False,
        },
        message="Login successful"
    )