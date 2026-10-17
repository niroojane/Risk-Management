"""Market Risk Controller - Business logic for PCA, correlation and market drivers"""
from ..workspace_controller import WorkspaceController
from ...schemas.workspace import CorrelationViewRequest, MarketDriversRequest, PCAViewRequest, ViewResponse
from ...services.analytics import workspace as ws_analytics


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
        returns = await self._load_returns(request)
        data = await self._compute(ws_analytics.correlation_view, returns, request.asset1, request.asset2,
                                   request.window)
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
