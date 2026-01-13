"""
Cache Service with TTL support
In-memory caching for API responses and computed data
"""
import asyncio
import time
import logging
from typing import Any, Optional, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """
    Cache entry with value and expiration time

    Attributes:
        value: The cached value (any type)
        expires_at: Unix timestamp when entry expires
        created_at: Unix timestamp when entry was created
    """

    value: Any
    expires_at: float
    created_at: float


class CacheService:
    """
    In-memory cache service with TTL support

    Features:
    - Per-key TTL configuration
    - Automatic expiration checking
    - Background cleanup task
    - Cache statistics (hits/misses)
    - Type-agnostic (supports any Python object)

    Args:
        default_ttl: Default TTL in seconds (default 300 = 5 minutes)
        cleanup_interval: How often to run cleanup task in seconds (default 60)
    """

    def __init__(self, default_ttl: int = 300, cleanup_interval: int = 60):
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval

        # Cache storage
        self._cache: Dict[str, CacheEntry] = {}

        # Statistics
        self._hits = 0
        self._misses = 0
        self._sets = 0

        # Async lock for thread safety
        self._lock = asyncio.Lock()

        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None

        logger.info(
            f"CacheService initialized with default TTL: {default_ttl}s, "
            f"cleanup interval: {cleanup_interval}s"
        )

    async def start(self) -> None:
        """
        Start the cache service and background cleanup task
        """
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("CacheService background cleanup task started")

    async def stop(self) -> None:
        """
        Stop the cache service and cleanup task
        """
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("CacheService background cleanup task stopped")

    async def _cleanup_loop(self) -> None:
        """
        Background task to periodically remove expired entries
        """
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                removed = await self._remove_expired()
                if removed > 0:
                    logger.debug(f"Cache cleanup: removed {removed} expired entries")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup loop: {e}")

    async def _remove_expired(self) -> int:
        """
        Remove expired entries from cache

        Returns:
            Number of entries removed
        """
        now = time.time()
        removed = 0

        async with self._lock:
            keys_to_remove = [
                key for key, entry in self._cache.items()
                if entry.expires_at < now
            ]
            for key in keys_to_remove:
                del self._cache[key]
                removed += 1

        return removed

    def _is_expired(self, entry: CacheEntry) -> bool:
        """
        Check if cache entry is expired

        Args:
            entry: Cache entry to check

        Returns:
            True if expired, False otherwise
        """
        return time.time() > entry.expires_at

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value if exists and not expired, None otherwise
        """
        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._misses += 1
                logger.debug(f"Cache MISS: {key}")
                return None

            if self._is_expired(entry):
                del self._cache[key]
                self._misses += 1
                logger.debug(f"Cache MISS (expired): {key}")
                return None

            self._hits += 1
            logger.debug(
                f"Cache HIT: {key} (age: {time.time() - entry.created_at:.1f}s)"
            )
            return entry.value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """
        Set value in cache with TTL

        Args:
            key: Cache key
            value: Value to cache (any type)
            ttl: Time to live in seconds (uses default_ttl if None)
        """
        ttl = ttl if ttl is not None else self.default_ttl
        now = time.time()

        entry = CacheEntry(
            value=value,
            expires_at=now + ttl,
            created_at=now
        )

        async with self._lock:
            self._cache[key] = entry
            self._sets += 1

        logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")

    async def delete(self, key: str) -> bool:
        """
        Delete value from cache

        Args:
            key: Cache key

        Returns:
            True if key existed, False otherwise
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache DELETE: {key}")
                return True
            return False

    async def clear(self) -> int:
        """
        Clear all cache entries

        Returns:
            Number of entries cleared
        """
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()

        logger.info(f"Cache cleared: {count} entries removed")
        return count

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache (and is not expired)

        Args:
            key: Cache key

        Returns:
            True if key exists and not expired, False otherwise
        """
        value = await self.get(key)
        return value is not None

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "entries": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "sets": self._sets,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
        }

    def reset_stats(self) -> None:
        """Reset cache statistics"""
        self._hits = 0
        self._misses = 0
        self._sets = 0
        logger.info("Cache statistics reset")

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"CacheService(entries={stats['entries']}, "
            f"hits={stats['hits']}, misses={stats['misses']}, "
            f"hit_rate={stats['hit_rate_percent']}%)"
        )
