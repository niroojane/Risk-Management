"""
Pytest configuration and shared fixtures
Ce fichier contient les fixtures réutilisables pour tous les tests
"""
import pytest
import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an instance of the default event loop for the test session.
    Nécessaire pour les tests async.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def cache_service():
    """
    Fixture providing a CacheService instance for testing
    Démarre et arrête automatiquement le service
    """
    from app.services.cache_service import CacheService

    cache = CacheService(default_ttl=5, cleanup_interval=60)
    await cache.start()

    yield cache

    await cache.stop()


@pytest.fixture
def rate_limiter():
    """
    Fixture providing a RateLimiter instance for testing
    """
    from app.core.rate_limiter import RateLimiter

    limiter = RateLimiter(max_calls=10, period=1, name="test")
    return limiter


@pytest.fixture
def binance_rate_limiter():
    """
    Fixture providing a BinanceRateLimiter instance for testing
    """
    from app.core.rate_limiter import BinanceRateLimiter

    limiter = BinanceRateLimiter(max_calls=100, period=1)
    return limiter


@pytest.fixture
def mock_binance_credentials():
    """
    Mock Binance API credentials pour les tests
    """
    return {
        "api_key": "test_api_key_12345",
        "api_secret": "test_api_secret_67890",
    }


@pytest.fixture
def sample_tickers():
    """
    Sample ticker list for testing
    """
    return ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'BNBUSDT', 'SOLUSDT']
