"""Common API schemas Reusable schemas for API requests and responses"""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


class APIResponse(BaseModel):
    """Standard response wrapper for all API endpoints"""
    success: bool = Field(True, description="Request success status")
    data: Any = Field(..., description="Response data")
    message: Optional[str] = Field(None, description="Optional message")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {},
                "message": "Data retrieved successfully",
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }


class ErrorResponse(BaseModel):
    """Error response format"""
    success: bool = Field(False, description="Always False for errors")
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Detailed error message")
    detail: Optional[str] = Field(None, description="Additional details")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Error timestamp"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "ValidationError",
                "message": "Invalid symbol format",
                "detail": "Symbol must be at least 3 characters",
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }
