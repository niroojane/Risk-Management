"""Current Portfolio and Strategy Return views: performance, calendar, return / beta / P&L analysis"""
from typing import List

import pandas as pd

from app.controllers.base import WorkspaceController
from app.core.exceptions import DataValidationError
from app.schemas.portfolio import BetaViewRequest, CalendarViewRequest, PerformanceViewRequest
from app.schemas.workspace import PairViewRequest, ViewResponse, WorkspaceRequest
from src.PortfolioAnalytics import allocation_frame, build_constraints, to_returns
from src.Rebalancing import rebalanced_portfolio
from src import Account as account_analytics
from src import Workspace as ws_analytics


class PortfolioController(WorkspaceController):
    """Views comparing the named portfolio series"""

    async def performance(self, request: PerformanceViewRequest) -> ViewResponse:
        warnings: List[str] = []
        ws = await self._load_workspace(request, warnings)
        start, end = self._window(request)
        allocations = allocation_frame(request.allocations, ws.prices.columns)

        # The constrained frontier respects the risk limits too, measured as in the optimization
        risk = request.risk_constraints.as_dict() if request.risk_constraints else {}
        bench_weights = allocations.loc[request.benchmark] if request.benchmark in allocations.index else None
        if bench_weights is None and set(risk) - {'volatility'}:
            warnings.append("Efficient frontier: beta / tracking error / information ratio limits left out "
                            "(no benchmark allocation selected).")
            risk = {k: v for k, v in risk.items() if k == 'volatility'}

        def run():
            window = ws.prices.loc[start:end]
            bench_returns = None
            if 'beta' in risk and request.benchmark_frequency is not None:
                bench_returns = rebalanced_portfolio(
                    window, bench_weights, frequency=request.benchmark_frequency.value
                ).sum(axis=1).pct_change()
            constraints = build_constraints(
                to_returns(window), [(c.asset, c.sign.solver_sign, c.limit) for c in request.constraints],
                risk, bench_weights, bench_returns,
            )
            return ws_analytics.performance_view(
                ws, start, end, allocations, request.benchmark, request.vol_window, constraints,
                request.frontier_points,
            )

        data = await self._compute(run)
        return self._response(data, warnings, f"Performance of {len(ws.names)} series")

    async def calendar(self, request: CalendarViewRequest) -> ViewResponse:
        warnings: List[str] = []
        ws = await self._load_workspace(request, warnings)
        start, end = self._window(request)
        data = await self._compute(
            ws_analytics.calendar_view, ws, start, end, request.fund, request.benchmark, request.period.value
        )
        return self._response(data, warnings, f"{request.period.value}ly metrics of '{request.fund}'")

    async def return_analysis(self, request: PairViewRequest) -> ViewResponse:
        warnings: List[str] = []
        ws = await self._load_workspace(request, warnings)
        start, end = self._window(request)
        data = await self._compute(ws_analytics.return_analysis_view, ws, start, end, request.fund, request.benchmark)
        return self._response(data, warnings, f"Return analysis of '{request.fund}' vs '{request.benchmark}'")

    async def beta(self, request: BetaViewRequest) -> ViewResponse:
        warnings: List[str] = []
        ws = await self._load_workspace(request, warnings)
        start, end = self._window(request)
        data = await self._compute(
            ws_analytics.beta_view, ws, start, end, request.fund, request.benchmark, request.window
        )
        return self._response(data, warnings, f"Beta of '{request.fund}' vs '{request.benchmark}'")

    async def pnl_analysis(self, request: WorkspaceRequest) -> ViewResponse:
        """Portfolio value, P&L history and cumulative returns of the real portfolio vs. the series"""
        if self._account is None:
            raise DataValidationError("The P&L analysis needs the account service")
        request = request.model_copy(update={'include_historical': True})
        warnings: List[str] = []
        ws = await self._load_workspace(request, warnings)
        start, end = self._window(request)

        history = await self._account.get_history(request.use_cache)
        prices = await self._account.get_history_prices(history, request.use_cache)
        pnl_history, daily, pnl_warnings = await self._account.pnl_history(history, prices, request.use_cache)
        warnings += pnl_warnings

        def run():
            if pnl_history.empty:
                # no trade history: value and returns only, as the notebook ('P&L charts skipped')
                data = {'positions': history.positions.loc[start:end], 'cumulative_contribution': pd.DataFrame(),
                        'daily_pnl': pd.DataFrame()}
            else:
                data = account_analytics.pnl_analysis(history.positions, pnl_history, daily, start, end)
            data['cumulative_return'] = ws_analytics.levels(ws.series_returns().loc[start:end])
            data['history_start'] = history.positions.index[0]
            return data

        data = await self._compute(run)
        return self._response(data, warnings, "P&L analysis of the real portfolio")
