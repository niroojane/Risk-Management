"""Asset Metrics API schemas Request and response schemas for asset metrics endpoint"""
from typing import List
from pydantic import Field

from app.common import APIResponse
from ..analytics_schemas import AnalyticsRequest
from ...models.investment_universe import AssetMetrics


class AssetMetricsRequest(AnalyticsRequest):
    """Request parameters for asset metrics endpoint"""

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
                "start_date": "2021-01-01T00:00:00Z",
                "end_date": "2024-12-31T23:59:59Z"
            }]
        }
    }


class AssetMetricsResponse(APIResponse):
    """Response for asset metrics endpoint"""
    data: List[AssetMetrics] = Field(..., description="Metrics for requested assets")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "success": True,
                "data": [
                    {
                        "symbol": "BTCUSDT",
                        "total_return": 1.35,
                        "ytd_return": 0.42,
                        "annualized_return": 0.33,
                        "volatility_1y_daily": 0.45,
                        "volatility_3y_weekly": 0.52,
                        "volatility_5y_monthly": 0.61,
                        "volatility_monthly": 0.61,
                        "cvar_parametric_95": -0.36,
                        "max_drawdown": -0.77,
                        "max_drawdown_date": "2022-11-21"
                    }
                ],
                "message": "Asset metrics calculated successfully",
                "timestamp": "2024-01-01T12:00:00Z"
            }]
        }
    }
