"""
Final Canonical Question Schema

This module defines the single, canonical Question schema used by all question banks.
Designed for 10-year sustainability, large-scale datasets, and future extensibility.

Architectural Decisions:
1. Versioning: Explicit schema_version field enables future migrations and backward compatibility
2. Discriminated Union: Type-safe payload selection at parse time for performance and correctness
3. Normalized Answers: Single source of truth in 'answer' field prevents duplication and security issues
4. Extensibility: Controlled extension mechanism via 'extensions' field while maintaining strict validation

Question Types:
- multiple_choice: Select one correct answer from options
- matching: Match pairs of items (left-right pairs)
- true_false: True/False questions
- input: Text input (fill in the blank)
- ordering: Order items in correct sequence (word bank)
- image_choice: Select from image options (future-ready)

Schema Structure:
- Common fields: schema_version, id, level_id, order, type, difficulty, question, xp, time_limit, tags, extensions
- Type-specific payload: Different structure per question type (NO correct answers in payload)
- Type-specific answer: All correct answers live here (backend only, not sent to frontend)
"""

from enum import Enum
from typing import List, Optional, Dict, Any, Union, Literal, Annotated
from pydantic import BaseModel, Field, field_validator, model_validator, Discriminator


# ==================== ENUMS ====================

class QuestionType(str, Enum):
    """Supported question types"""
    MULTIPLE_CHOICE = "multiple_choice"
    MATCHING = "matching"
    TRUE_FALSE = "true_false"
    INPUT = "input"  # Also known as "fill_blank"
    ORDERING = "ordering"  # Also known as "word_bank"
    IMAGE_CHOICE = "image_choice"  # Future-ready


class Difficulty(str, Enum):
    """Question difficulty levels"""
    VERY_EASY = "very_easy"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


# ==================== TYPE-SPECIFIC PAYLOAD SCHEMAS ====================
# IMPORTANT: Payloads must NEVER contain correct answers.
# All answers live in the 'answer' field for security and single source of truth.

class MultipleChoicePayload(BaseModel):
    """Payload for multiple_choice questions (frontend-safe, no answers)"""
    # Discriminator field for Pydantic discriminated union
    type: Literal["multiple_choice"] = "multiple_choice"
    
    options: List[str] = Field(..., min_length=2, max_length=6, description="List of answer options (shuffled for display)")
    shuffle: bool = Field(default=True, description="Whether to shuffle options")
    
    @field_validator("options")
    @classmethod
    def validate_options(cls, v: List[str]) -> List[str]:
        if len(v) < 2:
            raise ValueError("multiple_choice must have at least 2 options")
        if len(v) > 6:
            raise ValueError("multiple_choice should have at most 6 options")
        return v


class MatchingPair(BaseModel):
    """A single pair for matching questions"""
    left: str = Field(..., min_length=1, description="Left side item")
    right: str = Field(..., min_length=1, description="Right side item")


class MatchingPayload(BaseModel):
    """Payload for matching questions (frontend-safe, no answers)"""
    # Discriminator field for Pydantic discriminated union
    type: Literal["matching"] = "matching"
    
    pairs: List[MatchingPair] = Field(..., min_length=2, max_length=8, description="List of pairs to match (shuffled for display)")
    shuffle: bool = Field(default=True, description="Whether to shuffle pairs")
    
    @field_validator("pairs")
    @classmethod
    def validate_pairs(cls, v: List[MatchingPair]) -> List[MatchingPair]:
        if len(v) < 2:
            raise ValueError("matching must have at least 2 pairs")
        if len(v) > 8:
            raise ValueError("matching should have at most 8 pairs")
        return v


class TrueFalsePayload(BaseModel):
    """Payload for true_false questions (frontend-safe, no answers)"""
    # Discriminator field for Pydantic discriminated union
    type: Literal["true_false"] = "true_false"
    
    # No additional fields needed - answer is in 'answer' field


class InputPayload(BaseModel):
    """Payload for input (fill_blank) questions (frontend-safe, no answers)"""
    # Discriminator field for Pydantic discriminated union
    type: Literal["input"] = "input"
    
    placeholder: Optional[str] = Field(default=None, description="Placeholder text for input field")
    case_sensitive: bool = Field(default=False, description="Whether answer is case-sensitive (hint only)")


