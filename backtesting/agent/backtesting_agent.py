"""
Backtesting Agent.

Main orchestrator for the backtesting pipeline. Coordinates:
1. Data fetching from Binance
2. Strategy execution via Lean Engine (Docker)
3. Results parsing and reporting

This agent is designed to be called by other agents in the system
(e.g., after the compilation agent validates a strategy).
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..config.settings import get_settings
from ..config.intervals import BinanceInterval
from ..data.fetcher.binance_client import BinanceDataFetcher
from ..data.converter.lean_converter import LeanDataConverter
from ..data.storage.file_manager import DataFileManager
from ..data.models import KlineData
from ..engine.lean_runner import LeanRunner, LeanBacktestConfig
from ..results.parser import ResultsParser
from ..results.models import BacktestReport
from ..utils.time_utils import timestamp_to_ms, ms_to_timestamp


logger = logging.getLogger(__name__)


@dataclass
class BacktestRequest:
    """
    Request to run a backtest.
    
    Can be created from user input or programmatically by other agents.
    """
    # Strategy definition
    strategy_code: Optional[str] = None      # Raw Python code for strategy
    strategy_file: Optional[Path] = None     # Path to strategy file
    strategy_name: str = "custom_strategy"
    
    # Symbol and timeframe
    symbol: str = "BTCUSDT"
    interval: str = "1h"
    
    # Date range
    start_date: Union[datetime, str] = None
    end_date: Union[datetime, str] = None
    
    # Capital and settings
    initial_capital: float = 100000.0
    
    # Strategy parameters (passed to strategy)
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Options
    use_cached_data: bool = True
    force_data_refresh: bool = False
    
    # Request metadata
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    def __post_init__(self):
        # Set default dates if not provided
        if self.start_date is None:
            # Default to 6 months ago
            self.start_date = datetime(2024, 1, 1)
        if self.end_date is None:
            self.end_date = datetime(2024, 6, 1)
        
        # Convert string dates
        if isinstance(self.start_date, str):
            self.start_date = datetime.fromisoformat(self.start_date)
        if isinstance(self.end_date, str):
            self.end_date = datetime.fromisoformat(self.end_date)


@dataclass
class BacktestResponse:
    """
    Response from a backtest run.
    
    Contains the full report plus metadata about the execution.
    """
    request_id: str
    success: bool
    
    # Results
    report: Optional[BacktestReport] = None
    results_dir: Optional[Path] = None  # Path to results folder for this specific run
    
    # Execution details
    data_fetch_time: float = 0.0
    conversion_time: float = 0.0
    execution_time: float = 0.0
    total_time: float = 0.0
    
    # Data info
    bars_fetched: int = 0
    data_source: str = "binance"
    used_cache: bool = False
    
    # Errors
    error_message: Optional[str] = None
    error_stage: Optional[str] = None  # "data_fetch", "conversion", "execution", "parsing"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "request_id": self.request_id,
            "success": self.success,
            "report": self.report.to_dict() if self.report else None,
            "results_dir": str(self.results_dir) if self.results_dir else None,
            "execution": {
                "data_fetch_time": self.data_fetch_time,
                "conversion_time": self.conversion_time,
                "execution_time": self.execution_time,
                "total_time": self.total_time,
            },
            "data": {
                "bars_fetched": self.bars_fetched,
                "data_source": self.data_source,
                "used_cache": self.used_cache,
            },
            "error": {
                "message": self.error_message,
                "stage": self.error_stage,
            } if self.error_message else None,
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a condensed summary for quick display."""
        if not self.success:
            return {
                "success": False,
                "error": self.error_message,
                "stage": self.error_stage,
            }
        
        return {
            "success": True,
            "summary": self.report.to_summary() if self.report else {},
            "evaluation": self.report.get_evaluation_score() if self.report else {},
            "total_time": f"{self.total_time:.1f}s",
        }


