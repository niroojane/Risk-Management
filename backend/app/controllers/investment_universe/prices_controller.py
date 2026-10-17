"""Prices Controller - Business logic for historical price operations"""
from datetime import datetime, timezone

from ...services.binance import PriceService
from ...schemas.investment_universe import PricesRequest, PricesResponse, PricesData


class PricesController:
    """Controller orchestrating price data operations"""

    def __init__(self, price_service: PriceService):
        self._service = price_service

    async def get_prices(self, request: PricesRequest) -> PricesResponse:
        """Get historical prices for a list of symbols within date range"""
        result = await self._service.get_prices(
            symbols=request.symbols,
            start_date=request.start_date,
            end_date=request.end_date,
            use_cache=request.use_cache,
        )

        prices_data = PricesData(
            symbols=result["symbols"],
            start_date=result["start_date"],
            end_date=result["end_date"],
            data=result["data"],
            count=result["count"],
        )

        return PricesResponse(
            success=True,
            data=prices_data,
            message=f"Retrieved {result['count']} price data points for {len(result['symbols'])} symbols",
            timestamp=datetime.now(timezone.utc),
        )
