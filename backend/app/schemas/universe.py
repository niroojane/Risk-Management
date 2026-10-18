"""Investment Universe: market caps, prices and per-asset metrics"""
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.common import APIResponse, QuoteAsset
from app.schemas.analytics import AnalyticsRequest


class MarketCapItem(BaseModel):
    """Single asset market cap data"""
    symbol: str = Field(..., description="Trading symbol (e.g., BTCUSDT)")
    long_name: str = Field(..., description="Full asset name")
    base_asset: str = Field(..., description="Base asset (e.g., BTC)")
    quote_asset: str = Field(..., description="Quote asset (e.g., USDT)")
    price: float = Field(..., description="Current price", gt=0)
    supply: float = Field(..., description="Circulating supply", ge=0)
    market_cap: float = Field(..., description="Market capitalization", ge=0)


class AssetMetrics(BaseModel):
    """Return and risk metrics of a single asset over the requested period"""
    symbol: str = Field(..., description="Trading symbol")
    total_return: Optional[float] = Field(None, description="Return since the start date")
    ytd_return: Optional[float] = Field(None, description="Return since the start of the last year")
    annualized_return: Optional[float] = Field(None, description="Annualized return")
    volatility_1y_daily: Optional[float] = Field(None, description="Annualized volatility, last year of daily returns")
    volatility_3y_weekly: Optional[float] = Field(None, description="Annualized volatility, last 3 years of weekly returns")
    volatility_5y_monthly: Optional[float] = Field(None, description="Annualized volatility, last 5 years of monthly returns")
    volatility_monthly: Optional[float] = Field(None, description="Annualized volatility, whole period of monthly returns")
    cvar_parametric_95: Optional[float] = Field(None, description="Parametric monthly CVaR at 95%")
    max_drawdown: Optional[float] = Field(None, description="Maximum drawdown", le=0)
    max_drawdown_date: Optional[date] = Field(None, description="Date of the maximum drawdown")


class MarketCapRequest(BaseModel):
    """Request parameters for market cap endpoint"""
    quote: QuoteAsset = Field(QuoteAsset.USDT, description="Quote asset")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "quote": "USDT"
            }]
        }
    }


class MarketCapResponse(APIResponse):
    """Response for market cap endpoint"""
    data: List[MarketCapItem] = Field(..., description="List of assets with market cap")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "success": True,
                "data": [
                    {
                        "symbol": "BTCUSDT",
                        "long_name": "Bitcoin",
                        "base_asset": "BTC",
                        "quote_asset": "USDT",
                        "price": 42000.50,
                        "supply": 19000000.0,
                        "market_cap": 798009500000.0
                    },
                    {
                        "symbol": "ETHUSDT",
                        "long_name": "Ethereum",
                        "base_asset": "ETH",
                        "quote_asset": "USDT",
                        "price": 2900.00,
                        "supply": 120000000.0,
                        "market_cap": 348000000000.0
                    }
                ],
                "message": "Market cap data retrieved successfully",
                "timestamp": "2024-01-01T12:00:00Z"
            }]
        }
    }


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
