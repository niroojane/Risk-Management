"""Market data operations - Prices and returns analytics"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import pandas as pd

from .binance_client import BinanceClient
from .transformers import KlineTransformer, ReturnTransformer, RiskTransformer
from ...core.config import CACHE_PRICES_TTL
from ...common import split_date_range
from ...models.investment_universe import MarketDataSnapshot

logger = logging.getLogger(__name__)


class MarketDataService:
    """Handles market data operations (prices + returns analytics)"""

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

    async def get_market_data(
        self,
        symbols: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        use_cache: bool = True,
    ) -> MarketDataSnapshot:
        """Get market data snapshot (prices + returns) for symbols"""
        if end_date is None:
            end_date = datetime.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        logger.info(
            f"Fetching market data for {len(symbols)} symbols "
            f"({start_date.date()} to {end_date.date()})"
        )

        date_chunks = split_date_range(start_date, end_date, chunk_months=3)
        logger.info(f"Split into {len(date_chunks)} chunks for parallel fetching")

        chunk_dataframes = await asyncio.gather(
            *[
                self._fetch_prices_for_chunk(symbols, chunk_start, chunk_end, use_cache)
                for chunk_start, chunk_end in date_chunks
            ]
        )

        if chunk_dataframes:
            price_data = pd.concat(chunk_dataframes, axis=0).sort_index()
            price_data = price_data[~price_data.index.duplicated(keep='first')]
        else:
            price_data = pd.DataFrame()

        prices_by_date = {
            idx.strftime('%Y-%m-%d'): values
            for idx, values in price_data.to_dict(orient='index').items()
        }
        returns_data = ReturnTransformer.calculate_asset_returns(price_data)
        risk_data = RiskTransformer.calculate_asset_risk(price_data)

        return MarketDataSnapshot(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            prices=prices_by_date,
            count=len(price_data),
            returns=returns_data,
            risk=risk_data,
            timestamp=datetime.now(timezone.utc)
        )

    async def get_historical_prices(
        self,
        symbols: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Get historical prices with detailed kline data (for internal use)"""
        if end_date is None:
            end_date = datetime.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        cache_key = f"historical_prices:{','.join(sorted(symbols))}:{start_date.date()}:{end_date.date()}"

        async def fetch():
            logger.info(
                f"Fetching historical prices for {len(symbols)} symbols "
                f"({start_date.date()} to {end_date.date()})"
            )

            start_timestamp = int(start_date.timestamp() * 1000)
            end_timestamp = int(end_date.timestamp() * 1000)

            async def fetch_symbol_klines(symbol: str):
                try:
                    raw_klines = await self._client._run_in_executor(
                        self._client.spot.klines,
                        symbol,
                        "1d",
                        startTime=start_timestamp,
                        endTime=end_timestamp
                    )

                    klines = KlineTransformer.to_dto_list(raw_klines)

                    return {
                        "symbol": symbol,
                        "klines": [k.model_dump() for k in klines]
                    }

                except Exception as e:
                    logger.warning(f"Failed to fetch prices for {symbol}: {e}")
                    return None

            results = await asyncio.gather(*[fetch_symbol_klines(symbol) for symbol in symbols])
            all_prices = [result for result in results if result is not None]

            return {
                "symbols": symbols,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "data": all_prices,
                "count": len(all_prices),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        return await self._client.fetch_with_cache(
            cache_key=cache_key,
            api_call=fetch,
            weight=len(symbols),
            ttl=CACHE_PRICES_TTL,
            use_cache=use_cache,
        )
