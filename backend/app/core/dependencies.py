"""
Dependency injection for FastAPI endpoints
Provides singleton instances of services and clients
"""
from functools import lru_cache
from typing import Annotated
from fastapi import Depends
import logging

# Import root modules
from .config import BINANCE_API_KEY, BINANCE_API_SECRET
from Binance_API import BinanceAPI

logger = logging.getLogger(__name__)


@lru_cache()
def get_binance_client() -> BinanceAPI:
    """
    Get singleton BinanceAPI client instance

    Returns:
        BinanceAPI: Configured Binance API client
    """
    if not BINANCE_API_KEY or not BINANCE_API_SECRET:
        logger.warning("Binance API credentials not configured")
        return None

    logger.info("Creating BinanceAPI client instance")
    return BinanceAPI(BINANCE_API_KEY, BINANCE_API_SECRET)


# Note: Cache and RateLimiter services will be imported once created
# Commented out for now to avoid import errors
# @lru_cache()
# def get_cache_service():
#     """Get singleton CacheService instance"""
#     from .services.cache_service import CacheService
#     from .config import CACHE_DEFAULT_TTL
#     return CacheService(ttl=CACHE_DEFAULT_TTL)


# @lru_cache()
# def get_rate_limiter():
#     """Get singleton RateLimiter instance"""
#     from .core.rate_limiter import RateLimiter
#     from .config import BINANCE_RATE_LIMIT_CALLS, BINANCE_RATE_LIMIT_PERIOD
#     return RateLimiter(
#         max_calls=BINANCE_RATE_LIMIT_CALLS,
#         period=BINANCE_RATE_LIMIT_PERIOD
#     )


# Type aliases for dependency injection
BinanceClient = Annotated[BinanceAPI, Depends(get_binance_client)]
# CacheService = Annotated[Any, Depends(get_cache_service)]
# RateLimiter = Annotated[Any, Depends(get_rate_limiter)]
