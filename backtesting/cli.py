#!/usr/bin/env python3
"""
Backtesting CLI.

Command-line interface for running backtests and managing data.

Supported intervals: 1m, 1h, 1d (must match Lean resolutions AND Binance klines)

Usage:
    python -m backtesting.cli fetch --symbol BTCUSDT --interval 1h --start 2024-01-01 --end 2024-06-01
    python -m backtesting.cli backtest --symbol BTCUSDT --interval 1h --start 2024-01-01 --end 2024-06-01
    python -m backtesting.cli cache --list
    python -m backtesting.cli status
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backtesting.agent import BacktestingAgent, BacktestRequest
from backtesting.data import BinanceDataFetcher, LeanDataConverter, DataFileManager
from backtesting.config import get_settings, BinanceInterval


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def parse_date(date_str: str) -> datetime:
    """Parse date string to datetime."""
    formats = ["%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unable to parse date: {date_str}")


async def cmd_fetch(args):
    """Fetch historical data from Binance."""
    print(f"\n📊 Fetching {args.symbol} {args.interval} data...")
    print(f"   Period: {args.start} to {args.end}")
    
    start_date = parse_date(args.start)
    end_date = parse_date(args.end)
    
    async with BinanceDataFetcher() as fetcher:
        def progress(fetched, total):
            pct = (fetched / total * 100) if total > 0 else 0
            print(f"\r   Progress: {fetched}/{total} bars ({pct:.1f}%)", end="")
        
        data = await fetcher.fetch_klines(
            symbol=args.symbol,
            interval=args.interval,
            start_time=start_date,
            end_time=end_date,
            progress_callback=progress,
        )
    
    print(f"\n\n✅ Fetched {len(data)} bars")
    
    # Save to cache
    manager = DataFileManager()
    filepath = manager.save(data)
    print(f"💾 Saved to: {filepath}")
    
    # Convert to Lean format if requested
    if args.convert:
        print("\n🔄 Converting to Lean format...")
        converter = LeanDataConverter()
        files = converter.convert(data)
        print(f"✅ Created {len(files)} Lean data files")
    
    return data


async def cmd_backtest(args):
    """Run a backtest."""
    print(f"\n🚀 Running backtest...")
    print(f"   Symbol: {args.symbol}")
    print(f"   Interval: {args.interval}")
    print(f"   Period: {args.start} to {args.end}")
    print(f"   Capital: ${args.capital:,.2f}")
    print(f"   Strategy: {args.strategy or 'simple_momentum'}")
    
    agent = BacktestingAgent()
    
    # Build request
    request = BacktestRequest(
        symbol=args.symbol,
        interval=args.interval,
        start_date=parse_date(args.start),
        end_date=parse_date(args.end),
        initial_capital=args.capital,
        strategy_name=args.strategy or "simple_momentum",
        use_cached_data=not args.no_cache,
    )
    
    # Add strategy file if provided
    if args.strategy_file:
        request.strategy_file = Path(args.strategy_file)
    
    response = await agent.run_backtest(request)
    
    # Print results
    print("\n" + "=" * 60)
    if response.success:
        print("✅ BACKTEST COMPLETED SUCCESSFULLY")
        print("=" * 60)
        
        summary = response.get_summary()
        
        print(f"\n📈 Results Summary:")
        for key, value in summary.get("summary", {}).items():
            print(f"   {key}: {value}")
        
        print(f"\n📊 Evaluation:")
        eval_data = summary.get("evaluation", {})
        print(f"   Performance Score: {eval_data.get('performance_score', 'N/A')}/3")
        print(f"   Risk Score: {eval_data.get('risk_score', 'N/A')}/3")
        print(f"   Consistency Score: {eval_data.get('consistency_score', 'N/A')}/3")
        print(f"   Overall Score: {eval_data.get('overall_score', 'N/A')}/3")
        
        if eval_data.get("evaluation_text"):
            print(f"\n   {eval_data['evaluation_text']}")
        
        print(f"\n⏱️  Execution Time: {response.total_time:.1f}s")
        print(f"   - Data fetch: {response.data_fetch_time:.1f}s")
        print(f"   - Conversion: {response.conversion_time:.1f}s")
        print(f"   - Backtest: {response.execution_time:.1f}s")
        
        # Save results if requested
        if args.output:
            output_path = Path(args.output)
            with open(output_path, "w") as f:
                json.dump(response.to_dict(), f, indent=2, default=str)
            print(f"\n💾 Results saved to: {output_path}")
    
    else:
        print("❌ BACKTEST FAILED")
        print("=" * 60)
        print(f"\n   Error: {response.error_message}")
        print(f"   Stage: {response.error_stage}")
    
    return response


async def cmd_cache(args):
    """Manage data cache."""
    manager = DataFileManager()
    
    if args.list:
        print("\n📁 Cached Data Files:")
        cached = manager.list_cached()
        
        if not cached:
            print("   No cached data found.")
        else:
            for item in cached:
                size_mb = item["size_bytes"] / (1024 * 1024)
                print(f"   {item['symbol']} {item['interval']}: "
                      f"{item['start_date']} - {item['end_date']} "
                      f"({size_mb:.2f} MB)")
        
        stats = manager.get_cache_stats()
        print(f"\n   Total: {stats['total_files']} files, "
              f"{stats['total_size_mb']:.2f} MB")
    
    if args.clear:
        print("\n🗑️  Clearing cache...")
        deleted = manager.delete_cached(
            symbol=args.symbol,
            interval=args.interval,
        )
        print(f"   Deleted {deleted} files")
    
    if args.stats:
        stats = manager.get_cache_stats()
        print("\n📊 Cache Statistics:")
        print(f"   Total files: {stats['total_files']}")
        print(f"   Total size: {stats['total_size_mb']:.2f} MB")
        print(f"   Symbols: {', '.join(stats['symbols']) or 'None'}")
        print(f"   Intervals: {', '.join(stats['intervals']) or 'None'}")


async def cmd_convert(args):
    """Convert cached data to Lean format."""
    print(f"\n🔄 Converting data to Lean format...")
    
    manager = DataFileManager()
    converter = LeanDataConverter()
    
    # Find cached data
    cached = manager.list_cached(symbol=args.symbol, interval=args.interval)
    
    if not cached:
        print("   No cached data found matching criteria.")
        return
    
    total_files = 0
    for item in cached:
        filepath = Path(item["filepath"])
        data = manager.load(filepath)
        
        print(f"   Converting {item['symbol']} {item['interval']}...")
        files = converter.convert(data)
        total_files += len(files)
    
    print(f"\n✅ Created {total_files} Lean data files")


async def cmd_status(args):
    """Show system status."""
    agent = BacktestingAgent()
    status = agent.get_status()
    
    print("\n📊 Backtesting System Status")
    print("=" * 60)
    
    print(f"\n🤖 Agent: {status['agent']} v{status['version']}")
    
    print("\n📡 Data Sources:")
    for source in status["capabilities"]["data_sources"]:
        print(f"   - {source}")
    
    print("\n⏱️  Supported Intervals:")
    intervals = status["capabilities"]["intervals"]
    print(f"   {', '.join(intervals[:8])}...")
    
    print("\n🐳 Execution Methods:")
    methods = status["capabilities"]["execution_methods"]
    for method, available in methods.items():
        icon = "✅" if available else "❌"
        print(f"   {icon} {method}")
    
    print("\n💾 Cache Status:")
    cache = status["cache_stats"]
    print(f"   Files: {cache['total_files']}")
    print(f"   Size: {cache['total_size_mb']:.2f} MB")
    
    print("\n📁 Converted Data:")
    converted = status["converted_data"]
    if converted:
        for item in converted[:5]:
            print(f"   {item['symbol']} ({item['resolution']}): "
                  f"{item['file_count']} files")
    else:
        print("   No converted data")
    
    print("\n📜 Strategies:")
    strategies = status["strategies"]
    if strategies:
        for s in strategies[:5]:
            print(f"   - {s['name']}")
    else:
        print("   No generated strategies")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="VibeTrader Backtesting CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Supported intervals (must match Lean resolutions 1:1 AND be available on Binance)
    SUPPORTED_INTERVALS = ["1m", "1h", "1d"]
    
    # Fetch command
    fetch_parser = subparsers.add_parser("fetch", help="Fetch historical data")
    fetch_parser.add_argument("--symbol", "-s", default="BTCUSDT", help="Trading symbol")
    fetch_parser.add_argument("--interval", "-i", default="1h", choices=SUPPORTED_INTERVALS,
                              help="Kline interval (only 1m, 1h, 1d supported)")
    fetch_parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    fetch_parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    fetch_parser.add_argument("--convert", "-c", action="store_true", help="Convert to Lean format")
    
    # Backtest command
    bt_parser = subparsers.add_parser("backtest", help="Run a backtest")
    bt_parser.add_argument("--symbol", "-s", default="BTCUSDT", help="Trading symbol")
    bt_parser.add_argument("--interval", "-i", default="1h", choices=SUPPORTED_INTERVALS,
                          help="Kline interval (only 1m, 1h, 1d supported)")
    bt_parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    bt_parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    bt_parser.add_argument("--capital", "-c", type=float, default=100000, help="Initial capital")
    bt_parser.add_argument("--strategy", help="Strategy name")
    bt_parser.add_argument("--strategy-file", "-f", help="Path to strategy file")
    bt_parser.add_argument("--output", "-o", help="Output file for results JSON")
    bt_parser.add_argument("--no-cache", action="store_true", help="Don't use cached data")
    
    # Cache command
    cache_parser = subparsers.add_parser("cache", help="Manage data cache")
    cache_parser.add_argument("--list", "-l", action="store_true", help="List cached files")
    cache_parser.add_argument("--clear", action="store_true", help="Clear cache")
    cache_parser.add_argument("--stats", action="store_true", help="Show cache statistics")
    cache_parser.add_argument("--symbol", "-s", help="Filter by symbol")
    cache_parser.add_argument("--interval", "-i", help="Filter by interval")
    
    # Convert command
    conv_parser = subparsers.add_parser("convert", help="Convert data to Lean format")
    conv_parser.add_argument("--symbol", "-s", help="Filter by symbol")
    conv_parser.add_argument("--interval", "-i", help="Filter by interval")
    
    # Status command
    subparsers.add_parser("status", help="Show system status")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Run appropriate command
    if args.command == "fetch":
        asyncio.run(cmd_fetch(args))
    elif args.command == "backtest":
        asyncio.run(cmd_backtest(args))
    elif args.command == "cache":
        asyncio.run(cmd_cache(args))
    elif args.command == "convert":
        asyncio.run(cmd_convert(args))
    elif args.command == "status":
        asyncio.run(cmd_status(args))


if __name__ == "__main__":
    main()
