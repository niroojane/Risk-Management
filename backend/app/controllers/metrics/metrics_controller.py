"""Value at Risk Controller - historical, parametric and simulated VaR / CVaR"""
from datetime import datetime, timezone

import pandas as pd

from ..analytics_controller import AnalyticsController
from ...common import frame_to_dict, series_to_dict, to_json_value
from ...schemas.metrics import (
    VaRAllocationResult,
    VaRBacktest,
    VaRMethodResult,
    VaRRequest,
    VaRResponse,
)
from ...services.analytics import portfolio_analytics as analytics


class MetricsController(AnalyticsController):
    """Controller orchestrating risk metrics"""

    async def get_var(self, request: VaRRequest) -> VaRResponse:
        """Historical, parametric and simulated VaR / CVaR of each allocation"""
        prices = await self._load_prices(request)
        returns = analytics.to_returns(prices)
        allocations = self._allocations(request)

        mean_shock = request.mean_shock
        if isinstance(mean_shock, dict):
            mean_shock = pd.Series(mean_shock, dtype=float).reindex(returns.columns).fillna(1.0)

        results = await self._compute(
            analytics.value_at_risk,
            prices,
            returns,
            allocations,
            var_centile=request.var_centile,
            iterations=request.iterations,
            num_scenarios=request.num_scenarios,
            stress_factor=request.stress_factor,
            mean_shock=mean_shock,
            horizon_days=request.horizon_days,
            theta=request.theta,
            methods=[m.value for m in request.methods],
            backtest_window=request.backtest_window,
        )

        data = {}
        for name, result in results.items():
            methods = {}
            for method, values in result['methods'].items():
                methods[method] = VaRMethodResult(
                    var=to_json_value(values['var']),
                    cvar=to_json_value(values['cvar']),
                    var_contribution=(
                        series_to_dict(values['var_contribution']) if 'var_contribution' in values else None
                    ),
                    cvar_contribution=(
                        series_to_dict(values['cvar_contribution']) if 'cvar_contribution' in values else None
                    ),
                    histogram=values.get('histogram'),
                )

            backtest = None
            if 'backtest' in result:
                backtest = VaRBacktest(
                    series=frame_to_dict(result['backtest']['series']),
                    kupiec=frame_to_dict(result['backtest']['kupiec']),
                )

            data[name] = VaRAllocationResult(methods=methods, backtest=backtest)

        return VaRResponse(
            success=True,
            data=data,
            message=f"Computed VaR at {1 - request.var_centile:.0%} for {len(data)} allocations",
            timestamp=datetime.now(timezone.utc),
        )
