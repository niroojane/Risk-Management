"""
Common Pydantic models
Reusable models for the entire API
"""
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class TimeInterval(str, Enum):
    """Supported time intervals"""
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"
    ONE_WEEK = "1w"
    ONE_MONTH = "1M"


class QuoteAsset(str, Enum):
    """Supported quote assets"""
    USDT = "USDT"
    BUSD = "BUSD"
    BTC = "BTC"
    ETH = "ETH"


class ReturnType(str, Enum):
    """Return calculation types"""
    SIMPLE = "simple"
    LOGARITHMIC = "log"


class APIResponse(BaseModel):
    """
    Standard response wrapper for all API endpoints
    Data wrapper format
    """
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
    """
    Error response format
    """
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
