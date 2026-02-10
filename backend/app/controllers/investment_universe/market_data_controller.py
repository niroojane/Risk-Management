"""Market Data Controller - Business logic for market data operations"""
from datetime import datetime, timezone

from ...services.binance import MarketDataService
from ...schemas.investment_universe import PricesRequest, PricesResponse


class MarketDataController:
    """Controller orchestrating market data operations (prices + returns)"""

    def __init__(self, market_data_service: MarketDataService):
        self._service = market_data_service

    async def get_market_data(self, request: PricesRequest) -> PricesResponse:
        """Get market data snapshot (prices + returns) for symbols within date range"""
        # Service returns MarketDataSnapshot
        snapshot = await self._service.get_market_data(
            symbols=request.symbols,
            start_date=request.start_date,
            end_date=request.end_date,
            use_cache=request.use_cache,
        )

        return PricesResponse(
            success=True,
            data=snapshot,
            message=f"Retrieved {snapshot.count} price data points for {len(snapshot.symbols)} symbols",
            timestamp=datetime.now(timezone.utc),
        )
