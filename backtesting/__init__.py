"""
VibeTrader Backtesting Module

Pipeline for fetching historical data from Binance, converting to Lean QuantConnect format,
running backtests, and parsing results.

Architecture:
    1. Data Fetcher: Binance API -> Raw JSON
    2. Converter: Raw JSON -> Lean Format
    3. Engine: Lean QuantConnect execution
    4. Results: Parse and structure backtest output
"""

__version__ = "1.0.0"
