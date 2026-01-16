"""Market Cap entities Domain objects for market capitalization data"""
from pydantic import BaseModel, Field


class MarketCapItem(BaseModel):
    """Single asset market cap data"""
    symbol: str = Field(..., description="Trading symbol (e.g., BTCUSDT)")
    long_name: str = Field(..., description="Full asset name")
    base_asset: str = Field(..., description="Base asset (e.g., BTC)")
    quote_asset: str = Field(..., description="Quote asset (e.g., USDT)")
    price: float = Field(..., description="Current price", gt=0)
    supply: float = Field(..., description="Circulating supply", ge=0)
    market_cap: float = Field(..., description="Market capitalization", ge=0)
