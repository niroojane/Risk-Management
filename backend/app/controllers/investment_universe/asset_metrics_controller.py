"""Asset Metrics Controller - Business logic for per-asset return and risk metrics"""
from datetime import datetime, timezone

from ..analytics_controller import AnalyticsController
from ...common import to_json_value
from ...models.investment_universe import AssetMetrics
from ...schemas.investment_universe import AssetMetricsRequest, AssetMetricsResponse
from ...services.analytics import portfolio_analytics as analytics


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
