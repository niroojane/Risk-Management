"""
Prices entities
Domain objects for price data
"""
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


class PriceDataPoint(BaseModel):
    """Single price data point"""
    timestamp: datetime = Field(..., description="Price timestamp")
    open: float = Field(..., description="Opening price", gt=0)
    high: float = Field(..., description="Highest price", gt=0)
    low: float = Field(..., description="Lowest price", gt=0)
    close: float = Field(..., description="Closing price", gt=0)
    volume: float = Field(..., description="Trading volume", ge=0)


class AssetPrices(BaseModel):
    """Price data for a single asset"""
    symbol: str = Field(..., description="Trading symbol")
    prices: List[PriceDataPoint] = Field(..., description="Historical prices")
