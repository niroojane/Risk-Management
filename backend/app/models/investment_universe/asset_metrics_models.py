"""Asset Metrics entities Domain objects for asset metrics data"""
from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


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
