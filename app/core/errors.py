"""
Centralized Exception System

Base exception class and domain-specific exceptions for clean error handling.
All services should raise domain exceptions instead of HTTPException.
"""

from typing import Optional, Any, Dict
from fastapi import HTTPException, status


class AppException(Exception):
    """
    Base exception class for all application errors.
    
    Attributes:
        message: Human-readable error message
        status_code: HTTP status code
        error_code: Application-specific error code
        details: Additional error details (optional)
    """
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API response"""
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details
            }
        }


# ==================== AUTH EXCEPTIONS ====================

class AuthException(AppException):
    """Base exception for authentication-related errors"""
    status_code = status.HTTP_401_UNAUTHORIZED


class InvalidCredentialsError(AuthException):
    """Invalid email or password"""
    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="INVALID_CREDENTIALS"
        )


class UserNotFoundError(AuthException):
    """User not found"""
    def __init__(self, email: Optional[str] = None):
        message = f"User not found" + (f": {email}" if email else "")
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="USER_NOT_FOUND"
        )


class UserAlreadyExistsError(AuthException):
    """User already exists (registration conflict)"""
    def __init__(self, email: str):
        super().__init__(
            message=f"Email already registered: {email}",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="USER_ALREADY_EXISTS",
            details={"email": email}
        )


class InvalidTokenError(AuthException):
    """Invalid or expired token"""
    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="INVALID_TOKEN"
        )


class UserInactiveError(AuthException):
    """User account is disabled"""
    def __init__(self):
        super().__init__(
            message="User account is disabled",
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="USER_INACTIVE"
        )


# ==================== SKU EXCEPTIONS ====================

class SkuException(AppException):
    """Base exception for SKU-related errors"""
    status_code = status.HTTP_400_BAD_REQUEST


class TaskNotFoundError(SkuException):
    """SKU or Mission task not found"""
    def __init__(self, task_id: int):
        super().__init__(
            message=f"Task not found: {task_id}",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="TASK_NOT_FOUND",
            details={"task_id": task_id}
        )


class LevelNotFoundError(SkuException):
    """SKU level not found"""
    def __init__(self, level_id: int):
        super().__init__(
            message=f"SKU level not found: {level_id}",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="LEVEL_NOT_FOUND",
            details={"level_id": level_id}
        )


class MissionNotFoundError(SkuException):
    """Mission not found"""
    def __init__(self, mission_id: int):
        super().__init__(
            message=f"Mission not found: {mission_id}",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="MISSION_NOT_FOUND",
            details={"mission_id": mission_id}
        )


# ==================== TRAINING EXCEPTIONS ====================

class TrainingException(AppException):
    """Base exception for training-related errors"""
    status_code = status.HTTP_400_BAD_REQUEST


class SectionNotFoundError(TrainingException):
    """Training section not found"""
    def __init__(self, section_id: str):
        super().__init__(
            message=f"Training section not found: {section_id}",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="SECTION_NOT_FOUND",
            details={"section_id": section_id}
        )


class UnitNotFoundError(TrainingException):
    """Training unit not found"""
    def __init__(self, unit_id: str):
        super().__init__(
            message=f"Training unit not found: {unit_id}",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="UNIT_NOT_FOUND",
            details={"unit_id": unit_id}
        )


class LevelNotFoundError(TrainingException):
    """Training level not found"""
    def __init__(self, level_id: str):
        super().__init__(
            message=f"Training level not found: {level_id}",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="LEVEL_NOT_FOUND",
            details={"level_id": level_id}
        )


class QuestionNotFoundError(TrainingException):
    """Training question not found"""
    def __init__(self, question_id: str):
        super().__init__(
            message=f"Training question not found: {question_id}",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="QUESTION_NOT_FOUND",
            details={"question_id": question_id}
        )


# ==================== GENERIC EXCEPTIONS ====================

class NotFoundError(AppException):
    """Generic resource not found error"""
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            message=f"{resource} not found: {identifier}",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            details={"resource": resource, "identifier": str(identifier)}
        )


class ValidationError(AppException):
    """Validation error"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details=details or {}
        )


class InternalServerError(AppException):
    """Internal server error"""
    def __init__(self, message: str = "Internal server error", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_SERVER_ERROR",
            details=details or {}
        )
