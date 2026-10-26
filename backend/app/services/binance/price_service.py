"""Price data operations (klines/candlestick data)"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import pandas as pd

from src import Binance_API as binance_api
from .binance_client import BinanceClient
from ...core.config import CACHE_PRICES_TTL
from .dates import split_date_range

logger = logging.getLogger(__name__)


def _utc_ms(day: datetime) -> int:
    """Milliseconds at 00:00 UTC of `day`'s date: Binance daily candles are UTC days, whatever
    the server's time zone"""
    return int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp() * 1000)


class PriceService:
    """Handles price/kline data retrieval from Binance"""

    def __init__(self, client: BinanceClient):
        self._client = client

    async def _fetch_prices_for_chunk(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """Daily closes of the UTC days from start_date up to end_date (excluded)"""
        cache_key = f"prices_chunk:{','.join(sorted(symbols))}:{start_date.date()}:{end_date.date()}"

        async def fetch():
            return await self._client._run_in_executor(
                binance_api.fetch_closes,
                self._client.spot,
                symbols,
                _utc_ms(start_date),
                _utc_ms(end_date) - 1,
            )

        result = await self._client.fetch_with_cache(
            cache_key=cache_key,
            api_call=fetch,
            weight=len(symbols),
            ttl=CACHE_PRICES_TTL,
            use_cache=use_cache,
        )

        return result if isinstance(result, pd.DataFrame) else pd.DataFrame()

    async def get_prices(
        self,
        symbols: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Get historical prices as dict indexed by date (for API responses)"""
        if end_date is None:
            end_date = datetime.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        price_data = await self.get_price_frame(symbols, start_date, end_date, use_cache)
        price_data.index = price_data.index.strftime('%Y-%m-%d')

        data_by_date = price_data.to_dict(orient='index')

        return {
            "symbols": symbols,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "data": data_by_date,
            "count": len(price_data),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def get_price_frame(
        self,
        symbols: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """Daily close prices as a DataFrame (DatetimeIndex x symbols, for analytics)"""
        if end_date is None:
            end_date = datetime.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        logger.info(
            f"Fetching prices for {len(symbols)} symbols "
            f"({start_date.date()} to {end_date.date()})"
        )

        # Whole UTC days, the end date included: on today, its candle (still open) gives the
        # latest price, as in the notebooks. Split into 3-month chunks.
        first_day = datetime(start_date.year, start_date.month, start_date.day)
        after_last_day = datetime(end_date.year, end_date.month, end_date.day) + timedelta(days=1)
        date_chunks = split_date_range(first_day, after_last_day, chunk_months=3)

        logger.info(f"Split into {len(date_chunks)} chunks for parallel fetching")

        # Fetch all chunks in parallel
        chunk_dataframes = await asyncio.gather(
            *[
                self._fetch_prices_for_chunk(symbols, chunk_start, chunk_end, use_cache)
                for chunk_start, chunk_end in date_chunks
            ]
        )

        # Merge all dataframes and remove duplicates
        if chunk_dataframes:
            price_data = pd.concat(chunk_dataframes, axis=0).sort_index()
            # Remove duplicate dates that may occur at chunk boundaries
            price_data = price_data[~price_data.index.duplicated(keep='first')]
            # Symbols with no klines in the whole range
            price_data = price_data.dropna(axis=1, how='all')
        else:
            price_data = pd.DataFrame()

        price_data.index = pd.to_datetime(price_data.index)
        return price_data
