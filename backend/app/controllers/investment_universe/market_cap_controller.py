"""Market Cap Controller - Business logic for market capitalization operations"""
from datetime import datetime, timezone

from ...services.binance import MarketCapService
from ...schemas.investment_universe import MarketCapRequest, MarketCapResponse


class MarketCapController:
    """Controller orchestrating market cap operations"""

    def __init__(self, market_cap_service: MarketCapService):
        self._service = market_cap_service

    async def get_market_cap(self, request: MarketCapRequest) -> MarketCapResponse:
        """Get all cryptocurrencies by market cap (filtering handled by frontend)"""
        market_cap_items = await self._service.get_market_cap(
            quote=request.quote.value, use_cache=True
        )

        return MarketCapResponse(
            success=True,
            data=market_cap_items,
            message=f"Retrieved {len(market_cap_items)} cryptocurrencies by market cap",
            timestamp=datetime.now(timezone.utc),
        )
