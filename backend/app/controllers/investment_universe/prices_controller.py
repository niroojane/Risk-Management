"""Prices Controller - Business logic for price data operations"""

from ...services.binance import MarketDataService
from ...schemas.investment_universe import PricesRequest


class PricesController:
    """Controller orchestrating price data operations"""

    def __init__(self, market_data_service: MarketDataService):
        self._service = market_data_service

    async def get_prices(self, request: PricesRequest):
        """Get historical prices for requested symbols"""
        print('testttttt')
        result = await self._service.get_prices(
            tickers=request.symbols,
            start_date=request.start_date,
            end_date=request.end_date,
            use_cache=True
        )
        
        print(result, "I'm just thereeeeeee")
        return result

        # return PricesResponse(
        #     success=True,
        #     data=result,  # Raw data for testing
        #     message=f"Retrieved prices for {len(request.symbols)} symbols",
        #     timestamp=datetime.utcnow(),
        # )