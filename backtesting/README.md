# VibeTrader Backtesting Module

Backtesting pipeline for crypto trading strategies using Binance historical data and Lean QuantConnect engine.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BACKTESTING PIPELINE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. DATA ACQUISITION                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │   Binance    │───►│   Fetcher    │───►│  Raw JSON    │                   │
│  │     API      │    │  (paginated) │    │   Storage    │                   │
│  └──────────────┘    └──────────────┘    └──────────────┘                   │
│                                                 │                            │
│  2. DATA TRANSFORMATION                         ▼                            │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │  Lean Data   │◄───│  Converter   │◄───│  Raw JSON    │                   │
│  │   Format     │    │              │    │              │                   │
│  └──────────────┘    └──────────────┘    └──────────────┘                   │
│         │                                                                    │
│  3. STRATEGY EXECUTION                                                       │
│         ▼                                                                    │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │   Strategy   │───►│ Lean Engine  │───►│   Results    │                   │
│  │    (.py)     │    │  (Docker)    │    │    JSON      │                   │
│  └──────────────┘    └──────────────┘    └──────────────┘                   │
│                                                 │                            │
│  4. RESULTS PROCESSING                          ▼                            │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │  Structured  │◄───│   Parser     │◄───│   Results    │                   │
│  │   Output     │    │              │    │    JSON      │                   │
│  └──────────────┘    └──────────────┘    └──────────────┘                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
backtesting/
├── __init__.py
├── config/                    # Configuration
│   ├── settings.py           # Global settings
│   └── intervals.py          # Binance interval mappings
├── data/                      # Data handling
│   ├── fetcher/              # Binance API client
│   │   └── binance_client.py
│   ├── converter/            # Lean format converter
│   │   └── lean_converter.py
│   ├── storage/              # File management
│   │   └── file_manager.py
│   └── models.py             # Data models
├── engine/                    # Lean execution
│   ├── lean_runner.py        # Lean Engine wrapper
│   └── strategy_generator.py # Strategy file generator
├── results/                   # Results processing
│   ├── parser.py             # Lean output parser
│   └── models.py             # Result models
├── agent/                     # Main orchestrator
│   └── backtesting_agent.py
├── utils/                     # Utilities
│   ├── rate_limiter.py       # API rate limiting
│   └── time_utils.py         # Time utilities
├── cli.py                     # Command-line interface
└── requirements.txt
```

## Quick Start

### Prerequisites

1. **Docker** - Required for running the Lean backtesting engine
   ```bash
   # macOS
   brew install --cask docker
   
   # Or download from https://www.docker.com/products/docker-desktop
   ```

2. **Pull the Lean Docker image** (optional - auto-pulled on first run)
   ```bash
   docker pull quantconnect/lean:latest
   ```

3. **Start Docker Desktop** - Ensure Docker daemon is running

### Installation

```bash
cd backtesting
pip install -r requirements.txt
```

### CLI Usage

```bash
# Fetch historical data
python -m backtesting.cli fetch --symbol BTCUSDT --interval 4h --start 2024-01-01 --end 2024-06-01

# Run a backtest
python -m backtesting.cli backtest --symbol BTCUSDT --interval 4h --start 2024-01-01 --end 2024-06-01

# Check system status
python -m backtesting.cli status

# Manage cache
python -m backtesting.cli cache --list
python -m backtesting.cli cache --stats
```

### Programmatic Usage

```python
import asyncio
from backtesting.agent import BacktestingAgent, BacktestRequest

async def main():
    agent = BacktestingAgent()
    
    request = BacktestRequest(
        symbol="BTCUSDT",
        interval="4h",
        start_date="2024-01-01",
        end_date="2024-06-01",
        initial_capital=100000.0,
    )
    
    response = await agent.run_backtest(request)
    
    if response.success:
        print(response.report.to_summary())
        print(response.report.get_evaluation_score())
    else:
        print(f"Error: {response.error_message}")

asyncio.run(main())
```

### Using with Custom Strategy Code

```python
from backtesting.agent import BacktestingAgent, BacktestRequest

