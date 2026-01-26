from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserCreate(BaseModel):
    name: str = Field(..., description="User's full name")
    username: str = Field(..., description="Username (will be used as email)")
    password: str
    gugus_depan: Optional[str] = None

    def get_full_name(self) -> str:
        return self.name

    def get_email(self) -> str:
        # Use username as email for now (can be changed later)
        return self.username.lower().strip()

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_active: bool

    class Config:
        from_attributes = True


# ============ GOOGLE OAUTH2 SCHEMAS ============

class GoogleTokenRequest(BaseModel):
    """Request payload for Google Sign-In (contains id_token from Google)"""
    id_token: str


class TokenResponse(BaseModel):
    """Generic token response"""
    access_token: str
    token_type: str = "bearer"


class GoogleAuthResponse(BaseModel):
    """Response after successful Google authentication"""
    id: int
    email: EmailStr
    full_name: str
    picture_url: Optional[str] = None
    access_token: str
    token_type: str = "bearer"

    class Config:
        from_attributes = True


# ============ EMAIL/PASSWORD LOGIN SCHEMAS ============

class LoginRequest(BaseModel):
    """Request payload for email/password login"""
    username: str = Field(..., description="Username (will be used as email)")
    password: str

    @property
    def email(self) -> str:
        return self.username.lower().strip()


class LoginResponse(BaseModel):
    """Response after successful email/password login"""
    id: int
    email: EmailStr
    full_name: str
    access_token: str
    token_type: str = "bearer"

    class Config:
        from_attributes = True