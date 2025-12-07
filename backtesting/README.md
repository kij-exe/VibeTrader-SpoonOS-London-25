# Backtesting - QuantConnect Lean + Binance

Backtesting pipeline: Fetch data (Binance API) → Convert to Lean format → Run in Docker → Parse results.

## Architecture

```
BacktestingAgent.run_backtest()
    ↓
1. Fetch Data      → BinanceFetcher (REST API)
2. Convert Format  → BinanceToLeanConverter (CSV + metadata)
3. Patch Strategy  → Inject dates, Resolution
4. Run Docker      → quantconnect/lean:latest
5. Parse Results   → JSON report → BacktestMetrics
```

## Components

### 1. Data Layer

#### `data/binance_fetcher.py` - BinanceFetcher
- Fetch OHLCV data via `/api/v3/klines`
- Pagination for large date ranges
- Rate limiting: 2400 req/min

**Timeframes:** `1m`, `1h`, `1d`

```python
bars = await fetcher.fetch_klines(
    symbol="BTCUSDT",
    interval="1h",
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 6, 30)
)
# Returns: List[Dict] with OHLCV + volume
```

#### `data/storage/file_manager.py` - Cache
File-based cache to avoid repeated API calls:

```
data_storage/
├── raw/BTCUSDT_1h_20240101_20240630.json    # Binance JSON
├── lean/crypto/binance/daily/btcusdt.csv    # Lean CSV
└── results/custom_strategy_abc123/          # Backtest output
```

**Cache Strategy:**
- Exact match → cache hit
- Superset match → slice cached data
- Miss → fetch from API

### 2. Conversion Layer

#### `data/converter/lean_converter.py` - BinanceToLeanConverter

**Why?** Lean requires specific CSV format with metadata.

**Lean CSV Format:**
```csv
# crypto/binance/daily/btcusdt.csv
20240101 00:00,45000.00,46000.00,44500.00,45800.00,123.456,5678901.234
# Format: datetime,open,high,low,close,volume,quote_volume
```

**Metadata:**
```csv
# btcusdt_metadata.csv
symbol,start_date,end_date,resolution,tick_type,data_source
btcusdt,20240101,20240630,daily,quote,binance
```

**Resolution Paths:**
- `1m` → `crypto/binance/minute/btcusdt.csv`
- `1h` → `crypto/binance/hour/btcusdt.csv`
- `1d` → `crypto/binance/daily/btcusdt.csv`

### 3. Strategy Preparation

**Problem:** Generated code has placeholders for dates/resolution.

**Solution:** Patch strategy file before execution:

```python
def _patch_strategy_file(code, symbol, timeframe, start, end):
    # Convert timeframe to Resolution
    resolution_map = {"1m": "Resolution.Minute", "1h": "Resolution.Hour", "1d": "Resolution.Daily"}
    
    # Inject dates
    code = inject_set_start_date(code, start)
    code = inject_set_end_date(code, end)
    
    # Fix add_crypto() call
    code = re.sub(r"add_crypto\([^)]+\)", f"add_crypto('{symbol}', {resolution_map[timeframe]})", code)
    
    return code
```

### 4. Execution Layer

#### `engine/lean_runner.py` - LeanDockerRunner

**Docker Setup:**
```python
container = docker_client.containers.run(
    image="quantconnect/lean:latest",
    command=["dotnet", "QuantConnect.Lean.Launcher.dll"],
    volumes={
        f"{LEAN_DATA_DIR}": {"bind": "/Lean/Data", "mode": "ro"},
        f"{STRATEGIES_DIR}": {"bind": "/Lean/Strategies", "mode": "ro"},
        f"{RESULTS_DIR}": {"bind": "/Results", "mode": "rw"}
    },
    remove=True
)
```

**Error Detection:**
```python
if "SyntaxError" in logs: stage = "compilation"
elif "algorithm initialization" in logs: stage = "initialization"
elif "Runtime Error" in logs: stage = "execution"
```

### 5. Results Parsing

**Lean Output:** `results/custom_strategy_{hash}/BasicTemplateFrameworkAlgorithm.json`

**Schema:**
```json
{
  "Statistics": {
    "Total Trades": "18",
    "Compounding Annual Return": "35.96%",
    "Drawdown": "12.34%",
    "Sharpe Ratio": "2.561",
    "Win Rate": "61%"
  },
  "Orders": {
    "1": {
      "Time": "2024-01-15 10:30:00",
      "Symbol": "BTCUSDT",
      "Type": "Market",
      "Direction": "Buy",
      "Quantity": 0.5,
      "Price": 45000.0
    }
  }
}
```

**Parse:**
```python
BacktestReport(
    success=True,
    metrics=BacktestMetrics(
        total_return_percent=35.96,
        max_drawdown_percent=12.34,
        sharpe_ratio=2.561,
        win_rate=61.0,
        total_trades=18
    ),
    orders=[Order(...), ...]
)
```

## LLM Context

### `docs/LEAN_INDICATORS_REFERENCE.md`
Comprehensive indicator documentation for LLM:
- 100+ indicators (RSI, MACD, Bollinger Bands, etc.)
- Usage examples
- Parameter details

**How It's Used:**
```python
# In quant_agent.py
@tool
async def get_lean_indicators() -> str:
    with open("docs/LEAN_INDICATORS_REFERENCE.md") as f:
        return f.read()
```

LLM calls this tool during code generation to check available indicators.

## Error Handling

Common errors:
1. **Invalid Symbol**: Symbol not on Binance → Ask user for valid pair
2. **Consolidator Error**: Resolution mismatch → Remove consolidators, use native Resolution
3. **Insufficient Data**: Date range out of bounds → Adjust date range
4. **Syntax Error**: Python syntax issue → Fix indentation/typos
5. **Runtime Error**: AttributeError, etc. → Fix method names

## Performance

**Cache Hit Rates:**
- Same params: ~95%
- Different params: ~60%
- New symbols: 0%

**Storage:**
- 1 year 1m: ~50 MB
- 1 year 1h: ~2 MB
- 1 year 1d: ~50 KB

**Execution Time:**
- Container startup: 2-3s
- 1 month daily: ~2s
- 6 months hourly: ~6s
- 1 year minute: ~15s

**API Rate Limits:**
- Binance: 2400 req/min
- Max bars per request: 1000
- Typical backtest: 1-526 requests

## Configuration

```bash
# .env
LEAN_DATA_DIR=/backtesting/data_storage/lean
LEAN_DOCKER_IMAGE=quantconnect/lean:latest
```

## Troubleshooting

**Docker not found:**
```bash
sudo apt-get install docker.io
sudo usermod -aG docker $USER
```

**Permission denied:**
```bash
sudo chown -R $USER:$USER backtesting/results
```

**No data for symbol:**
```bash
# Verify on Binance
curl "https://api.binance.com/api/v3/exchangeInfo?symbol=BTCUSDT"
```
