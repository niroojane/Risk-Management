"""
Application lifecycle events
Handles startup and shutdown operations
"""
import logging
from typing import TYPE_CHECKING

from ..config import (
    API_TITLE,
    API_VERSION,
    CORS_ORIGINS,
    BINANCE_API_KEY,
    BINANCE_API_SECRET,
    CACHE_DEFAULT_TTL,
)
from ..services.cache_service import CacheService
from ..services.binance_service import BinanceService

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)

# Global service instances (will be set in startup_event)
_cache_service: CacheService = None
_binance_service: BinanceService = None


async def startup_event() -> None:
    """
    Actions to perform on application startup

    - Log startup information
    - Initialize cache service
    - Validate Binance API credentials
    - Setup Binance service
    - Future: Setup WebSocket manager
    """
    global _cache_service, _binance_service

    logger.info(f"{API_TITLE} v{API_VERSION} starting up...")
    logger.info(f"CORS origins configured: {CORS_ORIGINS}")

    # Initialize cache service
    logger.info("Initializing cache service...")
    _cache_service = CacheService(default_ttl=CACHE_DEFAULT_TTL)
    await _cache_service.start()
    logger.info("✅ Cache service started")

    # Validate Binance API credentials
    if not BINANCE_API_KEY or not BINANCE_API_SECRET:
        logger.warning(
            "⚠️  Binance API credentials not configured. "
            "Set BINANCE_API_KEY and BINANCE_API_SECRET environment variables."
        )
        logger.warning("⚠️  Binance-related endpoints will not work.")
    else:
        logger.info("✅ Binance API credentials found")

        # Initialize Binance service
        logger.info("Initializing Binance service...")
        _binance_service = BinanceService(
            api_key=BINANCE_API_KEY,
            api_secret=BINANCE_API_SECRET,
            cache=_cache_service,
            enable_rate_limiting=True,
        )
        logger.info("✅ Binance service initialized")

    # Future initialization tasks:
    # - Setup WebSocket manager
    # - Load any required data
    # - Initialize other services

    logger.info(f"🚀 {API_TITLE} startup complete")


async def shutdown_event() -> None:
    """
    Actions to perform on application shutdown

    - Stop cache service
    - Cleanup resources
    - Close connections
    """
    global _cache_service, _binance_service

    logger.info(f"{API_TITLE} shutting down...")

    # Stop cache service
    if _cache_service:
        logger.info("Stopping cache service...")
        cache_stats = _cache_service.get_stats()
        logger.info(f"Cache stats: {cache_stats}")
        await _cache_service.stop()
        logger.info("✅ Cache service stopped")

    # Future cleanup tasks:
    # - Close WebSocket connections
    # - Close database connections (if any)
    # - Save any pending state

    logger.info(f"👋 {API_TITLE} shutdown complete")


def get_cache_service() -> CacheService:
    """
    Get the global cache service instance

    Returns:
        CacheService instance

    Raises:
        RuntimeError: If cache service not initialized
    """
    if _cache_service is None:
        raise RuntimeError("Cache service not initialized. Call startup_event first.")
    return _cache_service


def get_binance_service() -> BinanceService:
    """
    Get the global Binance service instance

    Returns:
        BinanceService instance

    Raises:
        RuntimeError: If Binance service not initialized
    """
    if _binance_service is None:
        raise RuntimeError(
            "Binance service not initialized. "
            "Ensure BINANCE_API_KEY and BINANCE_API_SECRET are set."
        )
    return _binance_service
