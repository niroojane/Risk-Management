"""Price API schemas Request and response schemas for prices endpoint"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from app.common import APIResponse


class PricesRequest(BaseModel):
    """Request parameters for prices endpoint"""
    symbols: List[str] = Field(
        ...,
        description="List of trading symbols (e.g., ['BTCUSDT', 'ETHUSDT'])",
        min_length=1
    )
    start_date: Optional[datetime] = Field(
        None,
        description="Start date for price history (default: end_date - 30 days)"
    )
    end_date: Optional[datetime] = Field(
        None,
        description="End date for price history (default: today)"
    )
    use_cache: bool = Field(
        True,
        description="Use cached data if available"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-01-31T23:59:59Z",
                "use_cache": True
            }]
        }
    }


class PricesData(BaseModel):
    """Prices data payload"""
    symbols: List[str] = Field(..., description="List of requested symbols")
    start_date: str = Field(..., description="Start date (ISO format)")
    end_date: str = Field(..., description="End date (ISO format)")
    data: Dict[str, Any] = Field(..., description="Price data indexed by date")
    count: int = Field(..., description="Number of data points")

class PricesResponse(APIResponse):
    """Response for prices endpoint"""
    data: PricesData = Field(..., description="Price history data")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "success": True,
                "data": {
                    "symbols": ["BTCUSDT", "ETHUSDT"],
                    "start_date": "2024-01-01T00:00:00",
                    "end_date": "2024-01-31T23:59:59",
                    "data": {
                        "2024-01-01": {
                            "BTCUSDT": 42000.50,
                            "ETHUSDT": 2200.30
                        },
                        "2024-01-02": {
                            "BTCUSDT": 42500.00,
                            "ETHUSDT": 2250.00
                        }
                    },
                    "count": 31
                },
                "message": "Price data retrieved successfully",
                "timestamp": "2024-01-01T12:00:00Z"
            }]
        }
    }
