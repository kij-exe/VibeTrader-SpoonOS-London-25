"""
Lean Engine Runner.

Executes backtests using Lean QuantConnect engine via Docker or CLI.
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config.settings import get_settings, LeanConfig


logger = logging.getLogger(__name__)


@dataclass
class LeanBacktestConfig:
    """Configuration for a Lean backtest run."""
    strategy_file: Path
    data_dir: Path
    output_dir: Path
    
    # Algorithm settings
    initial_capital: float = 100000.0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Execution settings
    timeout_seconds: int = 300
    
    # Additional config
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LeanBacktestResult:
    """Result from a Lean backtest execution."""
    success: bool
    strategy_name: str
    
    # Timing
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    
    # Output paths
    results_file: Optional[Path] = None
    log_file: Optional[Path] = None
    
    # Raw results
    statistics: Dict[str, Any] = field(default_factory=dict)
    runtime_statistics: Dict[str, Any] = field(default_factory=dict)
    
    # Errors
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "strategy_name": self.strategy_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": self.duration_seconds,
            "results_file": str(self.results_file) if self.results_file else None,
            "statistics": self.statistics,
            "runtime_statistics": self.runtime_statistics,
            "error_message": self.error_message,
        }


class LeanRunner:
    """
    Runs Lean backtests via Docker or local installation.
    
    Supports two modes:
    1. Docker mode: Uses quantconnect/lean Docker image
    2. Local mode: Uses locally installed Lean CLI
    """
    
    def __init__(
        self,
        config: Optional[LeanConfig] = None,
        use_docker: bool = True,
    ):
        settings = get_settings()
        self.config = config or settings.lean
        self.use_docker = use_docker
        self.paths = settings.paths
    
    def _check_docker(self) -> bool:
        """Check if Docker is available and running."""
        try:
            # Check if docker command exists
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return False
            
            # Check if Docker daemon is running
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                logger.warning("Docker daemon is not running")
                return False
            
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    async def run_backtest_docker(
        self,
        backtest_config: LeanBacktestConfig,
    ) -> LeanBacktestResult:
        """
        Run backtest using Docker.
        
        Args:
            backtest_config: Backtest configuration
        
        Returns:
            LeanBacktestResult
        """
        start_time = datetime.now()
        strategy_name = backtest_config.strategy_file.stem
        
        # Create temporary working directory
        temp_dir = tempfile.mkdtemp()
        work_dir = Path(temp_dir)
        
        try:
            # Copy strategy file
            strategy_dest = work_dir / backtest_config.strategy_file.name
            shutil.copy(backtest_config.strategy_file, strategy_dest)
            
            # Ensure output directory exists
            backtest_config.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Build Docker command
            # Lean expects: algorithm file, data folder, results folder
            docker_cmd = [
                "docker", "run", "--rm",
                "-v", f"{work_dir}:/Algorithm",
                "-v", f"{backtest_config.data_dir}:/Data",
                "-v", f"{backtest_config.output_dir}:/Results",
                self.config.docker_image,
                "--algorithm-location", f"/Algorithm/{strategy_dest.name}",
                "--algorithm-language", "Python",
                "--data-folder", "/Data",
                "--results-destination-folder", "/Results",
                "--close-automatically", "true",
            ]
            
            logger.info(f"Running Docker backtest for {strategy_name}")
            logger.debug(f"Docker command: {' '.join(docker_cmd)}")
            
            try:
                # Run Docker container
                process = await asyncio.create_subprocess_exec(
                    *docker_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=backtest_config.timeout_seconds,
                    )
                except asyncio.TimeoutError:
                    process.kill()
                    return LeanBacktestResult(
                        success=False,
                        strategy_name=strategy_name,
                        start_time=start_time,
                        end_time=datetime.now(),
                        duration_seconds=(datetime.now() - start_time).total_seconds(),
                        error_message=f"Backtest timed out after {backtest_config.timeout_seconds}s",
                    )
                
                end_time = datetime.now()
                
                if process.returncode != 0:
                    error_msg = stderr.decode() if stderr else "Unknown error"
                    return LeanBacktestResult(
                        success=False,
                        strategy_name=strategy_name,
                        start_time=start_time,
                        end_time=end_time,
                        duration_seconds=(end_time - start_time).total_seconds(),
                        error_message=error_msg,
                    )
                
                # Parse results
                return self._parse_results(
                    strategy_name=strategy_name,
                    output_dir=backtest_config.output_dir,
                    start_time=start_time,
                    end_time=end_time,
                )
                
            except Exception as e:
                logger.error(f"Docker backtest failed: {e}")
                return LeanBacktestResult(
                    success=False,
                    strategy_name=strategy_name,
                    start_time=start_time,
                    end_time=datetime.now(),
                    duration_seconds=(datetime.now() - start_time).total_seconds(),
                    error_message=str(e),
                )
        finally:
            # Clean up temp directory, ignoring permission errors from Docker
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                logger.debug(f"Failed to clean up temp directory {temp_dir}: {e}")
    
    def _parse_results(
        self,
        strategy_name: str,
        output_dir: Path,
        start_time: datetime,
        end_time: datetime,
    ) -> LeanBacktestResult:
        """Parse Lean backtest results from output directory."""
        # Look for main results file (contains orders for accurate trade counting)
        # Exclude summary, order-events, and data-monitor files
        all_json = list(output_dir.glob("*.json"))
        results_files = [
            f for f in all_json 
            if not any(x in f.name for x in ["summary", "order-events", "data-monitor"])
        ]
        
        # Fallback to summary if main file not found
        if not results_files:
            results_files = list(output_dir.glob("*-summary.json"))
        
        statistics = {}
        runtime_statistics = {}
        results_file = None
        
        if results_files:
            results_file = results_files[0]
            try:
                with open(results_file, "r") as f:
                    data = json.load(f)
                
                # Handle both summary format and main results format
                if isinstance(data, dict):
                    statistics = data.get("statistics", data.get("Statistics", {}))
                    runtime_statistics = data.get("runtimeStatistics", data.get("RuntimeStatistics", {}))
                
            except Exception as e:
                logger.warning(f"Failed to parse results file: {e}")
        
        # Look for log file
        log_files = list(output_dir.glob("*.log"))
        log_file = log_files[0] if log_files else None
        
        return LeanBacktestResult(
            success=True,
            strategy_name=strategy_name,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=(end_time - start_time).total_seconds(),
            results_file=results_file,
            log_file=log_file,
            statistics=statistics,
            runtime_statistics=runtime_statistics,
        )
    
    async def run_backtest(
        self,
        backtest_config: LeanBacktestConfig,
    ) -> LeanBacktestResult:
        """
        Run backtest using Docker.
        
        Args:
            backtest_config: Backtest configuration
        
        Returns:
            LeanBacktestResult
        """
        if not self._check_docker():
            raise RuntimeError(
                "Docker is not available. Please ensure Docker is installed and running."
            )
        return await self.run_backtest_docker(backtest_config)
