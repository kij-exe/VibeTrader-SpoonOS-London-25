"""
Data Loader

Utilities for loading and generating historical market data for backtesting.
"""

import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from app.strategy.interface import OHLCV


class DataLoader:
    """Load historical data from various sources"""
    
    @staticmethod
    def from_csv(
        filepath: str,
        symbol: str,
        timestamp_col: str = "timestamp",
        open_col: str = "open",
        high_col: str = "high",
        low_col: str = "low",
        close_col: str = "close",
        volume_col: str = "volume",
        timestamp_format: str = "%Y-%m-%d %H:%M:%S",
    ) -> List[OHLCV]:
        """
        Load OHLCV data from a CSV file.
        
        Args:
            filepath: Path to CSV file
            symbol: Symbol name to assign
            timestamp_col: Column name for timestamp
            open_col: Column name for open price
            high_col: Column name for high price
            low_col: Column name for low price
            close_col: Column name for close price
            volume_col: Column name for volume
            timestamp_format: Datetime format string
        
        Returns:
            List of OHLCV objects
        """
        data = []
        
        with open(filepath, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    bar = OHLCV(
                        timestamp=datetime.strptime(row[timestamp_col], timestamp_format),
                        symbol=symbol,
                        open=float(row[open_col]),
                        high=float(row[high_col]),
                        low=float(row[low_col]),
                        close=float(row[close_col]),
                        volume=float(row[volume_col]),
                    )
                    data.append(bar)
                except (ValueError, KeyError) as e:
                    continue  # Skip malformed rows
        
        return sorted(data, key=lambda x: x.timestamp)
    
    @staticmethod
    def from_json(filepath: str, symbol: str) -> List[OHLCV]:
        """
        Load OHLCV data from a JSON file.
        
        Expected format:
        [
            {"timestamp": "2024-01-01T00:00:00", "open": 100, "high": 105, ...},
            ...
        ]
        """
        data = []
        
        with open(filepath, "r") as f:
            records = json.load(f)
        
        for record in records:
            try:
                timestamp = record.get("timestamp") or record.get("time") or record.get("date")
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                elif isinstance(timestamp, (int, float)):
                    timestamp = datetime.fromtimestamp(timestamp / 1000)  # Assume ms
                
                bar = OHLCV(
                    timestamp=timestamp,
                    symbol=symbol,
                    open=float(record.get("open", record.get("o", 0))),
                    high=float(record.get("high", record.get("h", 0))),
                    low=float(record.get("low", record.get("l", 0))),
                    close=float(record.get("close", record.get("c", 0))),
                    volume=float(record.get("volume", record.get("v", 0))),
                )
                data.append(bar)
            except (ValueError, TypeError):
                continue
        
        return sorted(data, key=lambda x: x.timestamp)
    
    @staticmethod
    def generate_random(
        symbol: str,
        start_date: datetime,
        periods: int,
        timeframe_minutes: int = 60,
        initial_price: float = 100.0,
        volatility: float = 0.02,
        trend: float = 0.0001,
        seed: Optional[int] = None,
    ) -> List[OHLCV]:
        """
        Generate random OHLCV data for testing.
        
        Uses geometric Brownian motion for realistic price movement.
        
        Args:
            symbol: Symbol name
            start_date: Starting timestamp
            periods: Number of bars to generate
            timeframe_minutes: Minutes per bar
            initial_price: Starting price
            volatility: Price volatility (standard deviation of returns)
            trend: Drift/trend component
            seed: Random seed for reproducibility
        
        Returns:
            List of OHLCV objects
        """
        if seed is not None:
            random.seed(seed)
        
        data = []
        price = initial_price
        current_time = start_date
        
        for _ in range(periods):
            # Generate random return using geometric Brownian motion
            return_pct = random.gauss(trend, volatility)
            
            # Generate OHLC from the return
            open_price = price
            
            # Intrabar movement
            intrabar_vol = volatility * 0.5
            high_move = abs(random.gauss(0, intrabar_vol))
            low_move = abs(random.gauss(0, intrabar_vol))
            
            close_price = open_price * (1 + return_pct)
            high_price = max(open_price, close_price) * (1 + high_move)
            low_price = min(open_price, close_price) * (1 - low_move)
            
            # Volume with some randomness
            base_volume = 1000000
            volume = base_volume * (0.5 + random.random())
            
            bar = OHLCV(
                timestamp=current_time,
                symbol=symbol,
                open=round(open_price, 4),
                high=round(high_price, 4),
                low=round(low_price, 4),
                close=round(close_price, 4),
                volume=round(volume, 2),
            )
            data.append(bar)
            
            # Update for next iteration
            price = close_price
            current_time += timedelta(minutes=timeframe_minutes)
        
        return data
    
    @staticmethod
    def generate_trending(
        symbol: str,
        start_date: datetime,
        periods: int,
        timeframe_minutes: int = 60,
        initial_price: float = 100.0,
        trend_direction: str = "up",
        trend_strength: float = 0.001,
        volatility: float = 0.015,
        seed: Optional[int] = None,
    ) -> List[OHLCV]:
        """
        Generate trending market data.
        
        Args:
            symbol: Symbol name
            start_date: Starting timestamp
            periods: Number of bars
            timeframe_minutes: Minutes per bar
            initial_price: Starting price
            trend_direction: "up" or "down"
            trend_strength: Strength of trend
            volatility: Random volatility
            seed: Random seed
        
        Returns:
            List of OHLCV objects
        """
        trend = trend_strength if trend_direction == "up" else -trend_strength
        return DataLoader.generate_random(
            symbol=symbol,
            start_date=start_date,
            periods=periods,
            timeframe_minutes=timeframe_minutes,
            initial_price=initial_price,
            volatility=volatility,
            trend=trend,
            seed=seed,
        )
    
    @staticmethod
    def generate_ranging(
        symbol: str,
        start_date: datetime,
        periods: int,
        timeframe_minutes: int = 60,
        center_price: float = 100.0,
        range_percent: float = 0.05,
        volatility: float = 0.01,
        seed: Optional[int] = None,
    ) -> List[OHLCV]:
        """
        Generate range-bound/sideways market data.
        
        Price oscillates around center_price within range_percent bounds.
        """
        if seed is not None:
            random.seed(seed)
        
        data = []
        price = center_price
        current_time = start_date
        
        upper_bound = center_price * (1 + range_percent)
        lower_bound = center_price * (1 - range_percent)
        
        for _ in range(periods):
            # Mean reversion towards center
            distance_from_center = (price - center_price) / center_price
            mean_reversion = -distance_from_center * 0.1
            
            return_pct = random.gauss(mean_reversion, volatility)
            
            open_price = price
            close_price = open_price * (1 + return_pct)
            
            # Clamp to range
            close_price = max(lower_bound, min(upper_bound, close_price))
            
            intrabar_vol = volatility * 0.5
            high_price = max(open_price, close_price) * (1 + abs(random.gauss(0, intrabar_vol)))
            low_price = min(open_price, close_price) * (1 - abs(random.gauss(0, intrabar_vol)))
            
            volume = 1000000 * (0.5 + random.random())
            
            bar = OHLCV(
                timestamp=current_time,
                symbol=symbol,
                open=round(open_price, 4),
                high=round(high_price, 4),
                low=round(low_price, 4),
                close=round(close_price, 4),
                volume=round(volume, 2),
            )
            data.append(bar)
            
            price = close_price
            current_time += timedelta(minutes=timeframe_minutes)
        
        return data
