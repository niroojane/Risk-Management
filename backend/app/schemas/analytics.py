"""Shared request schemas for the analytics endpoints (strategy, performance, metrics, market risk)"""
import math
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.common import ConstraintSign


class AnalyticsRequest(BaseModel):
    """Universe and date range the analytics are computed on (daily closes)"""
    symbols: List[str] = Field(..., description="Trading symbols of the universe", min_length=1)
    start_date: datetime = Field(..., description="Start date of the price history")
    end_date: datetime = Field(..., description="End date of the price history")
    use_cache: bool = Field(True, description="Use cached prices if available")

    @field_validator('symbols')
    @classmethod
    def validate_symbols(cls, v: List[str]) -> List[str]:
        """Uppercase and de-duplicate symbols, keeping their order"""
        return list(dict.fromkeys(s.strip().upper() for s in v))

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v: datetime, info) -> datetime:
        """Validate end_date is after start_date"""
        if 'start_date' in info.data and v <= info.data['start_date']:
            raise ValueError("end_date must be after start_date")
        return v


class AllocationsRequest(AnalyticsRequest):
    """Analytics on named allocations: {name: {symbol: weight}}"""
    allocations: Dict[str, Dict[str, float]] = Field(
        ...,
        description="Named allocations, weights by symbol (missing symbols weigh 0)",
        min_length=1,
    )

    @field_validator('allocations')
    @classmethod
    def validate_weights(cls, v: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
        """Uppercase symbols and reject non-finite weights"""
        cleaned = {}
        for name, weights in v.items():
            if any(not math.isfinite(w) for w in weights.values()):
                raise ValueError(f"Allocation '{name}' has non-finite weights")
            cleaned[name] = {s.strip().upper(): w for s, w in weights.items()}
        return cleaned

    @model_validator(mode='after')
    def validate_allocation_symbols(self):
        """Every weighted symbol must be part of the universe"""
        for name, weights in self.allocations.items():
            unknown = sorted(set(weights) - set(self.symbols))
            if unknown:
                raise ValueError(f"Allocation '{name}' uses symbols outside 'symbols': {unknown}")
        return self


class WeightConstraint(BaseModel):
    """Bound on the weight of one asset, or of every asset with 'All'"""
    asset: str = Field(..., description="Symbol, or 'All' for every asset")
    sign: ConstraintSign = Field(..., description="'=', '>=' or '<=' ('≥' / '≤' accepted)")
    limit: float = Field(..., description="Weight limit, in decimals", ge=0, le=1)

    @field_validator('asset')
    @classmethod
    def normalize_asset(cls, v: str) -> str:
        return 'All' if v.strip().lower() == 'all' else v.strip().upper()


class RiskConstraint(BaseModel):
    """Bound on a portfolio risk measure"""
    sign: ConstraintSign = Field(..., description="'=', '>=' or '<=' ('≥' / '≤' accepted)")
    limit: float = Field(..., description="Limit (annualized, in decimals for volatility / tracking error)")


class RiskConstraints(BaseModel):
    """Portfolio-level constraints; beta, tracking error and information ratio are vs. the benchmark"""
    volatility: Optional[RiskConstraint] = None
    beta: Optional[RiskConstraint] = None
    tracking_error: Optional[RiskConstraint] = None
    information_ratio: Optional[RiskConstraint] = None

    def as_dict(self) -> Dict[str, tuple]:
        """{name: (solver sign, limit)} of the constraints that are set"""
        return {
            name: (constraint.sign.solver_sign, constraint.limit)
            for name, constraint in (
                ('volatility', self.volatility),
                ('beta', self.beta),
                ('tracking_error', self.tracking_error),
                ('information_ratio', self.information_ratio),
            )
            if constraint is not None
        }
