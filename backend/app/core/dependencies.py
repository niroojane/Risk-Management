"""
Dependency injection for FastAPI endpoints
Provides singleton instances of services and clients
"""
from functools import lru_cache
from typing import Annotated, Optional
from fastapi import Depends
import logging

# Import root modules
from .config import BINANCE_API_KEY, BINANCE_API_SECRET, CACHE_DEFAULT_TTL
from Binance_API import BinanceAPI

logger = logging.getLogger(__name__)


@lru_cache()
def get_binance_client() -> Optional[BinanceAPI]:
    """
    Get singleton BinanceAPI client instance (legacy)

    Returns:
        BinanceAPI: Configured Binance API client
    """
    if not BINANCE_API_KEY or not BINANCE_API_SECRET:
        logger.warning("Binance API credentials not configured")
        return None

    logger.info("Creating BinanceAPI client instance")
    return BinanceAPI(BINANCE_API_KEY, BINANCE_API_SECRET)


@lru_cache()
def get_cache_service():
    """Get singleton CacheService instance"""
    from ..services.cache_service import CacheService
    logger.info("Creating CacheService instance")
    return CacheService(default_ttl=CACHE_DEFAULT_TTL)


@lru_cache()
def get_binance_service():
    """
    Get singleton BinanceService instance (modern async wrapper)

    Returns:
        BinanceService: Configured Binance service with rate limiting and caching
    """
    from ..services.binance_service import BinanceService

    if not BINANCE_API_KEY or not BINANCE_API_SECRET:
        logger.warning("Binance API credentials not configured")
        return None

    cache = get_cache_service()
    logger.info("Creating BinanceService instance with cache and rate limiting")

    return BinanceService(
        api_key=BINANCE_API_KEY,
        api_secret=BINANCE_API_SECRET,
        cache=cache,
        enable_rate_limiting=True
    )


# Type aliases for dependency injection
BinanceClient = Annotated[Optional[BinanceAPI], Depends(get_binance_client)]
BinanceServiceDep = Annotated[Optional["BinanceService"], Depends(get_binance_service)]
CacheServiceDep = Annotated["CacheService", Depends(get_cache_service)]
