"""
Lean QuantConnect data format converter.

Converts Binance kline data to Lean's expected format for crypto data.

Lean Crypto Data Structure:
    data/
    └── crypto/
        └── binance/
            └── {resolution}/
                └── {symbol}/
                    └── {date}_{type}.zip

Resolution: minute, hour, daily
Type: trade, quote, openinterest

CSV Format (inside zip):
    Time (ms since midnight),Open,High,Low,Close,Volume
    
For minute data, time is milliseconds since midnight UTC.
For daily data, time is typically 0.
"""

import csv
import io
import logging
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ...config.settings import get_settings
from ...config.intervals import BinanceInterval, INTERVAL_MINUTES
from ...utils.time_utils import ms_to_timestamp
from ..models import KlineData, KlineBar


logger = logging.getLogger(__name__)


class LeanDataConverter:
    """
    Converts kline data to Lean QuantConnect format.
    
    Lean expects crypto data in a specific directory structure with
    zipped CSV files.
    """
    
    # Lean resolution names
    RESOLUTION_MINUTE = "minute"
    RESOLUTION_HOUR = "hour"
    RESOLUTION_DAILY = "daily"
    
    def __init__(self, output_dir: Optional[Path] = None):
        settings = get_settings()
        self.output_dir = output_dir or settings.paths.lean_data_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_lean_resolution(self, interval: str) -> str:
        """Map Binance interval to Lean resolution."""
        try:
            interval_enum = BinanceInterval(interval)
            minutes = INTERVAL_MINUTES[interval_enum]
            
            if minutes < 60:
                return self.RESOLUTION_MINUTE
            elif minutes < 1440:
                return self.RESOLUTION_HOUR
            else:
                return self.RESOLUTION_DAILY
        except (ValueError, KeyError):
            # Default to minute for unknown intervals
            return self.RESOLUTION_MINUTE
    
    def _get_lean_symbol(self, symbol: str) -> str:
        """
        Convert Binance symbol to Lean format.
        
        Binance: BTCUSDT
        Lean: btcusdt (lowercase)
        """
        return symbol.lower()
    
    def _get_output_path(
        self,
        symbol: str,
        resolution: str,
        use_symbol_folder: bool = False,
    ) -> Path:
        """
        Get output path for Lean data file.
        
        For hour/daily: data/crypto/binance/{resolution}/
        For minute: data/crypto/binance/{resolution}/{symbol}/
        """
        base_path = (
            self.output_dir
            / "crypto"
            / "binance"
            / resolution
        )
        
        if use_symbol_folder:
            lean_symbol = self._get_lean_symbol(symbol)
            return base_path / lean_symbol
        
        return base_path
    
    def _format_lean_time(
        self,
        timestamp_ms: int,
        resolution: str,
    ) -> str:
        """
        Format timestamp for Lean CSV.
        
        For minute data: milliseconds since midnight UTC (int)
        For hour/daily data: YYYYMMDD HH:mm format
        """
        dt = ms_to_timestamp(timestamp_ms)
        
        if resolution in (self.RESOLUTION_HOUR, self.RESOLUTION_DAILY):
            # Hour/Daily format: YYYYMMDD HH:mm
            return dt.strftime("%Y%m%d %H:%M")
        else:
            # Minute format: milliseconds since midnight
            midnight = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            ms_since_midnight = int((dt - midnight).total_seconds() * 1000)
            return str(ms_since_midnight)
    
    def _group_bars_by_date(
        self,
        bars: List[KlineBar],
    ) -> Dict[str, List[KlineBar]]:
        """Group bars by date (YYYYMMDD)."""
        grouped: Dict[str, List[KlineBar]] = {}
        
        for bar in bars:
            dt = ms_to_timestamp(bar.open_time)
            date_key = dt.strftime("%Y%m%d")
            
            if date_key not in grouped:
                grouped[date_key] = []
            grouped[date_key].append(bar)
        
        return grouped
    
    def _create_csv_content(
        self,
        bars: List[KlineBar],
        resolution: str,
        data_type: str = "trade",
    ) -> str:
        """
        Create CSV content for Lean.
        
        Trade format: Time,Open,High,Low,Close,Volume
        Quote format: Time,BidOpen,BidHigh,BidLow,BidClose,BidSize,AskOpen,AskHigh,AskLow,AskClose,AskSize
        """
        output = io.StringIO()
        
        for bar in sorted(bars, key=lambda x: x.open_time):
            time_value = self._format_lean_time(bar.open_time, resolution)
            
            if data_type == "quote":
                # Quote format: simulate bid/ask from OHLC
                # Bid is slightly below, Ask is slightly above
                spread = 0.0001  # 0.01% spread
                bid_open = bar.open * (1 - spread)
                bid_high = bar.high * (1 - spread)
                bid_low = bar.low * (1 - spread)
                bid_close = bar.close * (1 - spread)
                ask_open = bar.open * (1 + spread)
                ask_high = bar.high * (1 + spread)
                ask_low = bar.low * (1 + spread)
                ask_close = bar.close * (1 + spread)
                size = bar.volume / 2  # Split volume between bid/ask
                
                line = f"{time_value},{bid_open:.2f},{bid_high:.2f},{bid_low:.2f},{bid_close:.2f},{size:.2f},{ask_open:.2f},{ask_high:.2f},{ask_low:.2f},{ask_close:.2f},{size:.2f}\n"
            else:
                # Trade format
                line = f"{time_value},{bar.open},{bar.high},{bar.low},{bar.close},{bar.volume}\n"
            
            output.write(line)
        
        return output.getvalue()
    
    def _create_zip_file(
        self,
        csv_content: str,
        output_path: Path,
        filename_base: str,
        data_type: str = "trade",
        resolution: str = None,
    ) -> Path:
        """
        Create zipped CSV file.
        
        For minute: zip={date}_{type}.zip, csv={date}_symbol_resolution_{type}.csv
        For hour/daily: zip={symbol}_{type}.zip, csv={symbol}.csv
        """
        output_path.mkdir(parents=True, exist_ok=True)
        
        zip_filename = f"{filename_base}_{data_type}.zip"
        
        # For hour/daily, CSV filename is just symbol.csv
        if resolution in (self.RESOLUTION_HOUR, self.RESOLUTION_DAILY):
            csv_filename = f"{filename_base}.csv"
        else:
            csv_filename = f"{filename_base}_{data_type}.csv"
        
        zip_path = output_path / zip_filename
        
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(csv_filename, csv_content)
        
        return zip_path
    
    def convert(
        self,
        data: KlineData,
        data_type: str = "trade",
    ) -> List[Path]:
        """
        Convert KlineData to Lean format.
        
        For minute data: Creates date-based files (YYYYMMDD_trade.zip)
        For hour/daily: Creates single consolidated file (symbol_trade.zip)
        
        Args:
            data: KlineData to convert
            data_type: Type of data (trade, quote, etc.)
        
        Returns:
            List of created file paths
        """
        if not data.bars:
            logger.warning("No bars to convert")
            return []
        
        resolution = self._get_lean_resolution(data.interval)
        lean_symbol = self._get_lean_symbol(data.symbol)
        
        created_files: List[Path] = []
        
        # For hour and daily resolution, Lean expects a single consolidated file
        # in the resolution folder (not in a symbol subfolder)
        if resolution in (self.RESOLUTION_HOUR, self.RESOLUTION_DAILY):
            output_path = self._get_output_path(data.symbol, resolution, use_symbol_folder=False)
            
            # Create both trade and quote files (Lean needs both)
            for dtype in ["trade", "quote"]:
                # Create CSV content with appropriate format
                csv_content = self._create_csv_content(data.bars, resolution, dtype)
                zip_path = self._create_zip_file(
                    csv_content,
                    output_path,
                    lean_symbol,  # Use symbol as filename base
                    dtype,
                    resolution,
                )
                created_files.append(zip_path)
                logger.debug(f"Created {zip_path} with {len(data.bars)} bars")
        
        else:
            # For minute data, create date-based files in symbol subfolder
            output_path = self._get_output_path(data.symbol, resolution, use_symbol_folder=True)
            grouped = self._group_bars_by_date(data.bars)
            
            for date_str, bars in grouped.items():
                csv_content = self._create_csv_content(bars, resolution)
                zip_path = self._create_zip_file(
                    csv_content,
                    output_path,
                    date_str,  # Use date as filename base
                    data_type,
                )
                created_files.append(zip_path)
                logger.debug(f"Created {zip_path} with {len(bars)} bars")
        
        logger.info(
            f"Converted {len(data)} bars to {len(created_files)} Lean files "
            f"for {data.symbol} ({resolution})"
        )
        
        return created_files
    
    def convert_to_single_csv(
        self,
        data: KlineData,
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        Convert KlineData to a single CSV file (for debugging/inspection).
        
        Args:
            data: KlineData to convert
            output_path: Output file path (optional)
        
        Returns:
            Path to created CSV file
        """
        if output_path is None:
            output_path = (
                self.output_dir
                / f"{data.symbol}_{data.interval}_all.csv"
            )
        
        resolution = self._get_lean_resolution(data.interval)
        csv_content = self._create_csv_content(data.bars, resolution)
        
        # Add header
        header = "Time,Open,High,Low,Close,Volume\n"
        full_content = header + csv_content
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(full_content)
        
        logger.info(f"Created single CSV: {output_path}")
        return output_path
    
    def get_lean_data_path(self, symbol: str, resolution: str) -> Path:
        """Get the Lean data directory path for a symbol."""
        lean_symbol = self._get_lean_symbol(symbol)
        return (
            self.output_dir
            / "crypto"
            / "binance"
            / resolution
            / lean_symbol
        )
    
    def list_converted_data(self) -> List[dict]:
        """List all converted Lean data files."""
        results = []
        
        crypto_dir = self.output_dir / "crypto" / "binance"
        if not crypto_dir.exists():
            return results
        
        for resolution_dir in crypto_dir.iterdir():
            if not resolution_dir.is_dir():
                continue
            
            resolution = resolution_dir.name
            
            for symbol_dir in resolution_dir.iterdir():
                if not symbol_dir.is_dir():
                    continue
                
                symbol = symbol_dir.name.upper()
                zip_files = list(symbol_dir.glob("*.zip"))
                
                if zip_files:
                    dates = [f.stem.split("_")[0] for f in zip_files]
                    results.append({
                        "symbol": symbol,
                        "resolution": resolution,
                        "file_count": len(zip_files),
                        "date_range": f"{min(dates)} - {max(dates)}",
                        "path": str(symbol_dir),
                    })
        
        return results
    
    def clean_converted_data(
        self,
        symbol: Optional[str] = None,
        resolution: Optional[str] = None,
    ) -> int:
        """
        Remove converted Lean data files.
        
        Args:
            symbol: Filter by symbol (optional)
            resolution: Filter by resolution (optional)
        
        Returns:
            Number of files deleted
        """
        deleted = 0
        crypto_dir = self.output_dir / "crypto" / "binance"
        
        if not crypto_dir.exists():
            return 0
        
        for resolution_dir in crypto_dir.iterdir():
            if not resolution_dir.is_dir():
                continue
            
            if resolution and resolution_dir.name != resolution:
                continue
            
            for symbol_dir in resolution_dir.iterdir():
                if not symbol_dir.is_dir():
                    continue
                
                if symbol and symbol_dir.name.upper() != symbol.upper():
                    continue
                
                for zip_file in symbol_dir.glob("*.zip"):
                    zip_file.unlink()
                    deleted += 1
                
                # Remove empty directories
                if not any(symbol_dir.iterdir()):
                    symbol_dir.rmdir()
        
        return deleted
