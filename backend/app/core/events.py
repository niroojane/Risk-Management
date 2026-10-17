"""Application lifecycle events"""
import logging
from typing import TYPE_CHECKING

from .config import API_TITLE, API_VERSION, CORS_ORIGINS, BINANCE_API_KEY, BINANCE_API_SECRET
from .dependencies import get_cache_service, get_binance_service

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


async def startup_event() -> None:
    """Application startup - initialize services"""
    logger.info(f"{API_TITLE} v{API_VERSION} starting up...")
    logger.info(f"CORS origins: {CORS_ORIGINS}")

    # Start cache service background cleanup task
    cache = get_cache_service()
    await cache.start()
    logger.info("✅ Cache service started")

    # Validate Binance credentials
    if not BINANCE_API_KEY or not BINANCE_API_SECRET:
        logger.warning("⚠️ Binance API credentials not configured")
        logger.warning("⚠️ Binance endpoints will not work")
    else:
        # Initialize Binance service (triggers @lru_cache)
        get_binance_service()
        logger.info("✅ Binance service initialized")

    logger.info(f"🚀 {API_TITLE} ready")


async def shutdown_event() -> None:
    """Application shutdown - cleanup services"""
    logger.info(f"{API_TITLE} shutting down...")

    # Stop cache service background task
    try:
        cache = get_cache_service()
        stats = cache.get_stats()
        logger.info(f"Cache stats: {stats}")
        await cache.stop()
        logger.info("✅ Cache service stopped")
    except Exception as e:
        logger.warning(f"Error stopping cache: {e}")

    logger.info(f"👋 {API_TITLE} shutdown complete")
