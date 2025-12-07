"""
Time and date utilities for backtesting system.
"""

from datetime import datetime, timezone
from typing import Iterator, List, Optional, Tuple, Union


def timestamp_to_ms(dt: Union[datetime, str]) -> int:
    """
    Convert datetime to milliseconds timestamp.
    
    Args:
        dt: datetime object or ISO format string
    
    Returns:
        Timestamp in milliseconds
    """
    if isinstance(dt, str):
        dt = parse_date_string(dt)
    
    # Ensure timezone aware (assume UTC if naive)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    return int(dt.timestamp() * 1000)


def ms_to_timestamp(ms: int) -> datetime:
    """
    Convert milliseconds timestamp to datetime.
    
    Args:
        ms: Timestamp in milliseconds
    
    Returns:
        UTC datetime object
    """
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


def parse_date_string(date_str: str) -> datetime:
    """
    Parse various date string formats.
    
    Supports:
        - ISO format: "2024-01-15T10:30:00"
        - Date only: "2024-01-15"
        - With timezone: "2024-01-15T10:30:00Z"
    
    Args:
        date_str: Date string to parse
    
    Returns:
        datetime object (UTC)
    """
    # Remove 'Z' suffix and replace with +00:00
    date_str = date_str.replace("Z", "+00:00")
    
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    
    raise ValueError(f"Unable to parse date string: {date_str}")


def get_date_range_chunks(
    start_time: int,
    end_time: int,
    interval_ms: int,
    max_bars_per_chunk: int = 1000,
) -> Iterator[Tuple[int, int]]:
    """
    Split a date range into chunks suitable for API pagination.
    
    Args:
        start_time: Start timestamp in milliseconds
        end_time: End timestamp in milliseconds
        interval_ms: Interval duration in milliseconds
        max_bars_per_chunk: Maximum bars per API request
    
    Yields:
        Tuples of (chunk_start_ms, chunk_end_ms)
    """
    chunk_duration = interval_ms * max_bars_per_chunk
    current_start = start_time
    
    while current_start < end_time:
        chunk_end = min(current_start + chunk_duration, end_time)
        yield (current_start, chunk_end)
        current_start = chunk_end


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def get_trading_days(start: datetime, end: datetime) -> int:
    """
    Calculate approximate trading days between two dates.
    Crypto trades 24/7, so this returns calendar days.
    """
    delta = end - start
    return delta.days
