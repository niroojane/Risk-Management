"""
Market Cap API schemas
Request and response models for market cap endpoint
"""
from typing import List
from pydantic import BaseModel, Field

from ...common import QuoteAsset, APIResponse
from ...entities.investment_universe.market_cap_entities import MarketCapItem


class MarketCapRequest(BaseModel):
    """Request parameters for market cap endpoint"""
    top_n: int = Field(50, description="Number of top assets to return", ge=1, le=500)
    quote: QuoteAsset = Field(QuoteAsset.USDT, description="Quote asset")

    class Config:
        json_schema_extra = {
            "example": {
                "top_n": 50,
                "quote": "USDT"
            }
        }


class MarketCapResponse(APIResponse):
    """Response for market cap endpoint"""
    data: List[MarketCapItem] = Field(..., description="List of assets with market cap")

    class Config:
        json_schema_extra = {
            "example": {
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
            }
        }