class OrderingPayload(BaseModel):
    """Payload for ordering (word_bank) questions (frontend-safe, no answers)"""
    # Discriminator field for Pydantic discriminated union
    type: Literal["ordering"] = "ordering"
    
    items: List[str] = Field(..., min_length=2, max_length=10, description="Items to order (shuffled for display)")
    
    @field_validator("items")
    @classmethod
    def validate_items(cls, v: List[str]) -> List[str]:
        if len(v) < 2:
            raise ValueError("ordering must have at least 2 items")
        if len(v) > 10:
            raise ValueError("ordering should have at most 10 items")
        return v


class ImageChoicePayload(BaseModel):
    """Payload for image_choice questions (frontend-safe, no answers)"""
    # Discriminator field for Pydantic discriminated union
    type: Literal["image_choice"] = "image_choice"
    
    image_urls: List[str] = Field(..., min_length=2, max_length=6, description="List of image URLs (shuffled for display)")
    
    @field_validator("image_urls")
    @classmethod
    def validate_image_urls(cls, v: List[str]) -> List[str]:
        if len(v) < 2:
            raise ValueError("image_choice must have at least 2 images")
        if len(v) > 6:
            raise ValueError("image_choice should have at most 6 images")
        return v


# ==================== TYPE-SPECIFIC ANSWER SCHEMAS ====================
# All correct answers live here - single source of truth for backend verification.
# These are NEVER sent to the frontend.

class MultipleChoiceAnswer(BaseModel):
    """Answer for multiple_choice questions (backend only)"""
    correct_index: int = Field(..., ge=0, description="Index of correct option in payload.options")
    
    @model_validator(mode="after")
    def validate_index(self):
        # Note: This validation requires access to payload, handled in Question model
        return self


class MatchingAnswer(BaseModel):
    """Answer for matching questions (backend only)"""
    correct_pairs: List[Dict[str, str]] = Field(..., description="List of correct pair mappings {left: right}")


class TrueFalseAnswer(BaseModel):
    """Answer for true_false questions (backend only)"""
    correct_answer: bool = Field(..., description="The correct boolean answer")


class InputAnswer(BaseModel):
    """Answer for input questions (backend only)"""
    correct_answer: str = Field(..., min_length=1, description="The correct text answer")
    alternatives: Optional[List[str]] = Field(default=None, description="Alternative acceptable answers")


class OrderingAnswer(BaseModel):
    """Answer for ordering questions (backend only)"""
    correct_order: List[str] = Field(..., description="Correct order of items (must match payload.items)")


class ImageChoiceAnswer(BaseModel):
    """Answer for image_choice questions (backend only)"""
    correct_index: int = Field(..., ge=0, description="Index of correct image in payload.image_urls")


# ==================== MAIN QUESTION SCHEMA ====================

