"""Token bucket rate limiter for data providers."""

from __future__ import annotations

import asyncio
import time
from types import TracebackType


class TokenBucketRateLimiter:
    """Async rate limiter using token bucket + semaphore for concurrency."""

    def __init__(self, requests_per_minute: int, max_concurrent: int) -> None:
        self.requests_per_minute = requests_per_minute
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._tokens = float(requests_per_minute)
        self._max_tokens = float(requests_per_minute)
        self._refill_rate = requests_per_minute / 60.0  # tokens per second
        self._last_refill = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._max_tokens, self._tokens + elapsed * self._refill_rate)
        self._last_refill = now

    async def _acquire_token(self) -> None:
        while True:
            self._refill()
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return
            # Wait until at least one token is available
            wait_time = (1.0 - self._tokens) / self._refill_rate
            await asyncio.sleep(wait_time)

    async def __aenter__(self) -> TokenBucketRateLimiter:
        await self._semaphore.acquire()
        try:
            await self._acquire_token()
        except BaseException:
            self._semaphore.release()
            raise
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._semaphore.release()
