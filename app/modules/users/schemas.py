from pydantic import BaseModel
from typing import Optional, List

class PublicUserResponse(BaseModel):
    """
    Schema for public read-only user profile.
    CRITICAL: Never include sensitive data like email, password, or billing info here.
    """
    id: int
    full_name: Optional[str] = None
    picture_url: Optional[str] = None
    total_xp: int = 0
    streak: int = 0
    hack_level: str = "Script Kiddie"
    tkk_badges: List[str] = []