class Question(BaseModel):
    """
    Final canonical Question schema with 10-year sustainability features.
    
    Key Features:
    - Versioning: schema_version enables future migrations
    - Type Safety: Discriminated union ensures payload matches type at parse time
    - Security: Answers separated from payload (never sent to frontend)
    - Extensibility: Controlled extension via 'extensions' field
    
    This schema is used to validate all questions in the learning dataset.
    All question banks must conform to this structure.
    
    Extension Mechanism:
    - Use 'extensions' field for plugin-specific or experimental features
    - Keep 'extra = "forbid"' to prevent accidental field pollution
    - Document any extension keys in your plugin documentation
    """
    
    # ==================== VERSIONING ====================
    # Forward-compatible versioning: Enables future schema migrations
    # When schema changes, increment version and add migration logic
    schema_version: str = Field(
        default="1.0",
        description="Schema version for forward compatibility and migrations"
    )
    
    # ==================== CORE IDENTIFICATION ====================
    id: str = Field(..., min_length=1, description="Unique question identifier (stable)")
    level_id: str = Field(..., min_length=1, description="ID of the level this question belongs to")
    order: int = Field(..., ge=1, description="Sequence number within the level")
    
    # ==================== QUESTION METADATA ====================
    type: QuestionType = Field(..., description="Question type (discriminator for payload union)")
    difficulty: Difficulty = Field(..., description="Question difficulty level")
    question: str = Field(..., min_length=1, description="Question text")
    
    # ==================== TYPE-SPECIFIC PAYLOAD (FRONTEND-SAFE) ====================
    # Discriminated union: Pydantic selects correct payload type based on 'type' field
    # This fails fast at parse time, improving performance on large datasets
    # Payloads NEVER contain correct answers (security by design)
    payload: Annotated[
        Union[
            MultipleChoicePayload,
            MatchingPayload,
            TrueFalsePayload,
            InputPayload,
            OrderingPayload,
            ImageChoicePayload
        ],
        Discriminator("type")
    ] = Field(..., description="Type-specific question data (frontend-safe, no answers)")
    
    # ==================== TYPE-SPECIFIC ANSWER (BACKEND ONLY) ====================
    # Single source of truth: All correct answers live here
    # This field is NEVER sent to the frontend (security)
    # Optional globally but required per type (see validator below)
    # This future-proofs the schema for survey/discussion/diagnostic questions
    answer: Optional[Union[
        MultipleChoiceAnswer,
        MatchingAnswer,
        TrueFalseAnswer,
        InputAnswer,
        OrderingAnswer,
        ImageChoiceAnswer
    ]] = Field(default=None, description="Correct answer (backend verification only, never sent to frontend)")
    
    # ==================== SCORING AND TIMING ====================
    xp: int = Field(..., ge=1, le=100, description="XP points awarded for correct answer")
    time_limit: Optional[int] = Field(default=None, ge=5, le=300, description="Time limit in seconds (optional)")
    
    # ==================== METADATA ====================
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    
    # ==================== EXTENSIBILITY ====================
    # Controlled extension mechanism: Allows plugins/experiments without polluting core schema
    # Use this for: A/B testing flags, plugin-specific data, experimental features
    # Keep 'extra = "forbid"' to prevent accidental field pollution
    # Extension keys must be namespaced (see field_validator below)
    extensions: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extension field for plugins and experimental features. "
                   "Use namespaced keys (e.g., 'plugin_name.feature') to avoid conflicts."
    )
    
    # ==================== VALIDATORS ====================
    
    @model_validator(mode="before")
    def validate_schema_version_gate(cls, data: Any):
        """
        Enforce schema version gate: Reject unsupported versions.
        
        This ensures future versions like "2.0" are not silently accepted.
        When a new version is introduced, update the allowed set and add migration logic.
        Prevents silent data corruption from version mismatches.
        """
        if isinstance(data, dict):
            version = data.get("schema_version", "1.0")
            allowed_versions = {"1.0"}
            
            if version not in allowed_versions:
                raise ValueError(
                    f"Unsupported schema_version: {version}. "
                    f"Supported versions: {', '.join(allowed_versions)}"
                )
        
        return data
    
    @field_validator("extensions")
    @classmethod
    def validate_extensions_namespaced(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enforce namespaced extension keys to prevent unstructured data pollution.
        
        Rules:
        - Each key must contain a dot "." (namespace.rule format)
        - Keys cannot start with "core." (reserved namespace)
        
        This prevents extensions from becoming an unstructured junk field over time
        and maintains clear ownership of extension data.
        """
        for key in v.keys():
            # Must contain a dot for namespacing
            if "." not in key:
                raise ValueError(
                    f"Extension key '{key}' must be namespaced (e.g., 'plugin.feature'). "
                    f"Use format: 'namespace.key'"
                )
            
            # Cannot use reserved "core." namespace
            if key.startswith("core."):
                raise ValueError(
                    f"Extension key '{key}' cannot use reserved namespace 'core.*'. "
                    f"Use a different namespace (e.g., 'plugin.feature')."
                )
        
        return v
    
    @model_validator(mode="after")
    def validate_payload_type_consistency(self):
        """
        Guard against payload.type vs Question.type mismatch.
        
        Both fields exist:
        - Question.type (enum)
        - payload.type (Literal discriminator)
        
        This prevents double-source-of-truth corruption where payload.type
        doesn't match Question.type, which could cause validation confusion.
        """
        if hasattr(self.payload, 'type'):
            payload_type = self.payload.type
            question_type = self.type.value if isinstance(self.type, QuestionType) else str(self.type)
            
            if payload_type != question_type:
                raise ValueError(
                    f"Payload type '{payload_type}' does not match Question.type '{question_type}'. "
                    f"These must be consistent to prevent validation errors."
                )
        
        return self
    
    @model_validator(mode="after")
    def validate_answer_required_per_type(self):
        """
        Make answer optional globally but required per type.
        
        This future-proofs the schema for question types that don't need answers:
        - Survey questions (opinion-based)
        - Discussion prompts (no correct answer)
        - Diagnostic questions (exploratory)
        
        Current question types all require answers, but this allows future extensibility.
        """
        # Types that REQUIRE answers (all current types)
        types_requiring_answer = {
            QuestionType.MULTIPLE_CHOICE,
            QuestionType.MATCHING,
            QuestionType.TRUE_FALSE,
            QuestionType.INPUT,
            QuestionType.ORDERING,
            QuestionType.IMAGE_CHOICE,
        }
        
        if self.type in types_requiring_answer and self.answer is None:
            raise ValueError(
                f"Question type '{self.type}' requires an answer. "
                f"Provide an answer in the 'answer' field."
            )
        
        return self
    
    @model_validator(mode="after")
    def validate_answer_type_match(self):
        """
        Ensure answer type matches question type.
        This is a safety check - discriminated union should catch mismatches earlier.
        Only validates if answer is provided (answer can be None for future question types).
        """
        if self.answer is None:
            return self  # Skip validation if answer is None (handled by validate_answer_required_per_type)
        
        answer_type_map = {
            QuestionType.MULTIPLE_CHOICE: MultipleChoiceAnswer,
            QuestionType.MATCHING: MatchingAnswer,
            QuestionType.TRUE_FALSE: TrueFalseAnswer,
            QuestionType.INPUT: InputAnswer,
            QuestionType.ORDERING: OrderingAnswer,
            QuestionType.IMAGE_CHOICE: ImageChoiceAnswer,
        }
        
        expected_answer_type = answer_type_map.get(self.type)
        if expected_answer_type and not isinstance(self.answer, expected_answer_type):
            raise ValueError(
                f"Answer type mismatch: question type '{self.type}' requires "
                f"{expected_answer_type.__name__}, got {type(self.answer).__name__}"
            )
        
        return self
    
    @model_validator(mode="after")
    def validate_answer_payload_consistency(self):
        """
        Validate that answer is consistent with payload data.
        This ensures data integrity across payload and answer.
        Only validates if answer is provided.
        """
        if self.answer is None:
            return self  # Skip validation if answer is None
        
        # Multiple choice: answer index must be valid
        if self.type == QuestionType.MULTIPLE_CHOICE:
            if isinstance(self.payload, MultipleChoicePayload) and isinstance(self.answer, MultipleChoiceAnswer):
                if self.answer.correct_index >= len(self.payload.options):
                    raise ValueError(
                        f"correct_index {self.answer.correct_index} must be less than "
                        f"number of options ({len(self.payload.options)})"
                    )
        
        # Ordering: answer order must match payload items
        if self.type == QuestionType.ORDERING:
            if isinstance(self.payload, OrderingPayload) and isinstance(self.answer, OrderingAnswer):
                if set(self.answer.correct_order) != set(self.payload.items):
                    raise ValueError(
                        "correct_order must contain the same items as payload.items"
                    )
                if len(self.answer.correct_order) != len(self.payload.items):
                    raise ValueError(
                        "correct_order must have the same length as payload.items"
                    )
        
        # Image choice: answer index must be valid
        if self.type == QuestionType.IMAGE_CHOICE:
            if isinstance(self.payload, ImageChoicePayload) and isinstance(self.answer, ImageChoiceAnswer):
                if self.answer.correct_index >= len(self.payload.image_urls):
                    raise ValueError(
                        f"correct_index {self.answer.correct_index} must be less than "
                        f"number of images ({len(self.payload.image_urls)})"
                    )
        
        return self
    
    @model_validator(mode="after")
    def validate_no_answers_in_payload(self):
        """
        Security check: Ensure payload never contains correct answers.
        This prevents accidental answer leakage to frontend.
        """
        # Check for common answer field names in payload
        forbidden_fields = ['correct_answer', 'correct_index', 'correct_order', 'answer']
        
        if isinstance(self.payload, BaseModel):
            payload_dict = self.payload.model_dump()
            for field_name in forbidden_fields:
                if field_name in payload_dict:
                    raise ValueError(
                        f"Security violation: Payload must not contain '{field_name}'. "
                        f"All answers must be in the 'answer' field only."
                    )
        
        return self
    
    class Config:
        """Pydantic configuration"""
        use_enum_values = True
        extra = "forbid"  # Reject unknown fields (except via 'extensions')
        str_strip_whitespace = True
        # Enable discriminated union validation
        validate_assignment = True