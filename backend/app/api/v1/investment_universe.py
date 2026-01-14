"""
Investment Universe API endpoints
Provides market data and metrics for cryptocurrency assets
"""
from fastapi import APIRouter
from datetime import datetime

from ...models.schemas.investment_universe import (
    MarketCapRequest,
    MarketCapResponse,
)
from ...models.entities.investment_universe import MarketCapItem

router = APIRouter(prefix="/investment-universe", tags=["Investment Universe"])


@router.post("/market-cap", response_model=MarketCapResponse)
async def get_market_cap(request: MarketCapRequest) -> MarketCapResponse:
    """
    Get top N cryptocurrencies by market capitalization

    Returns a list of cryptocurrencies sorted by market cap, including:
    - Symbol and name
    - Current price
    - Circulating supply
    - Market capitalization
    """
    # TODO: Implement actual logic with BinanceService
    # For now, return mock data to demonstrate Swagger
    mock_data = [
        MarketCapItem(
            symbol="BTCUSDT",
            long_name="Bitcoin",
            base_asset="BTC",
            quote_asset="USDT",
            price=45000.00,
            supply=19500000.00,
            market_cap=877500000000.00
        ),
        MarketCapItem(
            symbol="ETHUSDT",
            long_name="Ethereum",
            base_asset="ETH",
            quote_asset="USDT",
            price=2500.00,
            supply=120000000.00,
            market_cap=300000000000.00
        )
    ]

    return MarketCapResponse(
        success=True,
        data=mock_data[:request.top_n],
        message=f"Top {request.top_n} cryptocurrencies by market cap",
        timestamp=datetime.utcnow()
    )
