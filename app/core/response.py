"""
Standard API Response Envelope

Provides consistent response format for all API endpoints.
"""

from typing import Any, Optional, Dict, Generic, TypeVar
from pydantic import BaseModel, field_serializer
from datetime import datetime

T = TypeVar('T')


class APIResponse(BaseModel, Generic[T]):
    """
    Standard API response envelope.
    
    All API responses follow this structure:
    {
        "success": true/false,
        "data": {...},
        "message": "...",
        "timestamp": "...",
        "meta": {...}
    }
    """
    success: bool
    data: Optional[T] = None
    message: Optional[str] = None
    timestamp: datetime = datetime.utcnow()
    meta: Optional[Dict[str, Any]] = None

    @field_serializer('timestamp')
    def serialize_timestamp(self, value: datetime) -> str:
        """Serialize datetime to ISO format string"""
        return value.isoformat()
    
    def model_dump_serializable(self) -> Dict[str, Any]:
        """
        Dump model to dict with proper datetime serialization.
        Recursively handles datetime objects in nested structures.
        """
        def serialize_value(v: Any) -> Any:
            """Recursively serialize datetime objects"""
            if isinstance(v, datetime):
                return v.isoformat()
            elif isinstance(v, dict):
                return {k: serialize_value(val) for k, val in v.items()}
            elif isinstance(v, list):
                return [serialize_value(item) for item in v]
            else:
                return v
        
        data = self.model_dump(exclude_none=True)
        return serialize_value(data)


def success(
    data: Any = None,
    message: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a successful API response.
    
    Args:
        data: Response data (can be any serializable type)
        message: Optional success message
        meta: Optional metadata (pagination, etc.)
    
    Returns:
        Dictionary with standard response format
    
    Example:
        return success(data={"user_id": 1}, message="User created successfully")
    """
    return APIResponse(
        success=True,
        data=data,
        message=message,
        meta=meta
    ).model_dump_serializable()


def error(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create an error API response.
    
    Args:
        message: Error message
        error_code: Optional error code
        details: Optional error details
    
    Returns:
        Dictionary with standard error response format
    
    Example:
        return error(message="User not found", error_code="USER_NOT_FOUND")
    """
    return APIResponse(
        success=False,
        message=message,
        meta={
            "error_code": error_code,
            "details": details
        } if error_code or details else None
    ).model_dump_serializable()
