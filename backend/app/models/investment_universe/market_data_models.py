"""Market Data entities - Domain objects for price and return analytics"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class AssetRiskMetrics(BaseModel):
    """Risk metrics for a single asset (volatility, drawdown, CVaR)"""
    symbol: str = Field(..., description="Trading symbol")
    annualized_vol_daily: Optional[float] = Field(
        None, description="Annualized Volatility (daily) - last 260 daily returns"
    )
    annualized_vol_3y_weekly: Optional[float] = Field(
        None, description="Annualized Volatility 3Y (Weekly) - last 153 weekly returns"
    )
    annualized_vol_5y_monthly: Optional[float] = Field(
        None, description="Annualized Volatility 5Y (Monthly) - last 50 monthly returns"
    )
    annualized_vol_since_inception_monthly: Optional[float] = Field(
        None, description="Annualized Volatility since inception (Monthly)"
    )
    inception_year: Optional[int] = Field(
        None, description="First year of available price history"
    )
    cvar_parametric_95: Optional[float] = Field(
        None, description="CVaR Parametric 95%"
    )
    max_drawdown: Optional[float] = Field(
        None, description="Maximum peak-to-trough drawdown"
    )
    date_of_max_drawdown: Optional[str] = Field(
        None, description="Date of maximum drawdown (YYYY-MM-DD)"
    )


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
    risk: Optional[List[AssetRiskMetrics]] = Field(
        None,
        description="Risk metrics per asset (volatility, drawdown, CVaR)"
    )
    timestamp: datetime = Field(..., description="Timestamp when the snapshot was created")
