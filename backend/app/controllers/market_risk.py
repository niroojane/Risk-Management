"""Market Risk tab: PCA, correlation, market drivers"""
import pandas as pd

from app.controllers.base import WorkspaceController
from app.schemas.market_risk import CorrelationViewRequest, MarketDriversRequest, PCAViewRequest
from app.schemas.workspace import ViewResponse
from src import Workspace as ws_analytics


class MarketRiskController(WorkspaceController):
    """Controller orchestrating market risk analysis"""

    async def get_pca_view(self, request: PCAViewRequest) -> ViewResponse:
        """Variance explained, eigen weights, eigen index and PCA similarity"""
        returns = await self._load_returns(request)
        data = await self._compute(
            ws_analytics.pca_view, returns, request.num_components, request.component, request.num_closest
        )
        return self._response(data, [], f"PCA of {returns.shape[1]} assets")

    async def get_correlation_view(self, request: CorrelationViewRequest) -> ViewResponse:
        """Rolling pair correlation, rolling mean returns, PC1 over time and correlation matrix"""
        # from history_start: the rolling charts reach back one window before start_date
        history_start = request.history_start
        if history_start is None or history_start.date() > request.start_date.date():
            history_start = request.start_date
        returns = await self._load_returns(request.model_copy(update={'start_date': history_start}))
        data = await self._compute(ws_analytics.correlation_view, returns, request.asset1, request.asset2,
                                   request.window, pd.Timestamp(request.start_date.date()),
                                   pd.Timestamp(request.end_date.date()))
        return self._response(data, [], f"Correlation of {request.asset1} / {request.asset2}")

    async def get_market_drivers(self, request: MarketDriversRequest) -> ViewResponse:
        """Eigen-portfolio market index, its drivers and its risk decomposition"""
        warnings = []
        ws = await self._load_workspace(request, warnings)
        start, end = self._window(request)
        data = await self._compute(
            ws_analytics.market_drivers_view, ws, start, end, request.eigen_frequency.value, request.component,
            request.window,
        )
        return self._response(data, warnings, "Market drivers")
