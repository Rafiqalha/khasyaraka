"""
Training Module Schemas

Pydantic models for Training API requests and responses.
Includes both legacy Supabase schemas and new SQLAlchemy-based schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

# ==================== LEGACY SCHEMAS (Supabase - for backward compatibility) ====================
# These are kept for compatibility with old service-based endpoints

class QuestionSchema(BaseModel):
    """Legacy schema for Supabase-based questions"""
    id: int
    lesson_id: int
    question: str
    type: str          # multiple_choice / true_false
    options: List[str] # Disimpan sebagai JSONB di Supabase
    correct_index: int
    explanation: Optional[str] = None


class LessonSchema(BaseModel):
    """Legacy schema for Supabase-based lessons"""
    id: int
    path_id: int       # Foreign Key ke training_paths
    title: str
    description: str
    icon_name: str
    status: str = "locked" # locked, active, completed
    stars: int = 0
    order_index: int


class PathSchema(BaseModel):
    """Legacy schema for Supabase-based paths"""
    id: int
    title: str
    description: str
    color_hex: str
    order_index: int
    lessons: List[LessonSchema] = [] # List kosong default


# ==================== NEW SCHEMAS (SQLAlchemy-based) ====================

# ==================== SECTION SCHEMAS ====================

class TrainingSectionBase(BaseModel):
    """Base schema for Training Section"""
    id: str = Field(..., description="Section ID (e.g., 'puk')")
    title: str = Field(..., description="Section title")
    description: Optional[str] = Field(None, description="Section description")
    tier: str = Field("free", description="Tier: 'free' or 'premium'")
    order: int = Field(1, description="Display order")


class TrainingSectionResponse(TrainingSectionBase):
    """Response schema for Training Section"""
    is_active: bool = Field(True, description="Whether section is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    model_config = {"from_attributes": True}


class TrainingSectionWithUnits(TrainingSectionResponse):
    """Section with nested units"""
    units: List["TrainingUnitResponse"] = Field(default_factory=list, description="List of units in this section")


# ==================== UNIT SCHEMAS ====================

class TrainingUnitBase(BaseModel):
    """Base schema for Training Unit"""
    id: str = Field(..., description="Unit ID (e.g., 'puk_unit_1')")
    section_id: str = Field(..., description="Parent section ID")
    title: str = Field(..., description="Unit title")
    description: Optional[str] = Field(None, description="Unit description")
    order: int = Field(1, description="Display order")
    total_levels: int = Field(0, description="Total number of levels in this unit")


class TrainingUnitResponse(TrainingUnitBase):
    """Response schema for Training Unit"""
    is_active: bool = Field(True, description="Whether unit is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    model_config = {"from_attributes": True}


class TrainingUnitWithLevels(TrainingUnitResponse):
    """Unit with nested levels"""
    levels: List["TrainingLevelResponse"] = Field(default_factory=list, description="List of levels in this unit")


# ==================== LEVEL SCHEMAS ====================

class TrainingLevelBase(BaseModel):
    """Base schema for Training Level"""
    id: str = Field(..., description="Level ID (e.g., 'puk_u1_l1')")
    unit_id: str = Field(..., description="Parent unit ID")
    level_number: int = Field(..., description="Level number (1, 2, 3, ...)")
    difficulty: str = Field("easy", description="Difficulty: very_easy, easy, medium, hard")
    total_questions: int = Field(5, description="Total questions in this level")
    min_correct: int = Field(4, description="Minimum correct answers to pass")
    xp_reward: int = Field(10, description="XP reward for completing level")
    unlock_rule: Optional[Dict[str, Any]] = Field(None, description="Unlock rule JSON")


class TrainingLevelResponse(TrainingLevelBase):
    """Response schema for Training Level"""
    is_active: bool = Field(True, description="Whether level is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    model_config = {"from_attributes": True}


class TrainingLevelWithQuestions(TrainingLevelResponse):
    """Level with nested questions"""
    questions: List["TrainingQuestionResponse"] = Field(default_factory=list, description="List of questions in this level")


# ==================== QUESTION SCHEMAS ====================

class TrainingQuestionBase(BaseModel):
    """Base schema for Training Question"""
    id: str = Field(..., description="Question ID (e.g., 'q_puk_u1_l1_01')")
    level_id: str = Field(..., description="Parent level ID")
    type: str = Field(..., description="Question type: multiple_choice, matching, fill_blank, etc.")
    question: str = Field(..., description="Question text")
    payload: Dict[str, Any] = Field(..., description="Question-specific data (options, pairs, etc.)")
    xp: int = Field(2, description="XP reward for correct answer")
    order: int = Field(1, description="Display order")


class TrainingQuestionResponse(TrainingQuestionBase):
    """Response schema for Training Question"""
    is_active: bool = Field(True, description="Whether question is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    model_config = {"from_attributes": True}


# ==================== LIST RESPONSE SCHEMAS ====================

class SectionListResponse(BaseModel):
    """Response for list of sections"""
    total: int = Field(..., description="Total number of sections")
    sections: List[TrainingSectionResponse] = Field(..., description="List of sections")


class UnitListResponse(BaseModel):
    """Response for list of units"""
    total: int = Field(..., description="Total number of units")
    section_id: str = Field(..., description="Parent section ID")
    units: List[TrainingUnitResponse] = Field(..., description="List of units")


class LevelListResponse(BaseModel):
    """Response for list of levels"""
    total: int = Field(..., description="Total number of levels")
    unit_id: str = Field(..., description="Parent unit ID")
    levels: List[TrainingLevelResponse] = Field(..., description="List of levels")


class QuestionListResponse(BaseModel):
    """Response for list of questions"""
    total: int = Field(..., description="Total number of questions")
    level_id: str = Field(..., description="Parent level ID")
    questions: List[TrainingQuestionResponse] = Field(..., description="List of questions")


# ==================== LEARNING PATH SCHEMAS ====================

class PathLevelSchema(BaseModel):
    """Level schema for learning path response"""
    level_id: str = Field(..., description="Level ID")
    title: str = Field(..., description="Level title")
    level_number: int = Field(..., description="Level number")
    difficulty: str = Field(..., description="Difficulty level")
    xp_reward: int = Field(..., description="XP reward")
    status: str = Field("unlocked", description="Level status (hardcoded as unlocked)")


class PathUnitSchema(BaseModel):
    """Unit schema for learning path response"""
    unit_id: str = Field(..., description="Unit ID")
    unit_title: str = Field(..., description="Unit title")
    order: int = Field(..., description="Display order")
    levels: List[PathLevelSchema] = Field(default_factory=list, description="Levels in this unit")


class LearningPathResponse(BaseModel):
    """Response schema for learning path endpoint"""
    section_id: str = Field(..., description="Section ID")
    section_title: str = Field(..., description="Section title")
    units: List[PathUnitSchema] = Field(default_factory=list, description="Units in this section")


# Update forward references for nested schemas
TrainingSectionWithUnits.model_rebuild()
TrainingUnitWithLevels.model_rebuild()
TrainingLevelWithQuestions.model_rebuild()
