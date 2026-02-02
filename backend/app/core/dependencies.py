"""
Dependency injection for FastAPI endpoints
Provides singleton instances of services and clients
"""
from functools import lru_cache
from typing import Annotated, Optional, TYPE_CHECKING
from fastapi import Depends
import logging

# Import root modules
from .config import BINANCE_API_KEY, BINANCE_API_SECRET, CACHE_DEFAULT_TTL

# Type-only imports to avoid circular dependencies
if TYPE_CHECKING:
    from ..services.binance import (
        BinanceClient,
        MarketDataService,
        PriceService,
        QuantityService,
        PositionService,
    )
    from ..services.infrastructure.cache_service import CacheService

logger = logging.getLogger(__name__)


@lru_cache()
def get_cache_service():
    """Get singleton CacheService instance"""
    from ..services.infrastructure.cache_service import CacheService
    logger.info("Creating CacheService instance")
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


@lru_cache()
def get_market_data_service():
    """Get singleton MarketDataService instance"""
    from ..services.binance import MarketDataService

    client = get_binance_service()
    if client is None:
        return None

    logger.info("Creating MarketDataService instance")
    return MarketDataService(client)


@lru_cache()
def get_price_service():
    """Get singleton PriceService instance"""
    from ..services.binance import PriceService

    client = get_binance_service()
    if client is None:
        return None

    logger.info("Creating PriceService instance")
    return PriceService(client)


@lru_cache()
def get_quantity_service():
    """Get singleton QuantityService instance"""
    from ..services.binance import QuantityService

    client = get_binance_service()
    if client is None:
        return None

    logger.info("Creating QuantityService instance")
    return QuantityService(client)


@lru_cache()
def get_position_service():
    """Get singleton PositionService instance"""
    from ..services.binance import PositionService

    price_service = get_price_service()
    quantity_service = get_quantity_service()

    if price_service is None or quantity_service is None:
        return None

    logger.info("Creating PositionService instance")
    return PositionService(price_service, quantity_service)


# Type aliases for dependency injection
BinanceServiceDep = Annotated[Optional["BinanceClient"], Depends(get_binance_service)]
MarketDataServiceDep = Annotated[Optional["MarketDataService"], Depends(get_market_data_service)]
PriceServiceDep = Annotated[Optional["PriceService"], Depends(get_price_service)]
QuantityServiceDep = Annotated[Optional["QuantityService"], Depends(get_quantity_service)]
PositionServiceDep = Annotated[Optional["PositionService"], Depends(get_position_service)]
CacheServiceDep = Annotated["CacheService", Depends(get_cache_service)]
