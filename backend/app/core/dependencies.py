"""
Dependency injection for FastAPI endpoints
Provides singleton instances of services and clients
"""
from functools import lru_cache
from typing import Annotated, Optional, TYPE_CHECKING
from fastapi import Depends
import logging

from .config import BINANCE_API_KEY, BINANCE_API_SECRET, CACHE_DEFAULT_TTL, REDIS_URL
from .exceptions import ServiceUnavailableError

if TYPE_CHECKING:
    from ..services.binance import (
        BinanceClient,
        MarketCapService,
        MarketDataService,
        QuantityService,
        PositionService,
    )
    from ..services.infrastructure.cache_service import CacheService

logger = logging.getLogger(__name__)


@lru_cache()
def get_cache_service():
    """Get singleton cache instance - Redis if REDIS_URL is set, in-memory otherwise"""
    if REDIS_URL:
        from ..services.infrastructure.redis_cache_service import RedisCacheService
        logger.info("Using Redis cache")
        return RedisCacheService(url=REDIS_URL, default_ttl=CACHE_DEFAULT_TTL)
    from ..services.infrastructure.cache_service import CacheService
    logger.info("Using in-memory cache")
    return CacheService(default_ttl=CACHE_DEFAULT_TTL)


@lru_cache()
def get_binance_service():
    """Get singleton BinanceClient instance"""
    from ..services.binance import BinanceClient

    if not BINANCE_API_KEY or not BINANCE_API_SECRET:
        logger.warning("Binance API credentials not configured")
        return None

    cache = get_cache_service()
    logger.info("Creating BinanceClient instance with cache and rate limiting")

    return BinanceClient(
        api_key=BINANCE_API_KEY,
        api_secret=BINANCE_API_SECRET,
        cache=cache,
        enable_rate_limiting=True
    )


_BINANCE_NOT_CONFIGURED = ServiceUnavailableError(
    message="Binance service not configured",
    detail="Please set BINANCE_API_KEY and BINANCE_API_SECRET in .env file",
)


@lru_cache()
def get_market_cap_service():
    """Get singleton MarketCapService instance"""
    from ..services.binance import MarketCapService

    client = get_binance_service()
    if client is None:
        raise _BINANCE_NOT_CONFIGURED

    logger.info("Creating MarketCapService instance")
    return MarketCapService(client)


@lru_cache()
def get_market_data_service():
    """Get singleton MarketDataService instance"""
    from ..services.binance import MarketDataService

    client = get_binance_service()
    if client is None:
        raise _BINANCE_NOT_CONFIGURED

    logger.info("Creating MarketDataService instance")
    return MarketDataService(client)


@lru_cache()
def get_quantity_service():
    """Get singleton QuantityService instance"""
    from ..services.binance import QuantityService

    client = get_binance_service()
    if client is None:
        raise _BINANCE_NOT_CONFIGURED

    logger.info("Creating QuantityService instance")
    return QuantityService(client)


@lru_cache()
def get_position_service():
    """Get singleton PositionService instance"""
    from ..services.binance import PositionService

    market_data_service = get_market_data_service()
    quantity_service = get_quantity_service()

    logger.info("Creating PositionService instance")
    return PositionService(market_data_service, quantity_service)


# Type aliases for dependency injection
BinanceServiceDep = Annotated[Optional["BinanceClient"], Depends(get_binance_service)]
MarketCapServiceDep = Annotated["MarketCapService", Depends(get_market_cap_service)]
MarketDataServiceDep = Annotated["MarketDataService", Depends(get_market_data_service)]
QuantityServiceDep = Annotated["QuantityService", Depends(get_quantity_service)]
PositionServiceDep = Annotated["PositionService", Depends(get_position_service)]
CacheServiceDep = Annotated["CacheService", Depends(get_cache_service)]
