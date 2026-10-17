"""Tests for RateLimiter and BinanceRateLimiter"""
import pytest
import asyncio
from app.core.rate_limiter import RateLimitExceeded


@pytest.mark.asyncio
async def test_rate_limiter_basic_flow(rate_limiter):
    """Test basic flow: acquire, exhaustion, refill"""
    for _ in range(10):
        await rate_limiter.acquire(tokens=1)

    available = rate_limiter.get_available_tokens()
    assert available == pytest.approx(0.0, abs=0.1)

    with pytest.raises(RateLimitExceeded) as exc_info:
        await rate_limiter.acquire(tokens=1)

    assert hasattr(exc_info.value, 'retry_after')
    assert exc_info.value.retry_after > 0

    await asyncio.sleep(1.1)

    available = rate_limiter.get_available_tokens()
    assert available > 0


@pytest.mark.asyncio
async def test_rate_limiter_wait_and_acquire(rate_limiter):
    """Test wait_and_acquire which waits automatically"""
    for _ in range(10):
        await rate_limiter.acquire(tokens=1)

    import time
    start = time.time()
    await rate_limiter.wait_and_acquire(tokens=1)
    elapsed = time.time() - start

    assert elapsed > 0.05


@pytest.mark.asyncio
async def test_rate_limiter_reset(rate_limiter):
    """Test manual reset"""
    for _ in range(10):
        await rate_limiter.acquire(tokens=1)

    assert rate_limiter.get_available_tokens() == pytest.approx(0.0, abs=0.1)

    rate_limiter.reset()

    available = rate_limiter.get_available_tokens()
    assert available == 10.0


@pytest.mark.asyncio
async def test_binance_rate_limiter_weight_based(binance_rate_limiter):
    """Test weight-based acquisition for Binance API"""
    await binance_rate_limiter.acquire(weight=1)
    available = binance_rate_limiter.get_available_weight()
    assert available == pytest.approx(99.0, rel=0.1)

    await binance_rate_limiter.acquire(weight=10)
    available = binance_rate_limiter.get_available_weight()
    assert available == pytest.approx(89.0, rel=0.1)

    # Multiple API calls
    await binance_rate_limiter.acquire(weight=5)
    await binance_rate_limiter.acquire(weight=10)
    await binance_rate_limiter.acquire(weight=1)

    # Total: 1 + 10 + 5 + 10 + 1 = 27
    available = binance_rate_limiter.get_available_weight()
    assert available == pytest.approx(73.0, rel=0.1)


@pytest.mark.asyncio
async def test_rate_limiter_concurrent_safety(rate_limiter):
    """Test thread safety with concurrent acquisitions"""
    async def acquire_token():
        try:
            await rate_limiter.acquire(tokens=1)
            return True
        except RateLimitExceeded:
            return False

    # Try to acquire 15 tokens in parallel (max=10)
    tasks = [acquire_token() for _ in range(15)]
    results = await asyncio.gather(*tasks)

    successes = sum(results)
    assert successes == 10

    failures = len(results) - successes
    assert failures == 5
