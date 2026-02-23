"""Low-level async wrapper around Binance Spot API"""
import logging
import asyncio
from typing import Dict, Any, Optional, Callable, Protocol, runtime_checkable
import pandas as pd

from binance.spot import Spot
from ...core.rate_limiter import BinanceRateLimiter, RateLimitExceeded
from ...core.exceptions import ExternalAPIError
from ...core.config import BINANCE_RATE_LIMIT_CALLS, BINANCE_RATE_LIMIT_PERIOD


@runtime_checkable
class CacheProtocol(Protocol):
    async def get(self, key: str): ...
    async def set(self, key: str, value, ttl=None): ...
    async def delete(self, key: str) -> bool: ...

logger = logging.getLogger(__name__)


class BinanceClient:
    """Async wrapper for Binance Spot API with rate limiting and caching"""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        cache: Optional[CacheProtocol] = None,
        enable_rate_limiting: bool = True,
    ):
        self._spot = Spot(api_key=api_key, api_secret=api_secret)
        self._cache = cache

        self._rate_limiter = None
        if enable_rate_limiting:
            self._rate_limiter = BinanceRateLimiter(
                max_calls=BINANCE_RATE_LIMIT_CALLS,
                period=BINANCE_RATE_LIMIT_PERIOD,
            )

        logger.info("BinanceClient initialized with Spot API")

    async def _run_in_executor(self, func: Callable, *args, **kwargs):
        """Run synchronous function in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    async def _with_rate_limit(self, weight: int = 1):
        """Apply rate limiting before API call"""
        if self._rate_limiter:
            try:
                await self._rate_limiter.wait_and_acquire(weight=weight)
            except RateLimitExceeded as e:
                logger.error(f"Rate limit exceeded: {e}")
                raise ExternalAPIError(f"Binance rate limit exceeded: {e}")

    def _dataframe_to_dict(self, df: pd.DataFrame) -> list:
        """Convert DataFrame to list of dicts"""
        return df.reset_index().to_dict(orient="records")

    async def fetch_with_cache(
        self,
        cache_key: str,
        api_call: Callable,
        weight: int,
        ttl: int,
        use_cache: bool = True,
    ) -> Any:
        """Fetch data with caching and rate limiting"""
        if use_cache and self._cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Cache hit: {cache_key}")
                return cached

        await self._with_rate_limit(weight=weight)

        try:
            result = await api_call()

            if use_cache and self._cache:
                await self._cache.set(cache_key, result, ttl=ttl)

            return result

        except Exception as e:
            logger.error(f"API call failed for {cache_key}: {e}")
            raise ExternalAPIError(f"Binance API error: {e}")

    def get_rate_limiter_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        if self._rate_limiter:
            return {
                "available_weight": self._rate_limiter.get_available_weight(),
                "max_weight": BINANCE_RATE_LIMIT_CALLS,
            }
        return {"rate_limiting": "disabled"}

    @property
    def spot(self) -> Spot:
        """Access to Binance Spot API client"""
        return self._spot
