"""
Asset Metrics entities
Domain objects for asset metrics data
"""
from pydantic import BaseModel, Field


class AssetMetrics(BaseModel):
    """Computed metrics for a single asset"""
    symbol: str = Field(..., description="Trading symbol")
    volatility: float = Field(..., description="Annualized volatility", ge=0)
    avg_return: float = Field(..., description="Average return")
    max_drawdown: float = Field(..., description="Maximum drawdown", le=0)
    sharpe_ratio: float = Field(..., description="Sharpe ratio")
    total_volume: float = Field(..., description="Total volume traded", ge=0)
