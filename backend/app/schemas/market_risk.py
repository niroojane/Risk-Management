"""Market Risk tab: PCA, correlation, market drivers"""
from datetime import datetime
from typing import Optional

from pydantic import Field, field_validator

from app.common import RebalancingFrequency
from app.schemas.analytics import AnalyticsRequest
from app.schemas.workspace import WorkspaceRequest


class PCAViewRequest(AnalyticsRequest):
    num_components: int = Field(5, ge=1, le=50)
    component: str = Field('PC1')
    num_closest: int = Field(5, ge=1, le=100)


class CorrelationViewRequest(AnalyticsRequest):
    asset1: str
    asset2: str
    window: int = Field(252, ge=2, le=2000)
    history_start: Optional[datetime] = Field(
        None, description="Start of the price history the rolling windows can reach back to (default: start_date)"
    )

    @field_validator('asset1', 'asset2')
    @classmethod
    def upper(cls, v: str) -> str:
        return v.strip().upper()


class MarketDriversRequest(WorkspaceRequest):
    eigen_frequency: RebalancingFrequency = Field(RebalancingFrequency.QUARTERLY, description="Index rebalancing")
    component: str = Field('PC1', description="Principal component the index follows")
    window: int = Field(252, ge=10, le=2000, description="Rolling window of the risk decomposition")
