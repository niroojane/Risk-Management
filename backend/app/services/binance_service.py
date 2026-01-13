"""
Binance Service Wrapper
Wraps the legacy Binance_API with rate limiting, caching, and modern async interface
"""
import sys
from pathlib import Path
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd

# Add root directory to path to import Binance_API
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from Binance_API import BinanceAPI

from ..core.rate_limiter import BinanceRateLimiter, RateLimitExceeded
from ..core.exceptions import ExternalAPIError
from .cache_service import CacheService
from ..config import (
    BINANCE_RATE_LIMIT_CALLS,
    BINANCE_RATE_LIMIT_PERIOD,
    CACHE_MARKET_CAP_TTL,
    CACHE_PRICES_TTL,
    CACHE_INVENTORY_TTL,
)

logger = logging.getLogger(__name__)


class BinanceService:
    """
    Modern wrapper around legacy BinanceAPI class

    Features:
    - Rate limiting to prevent exceeding Binance API limits
    - Caching to reduce redundant API calls
    - Async interface for non-blocking operations
    - Error handling and logging
    - DataFrame to JSON conversion for REST API responses

    Args:
        api_key: Binance API key
        api_secret: Binance API secret
        cache: Cache service instance (optional)
        enable_rate_limiting: Enable rate limiting (default True)
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        cache: Optional[CacheService] = None,
        enable_rate_limiting: bool = True,
    ):
        self.api_key = api_key
        self.api_secret = api_secret

        # Initialize legacy API
        self._binance_api = BinanceAPI(api_key, api_secret)

        # Initialize rate limiter
        self._rate_limiter = None
        if enable_rate_limiting:
            self._rate_limiter = BinanceRateLimiter(
                max_calls=BINANCE_RATE_LIMIT_CALLS,
                period=BINANCE_RATE_LIMIT_PERIOD,
            )

        # Cache service
        self._cache = cache

        logger.info("BinanceService initialized")

    async def _run_in_executor(self, func, *args, **kwargs):
        """
        Run synchronous function in thread pool executor

        The legacy BinanceAPI is synchronous, so we need to run it in
        a separate thread to avoid blocking the async event loop.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    async def _with_rate_limit(self, weight: int = 1):
        """
        Acquire rate limit token before API call

        Args:
            weight: API endpoint weight
        """
        if self._rate_limiter:
            try:
                await self._rate_limiter.wait_and_acquire(weight=weight)
            except RateLimitExceeded as e:
                logger.error(f"Rate limit exceeded: {e}")
                raise ExternalAPIError(f"Binance rate limit exceeded: {e}")

    def _dataframe_to_dict(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Convert DataFrame to JSON-serializable dict

        Args:
            df: Pandas DataFrame

        Returns:
            Dictionary representation
        """
        # Reset index to include it in the output
        df_reset = df.reset_index()
        return df_reset.to_dict(orient="records")

    async def get_market_cap(
        self,
        quote: str = "USDT",
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get market capitalization data for all assets

        Args:
            quote: Quote asset (default USDT)
            use_cache: Whether to use cached data

        Returns:
            Dictionary with market cap data
        """
        cache_key = f"market_cap:{quote}"

        # Check cache
        if use_cache and self._cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning cached market cap for {quote}")
                return cached

        # Apply rate limiting
        await self._with_rate_limit(weight=40)  # Market data endpoints have higher weight

        try:
            # Call legacy API
            logger.info(f"Fetching market cap from Binance API (quote={quote})")
            df = await self._run_in_executor(
                self._binance_api.get_market_cap,
                quote=quote
            )

            # Convert to dict
            result = {
                "quote": quote,
                "data": self._dataframe_to_dict(df),
                "count": len(df),
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Cache result
            if use_cache and self._cache:
                await self._cache.set(cache_key, result, ttl=CACHE_MARKET_CAP_TTL)

            return result

        except Exception as e:
            logger.error(f"Error fetching market cap: {e}")
            raise ExternalAPIError(f"Failed to fetch market cap: {e}")

    async def get_prices(
        self,
        tickers: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get historical prices for a list of tickers

        Args:
            tickers: List of ticker symbols (e.g., ['BTCUSDT', 'ETHUSDT'])
            start_date: Start date (default: 30 days ago)
            end_date: End date (default: today)
            use_cache: Whether to use cached data

        Returns:
            Dictionary with price data
        """
        # Default dates
        if end_date is None:
            end_date = datetime.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        # Create cache key
        cache_key = f"prices:{','.join(sorted(tickers))}:{start_date.date()}:{end_date.date()}"

        # Check cache
        if use_cache and self._cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning cached prices for {len(tickers)} tickers")
                return cached

        # Apply rate limiting (1 weight per ticker)
        await self._with_rate_limit(weight=len(tickers))

        try:
            # Call legacy API
            logger.info(
                f"Fetching prices for {len(tickers)} tickers from Binance API "
                f"({start_date.date()} to {end_date.date()})"
            )
            df = await self._run_in_executor(
                self._binance_api.get_price,
                ticker_list=tickers,
                date=end_date
            )

            # Filter date range if needed
            if start_date:
                df = df[df.index >= start_date.strftime('%Y-%m-%d')]

            # Convert to dict
            result = {
                "tickers": tickers,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "data": self._dataframe_to_dict(df),
                "count": len(df),
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Cache result
            if use_cache and self._cache:
                await self._cache.set(cache_key, result, ttl=CACHE_PRICES_TTL)

            return result

        except Exception as e:
            logger.error(f"Error fetching prices: {e}")
            raise ExternalAPIError(f"Failed to fetch prices: {e}")

    async def get_inventory(
        self,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get current portfolio inventory (positions)

        Args:
            use_cache: Whether to use cached data

        Returns:
            Dictionary with inventory data
        """
        cache_key = "inventory:current"

        # Check cache
        if use_cache and self._cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info("Returning cached inventory")
                return cached

        # Apply rate limiting
        await self._with_rate_limit(weight=10)  # Account data has weight 10

        try:
            # Call legacy API
            logger.info("Fetching inventory from Binance API")
            df = await self._run_in_executor(self._binance_api.get_inventory)

            # Convert to dict
            result = {
                "data": self._dataframe_to_dict(df),
                "total_value": df.loc['Total', 'Price in USDT'] if 'Total' in df.index else 0,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Cache result (short TTL for inventory)
            if use_cache and self._cache:
                await self._cache.set(cache_key, result, ttl=CACHE_INVENTORY_TTL)

            return result

        except Exception as e:
            logger.error(f"Error fetching inventory: {e}")
            raise ExternalAPIError(f"Failed to fetch inventory: {e}")

    async def get_positions_history(
        self,
        end_date: Optional[datetime] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get historical positions

        Args:
            end_date: End date (default: today)
            use_cache: Whether to use cached data

        Returns:
            Dictionary with positions and quantities history
        """
        if end_date is None:
            end_date = datetime.today()

        cache_key = f"positions_history:{end_date.date()}"

        # Check cache
        if use_cache and self._cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning cached positions history for {end_date.date()}")
                return cached

        # Apply rate limiting
        await self._with_rate_limit(weight=10)

        try:
            # Call legacy API
            logger.info(f"Fetching positions history from Binance API (end={end_date.date()})")
            positions, quantities = await self._run_in_executor(
                self._binance_api.get_positions_history,
                enddate=end_date
            )

            # Convert to dict
            result = {
                "positions": self._dataframe_to_dict(positions),
                "quantities": self._dataframe_to_dict(quantities),
                "end_date": end_date.isoformat(),
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Cache result
            if use_cache and self._cache:
                await self._cache.set(cache_key, result, ttl=CACHE_PRICES_TTL)

            return result

        except Exception as e:
            logger.error(f"Error fetching positions history: {e}")
            raise ExternalAPIError(f"Failed to fetch positions history: {e}")

    async def get_trades(
        self,
        symbols: List[str],
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get trade history for symbols

        Args:
            symbols: List of symbols (e.g., ['BTCUSDT', 'ETHUSDT'])
            use_cache: Whether to use cached data

        Returns:
            Dictionary with trade history
        """
        cache_key = f"trades:{','.join(sorted(symbols))}"

        # Check cache
        if use_cache and self._cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning cached trades for {len(symbols)} symbols")
                return cached

        # Apply rate limiting
        await self._with_rate_limit(weight=len(symbols) * 5)

        try:
            # Call legacy API
            logger.info(f"Fetching trades for {len(symbols)} symbols from Binance API")
            df = await self._run_in_executor(
                self._binance_api.get_trades,
                symbols=symbols
            )

            # Convert to dict
            result = {
                "symbols": symbols,
                "data": self._dataframe_to_dict(df),
                "count": len(df),
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Cache result
            if use_cache and self._cache:
                await self._cache.set(cache_key, result, ttl=CACHE_PRICES_TTL)

            return result

        except Exception as e:
            logger.error(f"Error fetching trades: {e}")
            raise ExternalAPIError(f"Failed to fetch trades: {e}")

    def get_rate_limiter_stats(self) -> Dict[str, Any]:
        """
        Get rate limiter statistics

        Returns:
            Dictionary with available weight and max weight
        """
        if self._rate_limiter:
            return {
                "available_weight": self._rate_limiter.get_available_weight(),
                "max_weight": BINANCE_RATE_LIMIT_CALLS,
            }
        return {"rate_limiting": "disabled"}
