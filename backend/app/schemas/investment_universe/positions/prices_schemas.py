"""Prices API schemas Request and response schemas for prices endpoint"""
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field, field_validator

from app.common import TimeInterval, APIResponse
from ....models.investment_universe import AssetPrices


class PricesRequest(BaseModel):
    """Request parameters for prices endpoint"""
    symbols: List[str] = Field(..., description="List of trading symbols", min_length=1)
    start_date: datetime = Field(..., description="Start date for historical data")
    end_date: datetime = Field(..., description="End date for historical data")
    interval: TimeInterval = Field(TimeInterval.ONE_DAY, description="Time interval")

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
                "interval": "1d"
            }
        }


class PricesResponse(APIResponse):
    """Response for prices endpoint"""
    data: List[AssetPrices] = Field(..., description="Price data for requested assets")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": [
                    {
                        "symbol": "BTCUSDT",
                        "prices": [
                            {
                                "open_time": "2024-01-01T00:00:00Z",
                                "open": 42000.50,
                                "high": 43500.00,
                                "low": 41800.00,
                                "close": 43200.75,
                                "volume": 1250000.00,
                                "close_time": "2024-01-01T23:59:59Z",
                                "quote_asset_volume": 52500000.00,
                                "number_of_trades": 125000,
                                "taker_buy_base_volume": 625000.00,
                                "taker_buy_quote_volume": 26250000.00
                            }
                        ]
                    },
                    {
                        "symbol": "ETHUSDT",
                        "prices": [
                            {
                                "open_time": "2024-01-01T00:00:00Z",
                                "open": 2800.00,
                                "high": 2950.00,
                                "low": 2750.00,
                                "close": 2900.50,
                                "volume": 850000.00,
                                "close_time": "2024-01-01T23:59:59Z",
                                "quote_asset_volume": 2450000.00,
                                "number_of_trades": 85000,
                                "taker_buy_base_volume": 425000.00,
                                "taker_buy_quote_volume": 1225000.00
                            }
                        ]
                    }
                ],
                "message": "Price data retrieved successfully",
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }
