"""Yahoo Finance data for the backend: cached, run off the event loop"""
import asyncio
import datetime
import logging
from typing import Iterable, List, Optional, Sequence, Tuple

import pandas as pd

from src import Yahoo_API as yahoo_api
from ..cache import CacheService
from ...core.config import CACHE_PRICES_TTL

logger = logging.getLogger(__name__)

CURRENCY_TTL = 24 * 3600


def _as_date(value) -> datetime.date:
    if value is None:
        return datetime.date.today()
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    return pd.Timestamp(value).date()


class YahooMarketData:
    """Async, cached access to the yahoo_api helpers (same functions as the Multi Asset App)"""

    def __init__(self, cache: Optional[CacheService] = None):
        self._cache = cache

    async def _cached(self, key: str, ttl: int, use_cache: bool, factory):
        if use_cache and self._cache:
            cached = await self._cache.get(key)
            if cached is not None:
                return cached
        value = await asyncio.to_thread(factory)
        if self._cache:
            await self._cache.set(key, value, ttl=ttl)
        return value

    async def close(self, tickers: Sequence[str], start=None, end=None, use_cache: bool = True) -> pd.DataFrame:
        """Adjusted daily closes in each ticker's quote currency (gaps <= 5 days forward-filled)"""
        tickers = sorted({t for t in tickers if t})
        if not tickers:
            return pd.DataFrame()
        start, end = _as_date(start), _as_date(end)
        key = f"yahoo:close:{','.join(tickers)}:{start}:{end}"

        def fetch():
            prices = yahoo_api.get_close(tickers, start=start, end=end, max_workers=8)
            if prices.attrs.get('failed'):
                logger.warning(f"Yahoo returned no prices for {prices.attrs['failed']}")
            return prices

        prices = await self._cached(key, CACHE_PRICES_TTL, use_cache, fetch)
        return prices.copy()

    async def currencies(self, tickers: Iterable[str], use_cache: bool = True) -> pd.Series:
        """Quote currency of each ticker ('USD', 'EUR', 'GBp'...); None when unknown"""
        tickers = sorted(set(tickers))
        if not tickers:
            return pd.Series(dtype=object)
        key = f"yahoo:currencies:{','.join(tickers)}"
        return await self._cached(key, CURRENCY_TTL, use_cache, lambda: yahoo_api.get_currencies(tickers))

    async def fx(self, currencies: Iterable[str], base: str, start=None, use_cache: bool = True) -> pd.DataFrame:
        """Daily `base` per 1 unit of each currency; missing rates stay out (see attrs['missing'])"""
        wanted = sorted({c for c in currencies if isinstance(c, str) and c})
        start = _as_date(start)
        key = f"yahoo:fx:{','.join(wanted)}:{base}:{start}"
        return await self._cached(key, CACHE_PRICES_TTL, use_cache,
                                  lambda: yahoo_api.get_fx_rates(wanted, base, start=start))

    async def fx_or_one(self, currencies: Iterable[str], base: str, start=None,
                        use_cache: bool = True) -> Tuple[pd.DataFrame, List[str]]:
        """FX like the notebook's fx_rates: currencies without a rate are treated as 1.0"""
        fx = (await self.fx(currencies, base, start, use_cache)).copy()
        warnings = []
        for c in fx.attrs.get('missing', []):
            warnings.append(f"No FX rate for {c} -> {base}; treated as 1.0")
            fx[c] = 1.0
        return fx, warnings

    async def search(self, query: str) -> pd.DataFrame:
        return await asyncio.to_thread(yahoo_api.search_yahoo, query)

    async def details(self, tickers: Sequence[str], refresh: bool = False) -> pd.DataFrame:
        return await asyncio.to_thread(yahoo_api.fetch_ticker_details, list(tickers), refresh)

    async def has_prices(self, ticker: str) -> bool:
        return await asyncio.to_thread(yahoo_api.has_price_history, ticker)
