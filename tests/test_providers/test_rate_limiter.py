"""Tests for TokenBucketRateLimiter."""

import asyncio
import time

import pytest

from fin_toolkit.providers.rate_limiter import TokenBucketRateLimiter


class TestTokenBucketRateLimiter:
    async def test_allows_burst_up_to_limit(self) -> None:
        limiter = TokenBucketRateLimiter(requests_per_minute=6, max_concurrent=10)
        start = time.monotonic()
        for _ in range(6):
            async with limiter:
                pass
        elapsed = time.monotonic() - start
        # 6 requests should be nearly instant (burst)
        assert elapsed < 1.0

    async def test_throttles_after_burst(self) -> None:
        limiter = TokenBucketRateLimiter(requests_per_minute=60, max_concurrent=10)
        # Drain all tokens
        for _ in range(60):
            async with limiter:
                pass
        # Next request should wait for refill (~1 second for 60 rpm)
        start = time.monotonic()
        async with limiter:
            pass
        elapsed = time.monotonic() - start
        assert elapsed >= 0.5  # should wait at least ~1s but allow some tolerance

    async def test_max_concurrent_limits_parallelism(self) -> None:
        limiter = TokenBucketRateLimiter(requests_per_minute=600, max_concurrent=2)
        concurrent_count = 0
        max_observed = 0

        async def task() -> None:
            nonlocal concurrent_count, max_observed
            async with limiter:
                concurrent_count += 1
                max_observed = max(max_observed, concurrent_count)
                await asyncio.sleep(0.05)
                concurrent_count -= 1

        await asyncio.gather(*[task() for _ in range(6)])
        assert max_observed <= 2

    async def test_token_refill_over_time(self) -> None:
        limiter = TokenBucketRateLimiter(requests_per_minute=120, max_concurrent=10)
        # Drain all tokens (120 tokens, 2/sec refill)
        for _ in range(120):
            async with limiter:
                pass
        # Wait for refill: 1.5s at 2 tokens/sec = 3 tokens
        await asyncio.sleep(1.5)
        start = time.monotonic()
        async with limiter:
            pass
        elapsed = time.monotonic() - start
        # Should be nearly instant since tokens refilled
        assert elapsed < 0.3

    async def test_context_manager_releases_on_exception(self) -> None:
        limiter = TokenBucketRateLimiter(requests_per_minute=600, max_concurrent=1)
        with pytest.raises(ValueError, match="test error"):
            async with limiter:
                raise ValueError("test error")
        # Should still be able to acquire after exception
        async with limiter:
            pass

    def test_init_parameters(self) -> None:
        limiter = TokenBucketRateLimiter(requests_per_minute=30, max_concurrent=5)
        assert limiter.requests_per_minute == 30
        assert limiter.max_concurrent == 5
