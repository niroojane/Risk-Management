"""Strategy Controller - Business logic for portfolio optimization and the rolling backtest"""
from datetime import datetime, timezone
from typing import List

import pandas as pd

from ..analytics_controller import AnalyticsController
from ...common import frame_to_dict, to_payload
from ...schemas.analytics_schemas import WeightConstraint
from ...schemas.workspace import BacktestRequest, ViewResponse
from ...core.market import MULTI_ASSET, get_profile
from src.Backtest import run_backtest
from src.Rebalancing import rebalanced_portfolio
from src.Workspace import clean_prices
from ...schemas.strategy import OptimizationData, OptimizationRequest, OptimizationResponse
from ...services.analytics import portfolio_analytics as analytics


def _weight_rows(constraints: List[WeightConstraint]):
    return [(c.asset, c.sign.solver_sign, c.limit) for c in constraints]


class StrategyController(AnalyticsController):
    """Controller orchestrating portfolio optimization"""

    async def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        """Optimal allocation for each objective under the requested constraints"""
        prices = await self._load_prices(request)
        returns = analytics.to_returns(prices)
        bench_weights = (
            pd.Series(request.benchmark, dtype=float).reindex(returns.columns).fillna(0.0)
            if request.benchmark else None
        )
        objectives = [o.value for o in request.objectives]
        risk_constraints = request.risk_constraints.as_dict() if request.risk_constraints else None

        def run():
            bench_returns = None
            if bench_weights is not None and request.benchmark_frequency is not None:
                bench_returns = rebalanced_portfolio(
                    prices, bench_weights, frequency=request.benchmark_frequency.value
                ).sum(axis=1).pct_change()
            constraints = analytics.build_constraints(
                returns, _weight_rows(request.constraints), risk_constraints, bench_weights, bench_returns
            )
            allocations, warnings = analytics.optimize_allocations(returns, objectives, constraints, bench_weights)
            metrics = analytics.expected_metrics(returns, allocations)
            return allocations, metrics, warnings

        allocations, metrics, warnings = await self._compute(run)

        data = OptimizationData(
            allocations={
                name: {symbol: round(float(w), 6) for symbol, w in row.items()}
                for name, row in allocations.iterrows()
            },
            metrics=frame_to_dict(metrics),
            warnings=warnings,
        )

        return OptimizationResponse(
            success=True,
            data=data,
            message=f"Optimized {len(objectives)} objectives over {returns.shape[1]} symbols",
            timestamp=datetime.now(timezone.utc),
        )

    async def backtest(self, request: BacktestRequest) -> ViewResponse:
        """Rolling optimization of the core strategy blended with the overlays"""
        profile = get_profile()
        prices = clean_prices(await self._load_prices(request), excluded=profile.excluded_symbols)
        bench_weights = (
            pd.Series(request.benchmark, dtype=float).reindex(prices.columns).fillna(0.0)
            if request.benchmark else None
        )

        result = await self._compute(
            run_backtest,
            prices,
            request.objective.value,
            frequency=request.frequency.value,
            overlays=[(o.objective.value, o.limit) for o in request.overlays],
            weight_constraints=_weight_rows(request.constraints),
            risk_constraints=request.risk_constraints.as_dict() if request.risk_constraints else None,
            bench_weights=bench_weights,
            benchmark=(profile.benchmark_label, profile.benchmark_ticker),
            model_row=profile.model_row,
            calendar_annualization=profile.name == MULTI_ASSET,
        )

        schedules = {name: frame for name, frame in result['schedules'].items() if frame is not None}
        data = {
            'schedules': {name: frame_to_dict(frame.round(6)) for name, frame in schedules.items()},
            'tables': to_payload(schedules),
            'model': {symbol: round(float(w), 6) for symbol, w in result['model'].items()},
            'metrics': to_payload(result['metrics']),
            'symbols': list(prices.columns),
        }
        return ViewResponse(
            success=True,
            data=data,
            warnings=result['warnings'],
            message=f"Rolling {request.objective.value} over {len(next(iter(schedules.values())))} periods",
            timestamp=datetime.now(timezone.utc),
        )
