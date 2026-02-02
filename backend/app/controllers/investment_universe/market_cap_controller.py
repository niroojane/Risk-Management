"""Market Cap Controller - Business logic for market capitalization operations"""
from datetime import datetime, timezone

from ...services.binance import MarketDataService
from ...schemas.investment_universe import MarketCapRequest, MarketCapResponse
from ...mappers.investment_universe import MarketCapMapper


class MarketCapController:
    """Controller orchestrating market cap operations"""

    def __init__(self, market_data_service: MarketDataService):
        self._service = market_data_service

    async def get_market_cap(self, request: MarketCapRequest) -> MarketCapResponse:
        """Get all cryptocurrencies by market cap (filtering handled by frontend)"""
        result = await self._service.get_market_cap(
            quote=request.quote.value, use_cache=True
        )

        market_cap_items = MarketCapMapper.to_entities(raw_data=result["data"])

        return MarketCapResponse(
            success=True,
            data=market_cap_items,
            message=f"Retrieved {len(market_cap_items)} cryptocurrencies by market cap",
            timestamp=datetime.now(timezone.utc),
        )
