"""Risk Analysis tab: risk contribution, trajectories, tracking error, Value at Risk, stress"""
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

from app.common import APIResponse, RebalancingFrequency, VaRMethod
from app.schemas.analytics import AllocationsRequest, AnalyticsRequest
from app.schemas.workspace import WorkspaceRequest, upper_keys


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


class RiskTrajectoryRequest(WorkspaceRequest):
    """Every series is decomposed: the fund to show is picked client-side"""
    window: int = Field(252, ge=10, le=2000, description="Rolling window")


class TrackingErrorViewRequest(RiskTrajectoryRequest):
    benchmark: str = Field(..., description="Benchmark series")


class VaRHistoryRequest(RiskTrajectoryRequest):
    method: VaRMethod = Field(VaRMethod.GUMBEL_COPULA, description="Simulation method")
    var_centile: float = Field(0.05, gt=0, lt=0.5)
    iterations: int = Field(10000, ge=100, le=100000)
    stress_factor: float = Field(1.0, ge=0)
    mean_factor: float = Field(1.0, ge=0)


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
            self.mean_shock = upper_keys(self.mean_shock)
        return self


Table = Dict[str, Dict[str, Any]]


ALLOCATIONS_EXAMPLE = {
    "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
    "start_date": "2023-01-01T00:00:00Z",
    "end_date": "2024-12-31T23:59:59Z",
    "allocations": {
        "Fund": {"BTCUSDT": 0.5, "ETHUSDT": 0.3, "BNBUSDT": 0.2},
        "Bitcoin": {"BTCUSDT": 1.0}
    },
}


StressFactor = Union[float, List[float], List[List[float]]]


class VaRRequest(AllocationsRequest):
    """Request parameters for the Value at Risk endpoint"""
    var_centile: float = Field(0.05, description="VaR percentile (0.05 = 95% VaR)", gt=0, lt=0.5)
    iterations: int = Field(10000, description="Simulated scenarios per draw", ge=100, le=100000)
    num_scenarios: int = Field(1, description="Independent draws averaged per method", ge=1, le=100)
    horizon_days: int = Field(1, description="Monte Carlo horizon, in days", ge=1, le=252)
    theta: float = Field(2.0, description="Gumbel copula dependence parameter", ge=1)
    methods: List[VaRMethod] = Field(default_factory=lambda: list(VaRMethod), description="Simulation methods")
    stress_factor: StressFactor = Field(
        1.0,
        description=("Volatility stress: a scalar, one multiplier per symbol, or an N x N grid "
                     "(diagonal = volatility multipliers, off-diagonal = correlation shocks)"),
    )
    mean_shock: Union[float, Dict[str, float]] = Field(
        1.0, description="Multiplier of the mean returns: a scalar or {symbol: multiplier} (missing -> 1)"
    )
    backtest_window: Optional[int] = Field(
        None, description="Rolling window of the VaR backtest + Kupiec test (omit to skip it)", ge=10
    )

    @field_validator('mean_shock')
    @classmethod
    def normalize_mean_shock(cls, v):
        if isinstance(v, dict):
            return {s.strip().upper(): w for s, w in v.items()}
        return v

    @model_validator(mode='after')
    def validate_stress_shape(self):
        n = len(self.symbols)
        stress = self.stress_factor
        if isinstance(stress, list):
            if stress and isinstance(stress[0], list):
                if len(stress) != n or any(len(row) != n for row in stress):
                    raise ValueError(f"stress_factor grid must be {n} x {n} (one row/column per symbol)")
            elif len(stress) != n:
                raise ValueError(f"stress_factor must have {n} values (one per symbol)")
        return self

    model_config = {
        "json_schema_extra": {
            "examples": [{**ALLOCATIONS_EXAMPLE, "var_centile": 0.05, "iterations": 10000, "stress_factor": 1.0}]
        }
    }


class Histogram(BaseModel):
    """Distribution of the simulated portfolio returns"""
    counts: List[int]
    bin_edges: List[float]


class VaRMethodResult(BaseModel):
    """VaR / CVaR of one method (daily returns, negative = loss)"""
    var: Optional[float] = None
    cvar: Optional[float] = None
    var_contribution: Optional[Dict[str, Optional[float]]] = Field(
        None, description="Contribution of each symbol to the VaR scenario (simulations only)"
    )
    cvar_contribution: Optional[Dict[str, Optional[float]]] = Field(
        None, description="Contribution of each symbol to the CVaR (simulations only)"
    )
    histogram: Optional[Histogram] = Field(None, description="Simulated distribution (simulations only)")


class VaRBacktest(BaseModel):
    """Rolling VaR vs. realized portfolio returns"""
    series: Table = Field(..., description="{date: {'Historical', 'Parametric', 'Multivariate', 'Portfolio'}}")
    kupiec: Table = Field(..., description="{statistic: {model: value}}")


class VaRAllocationResult(BaseModel):
    methods: Dict[str, VaRMethodResult] = Field(
        ..., description="historical, parametric and the requested simulation methods"
    )
    backtest: Optional[VaRBacktest] = None


class VaRResponse(APIResponse):
    data: Dict[str, VaRAllocationResult] = Field(..., description="VaR results by allocation")
