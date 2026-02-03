"""Positions API schemas Request and response schemas for positions endpoint"""
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field, field_validator

from app.common import APIResponse
from ....models.investment_universe import Position


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

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "symbols": ["BTCUSDT", "ETHUSDT"],
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-12-31T23:59:59Z"
            }]
        }
    }


class PositionsResponse(APIResponse):
    """Response for positions endpoint"""
    data: List[Position] = Field(..., description="Position data for requested assets")

    model_config = {
        "json_schema_extra": {
            "examples": [{
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
            }]
        }
    }
