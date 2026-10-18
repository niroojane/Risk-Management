"""Strategy tab: optimization and the rolling backtest"""
import math
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.common import APIResponse, OptimizationObjective, RebalancingFrequency
from app.schemas.analytics import AnalyticsRequest, RiskConstraints, WeightConstraint
from app.schemas.workspace import upper_keys


DEFAULT_OBJECTIVES = [
    OptimizationObjective.SHARPE_RATIO,
    OptimizationObjective.MINIMUM_VARIANCE,
    OptimizationObjective.RISK_PARITY,
    OptimizationObjective.MAXIMUM_DIVERSIFICATION,
    OptimizationObjective.EIGENPORTFOLIO,
]


class ConstrainedRequest(AnalyticsRequest):
    """Universe + weight constraints shared by the strategy endpoints"""
    constraints: List[WeightConstraint] = Field(
        default_factory=list, description="Weight bounds per asset ('All' applies to every asset)"
    )

    @model_validator(mode='after')
    def validate_constraint_assets(self):
        unknown = sorted({c.asset for c in self.constraints} - set(self.symbols) - {'All'})
        if unknown:
            raise ValueError(f"Constraints on symbols outside 'symbols': {unknown}")
        return self


class OptimizationRequest(ConstrainedRequest):
    """Request parameters for the optimization endpoint"""
    objectives: List[OptimizationObjective] = Field(
        default_factory=lambda: list(DEFAULT_OBJECTIVES),
        description="Objectives to optimize (tracking_error / information_ratio need a benchmark)",
        min_length=1,
    )
    risk_constraints: Optional[RiskConstraints] = Field(
        None, description="Portfolio-level constraints (beta, tracking error, IR are vs. the benchmark)"
    )
    benchmark: Optional[Dict[str, float]] = Field(
        None, description="Benchmark weights by symbol (missing symbols weigh 0)"
    )
    benchmark_frequency: Optional[RebalancingFrequency] = Field(
        None, description="Measure the beta constraint against the benchmark rebalanced at this frequency"
    )

    @field_validator('benchmark')
    @classmethod
    def normalize_benchmark(cls, v: Optional[Dict[str, float]]) -> Optional[Dict[str, float]]:
        if v is None:
            return v
        if any(not math.isfinite(w) for w in v.values()):
            raise ValueError("benchmark has non-finite weights")
        return {s.strip().upper(): w for s, w in v.items()}

    @model_validator(mode='after')
    def validate_benchmark_symbols(self):
        if self.benchmark:
            unknown = sorted(set(self.benchmark) - set(self.symbols))
            if unknown:
                raise ValueError(f"benchmark uses symbols outside 'symbols': {unknown}")
        return self

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"],
                "start_date": "2023-01-01T00:00:00Z",
                "end_date": "2024-12-31T23:59:59Z",
                "objectives": ["sharpe_ratio", "minimum_variance", "risk_parity", "tracking_error"],
                "constraints": [
                    {"asset": "All", "sign": "<=", "limit": 0.6},
                    {"asset": "BTCUSDT", "sign": ">=", "limit": 0.2}
                ],
                "risk_constraints": {"volatility": {"sign": "<=", "limit": 0.7}},
                "benchmark": {"BTCUSDT": 1.0}
            }]
        }
    }


class OptimizationData(BaseModel):
    """Optimized allocations and their expected metrics"""
    allocations: Dict[str, Dict[str, float]] = Field(
        ..., description="Weights by symbol for each objective (+ equal_weight)"
    )
    metrics: Dict[str, Dict[str, Optional[float]]] = Field(
        ..., description="{'Expected Returns' | 'Expected Volatility' | 'Sharpe Ratio': {allocation: value}}"
    )
    warnings: List[str] = Field(default_factory=list, description="Optimizer convergence warnings")


class OptimizationResponse(APIResponse):
    """Response for the optimization endpoint"""
    data: OptimizationData


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
        return upper_keys(v) if v else v
