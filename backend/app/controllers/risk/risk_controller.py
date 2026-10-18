"""Risk Controller - risk contribution, trajectories, tracking error, VaR history, stress preview"""
from datetime import datetime, timezone
from typing import List

import numpy as np
import pandas as pd

from ..workspace_controller import WorkspaceController
from ...common import to_payload
from ...core.market import get_profile
from ...schemas.workspace import (
    RiskContributionRequest,
    RiskTrajectoryRequest,
    StressPreviewRequest,
    TrackingErrorViewRequest,
    VaRHistoryRequest,
    ViewResponse,
)
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
        data = await self._compute(ws_analytics.risk_trajectory_view, ws, start, end, request.selected, request.window)
        return self._response(data, warnings, f"Ex-ante volatility of {len(ws.names)} series")

    async def tracking_error(self, request: TrackingErrorViewRequest) -> ViewResponse:
        warnings: List[str] = []
        ws = await self._load_workspace(request, warnings)
        start, end = self._window(request)
        data = await self._compute(
            ws_analytics.tracking_error_view, ws, start, end, request.selected, request.benchmark, request.window
        )
        return self._response(data, warnings, f"Ex-ante tracking error vs '{request.benchmark}'")

    async def var_history(self, request: VaRHistoryRequest) -> ViewResponse:
        warnings: List[str] = []
        ws = await self._load_workspace(request, warnings)
        start, end = self._window(request)
        data = await self._compute(
            ws_analytics.var_history_view, ws, start, end, request.selected, request.method.value, request.window,
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
