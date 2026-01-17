"""Prices entities Domain objects for price data"""
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


class PriceDataPoint(BaseModel):
    """Single price data point"""
    open_time: datetime = Field(..., description="Open timestamp")
    open: float = Field(..., description="Opening price", gt=0)
    high: float = Field(..., description="Highest price", gt=0)
    low: float = Field(..., description="Lowest price", gt=0)
    close: float = Field(..., description="Closing price", gt=0)
    volume: float = Field(..., description="Trading volume (Base Asset)", ge=0)
    close_time: datetime = Field(..., description="Close timestamp")
    quote_asset_volume: float = Field(..., description="Quote asset volume", ge=0)
    number_of_trades: int = Field(..., description="Number of trades", ge=0)
    taker_buy_base_volume: float = Field(..., description="Taker buy base asset volume", ge=0)
    taker_buy_quote_volume: float = Field(..., description="Taker buy quote asset volume", ge=0)


class AssetPrices(BaseModel):
    """Price data for a single asset"""
    symbol: str = Field(..., description="Trading symbol")
    prices: List[PriceDataPoint] = Field(..., description="Historical prices")
