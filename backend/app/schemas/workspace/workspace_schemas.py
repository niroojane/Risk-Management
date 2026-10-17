"""Workspace API schemas: requests of the app views built on named portfolio series

Every view request describes the series to simulate (allocations, strategy
schedules, Bitcoin, the real 'Historical Portfolio') on the price history
starting at `history_start`, and the analysis window [start_date, end_date].
Frames in the responses use the split layout {index, columns, data}.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

from app.common import APIResponse, OptimizationObjective, RebalancingFrequency, VaRMethod
from ..analytics_schemas import AllocationsRequest, AnalyticsRequest, RiskConstraints, WeightConstraint

Schedule = Dict[str, Dict[str, float]]


def _upper_keys(weights: Dict[str, float]) -> Dict[str, float]:
    return {s.strip().upper(): w for s, w in weights.items()}


class CalendarPeriod(str, Enum):
    YEAR = "Year"
    MONTH = "Month"


class WorkspaceRequest(AnalyticsRequest):
    """Universe, analysis window and the named series to simulate"""
    history_start: Optional[datetime] = Field(
        None, description="Start of the price history the series are simulated on (default: start_date)"
    )
    allocations: Dict[str, Dict[str, float]] = Field(
        default_factory=dict, description="Allocations -> 'Rebalanced <name>' and 'Buy and Hold <name>' series"
    )
    frequency: RebalancingFrequency = Field(RebalancingFrequency.MONTHLY, description="Rebalancing frequency")
    strategies: Dict[str, Schedule] = Field(
        default_factory=dict, description="Strategy schedules {name: {date: {symbol: weight}}} (Fund, Core, ...)"
    )
    include_bitcoin: bool = Field(True, description="Add the 'Bitcoin' buy-and-hold series")
    include_historical: bool = Field(False, description="Add the real 'Historical Portfolio' (Binance account)")

    @field_validator('allocations')
    @classmethod
    def normalize_allocations(cls, v):
        return {name: _upper_keys(w) for name, w in v.items()}

    @field_validator('strategies')
    @classmethod
    def normalize_strategies(cls, v):
        return {name: {date: _upper_keys(w) for date, w in schedule.items()} for name, schedule in v.items()}

    @model_validator(mode='after')
    def validate_history_start(self):
        if self.history_start is not None and self.history_start > self.start_date:
            raise ValueError("history_start must be on or before start_date")
        return self

    @property
    def price_start(self) -> datetime:
        return self.history_start or self.start_date


class PerformanceViewRequest(WorkspaceRequest):
    """Strategy tab: performance, drawdown, volatility, tables and efficient frontier"""
    benchmark: Optional[str] = Field(None, description="Allocation used for the tracking errors")
    vol_window: int = Field(252, ge=2, le=2000, description="Rolling volatility window")
    constraints: List[WeightConstraint] = Field(default_factory=list, description="Constraints of the frontier")
    frontier_points: int = Field(100, ge=0, le=200, description="Frontier points (0 to skip it)")


class PairViewRequest(WorkspaceRequest):
    """Views comparing a fund series with a benchmark series"""
    fund: str = Field(..., description="Series analysed")
    benchmark: str = Field(..., description="Benchmark series")


class CalendarViewRequest(PairViewRequest):
    period: CalendarPeriod = Field(CalendarPeriod.YEAR, description="Year or Month")

    @model_validator(mode='after')
    def validate_distinct(self):
        if self.fund == self.benchmark:
            raise ValueError("Benchmark and Fund must be different")
        return self


class BetaViewRequest(PairViewRequest):
    window: int = Field(252, ge=2, le=2000, description="Rolling window")


class RiskTrajectoryRequest(WorkspaceRequest):
    selected: str = Field(..., description="Series whose volatility is decomposed")
    window: int = Field(252, ge=10, le=2000, description="Rolling window")


class TrackingErrorViewRequest(RiskTrajectoryRequest):
    benchmark: str = Field(..., description="Benchmark series")


class VaRHistoryRequest(RiskTrajectoryRequest):
    method: VaRMethod = Field(VaRMethod.GUMBEL_COPULA, description="Simulation method")
    var_centile: float = Field(0.05, gt=0, lt=0.5)
    iterations: int = Field(10000, ge=100, le=100000)
    stress_factor: float = Field(1.0, ge=0)
    mean_factor: float = Field(1.0, ge=0)


class MarketDriversRequest(WorkspaceRequest):
    eigen_frequency: RebalancingFrequency = Field(RebalancingFrequency.QUARTERLY, description="Index rebalancing")
    component: str = Field('PC1', description="Principal component the index follows")
    window: int = Field(252, ge=10, le=2000, description="Rolling window of the risk decomposition")


class RiskContributionRequest(AllocationsRequest):
    """Volatility Analysis > Risk Contribution"""
    fund: str
    benchmark: str
    frequency: RebalancingFrequency = Field(RebalancingFrequency.MONTHLY)

    @model_validator(mode='after')
    def validate_names(self):
        for name in (self.fund, self.benchmark):
            if name not in self.allocations:
                raise ValueError(f"'{name}' is not one of the allocations")
        return self


class StressPreviewRequest(AnalyticsRequest):
    """Value at Risk: effect of the stress grid and mean shocks on the moments"""
    stress_factor: Union[float, List[List[float]]] = Field(1.0, description="Scalar or N x N stress grid")
    mean_shock: Union[float, Dict[str, float]] = Field(1.0, description="Scalar or {symbol: multiplier}")

    @model_validator(mode='after')
    def validate_grid(self):
        n = len(self.symbols)
        if isinstance(self.stress_factor, list) and (
            len(self.stress_factor) != n or any(len(row) != n for row in self.stress_factor)
        ):
            raise ValueError(f"stress_factor grid must be {n} x {n}")
        if isinstance(self.mean_shock, dict):
            self.mean_shock = _upper_keys(self.mean_shock)
        return self


class PCAViewRequest(AnalyticsRequest):
    num_components: int = Field(5, ge=1, le=50)
    component: str = Field('PC1')
    num_closest: int = Field(5, ge=1, le=100)


class CorrelationViewRequest(AnalyticsRequest):
    asset1: str
    asset2: str
    window: int = Field(252, ge=2, le=2000)

    @field_validator('asset1', 'asset2')
    @classmethod
    def upper(cls, v: str) -> str:
        return v.strip().upper()


class Overlay(BaseModel):
    objective: OptimizationObjective = Field(..., description="Overlay strategy objective")
    limit: float = Field(..., ge=0, le=1, description="Weight of the overlay in the fund")


class BacktestRequest(AnalyticsRequest):
    """Rolling optimization (Strategy > 'Get Results')"""
    objective: OptimizationObjective = Field(OptimizationObjective.MINIMUM_VARIANCE, description="Core strategy objective")
    overlays: List[Overlay] = Field(default_factory=list)
    frequency: RebalancingFrequency = Field(RebalancingFrequency.MONTHLY)
    constraints: List[WeightConstraint] = Field(default_factory=list)
    risk_constraints: Optional[RiskConstraints] = None
    benchmark: Optional[Dict[str, float]] = Field(None, description="Benchmark weights (relative objectives / risk)")

    @field_validator('benchmark')
    @classmethod
    def normalize_benchmark(cls, v):
        return _upper_keys(v) if v else v


class PositioningRequest(BaseModel):
    """Current holdings vs. the model allocation"""
    model_weights: Dict[str, float] = Field(default_factory=dict, description="Model weights by symbol")

    @field_validator('model_weights')
    @classmethod
    def normalize(cls, v):
        return _upper_keys(v)


class ViewResponse(APIResponse):
    """Frames ({index, columns, data}), series and scalars of a view"""
    data: Dict[str, Any]
    warnings: List[str] = Field(default_factory=list)
