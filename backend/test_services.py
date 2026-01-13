"""
Test script for Phase 2 services
Run this to validate cache service and rate limiter
"""
import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.cache_service import CacheService
from app.core.rate_limiter import RateLimiter, BinanceRateLimiter, RateLimitExceeded


async def test_cache_service():
    """Test cache service functionality"""
    print("\n" + "="*50)
    print("Testing Cache Service")
    print("="*50)

    cache = CacheService(default_ttl=5)
    await cache.start()

    # Test set and get
    print("\n1. Testing set/get...")
    await cache.set("test_key", {"data": "test_value"})
    value = await cache.get("test_key")
    assert value == {"data": "test_value"}, "Cache get failed"
    print("✅ Set/get works")

    # Test cache hit
    print("\n2. Testing cache hit...")
    value = await cache.get("test_key")
    assert value is not None, "Cache hit failed"
    print("✅ Cache hit works")

    # Test cache miss
    print("\n3. Testing cache miss...")
    value = await cache.get("non_existent_key")
    assert value is None, "Cache miss failed"
    print("✅ Cache miss works")

    # Test expiration
    print("\n4. Testing TTL expiration...")
    await cache.set("expiring_key", "value", ttl=1)
    print("   Waiting 2 seconds for expiration...")
    await asyncio.sleep(2)
    value = await cache.get("expiring_key")
    assert value is None, "TTL expiration failed"
    print("✅ TTL expiration works")

    # Test delete
    print("\n5. Testing delete...")
    await cache.set("delete_key", "value")
    deleted = await cache.delete("delete_key")
    assert deleted is True, "Delete failed"
    value = await cache.get("delete_key")
    assert value is None, "Delete verification failed"
    print("✅ Delete works")

    # Test statistics
    print("\n6. Testing statistics...")
    stats = cache.get_stats()
    print(f"   {stats}")
    assert stats["total_requests"] > 0, "Stats failed"
    print("✅ Statistics work")

    # Cleanup
    await cache.stop()
    print("\n✅ Cache service test passed!")


async def test_rate_limiter():
    """Test rate limiter functionality"""
    print("\n" + "="*50)
    print("Testing Rate Limiter")
    print("="*50)

    limiter = RateLimiter(max_calls=5, period=2, name="test")

    # Test normal acquisition
    print("\n1. Testing normal acquisition...")
    for i in range(5):
        await limiter.acquire()
        print(f"   Acquired token {i+1}/5")
    print("✅ Normal acquisition works")

    # Test rate limit exceeded
    print("\n2. Testing rate limit exceeded...")
    try:
        await limiter.acquire()
        assert False, "Should have raised RateLimitExceeded"
    except RateLimitExceeded as e:
        print(f"   ✅ Rate limit exceeded as expected: {e}")

    # Test wait and acquire
    print("\n3. Testing wait and acquire...")
    print("   Waiting for token refill...")
    await limiter.wait_and_acquire()
    print("✅ Wait and acquire works")

    # Test reset
    print("\n4. Testing reset...")
    limiter.reset()
    available = limiter.get_available_tokens()
    assert available == 5, "Reset failed"
    print("✅ Reset works")

    print("\n✅ Rate limiter test passed!")


async def test_binance_rate_limiter():
    """Test Binance-specific rate limiter"""
    print("\n" + "="*50)
    print("Testing Binance Rate Limiter")
    print("="*50)

    limiter = BinanceRateLimiter(max_calls=10, period=1)

    # Test weight-based acquisition
    print("\n1. Testing weight-based acquisition...")
    await limiter.acquire(weight=1)
    print("   Acquired weight=1")
    await limiter.acquire(weight=5)
    print("   Acquired weight=5")
    available = limiter.get_available_weight()
    print(f"   Available weight: {available:.2f}/10")
    assert available < 10, "Weight acquisition failed"
    print("✅ Weight-based acquisition works")

    # Reset for next test
    limiter.reset()

    # Test large weight
    print("\n2. Testing large weight acquisition...")
    await limiter.wait_and_acquire(weight=8)
    print("   Acquired weight=8")
    available = limiter.get_available_weight()
    print(f"   Available weight: {available:.2f}/10")
    print("✅ Large weight acquisition works")

    print("\n✅ Binance rate limiter test passed!")


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 Phase 2 Services Test Suite")
    print("="*60)

    try:
        await test_cache_service()
        await test_rate_limiter()
        await test_binance_rate_limiter()

        print("\n" + "="*60)
        print("🎉 All tests passed!")
        print("="*60)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
