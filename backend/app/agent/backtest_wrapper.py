"""
Wrapper around the backtesting CLI for programmatic use.

This provides a simple async interface to run backtests without going through
the CLI. Used by the compile node in the agent graph.
"""

import asyncio
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BacktestCLIWrapper:
    """Wrapper for running backtests via CLI."""
    
    def __init__(self, backtesting_dir: Optional[Path] = None):
        """
        Initialize wrapper.
        
        Args:
            backtesting_dir: Path to backtesting module root (auto-detected if None)
        """
        if backtesting_dir is None:
            # Auto-detect: backend/../backtesting
            backend_dir = Path(__file__).parent.parent.parent
            backtesting_dir = backend_dir.parent / "backtesting"
        
        self.backtesting_dir = backtesting_dir
        logger.info(f"Backtesting directory: {self.backtesting_dir}")
    
    async def run_backtest(
        self,
        strategy_code: str,
        symbol: str,
        interval: str,
        start_date: str,
        end_date: str,
        initial_capital: float
    ) -> Dict[str, Any]:
        """
        Run backtest with given strategy code.
        
        Args:
            strategy_code: Complete Lean QuantConnect strategy Python code
            symbol: Trading pair (e.g., BTCUSDT)
            interval: Timeframe (e.g., 1h, 4h, 1d)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            initial_capital: Starting capital in USDT
        
        Returns:
            Dict with success, metrics, and error messages
        """
        # Save strategy to temp file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False,
            dir=self.backtesting_dir / "strategies"
        ) as f:
            f.write(strategy_code)
            strategy_file = Path(f.name)
        
        try:
            logger.info(f"Running backtest: {symbol} {interval} {start_date} to {end_date}")
            logger.info(f"Strategy file: {strategy_file}")
            
            # Build command
            cmd = [
                "python3", "-m", "backtesting.cli", "backtest",
                "--symbol", symbol,
                "--interval", interval,
                "--start", start_date,
                "--end", end_date,
                "--strategy-file", str(strategy_file),
                "--initial-capital", str(initial_capital),
                "--output-format", "json"
            ]
            
            # Run command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.backtesting_dir.parent)
            )
            
            stdout, stderr = await process.communicate()
            
            # Parse output
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"Backtest failed: {error_msg}")
                
                return {
                    "success": False,
                    "error_message": error_msg,
                    "error_stage": "execution",
                    "metrics": {}
                }
            
            # Parse JSON output
            try:
                output = stdout.decode()
                
                # Try to extract JSON from output
                # CLI might print logs before JSON
                json_start = output.find("{")
                json_end = output.rfind("}") + 1
                
                if json_start >= 0 and json_end > json_start:
                    result_json = output[json_start:json_end]
                    result = json.loads(result_json)
                else:
                    # No JSON found, return raw output
                    result = {"raw_output": output}
                
                logger.info("Backtest completed successfully")
                
                return {
                    "success": True,
                    "metrics": result.get("metrics", {}),
                    "report": result,
                    "error_message": None
                }
                
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON output: {e}")
                # Return success with raw output
                return {
                    "success": True,
                    "metrics": {},
                    "raw_output": stdout.decode(),
                    "error_message": None
                }
        
        finally:
            # Clean up temp file
            try:
                strategy_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete temp file {strategy_file}: {e}")


async def test_wrapper():
    """Test the wrapper with a simple strategy."""
    print("Testing BacktestCLIWrapper...")
    
    wrapper = BacktestCLIWrapper()
    
    # Simple RSI strategy
    strategy_code = '''from AlgorithmImports import *

class TestStrategy(QCAlgorithm):
    def initialize(self):
        self.set_start_date(2025, 1, 1)
        self.set_end_date(2025, 12, 1)
        self.set_account_currency("USDT")
        self.set_cash("USDT", 100000, 1.0)
        self.set_brokerage_model(BrokerageName.BINANCE, AccountType.CASH)
        self.symbol = self.add_crypto("BTCUSDT", Resolution.Hour).symbol
        self.rsi = self.RSI(self.symbol, 14)
        self.set_warm_up(280, Resolution.Hour)
    
    def on_data(self, data):
        if not data.contains_key(self.symbol):
            return
        if not self.rsi.is_ready:
            return
        if self.rsi.current.value < 30 and not self.portfolio.invested:
            self.set_holdings(self.symbol, 1.0)
        elif self.rsi.current.value > 70 and self.portfolio.invested:
            self.liquidate()
'''
    
    result = await wrapper.run_backtest(
        strategy_code=strategy_code,
        symbol="BTCUSDT",
        interval="1h",
        start_date="2025-09-01",
        end_date="2025-12-01"
    )
    
    print(f"\nResult: {json.dumps(result, indent=2)}")
    
    if result["success"]:
        print("\n✅ Wrapper test passed!")
    else:
        print(f"\n❌ Wrapper test failed: {result.get('error_message')}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_wrapper())
