"""Price data operations (klines/candlestick data)"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone

from .binance_client import BinanceClient
from .transformers import KlineTransformer
from ...core.config import CACHE_PRICES_TTL
from ...models.investment_universe import AssetPrices, PriceDataPoint

logger = logging.getLogger(__name__)


class PriceService:
    """Handles price/kline data retrieval from Binance"""

    def __init__(self, client: BinanceClient):
        self._client = client

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

        cache_key = f"prices:{','.join(sorted(symbols))}:{start_date.date()}:{end_date.date()}"

        async def fetch():
            logger.info(
                f"Fetching prices for {len(symbols)} symbols "
                f"({start_date.date()} to {end_date.date()})"
            )

            start_timestamp = int(start_date.timestamp() * 1000)
            end_timestamp = int(end_date.timestamp() * 1000)

            # Fetch all symbols in parallel
            symbols_klines = {}
            for symbol in symbols:
                try:
                    if symbol == 'USDTUSDT':
                        symbols_klines[symbol] = []  # Handled by transformer
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

            price_data = KlineTransformer.merge_symbols_to_dataframe(symbols_klines)
            data_by_date = price_data.to_dict(orient='index')

            return {
                "symbols": symbols,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "data": data_by_date,
                "count": len(price_data),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        return await self._client.fetch_with_cache(
            cache_key=cache_key,
            api_call=fetch,
            weight=len(symbols),
            ttl=CACHE_PRICES_TTL,
            use_cache=use_cache,
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
