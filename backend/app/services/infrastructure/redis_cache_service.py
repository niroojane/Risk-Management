"""Redis cache implementation - drop-in replacement for CacheService"""
import pickle
import logging
from typing import Any, Optional, Dict

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_KEY_PREFIX = "riskapp:"


class RedisCacheService:
    """Redis-backed cache with TTL - same interface as CacheService"""

    def __init__(self, url: str, default_ttl: int = 300):
        self.default_ttl = default_ttl
        self._url = url
        self._client: Optional[aioredis.Redis] = None

    def _key(self, key: str) -> str:
        return f"{_KEY_PREFIX}{key}"

    async def start(self) -> None:
        self._client = aioredis.from_url(self._url, decode_responses=False)
        await self._client.ping()
        logger.info(f"RedisCacheService connected: {self._url}")

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("RedisCacheService disconnected")

    async def get(self, key: str) -> Optional[Any]:
        data = await self._client.get(self._key(key))
        if data is None:
            return None
        return pickle.loads(data)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ttl = ttl if ttl is not None else self.default_ttl
        await self._client.setex(self._key(key), ttl, pickle.dumps(value))

    async def delete(self, key: str) -> bool:
        return bool(await self._client.delete(self._key(key)))

    async def clear(self) -> int:
        pattern = f"{_KEY_PREFIX}*"
        keys = [k async for k in self._client.scan_iter(pattern)]
        if keys:
            return await self._client.delete(*keys)
        return 0

    def get_stats(self) -> Dict[str, Any]:
        return {"backend": "redis", "url": self._url}
