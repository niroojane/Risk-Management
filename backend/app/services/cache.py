"""In-memory cache with TTL and background cleanup"""
import asyncio
import time
import logging
from typing import Any, Optional, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with expiration"""
    value: Any
    expires_at: float
    created_at: float


class CacheService:
    """In-memory cache with TTL, auto-cleanup, and hit/miss stats"""

    def __init__(self, default_ttl: int = 300, cleanup_interval: int = 60):
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        self._cache: Dict[str, CacheEntry] = {}
        self._hits = 0
        self._misses = 0
        self._sets = 0
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        logger.info(f"CacheService initialized with default TTL: {default_ttl}s, cleanup interval: {cleanup_interval}s")

    async def start(self) -> None:
        """Start background cleanup task"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("CacheService background cleanup task started")

    async def stop(self) -> None:
        """Stop background cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("CacheService background cleanup task stopped")

    async def _cleanup_loop(self) -> None:
        """Periodically remove expired entries"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                removed = await self._remove_expired()
                if removed > 0:
                    logger.debug(f"Cache cleanup: removed {removed} expired entries")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")

    async def _remove_expired(self) -> int:
        """Remove expired entries, return count"""
        now = time.time()
        removed = 0

        async with self._lock:
            keys_to_remove = [k for k, e in self._cache.items() if e.expires_at < now]
            for key in keys_to_remove:
                del self._cache[key]
                removed += 1

        return removed

    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if entry is expired"""
        return time.time() > entry.expires_at

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (None if missing or expired)"""
        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._misses += 1
                return None

            if self._is_expired(entry):
                del self._cache[key]
                self._misses += 1
                return None

            self._hits += 1
            return entry.value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL"""
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

    async def delete(self, key: str) -> bool:
        """Delete key from cache, return True if existed"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> int:
        """Clear all entries, return count"""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()

        logger.info(f"Cache cleared: {count} entries")
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0

        return {
            "entries": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "sets": self._sets,
            "total_requests": total,
            "hit_rate_percent": round(hit_rate, 2),
        }
