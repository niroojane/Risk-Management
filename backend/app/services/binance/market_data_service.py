"""Market data operations - Prices and returns analytics"""
import asyncio
import logging
import math
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import pandas as pd

from .binance_client import BinanceClient
from .transformers import KlineTransformer
from ...core.config import CACHE_PRICES_TTL
from ...common import split_date_range
from ...models.investment_universe import (
    MarketDataSnapshot,
    MarketReturnsData,
    AssetReturnMetrics
)

logger = logging.getLogger(__name__)


def calculate_asset_returns(prices: pd.DataFrame) -> Optional[MarketReturnsData]:
    """Calculate return metrics for each asset and return as MarketReturnsData entity"""
    if prices.empty or len(prices) < 2:
        return None

    # Ensure index is datetime (needed when data comes from cache)
    if not isinstance(prices.index, pd.DatetimeIndex):
        prices.index = pd.to_datetime(prices.index)

    total_returns = (prices.iloc[-1] / prices.iloc[0] - 1)

    days_elapsed = (prices.index[-1] - prices.index[0]).days
    if days_elapsed > 0:
        annualized_returns = (1 + total_returns) ** (365 / days_elapsed) - 1
    else:
        annualized_returns = pd.Series(0.0, index=total_returns.index)

    latest_year = prices.index[-1].year
    ytd_start = pd.Timestamp(year=latest_year, month=1, day=1)
    ytd_prices = prices.loc[prices.index >= ytd_start]

    if len(ytd_prices) >= 2:
        ytd_returns = (ytd_prices.iloc[-1] / ytd_prices.iloc[0] - 1)
    else:
        ytd_returns = pd.Series(0.0, index=total_returns.index)

    assets = []
    for symbol in total_returns.index:
        # Skip symbols with invalid data (NaN or Inf)
        total_ret = float(total_returns[symbol])
        ytd_ret = float(ytd_returns[symbol])
        ann_ret = float(annualized_returns[symbol])

        if not (math.isnan(total_ret) or math.isnan(ytd_ret) or math.isnan(ann_ret) or
                math.isinf(total_ret) or math.isinf(ytd_ret) or math.isinf(ann_ret)):
            assets.append(AssetReturnMetrics(
                symbol=symbol,
                total_return=round(total_ret, 6),
                ytd_return=round(ytd_ret, 6),
                annualized_return=round(ann_ret, 6)
            ))

    return MarketReturnsData(
        period_start_date=prices.index[0].to_pydatetime(),
        ytd_start_date=ytd_start.to_pydatetime(),
        assets=assets
    )


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

        prices_by_date = price_data.to_dict(orient='index')
        returns_data = calculate_asset_returns(price_data)

        return MarketDataSnapshot(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            prices=prices_by_date,
            count=len(price_data),
            returns=returns_data,
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
