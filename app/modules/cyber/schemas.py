"""
Cyber Module Schemas

Pydantic models for CyberScout API requests and responses.
"""

from enum import Enum
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from app.modules.cyber.models import CyberCategory


class CyberModuleBase(BaseModel):
    id: str = Field(..., description="Module ID (e.g., mod_morse)")
    title: str = Field(..., description="Cyber module title")
    original_title: str = Field(..., description="Original scout title")
    difficulty: int = Field(..., description="Difficulty 1-4")
    min_read_seconds: int = Field(..., description="Minimum intel read seconds")
    intel_content: Dict[str, Any] = Field(..., description="Intel briefing content")


class CyberModuleResponse(CyberModuleBase):
    model_config = {"from_attributes": True}


class CyberModuleListResponse(BaseModel):
    total: int = Field(..., description="Total modules")
    modules: list[CyberModuleResponse] = Field(..., description="Module list")


class CyberLevelStatus(BaseModel):
    level: int = Field(..., description="Level number")
    stars: int = Field(0, description="Stars earned (0-3)")
    score: int = Field(0, description="Score for level")
    is_completed: bool = Field(False, description="Level completion")
    is_locked: bool = Field(False, description="Level locked status")


class CyberLevelsResponse(BaseModel):
    module_id: str = Field(..., description="Module ID")
    levels: list[CyberLevelStatus] = Field(..., description="Level status list")


class CyberChallengeResponse(BaseModel):
    """Response for a cyber challenge"""
    id: str = Field(..., description="Challenge ID")
    module_id: Optional[str] = Field(None, description="Module ID")
    level: int = Field(1, description="Level number")
    category: CyberCategory = Field(..., description="Challenge category")
    difficulty: int = Field(..., description="Difficulty 1-5")
    encrypted_data: Dict[str, Any] = Field(..., description="Encrypted payload data")
    decrypted_answer: Optional[str] = Field(None, description="Decrypted answer")
    xp_reward: int = Field(..., description="XP reward when solved")

    model_config = {"from_attributes": True}


class CyberLevelQuestionsResponse(BaseModel):
    module_id: str = Field(..., description="Module ID")
    level: int = Field(..., description="Level number")
    total: int = Field(..., description="Total questions")
    questions: list[CyberChallengeResponse] = Field(..., description="Questions list")


class CyberDashboardResponse(BaseModel):
    """Response for cyber dashboard stats"""
    hack_level: str = Field(..., description="Current hack level for user")
    decrypted_messages: int = Field(..., description="Total decrypted messages count")


class CyberSubmitRequest(BaseModel):
    """Request to submit decrypted answer"""
    module_id: str = Field(..., description="Module ID")
    level: int = Field(..., description="Level number")
    correct_answers: int = Field(..., description="Correct answers count")
    total_questions: int = Field(..., description="Total questions in level")
    score: int = Field(0, description="Score for level")


class CyberSubmitResponse(BaseModel):
    """Response for submission result"""
    success: bool = Field(..., description="Whether answer is correct")
    xp_gained: int = Field(..., description="XP gained from submission")
    new_total_xp: int = Field(..., description="Updated total XP")
    level_up: bool = Field(..., description="Whether hack level increased")
    message: str = Field(..., description="Result message")
    stars: int = Field(0, description="Stars awarded")
    unlocked_next_level: bool = Field(False, description="Next level unlocked")


# ============ SANDI PRAMUKA SCHEMAS ============

class SandiBase(BaseModel):
    """Base schema for Sandi Type"""
    codename: str = Field(..., description="Unique codename (e.g., 'morse', 'an_rot13')")
    name: str = Field(..., description="Display name (e.g., 'Morse Code')")
    description: Optional[str] = Field(None, description="Description of the cipher")
    difficulty: int = Field(1, ge=1, le=4, description="Difficulty level 1-4")
    category: str = Field(..., description="Category: encoding, substitution, transposition, visual")


class SandiCreate(SandiBase):
    """Schema for creating Sandi Type"""
    pass


class SandiResponse(SandiBase):
    """Schema for Sandi Type response"""
    id: int = Field(..., description="Sandi Type ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


class SandiListResponse(BaseModel):
    """Response for list of Sandi Types"""
    total: int = Field(..., description="Total Sandi types")
    sandi_types: list[SandiResponse] = Field(..., description="List of Sandi types")


class OperationMode(str, Enum):
    """Operation mode for encryption/decryption"""
    ENCRYPT = "ENCRYPT"
    DECRYPT = "DECRYPT"


class CyberToolRequest(BaseModel):
    """Request for encryption/decryption tool"""
    text: str = Field(..., description="Input text to process", min_length=1, max_length=1000)
    operation_mode: OperationMode = Field(..., description="ENCRYPT or DECRYPT")
    sandi_codename: str = Field(..., description="Sandi codename (e.g., 'morse', 'an_rot13')")


class CyberToolResponse(BaseModel):
    """Response from encryption/decryption tool"""
    result: str = Field(..., description="Encrypted or decrypted result")
    sandi_codename: str = Field(..., description="Sandi codename used")
    operation_mode: str = Field(..., description="Operation mode performed")


class SandiQuestionResponse(BaseModel):
    """Response for Sandi exam question"""
    id: int = Field(..., description="Question ID")
    sandi_id: int = Field(..., description="Sandi Type ID")
    question_text: str = Field(..., description="Question text")
    encrypted_text: str = Field(..., description="Encrypted text to decode")
    hint: Optional[str] = Field(None, description="Optional hint")
    difficulty: int = Field(..., description="Difficulty level")
    xp_reward: int = Field(..., description="XP reward for correct answer")

    model_config = {"from_attributes": True}


class SandiExamResponse(BaseModel):
    """Response for Sandi exam questions"""
    sandi_id: int = Field(..., description="Sandi Type ID")
    sandi_name: str = Field(..., description="Sandi name")
    total: int = Field(..., description="Total questions")
    questions: list[SandiQuestionResponse] = Field(..., description="List of questions")