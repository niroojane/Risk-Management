"""
Returns API schemas
Request and response models for returns endpoint
"""
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field, field_validator

from ...common import TimeInterval, ReturnType, APIResponse
from ...entities.investment_universe.returns_entities import AssetReturns


class ReturnsRequest(BaseModel):
    """Request parameters for returns endpoint"""
    symbols: List[str] = Field(..., description="List of trading symbols", min_length=1)
    start_date: datetime = Field(..., description="Start date")
    end_date: datetime = Field(..., description="End date")
    interval: TimeInterval = Field(TimeInterval.ONE_DAY, description="Time interval")
    return_type: ReturnType = Field(ReturnType.SIMPLE, description="Return calculation type")

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
                "end_date": "2024-12-31T23:59:59Z",
                "interval": "1d",
                "return_type": "simple"
            }
        }


class ReturnsResponse(APIResponse):
    """Response for returns endpoint"""
    data: List[AssetReturns] = Field(..., description="Return data for requested assets")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": [
                    {
                        "symbol": "BTCUSDT",
                        "return_type": "simple",
                        "returns": [
                            {
                                "timestamp": "2024-01-01T00:00:00Z",
                                "return_value": 0.025
                            },
                            {
                                "timestamp": "2024-01-02T00:00:00Z",
                                "return_value": 0.012
                            }
                        ]
                    },
                    {
                        "symbol": "ETHUSDT",
                        "return_type": "simple",
                        "returns": [
                            {
                                "timestamp": "2024-01-01T00:00:00Z",
                                "return_value": 0.032
                            },
                            {
                                "timestamp": "2024-01-02T00:00:00Z",
                                "return_value": -0.015
                            }
                        ]
                    }
                ],
                "message": "Returns calculated successfully",
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }
