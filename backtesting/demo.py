#!/usr/bin/env python3
"""
Backtesting Demo Script.

Demonstrates the backtesting pipeline with a simple example.
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backtesting.agent import BacktestingAgent, BacktestRequest
from backtesting.data import BinanceDataFetcher, LeanDataConverter, DataFileManager
from backtesting.config import get_settings


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def demo_fetch_data():
    """Demo: Fetch data from Binance."""
    print("\n" + "=" * 60)
    print("  DEMO: Fetching Data from Binance")
    print("=" * 60)
    
    async with BinanceDataFetcher() as fetcher:
        # Fetch 1 month of 4h data for BTCUSDT
        data = await fetcher.fetch_klines(
            symbol="BTCUSDT",
            interval="4h",
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 2, 1),
        )
    
    print(f"\n✅ Fetched {len(data)} bars")
    print(f"   Symbol: {data.symbol}")
    print(f"   Interval: {data.interval}")
    print(f"   First bar: {data.bars[0].open_datetime}")
    print(f"   Last bar: {data.bars[-1].open_datetime}")
    
    # Show sample data
    print("\n   Sample bars:")
    for bar in data.bars[:3]:
        print(f"   {bar.open_datetime}: O={bar.open:.2f} H={bar.high:.2f} "
              f"L={bar.low:.2f} C={bar.close:.2f} V={bar.volume:.0f}")
    
    return data


async def demo_convert_data(data):
    """Demo: Convert data to Lean format."""
    print("\n" + "=" * 60)
    print("  DEMO: Converting to Lean Format")
    print("=" * 60)
    
    converter = LeanDataConverter()
    files = converter.convert(data)
    
    print(f"\n✅ Created {len(files)} Lean data files")
    for f in files[:5]:
        print(f"   {f}")
    
    # Also create a single CSV for inspection
    csv_path = converter.convert_to_single_csv(data)
    print(f"\n   Debug CSV: {csv_path}")
    
    return files


async def demo_cache_management():
    """Demo: Cache management."""
    print("\n" + "=" * 60)
    print("  DEMO: Cache Management")
    print("=" * 60)
    
    manager = DataFileManager()
    
    # List cached data
    cached = manager.list_cached()
    print(f"\n📁 Cached files: {len(cached)}")
    
    for item in cached[:5]:
        size_kb = item["size_bytes"] / 1024
        print(f"   {item['symbol']} {item['interval']}: "
              f"{item['start_date']}-{item['end_date']} ({size_kb:.1f} KB)")
    
    # Show stats
    stats = manager.get_cache_stats()
    print(f"\n📊 Cache stats:")
    print(f"   Total files: {stats['total_files']}")
    print(f"   Total size: {stats['total_size_mb']:.2f} MB")


async def demo_full_backtest():
    """Demo: Full backtest pipeline."""
    print("\n" + "=" * 60)
    print("  DEMO: Full Backtest Pipeline")
    print("=" * 60)
    
    agent = BacktestingAgent()
    
    # Create request
    request = BacktestRequest(
        symbol="BTCUSDT",
        interval="4h",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 3, 1),
        initial_capital=100000.0,
        strategy_name="demo_rsi_strategy",
        parameters={
            "rsi_period": 14,
            "overbought": 70,
            "oversold": 30,
        },
    )
    
    print(f"\n🚀 Running backtest...")
    print(f"   Symbol: {request.symbol}")
    print(f"   Period: {request.start_date} to {request.end_date}")
    print(f"   Capital: ${request.initial_capital:,.2f}")
    
    # Run backtest
    response = await agent.run_backtest(request)
    
    # Show results
    print("\n" + "-" * 60)
    if response.success:
        print("✅ BACKTEST COMPLETED")
        
        summary = response.get_summary()
        print(f"\n📈 Summary:")
        for key, value in summary.get("summary", {}).items():
            print(f"   {key}: {value}")
        
        eval_scores = summary.get("evaluation", {})
        print(f"\n📊 Evaluation Scores:")
        print(f"   Performance: {eval_scores.get('performance_score', 'N/A')}/3")
        print(f"   Risk: {eval_scores.get('risk_score', 'N/A')}/3")
        print(f"   Consistency: {eval_scores.get('consistency_score', 'N/A')}/3")
        print(f"   Overall: {eval_scores.get('overall_score', 'N/A')}/3")
        
        if eval_scores.get("evaluation_text"):
            print(f"\n   💬 {eval_scores['evaluation_text']}")
        
        print(f"\n⏱️  Timing:")
        print(f"   Data fetch: {response.data_fetch_time:.1f}s")
        print(f"   Conversion: {response.conversion_time:.1f}s")
        print(f"   Execution: {response.execution_time:.1f}s")
        print(f"   Total: {response.total_time:.1f}s")
    else:
        print("❌ BACKTEST FAILED")
        print(f"   Error: {response.error_message}")
        print(f"   Stage: {response.error_stage}")
    
    return response


async def demo_agent_status():
    """Demo: Check agent status."""
    print("\n" + "=" * 60)
    print("  DEMO: Agent Status")
    print("=" * 60)
    
    agent = BacktestingAgent()
    status = agent.get_status()
    
    print(f"\n🤖 Agent: {status['agent']} v{status['version']}")
    
    print("\n📡 Capabilities:")
    print(f"   Data sources: {status['capabilities']['data_sources']}")
    print(f"   Intervals: {len(status['capabilities']['intervals'])} supported")
    
    methods = status['capabilities']['execution_methods']
    print("\n🐳 Execution methods:")
    for method, available in methods.items():
        icon = "✅" if available else "❌"
        print(f"   {icon} {method}")


async def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("  VIBETRADER BACKTESTING DEMO")
    print("=" * 60)
    
    try:
        # 1. Check status
        await demo_agent_status()
        
        # 2. Fetch data
        data = await demo_fetch_data()
        
        # 3. Convert data
        await demo_convert_data(data)
        
        # 4. Cache management
        await demo_cache_management()
        
        # 5. Full backtest
        await demo_full_backtest()
        
        print("\n" + "=" * 60)
        print("  DEMO COMPLETED SUCCESSFULLY")
        print("=" * 60 + "\n")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        print(f"\n❌ Demo failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
