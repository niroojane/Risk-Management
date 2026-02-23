"""Market Data API schemas - Request and response schemas for market data endpoint"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.common import APIResponse
from app.models.investment_universe import MarketDataSnapshot


class MarketDataRequest(BaseModel):
    """Request schema for fetching market data (prices + returns)"""
    symbols: List[str] = Field(..., min_length=1, description="List of trading symbols")
    start_date: Optional[datetime] = Field(None, description="Start date (default: 30 days ago)")
    end_date: Optional[datetime] = Field(None, description="End date (default: today)")
    use_cache: bool = Field(True, description="Use cached data if available")

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


class MarketDataResponse(APIResponse):
    """Response schema for market data endpoint with prices and returns analytics"""
    data: MarketDataSnapshot

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "success": True,
                "data": {
                    "symbols": ["BTCUSDT", "ETHUSDT"],
                    "start_date": "2024-01-01T00:00:00",
                    "end_date": "2024-01-31T23:59:59",
                    "prices": {
                        "2024-01-01": {
                            "BTCUSDT": 42000.50,
                            "ETHUSDT": 2200.30
                        },
                        "2024-01-02": {
                            "BTCUSDT": 42500.00,
                            "ETHUSDT": 2250.00
                        }
                    },
                    "count": 31,
                    "returns": {
                        "period_start_date": "2024-01-01T00:00:00",
                        "ytd_start_date": "2024-01-01T00:00:00",
                        "assets": [
                            {
                                "symbol": "BTCUSDT",
                                "total_return": 0.0119,
                                "ytd_return": 0.0119,
                                "annualized_return": 0.1401
                            },
                            {
                                "symbol": "ETHUSDT",
                                "total_return": 0.0227,
                                "ytd_return": 0.0227,
                                "annualized_return": 0.2825
                            }
                        ]
                    },
                    "risk": [
                        {
                            "symbol": "BTCUSDT",
                            "annualized_vol_daily": 0.6213,
                            "annualized_vol_3y_weekly": 0.5874,
                            "annualized_vol_5y_monthly": 0.7102,
                            "annualized_vol_since_inception_monthly": 0.7891,
                            "inception_year": 2020,
                            "cvar_parametric_95": -1.6934,
                            "max_drawdown": -0.7731,
                            "date_of_max_drawdown": "2022-11-21"
                        },
                        {
                            "symbol": "ETHUSDT",
                            "annualized_vol_daily": 0.7445,
                            "annualized_vol_3y_weekly": 0.6932,
                            "annualized_vol_5y_monthly": 0.8210,
                            "annualized_vol_since_inception_monthly": 0.9123,
                            "inception_year": 2020,
                            "cvar_parametric_95": -1.9544,
                            "max_drawdown": -0.8201,
                            "date_of_max_drawdown": "2022-06-18"
                        }
                    ],
                    "timestamp": "2024-01-01T12:00:00Z"
                },
                "message": "Price data retrieved successfully",
                "timestamp": "2024-01-01T12:00:00Z"
            }]
        }
    }
