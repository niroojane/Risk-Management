"""Account Controller - holdings, positioning vs. the model, P&L, history files"""
from datetime import datetime, timezone

import pandas as pd

from ...common import to_payload
from ...schemas.workspace import PositioningRequest, ViewResponse
from ...services.account import PortfolioAccount


class AccountController:
    """Controller orchestrating the real-portfolio operations (Binance account or Excel files)"""

    def __init__(self, account_service: PortfolioAccount):
        self._service = account_service

    @staticmethod
    def _response(data, message: str) -> ViewResponse:
        warnings = list(data.pop('warnings', []) or [])
        return ViewResponse(success=True, data=to_payload(data), warnings=warnings, message=message,
                            timestamp=datetime.now(timezone.utc))

    async def holdings(self, use_cache: bool = True) -> ViewResponse:
        """Value and weight of each held asset"""
        data = await self._service.holdings_view(use_cache)
        return self._response(data, f"{len(data['tickers'])} assets held")

    async def positioning(self, request: PositioningRequest) -> ViewResponse:
        """Current holdings vs. the model allocation"""
        data = await self._service.positioning(pd.Series(request.model_weights, dtype=float))
        return self._response(data, "Positioning vs model")

    async def pnl(self, use_cache: bool = True) -> ViewResponse:
        """Book cost, realized and unrealized P&L per held asset, and the trade history"""
        data = await self._service.pnl(use_cache)
        return self._response(data, "P&L of the real portfolio")

    async def upload(self) -> ViewResponse:
        """Save the history files to GitHub (Binance: push; Excel: 'Update Files')"""
        data = await self._service.upload()
        return self._response(data, "Files saved to GitHub")
