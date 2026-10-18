"""Current Portfolio and Strategy Return views: performance, calendar, beta"""
from enum import Enum
from typing import List, Optional

from pydantic import Field, model_validator

from app.schemas.analytics import WeightConstraint
from app.schemas.workspace import PairViewRequest, WorkspaceRequest


class CalendarPeriod(str, Enum):
    YEAR = "Year"
    MONTH = "Month"


class PerformanceViewRequest(WorkspaceRequest):
    """Strategy tab: performance, drawdown, volatility, tables and efficient frontier"""
    benchmark: Optional[str] = Field(None, description="Allocation used for the tracking errors")
    vol_window: int = Field(252, ge=2, le=2000, description="Rolling volatility window")
    constraints: List[WeightConstraint] = Field(default_factory=list, description="Constraints of the frontier")
    frontier_points: int = Field(100, ge=0, le=200, description="Frontier points (0 to skip it)")


class CalendarViewRequest(PairViewRequest):
    period: CalendarPeriod = Field(CalendarPeriod.YEAR, description="Year or Month")

    @model_validator(mode='after')
    def validate_distinct(self):
        if self.fund == self.benchmark:
            raise ValueError("Benchmark and Fund must be different")
        return self


class BetaViewRequest(PairViewRequest):
    window: int = Field(252, ge=2, le=2000, description="Rolling window")
