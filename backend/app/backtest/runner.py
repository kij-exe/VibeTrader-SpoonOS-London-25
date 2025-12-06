"""
Backtest Runner

CLI and programmatic interface for running backtests.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from app.backtest.data_loader import DataLoader
from app.backtest.engine import BacktestConfig, BacktestEngine, BacktestResult
from app.strategy.interface import BaseStrategy, StrategyConfig, OHLCV
from app.strategy.examples import get_strategy, STRATEGY_REGISTRY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BacktestRunner:
    """
    High-level interface for running backtests.
    
    Supports running single strategies or comparing multiple strategies.
    """
    
    def __init__(
        self,
        initial_capital: float = 10000.0,
        commission_rate: float = 0.001,
        slippage_rate: float = 0.0005,
    ):
        self.backtest_config = BacktestConfig(
            initial_capital=initial_capital,
            commission_rate=commission_rate,
            slippage_rate=slippage_rate,
        )
        self.engine = BacktestEngine(self.backtest_config)
    
    async def run_strategy(
        self,
        strategy: BaseStrategy,
        data: List[OHLCV],
        strategy_params: Optional[Dict[str, Any]] = None,
    ) -> BacktestResult:
        """
        Run a single strategy backtest.
        
        Args:
            strategy: Strategy instance
            data: Historical data
            strategy_params: Custom strategy parameters
        
        Returns:
            BacktestResult
        """
        if not data:
            raise ValueError("No data provided")
        
        symbol = data[0].symbol
        
        config = StrategyConfig(
            symbol=symbol,
            initial_capital=self.backtest_config.initial_capital,
            parameters=strategy_params or {},
        )
        
        result = await self.engine.run(strategy, data, config)
        return result
    
    async def run_by_name(
        self,
        strategy_name: str,
        data: List[OHLCV],
        strategy_params: Optional[Dict[str, Any]] = None,
    ) -> BacktestResult:
        """
        Run a backtest by strategy name.
        
        Args:
            strategy_name: Name from strategy registry
            data: Historical data
            strategy_params: Custom parameters
        
        Returns:
            BacktestResult
        """
        strategy = get_strategy(strategy_name)
        return await self.run_strategy(strategy, data, strategy_params)
    
    async def compare_strategies(
        self,
        strategy_names: List[str],
        data: List[OHLCV],
        strategy_params: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, BacktestResult]:
        """
        Run multiple strategies on the same data for comparison.
        
        Args:
            strategy_names: List of strategy names to compare
            data: Historical data
            strategy_params: Dict mapping strategy name to parameters
        
        Returns:
            Dict mapping strategy name to results
        """
        results = {}
        params = strategy_params or {}
        
        for name in strategy_names:
            strategy = get_strategy(name)
            result = await self.run_strategy(
                strategy, data, params.get(name, {})
            )
            results[name] = result
            logger.info(f"{name}: Return={result.metrics.total_return_percent:.2f}%")
        
        return results
    
    def print_results(self, result: BacktestResult) -> None:
        """Print formatted backtest results"""
        m = result.metrics
        
        print("\n" + "=" * 60)
        print(f"  BACKTEST RESULTS: {result.strategy_name} v{result.strategy_version}")
        print("=" * 60)
        print(f"\n  Period: {result.start_time} to {result.end_time}")
        print(f"  Initial Capital: ${self.backtest_config.initial_capital:,.2f}")
        
        # Show final equity from curve
        if result.equity_curve:
            final = result.equity_curve[-1]
            print(f"  Final Equity:    ${final['equity']:,.2f}")
            print(f"  Final Cash:      ${final['cash']:,.2f}")
            print(f"  Positions Value: ${final['positions_value']:,.2f}")
        
        print("\n  RETURNS")
        print(f"    Total Return:      ${m.total_return:,.2f} ({m.total_return_percent:+.2f}%)")
        
        print("\n  RISK METRICS")
        print(f"    Sharpe Ratio:      {m.sharpe_ratio:.2f}")
        print(f"    Max Drawdown:      ${m.max_drawdown:,.2f} ({m.max_drawdown_percent:.2f}%)")
        print(f"    Volatility:        {m.volatility:.2f}%")
        
        print("\n  TRADE STATISTICS")
        print(f"    Total Trades:      {m.total_trades}")
        print(f"    Winning Trades:    {m.winning_trades}")
        print(f"    Losing Trades:     {m.losing_trades}")
        print(f"    Win Rate:          {m.win_rate:.1f}%")
        
        if m.total_trades > 0:
            print(f"    Avg Win:           ${m.average_win:,.2f}")
            print(f"    Avg Loss:          ${m.average_loss:,.2f}")
            print(f"    Profit Factor:     {m.profit_factor:.2f}")
            print(f"    Expectancy:        ${m.expectancy:,.2f}")
        
        print("\n" + "=" * 60 + "\n")
    
    def results_to_json(self, result: BacktestResult) -> str:
        """Convert results to JSON string"""
        return json.dumps(result.to_dict(), indent=2, default=str)


async def demo_backtest():
    """
    Demonstration of the backtest system.
    
    Generates sample data and runs example strategies.
    """
    print("\n" + "=" * 60)
    print("  VIBETRADER BACKTEST DEMO")
    print("=" * 60 + "\n")
    
    # Generate sample data
    start_date = datetime(2024, 1, 1)
    
    print("Generating sample market data...")
    
    # Trending market
    trending_data = DataLoader.generate_trending(
        symbol="BTC/USDC",
        start_date=start_date,
        periods=500,
        timeframe_minutes=60,
        initial_price=40000,
        trend_direction="up",
        trend_strength=0.0005,
        volatility=0.015,
        seed=42,
    )
    
    # Ranging market
    ranging_data = DataLoader.generate_ranging(
        symbol="ETH/USDC",
        start_date=start_date,
        periods=500,
        timeframe_minutes=60,
        center_price=2000,
        range_percent=0.08,
        volatility=0.012,
        seed=123,
    )
    
    # Create runner
    runner = BacktestRunner(initial_capital=10000)
    
    # Test momentum strategy on trending market
    print("\n--- Momentum Strategy on Trending Market ---")
    result = await runner.run_by_name(
        "simple_momentum",
        trending_data,
        {"lookback_period": 10, "entry_threshold": 0.003, "exit_threshold": -0.003}
    )
    runner.print_results(result)
    
    # Test mean reversion on ranging market
    print("\n--- Mean Reversion Strategy on Ranging Market ---")
    result = await runner.run_by_name(
        "mean_reversion",
        ranging_data,
        {"lookback_period": 15, "entry_zscore": -1.0, "exit_zscore": 0.5}
    )
    runner.print_results(result)
    
    # Compare all strategies on trending data
    print("\n--- Strategy Comparison (Trending Market) ---")
    all_strategies = list(STRATEGY_REGISTRY.keys())
    comparison = await runner.compare_strategies(all_strategies, trending_data)
    
    print("\n  Summary:")
    print("  " + "-" * 50)
    for name, res in sorted(
        comparison.items(),
        key=lambda x: x[1].metrics.total_return_percent,
        reverse=True
    ):
        m = res.metrics
        print(f"  {name:20s} Return: {m.total_return_percent:+7.2f}%  "
              f"Sharpe: {m.sharpe_ratio:5.2f}  Trades: {m.total_trades:3d}")
    
    print("\n  Best strategy:", max(
        comparison.items(),
        key=lambda x: x[1].metrics.total_return_percent
    )[0])


if __name__ == "__main__":
    asyncio.run(demo_backtest())