class BacktestingAgent:
    """
    Main backtesting agent that orchestrates the entire pipeline.
    
    Usage:
        agent = BacktestingAgent()
        
        request = BacktestRequest(
            strategy_code="...",
            symbol="BTCUSDT",
            interval="4h",
            start_date="2024-01-01",
            end_date="2024-06-01",
        )
        
        response = await agent.run_backtest(request)
        print(response.report.to_summary())
    """
    
    def __init__(self):
        """Initialize the backtesting agent."""
        self.settings = get_settings()
        self.data_manager = DataFileManager()
        self.converter = LeanDataConverter()
        self.lean_runner = LeanRunner()
        self.results_parser = ResultsParser()
    
    async def run_backtest(self, request: BacktestRequest) -> BacktestResponse:
        """
        Run a complete backtest pipeline.
        
        Steps:
        1. Fetch historical data from Binance (or use cache)
        2. Convert data to Lean format
        3. Execute backtest via Lean Engine (Docker)
        4. Parse and return results
        
        Args:
            request: BacktestRequest with all parameters
        
        Returns:
            BacktestResponse with results or error
        """
        start_time = datetime.now()
        
        logger.info(
            f"Starting backtest {request.request_id}: "
            f"{request.symbol} {request.interval} "
            f"{request.start_date} to {request.end_date}"
        )
        
        response = BacktestResponse(
            request_id=request.request_id,
            success=False,
        )
        
        try:
            # Step 1: Fetch data
            data_start = datetime.now()
            kline_data, used_cache = await self._fetch_data(request)
            response.data_fetch_time = (datetime.now() - data_start).total_seconds()
            response.bars_fetched = len(kline_data)
            response.used_cache = used_cache
            
            logger.info(f"Data fetched: {len(kline_data)} bars (cache={used_cache})")
            
            # Step 2: Convert data and run Lean backtest
            exec_start = datetime.now()
            
            convert_start = datetime.now()
            lean_data_path = await self._convert_data(kline_data)
            response.conversion_time = (datetime.now() - convert_start).total_seconds()
            logger.info(f"Data converted to Lean format: {lean_data_path}")
            
            strategy_file = await self._prepare_strategy(request)
            logger.info(f"Strategy prepared: {strategy_file}")
            
            result, output_dir = await self._execute_lean_backtest(request, strategy_file, lean_data_path)
            
            response.execution_time = (datetime.now() - exec_start).total_seconds()
            response.results_dir = output_dir  # Store the exact results folder
            
            if not result.success:
                response.error_message = result.error_message
                response.error_stage = "execution"
                return response
            
            # Step 3: Parse results
            report = self._parse_results(result, request)
            
            response.success = True
            response.report = report
            
        except Exception as e:
            logger.error(f"Backtest failed: {e}", exc_info=True)
            response.error_message = str(e)
            response.error_stage = "unknown"
        
        finally:
            response.total_time = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"Backtest {request.request_id} completed in {response.total_time:.1f}s "
                f"(success={response.success})"
            )
        
        return response
    
    async def _fetch_data(
        self,
        request: BacktestRequest,
    ) -> tuple[KlineData, bool]:
        """Fetch historical data from Binance or cache."""
        start_ms = timestamp_to_ms(request.start_date)
        end_ms = timestamp_to_ms(request.end_date)
        
        # Check cache first
        if request.use_cached_data and not request.force_data_refresh:
            cached = self.data_manager.find_cached(
                request.symbol,
                request.interval,
                start_ms,
                end_ms,
            )
            if cached:
                return cached, True
        
        # Fetch from Binance
        async with BinanceDataFetcher() as fetcher:
            data = await fetcher.fetch_klines(
                symbol=request.symbol,
                interval=request.interval,
                start_time=start_ms,
                end_time=end_ms,
            )
        
        # Save to cache
        self.data_manager.save(data)
        
        return data, False
    
    async def _convert_data(self, data: KlineData) -> Path:
        """Convert kline data to Lean format."""
        # Convert and get the data directory
        self.converter.convert(data)
        
        # Return the Lean data root directory
        return self.settings.paths.lean_data_dir
    
    async def _prepare_strategy(self, request: BacktestRequest) -> Path:
        """Prepare strategy file for execution."""
        # If strategy file is provided, patch it with CLI parameters
        if request.strategy_file:
            if not request.strategy_file.exists():
                raise RuntimeError(
                    f"Strategy file not found: {request.strategy_file}"
                )
            return self._patch_strategy_file(request)
        
        # If strategy code is provided, patch it and write to a file
        if request.strategy_code:
            patched_code = self._patch_strategy_code(request.strategy_code, request)
            strategy_file = (
                self.settings.paths.strategies_dir
                / f"{request.strategy_name}_{request.request_id}.py"
            )
            strategy_file.write_text(patched_code)
            logger.info(f"Patched strategy code: {request.symbol}, {request.interval}, {request.start_date} to {request.end_date}")
            return strategy_file
        
        # No strategy provided
        raise RuntimeError(
            "No valid strategy file provided. "
            "Use --strategy-file to specify a strategy file path."
        )
    
    # Supported intervals that map 1:1 to Lean resolutions AND are available on Binance
    # Note: 1s is not supported by Binance klines API
    SUPPORTED_INTERVALS = {
        "1m": "Minute",
        "1h": "Hour",
        "1d": "Daily",
    }
    
    def _validate_interval(self, interval: str) -> str:
        """Validate interval is supported and return Lean resolution."""
        if interval not in self.SUPPORTED_INTERVALS:
            supported = ", ".join(self.SUPPORTED_INTERVALS.keys())
            raise RuntimeError(
                f"Interval '{interval}' is not supported. "
                f"Only {supported} are supported by Lean. "
                f"Other intervals (e.g., 15m, 4h) would produce incorrect indicator calculations."
            )
        return self.SUPPORTED_INTERVALS[interval]
    
    def _patch_strategy_code(self, code: str, request: 'BacktestRequest') -> str:
        """Patch strategy code with request parameters (symbol, dates, capital, resolution)."""
        import re
        
        content = code
        
        # Validate and get Lean resolution
        lean_resolution = self._validate_interval(request.interval)
        
        # Patch symbol and resolution: replace AddCrypto/add_crypto("XXXUSDT", Resolution.XXX)
        content = re.sub(
            r'[Aa]dd_?[Cc]rypto\(["\']([A-Z]+USDT)["\'],\s*Resolution\.\w+\)',
            f'AddCrypto("{request.symbol}", Resolution.{lean_resolution})',
            content
        )
        
        # Patch start date: replace SetStartDate or set_start_date(YYYY, M, D) 
        content = re.sub(
            r'[Ss]et_?[Ss]tart_?[Dd]ate\(\d+,\s*\d+,\s*\d+\)',
            f'SetStartDate({request.start_date.year}, {request.start_date.month}, {request.start_date.day})',
            content
        )
        
        # Patch end date: replace SetEndDate or set_end_date(YYYY, M, D)
        content = re.sub(
            r'[Ss]et_?[Ee]nd_?[Dd]ate\(\d+,\s*\d+,\s*\d+\)',
            f'SetEndDate({request.end_date.year}, {request.end_date.month}, {request.end_date.day})',
            content
        )
        
        # Patch initial capital: replace SetCash/set_cash("USDT", XXXXX, 
        content = re.sub(
            r'[Ss]et_?[Cc]ash\(["\']USDT["\'],\s*\d+',
            f'SetCash("USDT", {int(request.initial_capital)}',
            content
        )
        
        # Patch warmup resolution: replace SetWarmUp/set_warm_up(..., Resolution.XXX)
        content = re.sub(
            r'[Ss]et_?[Ww]arm_?[Uu]p\(([^,]+),\s*Resolution\.\w+\)',
            f'SetWarmUp(\\1, Resolution.{lean_resolution})',
            content
        )
        
        # Patch RSI indicator resolution if present (handles both numeric and variable periods)
        # Match: .RSI(symbol, period, type, Resolution.XXX) or .RSI(symbol, period)
        content = re.sub(
            r'\.RSI\(([^,]+),\s*([^,]+),\s*[^,]+,\s*Resolution\.\w+\)',
            f'.RSI(\\1, \\2, MovingAverageType.Wilders, Resolution.{lean_resolution})',
            content
        )
        
        # Also patch simple RSI calls: .RSI(symbol, period) - add resolution
        # This handles cases where RSI is created without explicit resolution
        
        # Patch any remaining Resolution.XXX in indicator creation
        # This catches indicators like EMA, SMA, etc. that use Resolution
        content = re.sub(
            r'Resolution\.(Hour|Minute|Daily|Second)',
            f'Resolution.{lean_resolution}',
            content
        )
        
        return content
    
    def _patch_strategy_file(self, request: BacktestRequest) -> Path:
        """Patch a strategy file with CLI parameters (symbol, dates, capital, resolution)."""
        content = request.strategy_file.read_text()
        patched_content = self._patch_strategy_code(content, request)
        
        # Write patched file to temp location
        patched_file = (
            self.settings.paths.strategies_dir
            / f"{request.strategy_file.stem}_{request.request_id}.py"
        )
        patched_file.write_text(patched_content)
        
        logger.info(f"Patched strategy: {request.symbol}, {request.interval}, {request.start_date} to {request.end_date}")
        return patched_file
    
    async def _execute_lean_backtest(
        self,
        request: BacktestRequest,
        strategy_file: Path,
        data_dir: Path,
    ) -> tuple:
        """Execute backtest via Lean Engine (requires Docker).
        
        Returns:
            tuple: (LeanBacktestResult, output_dir Path)
        """
        output_dir = (
            self.settings.paths.results_dir
            / f"{request.strategy_name}_{request.request_id}"
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        
        config = LeanBacktestConfig(
            strategy_file=strategy_file,
            data_dir=data_dir,
            output_dir=output_dir,
            initial_capital=request.initial_capital,
            start_date=request.start_date,
            end_date=request.end_date,
            parameters=request.parameters,
        )
        
        result = await self.lean_runner.run_backtest(config)
        return result, output_dir
    
    def _parse_results(self, lean_result, request: BacktestRequest) -> BacktestReport:
        """Parse Lean results into BacktestReport."""
        if lean_result.results_file and lean_result.results_file.exists():
            report = self.results_parser.parse_file(lean_result.results_file)
        else:
            # Create report from statistics
            report = BacktestReport(
                strategy_name=request.strategy_name,
                symbol=request.symbol,
                initial_capital=request.initial_capital,
                start_date=request.start_date,
                end_date=request.end_date,
                raw_statistics=lean_result.statistics,
                raw_runtime_statistics=lean_result.runtime_statistics,
            )
            
            # Parse metrics from raw statistics
            report.metrics = self.results_parser._parse_metrics(
                lean_result.statistics,
                lean_result.runtime_statistics,
            )
        
        # Add execution info
        report.execution_time_seconds = lean_result.duration_seconds
        report.generated_at = datetime.now()
        
        return report
    
    async def run_quick_backtest(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "1h",
        days: int = 30,
        strategy_type: str = "rsi",
        **kwargs,
    ) -> BacktestResponse:
        """
        Run a quick backtest with minimal configuration.
        
        Convenience method for testing and demos.
        
        Args:
            symbol: Trading symbol
            interval: Kline interval
            days: Number of days to backtest
            strategy_type: Type of strategy ("rsi", "momentum", etc.)
            **kwargs: Additional strategy parameters
        
        Returns:
            BacktestResponse
        """
        end_date = datetime.now()
        start_date = datetime(
            end_date.year,
            end_date.month,
            end_date.day - days if end_date.day > days else 1,
        )
        
        request = BacktestRequest(
            symbol=symbol,
            interval=interval,
            start_date=start_date,
            end_date=end_date,
            strategy_name=f"{strategy_type}_quick",
            parameters=kwargs,
        )
        
        return await self.run_backtest(request)
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status and capabilities."""
        return {
            "agent": "BacktestingAgent",
            "version": "1.0.0",
            "capabilities": {
                "data_sources": ["binance"],
                "intervals": [i.value for i in BinanceInterval],
                "docker_available": self.lean_runner._check_docker(),
            },
            "cache_stats": self.data_manager.get_cache_stats(),
            "converted_data": self.converter.list_converted_data(),
        }


# Convenience function for direct usage
async def run_backtest(
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    start_date: Union[datetime, str] = None,
    end_date: Union[datetime, str] = None,
    strategy_code: Optional[str] = None,
    initial_capital: float = 100000.0,
    **kwargs,
) -> BacktestResponse:
    """
    Convenience function to run a backtest.
    
    Example:
        response = await run_backtest(
            symbol="BTCUSDT",
            interval="4h",
            start_date="2024-01-01",
            end_date="2024-06-01",
        )
        print(response.get_summary())
    """
    agent = BacktestingAgent()
    
    request = BacktestRequest(
        symbol=symbol,
        interval=interval,
        start_date=start_date,
        end_date=end_date,
        strategy_code=strategy_code,
        initial_capital=initial_capital,
        parameters=kwargs,
    )
    
    return await agent.run_backtest(request)