strategy_code = '''
from AlgorithmImports import *

class MyStrategy(QCAlgorithm):
    def initialize(self):
        self.set_start_date(2024, 1, 1)
        self.set_end_date(2024, 6, 1)
        self.set_cash(100000)
        self.symbol = self.add_crypto("BTCUSDT", Resolution.Hour).symbol
        self.rsi = self.rsi(self.symbol, 14)
    
    def on_data(self, data):
        if not self.rsi.is_ready:
            return
        
        if self.rsi.current.value < 30 and not self.portfolio.invested:
            self.set_holdings(self.symbol, 1.0)
        elif self.rsi.current.value > 70 and self.portfolio.invested:
            self.liquidate()
'''

request = BacktestRequest(
    strategy_code=strategy_code,
    symbol="BTCUSDT",
    interval="1h",
    start_date="2024-01-01",
    end_date="2024-06-01",
)
```

## Components

### BinanceDataFetcher

Fetches historical kline data from Binance API with:
- Automatic pagination for large date ranges
- Rate limiting (request count and weight)
- Retry logic with exponential backoff
- Progress tracking

```python
from backtesting.data import BinanceDataFetcher

async with BinanceDataFetcher() as fetcher:
    data = await fetcher.fetch_klines(
        symbol="BTCUSDT",
        interval="4h",
        start_time="2024-01-01",
        end_time="2024-06-01",
    )
```

### LeanDataConverter

Converts Binance kline data to Lean QuantConnect format:
- Creates zipped CSV files organized by date
- Supports minute, hour, and daily resolutions
- Handles Lean's expected directory structure

```python
from backtesting.data import LeanDataConverter

converter = LeanDataConverter()
files = converter.convert(kline_data)
```

### LeanRunner

Executes backtests via Lean Engine:
- Docker mode (recommended)
- Local Lean CLI mode
- Simulation mode (for development)

```python
from backtesting.engine import LeanRunner, LeanBacktestConfig

runner = LeanRunner()
config = LeanBacktestConfig(
    strategy_file=Path("my_strategy.py"),
    data_dir=Path("data/lean"),
    output_dir=Path("results"),
)
result = await runner.run_backtest(config)
```

### ResultsParser

Parses Lean JSON output into structured reports:
- Performance metrics
- Risk metrics
- Trade records
- Equity curve

```python
from backtesting.results import ResultsParser

parser = ResultsParser()
report = parser.parse_file("results/backtest-results.json")
print(report.to_summary())
```

## Output Format

### BacktestReport

```python
{
    "strategy": {
        "name": "rsi_strategy",
        "version": "1.0.0"
    },
    "configuration": {
        "symbol": "BTCUSDT",
        "initial_capital": 100000.0,
        "start_date": "2024-01-01",
        "end_date": "2024-06-01"
    },
    "results": {
        "final_equity": 115000.0,
        "metrics": {
            "returns": {
                "total_return_percent": 15.0,
                "annual_return_percent": 30.0
            },
            "trades": {
                "total_trades": 45,
                "win_rate": 55.0
            },
            "risk": {
                "sharpe_ratio": 1.5,
                "max_drawdown_percent": 12.0
            }
        }
    }
}
```

### Evaluation Scores

The system provides 1-3 scores for:
- **Performance Score**: Based on returns and Sharpe ratio
- **Risk Score**: Based on drawdown and volatility
- **Consistency Score**: Based on win rate and profit factor

## Integration with Agent System

The BacktestingAgent is designed to be called by other agents:

```python
# From compilation agent after strategy validation
from backtesting.agent import BacktestingAgent, BacktestRequest

agent = BacktestingAgent()
response = await agent.run_backtest(BacktestRequest(
    strategy_code=validated_strategy_code,
    symbol=user_symbol,
    interval=user_interval,
    start_date=user_start,
    end_date=user_end,
))

# Pass to evaluation agent
evaluation_input = {
    "backtest_results": response.to_dict(),
    "user_query": original_user_query,
}
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BINANCE_BASE_URL` | Binance API base URL | `https://api.binance.com` |
| `LEAN_DOCKER_IMAGE` | Lean Docker image | `quantconnect/lean:latest` |
| `LEAN_EXECUTION_TIMEOUT` | Backtest timeout (seconds) | `300` |
| `LEAN_DEFAULT_CAPITAL` | Default starting capital | `100000` |
| `DEBUG` | Enable debug logging | `false` |

## Requirements

- Python 3.10+
- aiohttp (for Binance API)
- Docker (optional, for Lean Engine)
- Lean CLI (optional, alternative to Docker)
