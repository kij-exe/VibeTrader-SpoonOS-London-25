"""
File manager for storing and retrieving kline data.

Handles caching of raw Binance data to avoid re-fetching.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ...config.settings import get_settings
from ...config.intervals import BinanceInterval
from ...utils.time_utils import ms_to_timestamp, timestamp_to_ms
from ..models import KlineData, KlineBar


logger = logging.getLogger(__name__)


class DataFileManager:
    """
    Manages storage and retrieval of kline data files.
    
    File naming convention:
        {symbol}_{interval}_{start_date}_{end_date}.json
        e.g., BTCUSDT_4h_20240101_20240601.json
    """
    
    def __init__(self, base_dir: Optional[Path] = None):
        settings = get_settings()
        self.base_dir = base_dir or settings.paths.raw_data_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_filename(
        self,
        symbol: str,
        interval: str,
        start_time: int,
        end_time: int,
    ) -> str:
        """Generate filename for kline data."""
        start_date = ms_to_timestamp(start_time).strftime("%Y%m%d")
        end_date = ms_to_timestamp(end_time).strftime("%Y%m%d")
        return f"{symbol.upper()}_{interval}_{start_date}_{end_date}.json"
    
    def _get_filepath(
        self,
        symbol: str,
        interval: str,
        start_time: int,
        end_time: int,
    ) -> Path:
        """Get full filepath for kline data."""
        filename = self._get_filename(symbol, interval, start_time, end_time)
        return self.base_dir / filename
    
    def save(self, data: KlineData) -> Path:
        """
        Save kline data to JSON file.
        
        Args:
            data: KlineData to save
        
        Returns:
            Path to saved file
        """
        if not data.bars:
            raise ValueError("Cannot save empty KlineData")
        
        filepath = self._get_filepath(
            data.symbol,
            data.interval,
            data.start_time,
            data.end_time,
        )
        
        with open(filepath, "w") as f:
            json.dump(data.to_dict(), f, indent=2)
        
        logger.info(f"Saved {len(data)} bars to {filepath}")
        return filepath
    
    def load(self, filepath: Path) -> KlineData:
        """
        Load kline data from JSON file.
        
        Args:
            filepath: Path to JSON file
        
        Returns:
            KlineData object
        """
        with open(filepath, "r") as f:
            data = json.load(f)
        
        return KlineData.from_dict(data)
    
    def find_cached(
        self,
        symbol: str,
        interval: str,
        start_time: int,
        end_time: int,
    ) -> Optional[KlineData]:
        """
        Find cached data that covers the requested range.
        
        Returns cached data if it fully covers the requested range,
        otherwise returns None.
        
        Args:
            symbol: Trading pair
            interval: Kline interval
            start_time: Start timestamp in ms
            end_time: End timestamp in ms
        
        Returns:
            KlineData if cache hit, None otherwise
        """
        # Look for exact match first
        exact_path = self._get_filepath(symbol, interval, start_time, end_time)
        if exact_path.exists():
            logger.info(f"Cache hit (exact): {exact_path}")
            return self.load(exact_path)
        
        # Look for files that might contain our range
        pattern = f"{symbol.upper()}_{interval}_*.json"
        matching_files = list(self.base_dir.glob(pattern))
        
        for filepath in matching_files:
            try:
                data = self.load(filepath)
                # Check if cached data covers our range
                if data.start_time <= start_time and data.end_time >= end_time:
                    logger.info(f"Cache hit (superset): {filepath}")
                    # Filter to requested range
                    filtered_bars = [
                        bar for bar in data.bars
                        if start_time <= bar.open_time <= end_time
                    ]
                    return KlineData(
                        symbol=data.symbol,
                        interval=data.interval,
                        bars=filtered_bars,
                    )
            except Exception as e:
                logger.warning(f"Error loading cache file {filepath}: {e}")
                continue
        
        return None
    
    def list_cached(
        self,
        symbol: Optional[str] = None,
        interval: Optional[str] = None,
    ) -> List[dict]:
        """
        List all cached data files.
        
        Args:
            symbol: Filter by symbol (optional)
            interval: Filter by interval (optional)
        
        Returns:
            List of dicts with file metadata
        """
        if symbol and interval:
            pattern = f"{symbol.upper()}_{interval}_*.json"
        elif symbol:
            pattern = f"{symbol.upper()}_*.json"
        elif interval:
            pattern = f"*_{interval}_*.json"
        else:
            pattern = "*.json"
        
        results = []
        for filepath in self.base_dir.glob(pattern):
            try:
                # Parse filename
                parts = filepath.stem.split("_")
                if len(parts) >= 4:
                    results.append({
                        "filepath": str(filepath),
                        "symbol": parts[0],
                        "interval": parts[1],
                        "start_date": parts[2],
                        "end_date": parts[3],
                        "size_bytes": filepath.stat().st_size,
                    })
            except Exception:
                continue
        
        return results
    
    def delete_cached(
        self,
        symbol: Optional[str] = None,
        interval: Optional[str] = None,
        older_than_days: Optional[int] = None,
    ) -> int:
        """
        Delete cached data files.
        
        Args:
            symbol: Filter by symbol (optional)
            interval: Filter by interval (optional)
            older_than_days: Delete files older than N days (optional)
        
        Returns:
            Number of files deleted
        """
        cached = self.list_cached(symbol, interval)
        deleted = 0
        
        now = datetime.now()
        
        for item in cached:
            filepath = Path(item["filepath"])
            
            if older_than_days:
                mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                age_days = (now - mtime).days
                if age_days < older_than_days:
                    continue
            
            filepath.unlink()
            deleted += 1
            logger.info(f"Deleted cache file: {filepath}")
        
        return deleted
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        cached = self.list_cached()
        total_size = sum(item["size_bytes"] for item in cached)
        
        symbols = set(item["symbol"] for item in cached)
        intervals = set(item["interval"] for item in cached)
        
        return {
            "total_files": len(cached),
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "unique_symbols": len(symbols),
            "unique_intervals": len(intervals),
            "symbols": list(symbols),
            "intervals": list(intervals),
        }
