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
    )
    from ..services.cache import CacheService
    from ..services.account import PortfolioAccount
    from ..services.yahoo import YahooMarketData

logger = logging.getLogger(__name__)


@lru_cache()
def get_cache_service():
    """Get singleton CacheService instance"""
    from ..services.cache import CacheService
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
def get_yahoo_market_data():
    """Get singleton YahooMarketData instance (multi-asset profile)"""
    from ..services.yahoo import YahooMarketData
    return YahooMarketData(get_cache_service())


@lru_cache()
def get_price_service():
    """Get singleton price service: Binance klines, or Yahoo in the multi-asset profile"""
    from ..services.binance import PriceService
    from .market import MULTI_ASSET, get_currency_settings, get_profile

    if get_profile().name == MULTI_ASSET:
        from ..services.yahoo import YahooPriceService
        logger.info("Creating YahooPriceService instance")
        return YahooPriceService(get_yahoo_market_data(), get_currency_settings())

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
def get_account_service():
    """Get singleton real-portfolio service: Binance account, or Excel files in the multi-asset profile"""
    from ..services.account import AccountService, ExcelAccountService, GitHubStorage
    from .config import GITHUB_TOKEN, GITHUB_REPO_OWNER, GITHUB_REPO_NAME, GITHUB_BRANCH
    from .market import MULTI_ASSET, get_currency_settings, get_profile

    profile = get_profile()
    storage = GitHubStorage(
        owner=GITHUB_REPO_OWNER,
        repo=GITHUB_REPO_NAME,
        branch=GITHUB_BRANCH,
        folder=profile.data_folder,
        token=GITHUB_TOKEN or None,
    )

    if profile.name == MULTI_ASSET:
        logger.info("Creating ExcelAccountService instance")
        return ExcelAccountService(storage, get_yahoo_market_data(), get_currency_settings(), profile,
                                   get_cache_service())

    client = get_binance_service()
    if client is None:
        return None
    logger.info("Creating AccountService instance")
    return AccountService(client, get_price_service(), get_quantity_service(), storage, get_cache_service())


def get_required_account_service():
    """Real-portfolio service, or a 503 when Binance credentials are not configured"""
    from .exceptions import ServiceUnavailableError

    service = get_account_service()
    if service is None:
        raise ServiceUnavailableError(
            message="Binance service not configured",
            detail="Please set BINANCE_API_KEY and BINANCE_API_SECRET in the .env file of the Risk Management folder",
        )
    return service


def get_required_price_service():
    """PriceService, or a 503 when Binance credentials are not configured"""
    from .exceptions import ServiceUnavailableError

    service = get_price_service()
    if service is None:
        raise ServiceUnavailableError(
            message="Binance service not configured",
            detail="Please set BINANCE_API_KEY and BINANCE_API_SECRET in the .env file of the Risk Management folder",
        )
    return service


# Type aliases for dependency injection
BinanceServiceDep = Annotated[Optional["BinanceClient"], Depends(get_binance_service)]
MarketDataServiceDep = Annotated[Optional["MarketDataService"], Depends(get_market_data_service)]
PriceServiceDep = Annotated[Optional["PriceService"], Depends(get_price_service)]
RequiredPriceServiceDep = Annotated["PriceService", Depends(get_required_price_service)]
RequiredAccountServiceDep = Annotated["PortfolioAccount", Depends(get_required_account_service)]
AccountServiceDep = Annotated[Optional["PortfolioAccount"], Depends(get_account_service)]
YahooMarketDataDep = Annotated["YahooMarketData", Depends(get_yahoo_market_data)]
QuantityServiceDep = Annotated[Optional["QuantityService"], Depends(get_quantity_service)]
CacheServiceDep = Annotated["CacheService", Depends(get_cache_service)]
