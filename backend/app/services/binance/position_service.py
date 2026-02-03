"""Position calculations (orchestrates price and quantity services)"""
import logging
from typing import List, Optional
from datetime import datetime

from .price_service import PriceService
from .quantity_service import QuantityService
from .transformers import KlineTransformer, BalanceTransformer
from ...models.investment_universe import Position

logger = logging.getLogger(__name__)


class PositionService:
    """Orchestrates position calculations using price and quantity data"""

    def __init__(self, price_service: PriceService, quantity_service: QuantityService):
        self._price_service = price_service
        self._quantity_service = quantity_service

    async def get_historical_positions(
        self,
        symbols: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        use_cache: bool = True,
    ) -> List[Position]:
        """Calculate historical positions by multiplying quantities by prices"""
        logger.info(f"Calculating historical positions for {len(symbols)} symbols")

        # Fetch prices and quantities in parallel
        prices_data = await self._price_service.get_historical_prices(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            use_cache=use_cache
        )

        # Calculate limit based on date range
        if start_date and end_date:
            days_diff = (end_date - start_date).days + 1
            calculated_limit = min(days_diff, 365)
        else:
            calculated_limit = 30

        quantities_data = await self._quantity_service.get_historical_quantities(
            end_date=end_date,
            limit=calculated_limit,
            use_cache=use_cache
        )

        # Transform prices to dict: {symbol: {date: price}}
        prices_dict = {}
        for symbol_data in prices_data["data"]:
            symbol = symbol_data["symbol"]
            prices_dict[symbol] = KlineTransformer.dict_to_dict_by_date(symbol_data["klines"])

        # Transform quantities to dict: {symbol: {date: quantity}}
        quantities_dict = BalanceTransformer.snapshots_to_quantities_dict(
            quantities_data["data"]
        )

        # Calculate positions: position = quantity * price
        positions = []
        for symbol in symbols:
            if symbol not in prices_dict or symbol not in quantities_dict:
                continue

            # Find common dates between prices and quantities
            common_dates = set(prices_dict[symbol].keys()) & set(quantities_dict[symbol].keys())

            for date in sorted(common_dates):
                position_value = quantities_dict[symbol][date] * prices_dict[symbol][date]
                positions.append(Position(
                    date=datetime.combine(date, datetime.min.time()),
                    symbol=symbol,
                    position=round(position_value, 2)
                ))

        return positions
