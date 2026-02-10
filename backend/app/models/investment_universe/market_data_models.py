"""Market Data entities - Domain objects for price and return analytics"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class AssetReturnMetrics(BaseModel):
    """Return metrics for a single asset over a period"""
    symbol: str = Field(..., description="Trading symbol")
    total_return: float = Field(..., description="Total return over the period")
    ytd_return: float = Field(..., description="Year-to-date return")
    annualized_return: float = Field(..., description="Annualized return")


class MarketReturnsData(BaseModel):
    """Return analytics for multiple assets over a period"""
    period_start_date: datetime = Field(..., description="Start date of the analysis period")
    ytd_start_date: datetime = Field(..., description="Start date of the year-to-date calculation")
    assets: List[AssetReturnMetrics] = Field(..., description="Return metrics for each asset")


class MarketDataSnapshot(BaseModel):
    """Complete market data snapshot containing prices and return analytics"""
    symbols: List[str] = Field(..., description="List of symbols included")
    start_date: datetime = Field(..., description="Start date of the data range")
    end_date: datetime = Field(..., description="End date of the data range")
    prices: Dict[str, Any] = Field(..., description="Price data indexed by date")
    count: int = Field(..., description="Number of price data points", ge=0)
    returns: Optional[MarketReturnsData] = Field(
        None,
        description="Return analytics (optional, only if enough data)"
    )
    timestamp: datetime = Field(..., description="Timestamp when the snapshot was created")
