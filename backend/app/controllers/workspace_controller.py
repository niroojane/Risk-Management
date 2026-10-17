"""Base controller for the views built on named portfolio series"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

from .analytics_controller import AnalyticsController
from ..common import to_payload
from ..core.exceptions import DataValidationError
from ..core.market import get_profile
from ..schemas.workspace import ViewResponse, WorkspaceRequest
from ..services.account import PortfolioAccount
from ..services.analytics import workspace as ws_analytics
from ..services.analytics.portfolio_analytics import allocation_frame
from ..services.binance import PriceService


class WorkspaceController(AnalyticsController):
    """Loads prices (and the account history when requested) and builds the workspace"""

    def __init__(self, price_service: PriceService, account_service: Optional[PortfolioAccount] = None):
        super().__init__(price_service)
        self._account = account_service

    async def _load_universe(self, request: WorkspaceRequest, warnings: List[str]) -> pd.DataFrame:
        """Universe prices from `history_start`, cleaned as the notebook's 'Get Prices'"""
        raw = await self._price_service.get_price_frame(
            symbols=request.symbols,
            start_date=request.price_start,
            end_date=request.end_date,
            use_cache=request.use_cache,
        )
        prices = ws_analytics.clean_prices(raw.astype(float), excluded=get_profile().excluded_symbols)
        dropped = [s for s in request.symbols if s not in prices.columns]
        if dropped:
            warnings.append(f"Not enough price history, excluded: {', '.join(dropped)}")
        if prices.shape[1] == 0 or len(prices) < 3:
            raise DataValidationError("Not enough price data for this universe and date range")
        return prices

    async def _load_workspace(self, request: WorkspaceRequest, warnings: List[str]) -> ws_analytics.Workspace:
        prices = await self._load_universe(request, warnings)

        positions = historical_prices = None
        if request.include_historical:
            if self._account is None:
                raise DataValidationError("The Historical Portfolio needs the Binance account service")
            history = await self._account.get_history(request.use_cache)
            positions = history.positions
            historical_prices = await self._account.get_history_prices(history, request.use_cache)

        allocations = allocation_frame(request.allocations, prices.columns) if request.allocations else None
        strategies = {}
        for name, schedule in request.strategies.items():
            frame = pd.DataFrame.from_dict(schedule, orient='index', dtype=float)
            frame.index = pd.to_datetime(frame.index)
            strategies[name] = frame.reindex(columns=prices.columns).fillna(0.0)

        profile = get_profile()
        return await self._compute(
            ws_analytics.build_workspace,
            prices,
            allocations=allocations,
            frequency=request.frequency.value,
            strategies=strategies,
            include_bitcoin=request.include_bitcoin,
            positions=positions,
            historical_prices=historical_prices,
            benchmark=(profile.benchmark_label, profile.benchmark_ticker),
            cash=profile.cash_assets,
        )

    @staticmethod
    def _response(data: Dict[str, Any], warnings: List[str], message: str) -> ViewResponse:
        warnings = warnings + list(data.pop('warnings', []) or [])
        return ViewResponse(
            success=True,
            data=to_payload(data),
            warnings=warnings,
            message=message,
            timestamp=datetime.now(timezone.utc),
        )

    @staticmethod
    def _window(request: WorkspaceRequest):
        return pd.Timestamp(request.start_date.date()), pd.Timestamp(request.end_date.date())
