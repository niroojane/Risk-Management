"""Investment Universe: market caps, prices, per-asset metrics"""
from datetime import datetime, timezone

from app.common import to_json_value
from app.controllers.base import AnalyticsController
from app.schemas.universe import (
    AssetMetrics,
    AssetMetricsRequest,
    AssetMetricsResponse,
    MarketCapRequest,
    MarketCapResponse,
    PricesData,
    PricesRequest,
    PricesResponse,
)
from src import PortfolioAnalytics as analytics
from app.services.binance import MarketDataService, PriceService


class MarketCapController:
    """Controller orchestrating market cap operations"""

    def __init__(self, market_data_service: MarketDataService):
        self._service = market_data_service

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


class AssetMetricsController(AnalyticsController):
    """Controller orchestrating asset metrics calculations"""

    async def get_asset_metrics(self, request: AssetMetricsRequest) -> AssetMetricsResponse:
        """Returns, volatilities, CVaR and max drawdown per symbol"""
        prices = await self._load_prices(request)
        metrics = await self._compute(analytics.asset_metrics, prices)

        data = [
            AssetMetrics(symbol=symbol, **{k: to_json_value(v) for k, v in row.items()})
            for symbol, row in metrics.iterrows()
        ]

        return AssetMetricsResponse(
            success=True,
            data=data,
            message=f"Calculated metrics for {len(data)} symbols",
            timestamp=datetime.now(timezone.utc),
        )
