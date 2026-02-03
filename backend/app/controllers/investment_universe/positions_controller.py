"""Positions Controller - Business logic for position operations"""
from datetime import datetime, timezone

from ...services.binance import PositionService
from ...schemas.investment_universe import (
    PositionsRequest,
    PositionsResponse,
)


class PositionsController:
    """Controller orchestrating position operations"""

    def __init__(self, position_service: PositionService):
        self._service = position_service

    async def get_positions(self, request: PositionsRequest) -> PositionsResponse:
        """Calculate historical positions (quantities × prices)"""
        positions = await self._service.get_historical_positions(
            symbols=request.symbols,
            start_date=request.start_date,
            end_date=request.end_date,
            use_cache=True,
        )

        return PositionsResponse(
            success=True,
            data=positions,
            message=f"Retrieved {len(positions)} positions for {len(request.symbols)} symbols",
            timestamp=datetime.now(timezone.utc),
        )
