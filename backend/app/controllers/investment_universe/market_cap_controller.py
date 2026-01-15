"""Market Cap Controller - Business logic for market capitalization operations"""
from datetime import datetime

from ...services.binance_service import BinanceService
from ...schemas.investment_universe import MarketCapRequest, MarketCapResponse
from ...mappers.investment_universe import MarketCapMapper
from ...core.exceptions import ExternalAPIError


class MarketCapController:
    """Controller orchestrating market cap operations between services and mappers"""

    def __init__(self, binance_service: BinanceService):
        self._binance_service = binance_service

    async def get_market_cap(self, request: MarketCapRequest) -> MarketCapResponse:
        """Get top N cryptocurrencies by market cap from Binance API"""
        result = await self._binance_service.get_market_cap(
            quote=request.quote.value,
            use_cache=True
        )

        # Transform to domain entities
        market_cap_items = MarketCapMapper.to_entities(
            raw_data=result["data"],
            limit=request.top_n
        )

        return MarketCapResponse(
            success=True,
            data=market_cap_items,
            message=f"Top {request.top_n} cryptocurrencies by market cap",
            timestamp=datetime.utcnow()
        )
