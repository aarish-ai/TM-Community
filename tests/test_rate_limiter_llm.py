import time
import pytest
import asyncio
from truth_mirror.rate_limiter import llm_sync_limiter, AsyncRateLimiter

def test_sync_llm_limiter():
    start = time.time()
    llm_sync_limiter.wait()
    llm_sync_limiter.wait()
    duration = time.time() - start
    assert duration >= 2.0, "Second wait should enforce 2.0s delay"

@pytest.mark.asyncio
async def test_async_rate_limiter():
    limiter = AsyncRateLimiter(delay_seconds=0.1)
    start = time.time()
    await limiter.wait()
    await limiter.wait()
    duration = time.time() - start
    assert duration >= 0.1, "Async limiter should enforce delay"
