"""Positions API schemas Request and response schemas for positions endpoint"""
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field, field_validator

from app.common import APIResponse


class PositionsRequest(BaseModel):
    """Request parameters for positions endpoint"""
    symbols: List[str] = Field(..., description="List of trading symbols", min_length=1)
    start_date: datetime = Field(..., description="Start date for historical data")
    end_date: datetime = Field(..., description="End date for historical data")

    @field_validator('symbols')
    @classmethod
    def validate_symbols(cls, v: List[str]) -> List[str]:
        """Validate and uppercase symbols"""
        if not v:
            raise ValueError("At least one symbol is required")
        return [s.upper() for s in v]

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v: datetime, info) -> datetime:
        """Validate end_date is after start_date"""
        if 'start_date' in info.data and v <= info.data['start_date']:
            raise ValueError("end_date must be after start_date")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "symbols": ["BTCUSDT", "ETHUSDT"],
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-12-31T23:59:59Z"
            }
        }


class PositionDataPoint(BaseModel):
    """Single position data point"""
    date: datetime = Field(..., description="Position timestamp")
    symbol: str = Field(..., description="Trading symbol")
    position: float = Field(..., description="Position value in quote asset (USDT)", ge=0)

    class Config:
        json_schema_extra = {
            "example": {
                "date": "2024-01-01T00:00:00Z",
                "symbol": "BTCUSDT",
                "position": 5000.00
            }
        }


class PositionsResponse(APIResponse):
    """Response for positions endpoint"""
    data: List[PositionDataPoint] = Field(..., description="Position data for requested assets")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": [
                    {
                        "date": "2024-01-01T00:00:00Z",
                        "symbol": "BTCUSDT",
                        "position": 5000.00
                    },
                    {
                        "date": "2024-01-01T00:00:00Z",
                        "symbol": "ETHUSDT",
                        "position": 3000.00
                    },
                    {
                        "date": "2024-01-02T00:00:00Z",
                        "symbol": "BTCUSDT",
                        "position": 5100.00
                    },
                    {
                        "date": "2024-01-02T00:00:00Z",
                        "symbol": "ETHUSDT",
                        "position": 3050.00
                    }
                ],
                "message": "Position data retrieved successfully",
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }
