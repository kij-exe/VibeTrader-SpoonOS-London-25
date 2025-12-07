"""
Data models for kline/candlestick data.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class KlineBar:
    """
    Single kline/candlestick bar.
    
    Matches Binance klines response format.
    """
    open_time: int          # Open time in ms
    open: float             # Open price
    high: float             # High price
    low: float              # Low price
    close: float            # Close price
    volume: float           # Base asset volume
    close_time: int         # Close time in ms
    quote_volume: float     # Quote asset volume
    trades: int             # Number of trades
    taker_buy_base: float   # Taker buy base asset volume
    taker_buy_quote: float  # Taker buy quote asset volume
    
    @classmethod
    def from_binance_response(cls, data: List) -> "KlineBar":
        """
        Create KlineBar from Binance API response array.
        
        Binance format:
        [
            1499040000000,      // Open time
            "0.01634790",       // Open
            "0.80000000",       // High
            "0.01575800",       // Low
            "0.01577100",       // Close
            "148976.11427815",  // Volume
            1499644799999,      // Close time
            "2434.19055334",    // Quote asset volume
            308,                // Number of trades
            "1756.87402397",    // Taker buy base asset volume
            "28.46694368",      // Taker buy quote asset volume
            "17928899.62484339" // Ignore
        ]
        """
        return cls(
            open_time=int(data[0]),
            open=float(data[1]),
            high=float(data[2]),
            low=float(data[3]),
            close=float(data[4]),
            volume=float(data[5]),
            close_time=int(data[6]),
            quote_volume=float(data[7]),
            trades=int(data[8]),
            taker_buy_base=float(data[9]),
            taker_buy_quote=float(data[10]),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "open_time": self.open_time,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "close_time": self.close_time,
            "quote_volume": self.quote_volume,
            "trades": self.trades,
            "taker_buy_base": self.taker_buy_base,
            "taker_buy_quote": self.taker_buy_quote,
        }
    
    @property
    def open_datetime(self) -> datetime:
        """Get open time as datetime."""
        from ..utils.time_utils import ms_to_timestamp
        return ms_to_timestamp(self.open_time)
    
    @property
    def close_datetime(self) -> datetime:
        """Get close time as datetime."""
        from ..utils.time_utils import ms_to_timestamp
        return ms_to_timestamp(self.close_time)


@dataclass
class KlineData:
    """
    Collection of kline bars with metadata.
    """
    symbol: str
    interval: str
    bars: List[KlineBar] = field(default_factory=list)
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    
    def __post_init__(self):
        if self.bars:
            if self.start_time is None:
                self.start_time = self.bars[0].open_time
            if self.end_time is None:
                self.end_time = self.bars[-1].close_time
    
    def __len__(self) -> int:
        return len(self.bars)
    
    def __iter__(self):
        return iter(self.bars)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "bar_count": len(self.bars),
            "bars": [bar.to_dict() for bar in self.bars],
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KlineData":
        """Create from dictionary."""
        bars = [
            KlineBar(**bar) if isinstance(bar, dict) else bar
            for bar in data.get("bars", [])
        ]
        return cls(
            symbol=data["symbol"],
            interval=data["interval"],
            bars=bars,
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
        )
    
    def merge(self, other: "KlineData") -> "KlineData":
        """
        Merge with another KlineData, removing duplicates.
        
        Assumes both have the same symbol and interval.
        """
        if self.symbol != other.symbol or self.interval != other.interval:
            raise ValueError("Cannot merge KlineData with different symbol/interval")
        
        # Use dict to deduplicate by open_time
        bars_dict = {bar.open_time: bar for bar in self.bars}
        for bar in other.bars:
            bars_dict[bar.open_time] = bar
        
        # Sort by open_time
        merged_bars = sorted(bars_dict.values(), key=lambda x: x.open_time)
        
        return KlineData(
            symbol=self.symbol,
            interval=self.interval,
            bars=merged_bars,
        )
    
    @property
    def closes(self) -> List[float]:
        """Get list of close prices."""
        return [bar.close for bar in self.bars]
    
    @property
    def opens(self) -> List[float]:
        """Get list of open prices."""
        return [bar.open for bar in self.bars]
    
    @property
    def highs(self) -> List[float]:
        """Get list of high prices."""
        return [bar.high for bar in self.bars]
    
    @property
    def lows(self) -> List[float]:
        """Get list of low prices."""
        return [bar.low for bar in self.bars]
    
    @property
    def volumes(self) -> List[float]:
        """Get list of volumes."""
        return [bar.volume for bar in self.bars]
