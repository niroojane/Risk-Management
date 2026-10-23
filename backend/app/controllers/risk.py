"""Risk Analysis tab: risk contribution, trajectories, tracking error, Value at Risk, stress"""
from datetime import datetime, timezone
from typing import List

import numpy as np
import pandas as pd

from app.common import frame_to_dict, series_to_dict, to_json_value, to_payload
from app.controllers.base import WorkspaceController
from app.core.market import get_profile
from app.schemas.risk import (
    RiskContributionRequest,
    RiskTrajectoryRequest,
    StressPreviewRequest,
    TrackingErrorViewRequest,
    VaRAllocationResult,
    VaRBacktest,
    VaRHistoryRequest,
    VaRMethodResult,
    VaRRequest,
    VaRResponse,
)
from app.schemas.workspace import ViewResponse
from src import PortfolioAnalytics as analytics
from src import Workspace as ws_analytics


class RiskController(WorkspaceController):
    """Controller orchestrating the Risk Analysis views"""

    async def contribution(self, request: RiskContributionRequest) -> ViewResponse:
        prices = ws_analytics.clean_prices(await self._load_prices(request), excluded=get_profile().excluded_symbols)
        allocations = self._allocations(request).reindex(columns=prices.columns, fill_value=0.0)
        data = await self._compute(
            ws_analytics.risk_contribution_view, prices, allocations, request.fund, request.benchmark,
            request.frequency.value,
        )
        return self._response(data, [], f"Risk contribution of '{request.fund}'")

    async def trajectory(self, request: RiskTrajectoryRequest) -> ViewResponse:
        warnings: List[str] = []
        ws = await self._load_workspace(request, warnings)
        start, end = self._window(request)
        data = await self._compute(ws_analytics.risk_trajectory_view, ws, start, end, request.window)
        return self._response(data, warnings, f"Ex-ante volatility of {len(ws.names)} series")

    async def tracking_error(self, request: TrackingErrorViewRequest) -> ViewResponse:
        warnings: List[str] = []
        ws = await self._load_workspace(request, warnings)
        start, end = self._window(request)
        data = await self._compute(
            ws_analytics.tracking_error_view, ws, start, end, request.benchmark, request.window
        )
        return self._response(data, warnings, f"Ex-ante tracking error vs '{request.benchmark}'")

    async def var_history(self, request: VaRHistoryRequest) -> ViewResponse:
        warnings: List[str] = []
        ws = await self._load_workspace(request, warnings)
        start, end = self._window(request)
        data = await self._compute(
            ws_analytics.var_history_view, ws, start, end, request.method.value, request.window,
            request.var_centile, request.iterations, request.stress_factor, request.mean_factor,
        )
        return self._response(data, warnings, f"Rolling {request.method.value} VaR of {len(ws.names)} series")

    async def stress_preview(self, request: StressPreviewRequest) -> ViewResponse:
        returns = await self._load_returns(request)
        n = returns.shape[1]
        grid = (np.asarray(request.stress_factor, dtype=float) if isinstance(request.stress_factor, list)
                else np.eye(n) * float(request.stress_factor))
        mean_shock = (pd.Series(request.mean_shock, dtype=float) if isinstance(request.mean_shock, dict)
                      else pd.Series(float(request.mean_shock), index=returns.columns))
        data = await self._compute(ws_analytics.stress_preview, returns, grid, mean_shock)
        return ViewResponse(success=True, data=to_payload(data), message="Stressed moments",
                            timestamp=datetime.now(timezone.utc))

    async def value_at_risk(self, request: VaRRequest) -> VaRResponse:
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
