"""Price data operations (klines/candlestick data)"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import pandas as pd

from .binance_client import BinanceClient
from .transformers import KlineTransformer
from ...core.config import CACHE_PRICES_TTL
from ...common import split_date_range

logger = logging.getLogger(__name__)


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
        """Fetch prices for a single date range chunk"""
        cache_key = f"prices_chunk:{','.join(sorted(symbols))}:{start_date.date()}:{end_date.date()}"

        async def fetch():
            start_timestamp = int(start_date.timestamp() * 1000)
            end_timestamp = int(end_date.timestamp() * 1000)

            symbols_klines = {}
            for symbol in symbols:
                try:
                    if symbol == 'USDTUSDT':
                        symbols_klines[symbol] = []
                        continue

                    klines = await self._client._run_in_executor(
                        self._client.spot.klines,
                        symbol=symbol,
                        interval="1d",
                        startTime=start_timestamp,
                        endTime=end_timestamp
                    )
                    symbols_klines[symbol] = klines if klines else []

                except Exception as e:
                    logger.warning(f"Failed to fetch {symbol}: {e}")
                    continue

            return KlineTransformer.merge_symbols_to_dataframe(symbols_klines)

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

        # Split date range into 3-month chunks
        date_chunks = split_date_range(start_date, end_date, chunk_months=3)

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
        else:
            price_data = pd.DataFrame()

        price_data.index = pd.to_datetime(price_data.index)
        return price_data
