"""
Rate limiting utilities for API calls.

Implements token bucket algorithm for both request count and weight-based limiting.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class RateLimiter:
    """
    Simple rate limiter using token bucket algorithm.
    
    Args:
        max_requests: Maximum requests allowed per window
        window_seconds: Time window in seconds (default 60)
    """
    max_requests: int
    window_seconds: float = 60.0
    
    def __post_init__(self):
        self._tokens = float(self.max_requests)
        self._last_update = time.monotonic()
        self._lock = asyncio.Lock()
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_update
        self._last_update = now
        
        # Add tokens based on elapsed time
        refill_rate = self.max_requests / self.window_seconds
        self._tokens = min(self.max_requests, self._tokens + elapsed * refill_rate)
    
    async def acquire(self, tokens: int = 1) -> None:
        """
        Acquire tokens, waiting if necessary.
        
        Args:
            tokens: Number of tokens to acquire
        """
        async with self._lock:
            while True:
                self._refill()
                
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return
                
                # Calculate wait time
                needed = tokens - self._tokens
                refill_rate = self.max_requests / self.window_seconds
                wait_time = needed / refill_rate
                
                await asyncio.sleep(min(wait_time, 1.0))  # Max 1 second wait per iteration
    
    @property
    def available_tokens(self) -> float:
        """Get current available tokens."""
        self._refill()
        return self._tokens


class WeightedRateLimiter:
    """
    Rate limiter that tracks both request count and weight.
    
    Binance uses weight-based rate limiting where different endpoints
    have different weights.
    """
    
    def __init__(
        self,
        max_requests: int = 1200,
        max_weight: int = 6000,
        window_seconds: float = 60.0,
    ):
        self.request_limiter = RateLimiter(max_requests, window_seconds)
        self.weight_limiter = RateLimiter(max_weight, window_seconds)
    
    async def acquire(self, weight: int = 1) -> None:
        """
        Acquire both request and weight tokens.
        
        Args:
            weight: Weight of the request
        """
        # Acquire both in parallel
        await asyncio.gather(
            self.request_limiter.acquire(1),
            self.weight_limiter.acquire(weight),
        )
    
    @property
    def available_weight(self) -> float:
        """Get current available weight."""
        return self.weight_limiter.available_tokens
    
    @property
    def available_requests(self) -> float:
        """Get current available requests."""
        return self.request_limiter.available_tokens
