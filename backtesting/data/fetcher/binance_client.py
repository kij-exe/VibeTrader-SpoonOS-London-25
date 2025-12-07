"""
Binance API client for fetching historical kline data.

Features:
- Automatic pagination for large date ranges
- Rate limiting (request count and weight)
- Retry logic with exponential backoff
- Progress tracking
"""

import asyncio
import logging
from datetime import datetime
from typing import AsyncIterator, Callable, List, Optional, Union

import aiohttp

from ...config.settings import get_settings, BinanceConfig
from ...config.intervals import BinanceInterval, get_interval_ms, get_weight_for_limit
from ...utils.rate_limiter import WeightedRateLimiter
from ...utils.time_utils import (
    timestamp_to_ms,
    ms_to_timestamp,
    get_date_range_chunks,
)
from ..models import KlineBar, KlineData


logger = logging.getLogger(__name__)


class BinanceAPIError(Exception):
    """Binance API error."""
    def __init__(self, status: int, message: str, code: Optional[int] = None):
        self.status = status
        self.message = message
        self.code = code
        super().__init__(f"Binance API Error {status}: {message} (code={code})")


class BinanceDataFetcher:
    """
    Fetches historical kline data from Binance API.
    
    Usage:
        async with BinanceDataFetcher() as fetcher:
            data = await fetcher.fetch_klines(
                symbol="BTCUSDT",
                interval="4h",
                start_time="2024-01-01",
                end_time="2024-06-01",
            )
    """
    
    def __init__(
        self,
        config: Optional[BinanceConfig] = None,
        rate_limiter: Optional[WeightedRateLimiter] = None,
    ):
        settings = get_settings()
        self.config = config or settings.binance
        self.rate_limiter = rate_limiter or WeightedRateLimiter(
            max_requests=self.config.rate_limit_requests,
            max_weight=self.config.rate_limit_weight,
        )
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self) -> "BinanceDataFetcher":
        """Create aiohttp session."""
        self._session = aiohttp.ClientSession(
            headers={"User-Agent": self.config.user_agent}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Close aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None
    
    @property
    def session(self) -> aiohttp.ClientSession:
        """Get current session, raising if not initialized."""
        if self._session is None:
            raise RuntimeError(
                "BinanceDataFetcher must be used as async context manager"
            )
        return self._session
    
    async def _make_request(
        self,
        endpoint: str,
        params: dict,
        max_retries: int = 3,
    ) -> List:
        """
        Make API request with rate limiting and retry logic.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            max_retries: Maximum retry attempts
        
        Returns:
            JSON response data
        """
        url = f"{self.config.base_url}{endpoint}"
        weight = get_weight_for_limit(params.get("limit", self.config.default_limit))
        
        for attempt in range(max_retries):
            # Wait for rate limit
            await self.rate_limiter.acquire(weight)
            
            try:
                async with self.session.get(url, params=params) as response:
                    # Log rate limit headers
                    used_weight = response.headers.get("X-MBX-USED-WEIGHT-1M", "?")
                    logger.debug(f"Request weight used: {used_weight}")
                    
                    if response.status == 200:
                        return await response.json()
                    
                    # Handle errors
                    error_data = await response.json()
                    error_code = error_data.get("code")
                    error_msg = error_data.get("msg", "Unknown error")
                    
                    # Rate limit exceeded
                    if response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", 60))
                        logger.warning(f"Rate limited, waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue
                    
                    # IP ban
                    if response.status == 418:
                        ban_until = response.headers.get("Retry-After", "unknown")
                        raise BinanceAPIError(
                            418, f"IP banned until {ban_until}", error_code
                        )
                    
                    # Other errors
                    raise BinanceAPIError(response.status, error_msg, error_code)
            
            except aiohttp.ClientError as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
        
        raise RuntimeError("Max retries exceeded")
    
    async def fetch_klines_chunk(
        self,
        symbol: str,
        interval: Union[str, BinanceInterval],
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 1000,
    ) -> List[KlineBar]:
        """
        Fetch a single chunk of kline data.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            interval: Kline interval (e.g., "4h")
            start_time: Start timestamp in ms
            end_time: End timestamp in ms
            limit: Number of bars (max 1500)
        
        Returns:
            List of KlineBar objects
        """
        if isinstance(interval, BinanceInterval):
            interval = interval.value
        
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": min(limit, self.config.max_limit),
        }
        
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        
        data = await self._make_request(self.config.klines_endpoint, params)
        
        return [KlineBar.from_binance_response(bar) for bar in data]
    
    async def fetch_klines(
        self,
        symbol: str,
        interval: Union[str, BinanceInterval],
        start_time: Union[datetime, str, int],
        end_time: Union[datetime, str, int],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> KlineData:
        """
        Fetch kline data for a date range with automatic pagination.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            interval: Kline interval (e.g., "4h")
            start_time: Start time (datetime, ISO string, or ms timestamp)
            end_time: End time (datetime, ISO string, or ms timestamp)
            progress_callback: Optional callback(fetched_bars, total_estimated)
        
        Returns:
            KlineData with all bars
        """
        # Normalize interval
        if isinstance(interval, str):
            interval_enum = BinanceInterval(interval)
        else:
            interval_enum = interval
        
        # Convert times to ms
        if not isinstance(start_time, int):
            start_time = timestamp_to_ms(start_time)
        if not isinstance(end_time, int):
            end_time = timestamp_to_ms(end_time)
        
        interval_ms = get_interval_ms(interval_enum)
        
        # Calculate chunks
        chunks = list(get_date_range_chunks(
            start_time,
            end_time,
            interval_ms,
            max_bars_per_chunk=self.config.default_limit,
        ))
        
        # Estimate total bars
        total_estimated = (end_time - start_time) // interval_ms
        
        logger.info(
            f"Fetching {symbol} {interval_enum.value} data: "
            f"{ms_to_timestamp(start_time)} to {ms_to_timestamp(end_time)} "
            f"(~{total_estimated} bars in {len(chunks)} chunks)"
        )
        
        all_bars: List[KlineBar] = []
        
        for i, (chunk_start, chunk_end) in enumerate(chunks):
            bars = await self.fetch_klines_chunk(
                symbol=symbol,
                interval=interval_enum.value,
                start_time=chunk_start,
                end_time=chunk_end,
                limit=self.config.default_limit,
            )
            
            all_bars.extend(bars)
            
            if progress_callback:
                progress_callback(len(all_bars), total_estimated)
            
            logger.debug(
                f"Chunk {i + 1}/{len(chunks)}: fetched {len(bars)} bars "
                f"(total: {len(all_bars)})"
            )
        
        # Remove duplicates and sort
        bars_dict = {bar.open_time: bar for bar in all_bars}
        sorted_bars = sorted(bars_dict.values(), key=lambda x: x.open_time)
        
        logger.info(f"Fetched {len(sorted_bars)} unique bars for {symbol}")
        
        return KlineData(
            symbol=symbol.upper(),
            interval=interval_enum.value,
            bars=sorted_bars,
        )
    
    async def fetch_klines_stream(
        self,
        symbol: str,
        interval: Union[str, BinanceInterval],
        start_time: Union[datetime, str, int],
        end_time: Union[datetime, str, int],
    ) -> AsyncIterator[List[KlineBar]]:
        """
        Stream kline data in chunks (memory efficient for large ranges).
        
        Yields:
            Lists of KlineBar objects (one per chunk)
        """
        if isinstance(interval, str):
            interval_enum = BinanceInterval(interval)
        else:
            interval_enum = interval
        
        if not isinstance(start_time, int):
            start_time = timestamp_to_ms(start_time)
        if not isinstance(end_time, int):
            end_time = timestamp_to_ms(end_time)
        
        interval_ms = get_interval_ms(interval_enum)
        
        chunks = get_date_range_chunks(
            start_time,
            end_time,
            interval_ms,
            max_bars_per_chunk=self.config.default_limit,
        )
        
        for chunk_start, chunk_end in chunks:
            bars = await self.fetch_klines_chunk(
                symbol=symbol,
                interval=interval_enum.value,
                start_time=chunk_start,
                end_time=chunk_end,
            )
            yield bars
    
    async def get_server_time(self) -> int:
        """Get Binance server time in milliseconds."""
        data = await self._make_request("/api/v3/time", {})
        return data["serverTime"]
    
    async def validate_symbol(self, symbol: str) -> bool:
        """Check if a symbol is valid on Binance."""
        try:
            # Fetch 1 bar to validate
            await self.fetch_klines_chunk(
                symbol=symbol,
                interval="1d",
                limit=1,
            )
            return True
        except BinanceAPIError as e:
            if e.code == -1121:  # Invalid symbol
                return False
            raise
