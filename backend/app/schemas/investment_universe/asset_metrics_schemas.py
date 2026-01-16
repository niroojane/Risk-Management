"""Asset Metrics API schemas Request and response schemas for asset metrics endpoint"""
from typing import List
from pydantic import BaseModel, Field, field_validator

from app.common import APIResponse
from ...models.investment_universe import AssetMetrics


class AssetMetricsRequest(BaseModel):
    """Request parameters for asset metrics endpoint"""
    symbols: List[str] = Field(..., description="List of trading symbols", min_length=1)
    lookback_period: int = Field(30, description="Lookback period in days", ge=1, le=365)

    @field_validator('symbols')
    @classmethod
    def validate_symbols(cls, v: List[str]) -> List[str]:
        """Validate and uppercase symbols"""
        if not v:
            raise ValueError("At least one symbol is required")
        return [s.upper() for s in v]

    class Config:
        json_schema_extra = {
            "example": {
                "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
                "lookback_period": 30
            }
        }


class AssetMetricsResponse(APIResponse):
    """Response for asset metrics endpoint"""
    data: List[AssetMetrics] = Field(..., description="Metrics for requested assets")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": [
                    {
                        "symbol": "BTCUSDT",
                        "volatility": 0.45,
                        "avg_return": 0.002,
                        "max_drawdown": -0.25,
                        "sharpe_ratio": 1.5,
                        "total_volume": 125000000.00
                    },
                    {
                        "symbol": "ETHUSDT",
                        "volatility": 0.52,
                        "avg_return": 0.003,
                        "max_drawdown": -0.30,
                        "sharpe_ratio": 1.2,
                        "total_volume": 85000000.00
                    }
                ],
                "message": "Asset metrics calculated successfully",
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }
