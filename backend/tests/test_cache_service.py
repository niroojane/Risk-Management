"""Tests for CacheService"""
import pytest
import asyncio


@pytest.mark.asyncio
async def test_cache_basic_operations(cache_service):
    """Test set, get, delete with different data types"""
    await cache_service.set("test_key", {"data": "test_value"})

    value = await cache_service.get("test_key")
    assert value == {"data": "test_value"}

    deleted = await cache_service.delete("test_key")
    assert deleted is True

    value = await cache_service.get("test_key")
    assert value is None

    # Test different data types
    await cache_service.set("int_key", 42)
    await cache_service.set("list_key", [1, 2, 3])
    await cache_service.set("dict_key", {"a": 1, "b": 2})

    assert await cache_service.get("int_key") == 42
    assert await cache_service.get("list_key") == [1, 2, 3]
    assert await cache_service.get("dict_key") == {"a": 1, "b": 2}


@pytest.mark.asyncio
async def test_cache_ttl_expiration(cache_service):
    """Test automatic TTL expiration"""
    await cache_service.set("expiring_key", "value", ttl=1)

    value = await cache_service.get("expiring_key")
    assert value == "value"

    await asyncio.sleep(1.5)

    value = await cache_service.get("expiring_key")
    assert value is None

    # Test multiple TTLs
    await cache_service.set("short_ttl", "value1", ttl=1)
    await cache_service.set("long_ttl", "value2", ttl=10)

    await asyncio.sleep(1.5)

    assert await cache_service.get("short_ttl") is None
    assert await cache_service.get("long_ttl") == "value2"


@pytest.mark.asyncio
async def test_cache_handles_missing_keys(cache_service):
    """Test handling of missing keys"""
    value = await cache_service.get("non_existent_key")
    assert value is None

    deleted = await cache_service.delete("non_existent")
    assert deleted is False

    await cache_service.set("exists_key", "value")
    assert await cache_service.get("exists_key") is not None
    assert await cache_service.get("non_existent") is None


@pytest.mark.asyncio
async def test_cache_statistics(cache_service):
    """Test hit/miss statistics tracking"""
    await cache_service.set("key1", "value1")
    await cache_service.set("key2", "value2")

    await cache_service.get("key1")  # hit
    await cache_service.get("key1")  # hit
    await cache_service.get("non_existent")  # miss

    stats = cache_service.get_stats()

    assert stats["sets"] == 2
    assert stats["hits"] == 2
    assert stats["misses"] == 1
    assert stats["total_requests"] == 3
    assert stats["hit_rate_percent"] == pytest.approx(66.67, rel=0.1)
