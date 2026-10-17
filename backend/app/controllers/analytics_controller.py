"""Base controller for analytics endpoints - loads prices and runs CPU-bound computations"""
import asyncio
import logging
from typing import Any, Callable

import numpy as np
import pandas as pd
from numpy.linalg import LinAlgError

from ..core.exceptions import DataValidationError
from ..schemas.analytics_schemas import AllocationsRequest, AnalyticsRequest
from ..services.analytics.portfolio_analytics import allocation_frame, to_returns
from ..services.binance import PriceService

logger = logging.getLogger(__name__)

MIN_OBSERVATIONS = 3


class AnalyticsController:
    """Shared plumbing: price loading, validation and off-loop computation"""

    def __init__(self, price_service: PriceService):
        self._price_service = price_service

    async def _load_prices(self, request: AnalyticsRequest) -> pd.DataFrame:
        """Daily close prices of the requested symbols (DatetimeIndex x symbols)"""
        prices = await self._price_service.get_price_frame(
            symbols=request.symbols,
            start_date=request.start_date,
            end_date=request.end_date,
            use_cache=request.use_cache,
        )

        missing = [s for s in request.symbols if s not in prices.columns or prices[s].isna().all()]
        if missing:
            raise DataValidationError(
                message=f"No price data for: {', '.join(missing)}",
                detail="Check the symbols and that they were listed during the requested period",
            )

        prices = prices[request.symbols].astype(float).sort_index()
        if len(prices) < MIN_OBSERVATIONS:
            raise DataValidationError(
                message=f"Not enough price history ({len(prices)} days)",
                detail=f"At least {MIN_OBSERVATIONS} daily prices are needed",
            )
        return prices

    async def _load_returns(self, request: AnalyticsRequest) -> pd.DataFrame:
        """Daily simple returns of the requested symbols"""
        return to_returns(await self._load_prices(request))

    @staticmethod
    def _allocations(request: AllocationsRequest) -> pd.DataFrame:
        """Allocation grid of the request (index = names, columns = symbols)"""
        return allocation_frame(request.allocations, request.symbols)

    @staticmethod
    async def _compute(func: Callable[..., Any], *args, **kwargs) -> Any:
        """Run a CPU-bound analytics function in a worker thread.

        Invalid inputs surfacing as ValueError / LinAlgError become 400s.
        """
        try:
            with np.errstate(divide='ignore', invalid='ignore'):
                return await asyncio.to_thread(func, *args, **kwargs)
        except (ValueError, LinAlgError) as exc:
            logger.warning(f"Analytics computation failed: {exc}")
            raise DataValidationError(message=str(exc), detail="The computation could not be performed on this input")
