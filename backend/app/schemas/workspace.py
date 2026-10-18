"""Shared view schemas: the named portfolio series a view is computed on, and the view response.

Every view request describes the series to simulate (allocations, strategy schedules, the
benchmark, the real 'Historical Portfolio') on the price history starting at `history_start`,
and the analysis window [start_date, end_date]. Frames in the responses use the split layout
{index, columns, data}.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator, model_validator

from app.common import APIResponse, RebalancingFrequency
from app.schemas.analytics import AnalyticsRequest


Schedule = Dict[str, Dict[str, float]]


def upper_keys(weights: Dict[str, float]) -> Dict[str, float]:
    return {s.strip().upper(): w for s, w in weights.items()}


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
        return {name: upper_keys(w) for name, w in v.items()}

    @field_validator('strategies')
    @classmethod
    def normalize_strategies(cls, v):
        return {name: {date: upper_keys(w) for date, w in schedule.items()} for name, schedule in v.items()}

    @model_validator(mode='after')
    def validate_history_start(self):
        if self.history_start is not None and self.history_start > self.start_date:
            raise ValueError("history_start must be on or before start_date")
        return self

    @property
    def price_start(self) -> datetime:
        return self.history_start or self.start_date


class PairViewRequest(WorkspaceRequest):
    """Views comparing a fund series with a benchmark series"""
    fund: str = Field(..., description="Series analysed")
    benchmark: str = Field(..., description="Benchmark series")


class ViewResponse(APIResponse):
    """Frames ({index, columns, data}), series and scalars of a view"""
    data: Dict[str, Any]
    warnings: List[str] = Field(default_factory=list)
