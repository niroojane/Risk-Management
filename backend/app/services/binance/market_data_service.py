"""Market data operations (public Binance endpoints)"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from .binance_service import BinanceClient
from ...core.config import CACHE_MARKET_CAP_TTL, CACHE_PRICES_TTL

logger = logging.getLogger(__name__)


class MarketDataService:
    """Handles public market data endpoints"""

    def __init__(self, client: BinanceClient):
        self._client = client

    async def get_market_cap(
        self, quote: str = "USDT", use_cache: bool = True
    ) -> Dict[str, Any]:
        """Get market capitalization data for all assets"""
        cache_key = f"market_cap:{quote}"

        async def fetch():
            logger.info(f"Fetching market cap from Binance API (quote={quote})")
            df = await self._client._run_in_executor(
                self._client.api.get_market_cap, quote=quote
            )
            return {
                "quote": quote,
                "data": self._client._dataframe_to_dict(df),
                "count": len(df),
                "timestamp": datetime.utcnow().isoformat(),
            }

        return await self._client.fetch_with_cache(
            cache_key=cache_key,
            api_call=fetch,
            weight=40,
            ttl=CACHE_MARKET_CAP_TTL,
            use_cache=use_cache,
        )

    async def get_prices(
        self,
        tickers: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Get historical prices for a list of tickers"""
        if end_date is None:
            end_date = datetime.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        cache_key = f"prices:{','.join(sorted(tickers))}:{start_date.date()}:{end_date.date()}"

        async def fetch():
            logger.info(
                f"Fetching prices for {len(tickers)} tickers "
                f"({start_date.date()} to {end_date.date()})"
            )
            df = await self._client._run_in_executor(
                self._client.api.get_price, ticker_list=tickers, date=end_date
            )

            if start_date:
                df = df[df.index >= start_date.strftime("%Y-%m-%d")]

            return {
                "tickers": tickers,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "data": self._client._dataframe_to_dict(df),
                "count": len(df),
                "timestamp": datetime.utcnow().isoformat(),
            }

        return await self._client.fetch_with_cache(
            cache_key=cache_key,
            api_call=fetch,
            weight=len(tickers),
            ttl=CACHE_PRICES_TTL,
            use_cache=use_cache,
        )
