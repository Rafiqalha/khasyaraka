from pydantic import BaseModel, ConfigDict
from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime

class TKKLevelEnum(str, Enum):
    PURWA = "purwa"
    MADYA = "madya"
    UTAMA = "utama"

class TKKBase(BaseModel):
    slug: str
    name: str  # Enriched from metadata
    description: str # Enriched from metadata
    level: TKKLevelEnum
    attained_at: datetime
    image_url: Optional[str] = None # Enriched from metadata

    model_config = ConfigDict(from_attributes=True)

class TKKSubmission(BaseModel):
    tkk_slug: str
    answers: Dict[str, Any] # Flexible key-value for answers

class TKKVerificationResult(BaseModel):
    success: bool
    score: float
    message: str
    awarded_level: Optional[TKKLevelEnum] = None
    previous_level: Optional[TKKLevelEnum] = None

class UserTKKProfile(BaseModel):
    user_id: int
    achieved_tkks: List[TKKBase]
