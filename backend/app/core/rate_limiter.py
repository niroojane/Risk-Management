"""
Rate Limiter for API calls
Implements Token Bucket algorithm to prevent exceeding rate limits
"""
import asyncio
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded"""

    def __init__(self, retry_after: float):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after:.2f} seconds")


class RateLimiter:
    """
    Token Bucket Rate Limiter

    Allows burst traffic up to max_calls, then enforces steady rate.
    Thread-safe for async operations.

    Args:
        max_calls: Maximum number of calls allowed per period
        period: Time period in seconds
        name: Identifier for logging
    """

    def __init__(self, max_calls: int, period: int, name: str = "default"):
        self.max_calls = max_calls
        self.period = period
        self.name = name

        # Token bucket state
        self.tokens = float(max_calls)
        self.last_update = time.monotonic()

        # Async lock for thread safety
        self._lock = asyncio.Lock()

        logger.info(
            f"RateLimiter '{name}' initialized: {max_calls} calls per {period}s"
        )

    def _refill_tokens(self) -> None:
        """
        Refill tokens based on elapsed time

        Tokens refill at a steady rate: (max_calls / period) tokens per second
        """
        now = time.monotonic()
        elapsed = now - self.last_update

        # Calculate tokens to add based on elapsed time
        tokens_to_add = elapsed * (self.max_calls / self.period)
        self.tokens = min(self.max_calls, self.tokens + tokens_to_add)
        self.last_update = now

    async def acquire(self, tokens: int = 1) -> None:
        """
        Acquire tokens to make API call(s)

        Args:
            tokens: Number of tokens to acquire (default 1)

        Raises:
            RateLimitExceeded: If not enough tokens available
        """
        async with self._lock:
            self._refill_tokens()

            if self.tokens >= tokens:
                self.tokens -= tokens
                logger.debug(
                    f"RateLimiter '{self.name}': Acquired {tokens} token(s). "
                    f"Remaining: {self.tokens:.2f}/{self.max_calls}"
                )
            else:
                # Calculate wait time needed
                tokens_needed = tokens - self.tokens
                wait_time = tokens_needed / (self.max_calls / self.period)

                logger.warning(
                    f"RateLimiter '{self.name}': Rate limit reached. "
                    f"Need {tokens_needed:.2f} more tokens. Wait time: {wait_time:.2f}s"
                )
                raise RateLimitExceeded(retry_after=wait_time)

    async def wait_and_acquire(self, tokens: int = 1) -> None:
        """
        Wait until tokens are available, then acquire

        Args:
            tokens: Number of tokens to acquire (default 1)
        """
        while True:
            try:
                await self.acquire(tokens)
                return
            except RateLimitExceeded as e:
                logger.info(
                    f"RateLimiter '{self.name}': Waiting {e.retry_after:.2f}s "
                    f"before retry..."
                )
                await asyncio.sleep(e.retry_after)

    def get_available_tokens(self) -> float:
        """
        Get current number of available tokens

        Returns:
            Number of tokens currently available
        """
        self._refill_tokens()
        return self.tokens

    def reset(self) -> None:
        """
        Reset rate limiter to full capacity

        Useful for testing or manual intervention
        """
        self.tokens = float(self.max_calls)
        self.last_update = time.monotonic()
        logger.info(f"RateLimiter '{self.name}' reset to full capacity")


class BinanceRateLimiter:
    """
    Specialized rate limiter for Binance API

    Binance has multiple rate limits:
    - Weight-based limits (each endpoint has a weight)
    - Order limits (for trading endpoints)
    - WebSocket connection limits

    This implementation focuses on weight-based limits for now.
    """

    def __init__(self, max_calls: int, period: int):
        self.limiter = RateLimiter(
            max_calls=max_calls,
            period=period,
            name="Binance"
        )

    async def acquire(self, weight: int = 1) -> None:
        """
        Acquire permission for Binance API call

        Args:
            weight: API endpoint weight (default 1)
                   - Most endpoints: weight=1
                   - Market data: weight=1-40
                   - Account data: weight=5-40
        """
        await self.limiter.acquire(tokens=weight)

    async def wait_and_acquire(self, weight: int = 1) -> None:
        """
        Wait if needed, then acquire permission

        Args:
            weight: API endpoint weight
        """
        await self.limiter.wait_and_acquire(tokens=weight)

    def get_available_weight(self) -> float:
        """Get currently available weight"""
        return self.limiter.get_available_tokens()

    def reset(self) -> None:
        """Reset rate limiter"""
        self.limiter.reset()
