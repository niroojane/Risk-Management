"""
Tests for RateLimiter and BinanceRateLimiter
Tests essentiels pour l'algorithme Token Bucket
"""
import pytest
import asyncio
from app.core.rate_limiter import RateLimitExceeded


@pytest.mark.asyncio
async def test_rate_limiter_basic_flow(rate_limiter):
    """
    Test le flow basique : acquire, épuisement, refill
    Couvre le cas d'usage principal
    """
    # Acquire des tokens jusqu'à la limite (max=10)
    for i in range(10):
        await rate_limiter.acquire(tokens=1)

    # Tous les tokens sont utilisés (ou presque, selon le timing)
    available = rate_limiter.get_available_tokens()
    assert available == pytest.approx(0.0, abs=0.1)

    # Essayer d'acquérir encore → doit lever une exception
    with pytest.raises(RateLimitExceeded) as exc_info:
        await rate_limiter.acquire(tokens=1)

    assert hasattr(exc_info.value, 'retry_after')
    assert exc_info.value.retry_after > 0

    # Attendre que les tokens se rechargent (period=1s)
    await asyncio.sleep(1.1)

    # Des tokens doivent être disponibles maintenant
    available = rate_limiter.get_available_tokens()
    assert available > 0


@pytest.mark.asyncio
async def test_rate_limiter_wait_and_acquire(rate_limiter):
    """
    Test wait_and_acquire qui attend automatiquement
    Important pour éviter les exceptions en production
    """
    # Utiliser tous les tokens
    for i in range(10):
        await rate_limiter.acquire(tokens=1)

    # wait_and_acquire doit attendre puis réussir
    import time
    start = time.time()
    await rate_limiter.wait_and_acquire(tokens=1)
    elapsed = time.time() - start

    # Doit avoir attendu au moins un peu
    assert elapsed > 0.05


@pytest.mark.asyncio
async def test_rate_limiter_reset(rate_limiter):
    """
    Test le reset manuel du rate limiter
    Utile pour les tests et situations d'urgence
    """
    # Utiliser tous les tokens
    for i in range(10):
        await rate_limiter.acquire(tokens=1)

    assert rate_limiter.get_available_tokens() == pytest.approx(0.0, abs=0.1)

    # Reset
    rate_limiter.reset()

    # Tous les tokens sont revenus
    available = rate_limiter.get_available_tokens()
    assert available == 10.0


@pytest.mark.asyncio
async def test_binance_rate_limiter_weight_based(binance_rate_limiter):
    """
    Test l'acquisition basée sur le weight pour Binance
    Critique car chaque endpoint Binance a un weight différent
    """
    # Acquire avec weight=1 (endpoint léger)
    await binance_rate_limiter.acquire(weight=1)
    available = binance_rate_limiter.get_available_weight()
    assert available == pytest.approx(99.0, rel=0.1)

    # Acquire avec weight=10 (endpoint lourd)
    await binance_rate_limiter.acquire(weight=10)
    available = binance_rate_limiter.get_available_weight()
    assert available == pytest.approx(89.0, rel=0.1)

    # Scénario réaliste : plusieurs appels API
    await binance_rate_limiter.acquire(weight=5)  # get prices
    await binance_rate_limiter.acquire(weight=10)  # account snapshot
    await binance_rate_limiter.acquire(weight=1)  # get klines

    # Total utilisé : 1 + 10 + 5 + 10 + 1 = 27
    available = binance_rate_limiter.get_available_weight()
    assert available == pytest.approx(73.0, rel=0.1)


@pytest.mark.asyncio
async def test_rate_limiter_concurrent_safety(rate_limiter):
    """
    Test la thread safety avec acquisitions concurrentes
    Important car FastAPI est async et multi-thread
    """
    async def acquire_token():
        try:
            await rate_limiter.acquire(tokens=1)
            return True
        except RateLimitExceeded:
            return False

    # Essayer d'acquérir 15 tokens en parallèle (max=10)
    tasks = [acquire_token() for _ in range(15)]
    results = await asyncio.gather(*tasks)

    # Exactement 10 doivent réussir
    successes = sum(results)
    assert successes == 10

    # Les 5 autres doivent échouer
    failures = len(results) - successes
    assert failures == 5
