# Quant Agent System Context

## Strategy Generation Rules

When generating trading strategies for the Lean QuantConnect backtesting engine:

### 1. ALWAYS Use Lean's Built-in Indicators

**NEVER implement your own indicator calculations.** Use Lean's 100+ pre-built indicators:

```python
# ✅ CORRECT - Use Lean's built-in RSI
self.rsi = self.RSI(self.symbol, 14)

# ❌ WRONG - Don't implement your own
def calculate_rsi(prices, period):  # DON'T DO THIS
    ...
```

### 2. Common Indicators Quick Reference

| Indicator | Code | Access Value |
|-----------|------|--------------|
| RSI | `self.RSI(symbol, 14)` | `.current.value` |
| MACD | `self.MACD(symbol, 12, 26, 9)` | `.current.value`, `.signal.current.value` |
| Bollinger Bands | `self.BB(symbol, 20, 2)` | `.upper_band`, `.middle_band`, `.lower_band` |
| SMA | `self.SMA(symbol, 20)` | `.current.value` |
| EMA | `self.EMA(symbol, 20)` | `.current.value` |
| ATR | `self.ATR(symbol, 14)` | `.current.value` |
| Stochastic | `self.STO(symbol, 14, 3, 3)` | `.stoch_k`, `.stoch_d` |
| ADX | `self.ADX(symbol, 14)` | `.current.value` |
| CCI | `self.CCI(symbol, 20)` | `.current.value` |
| OBV | `self.OBV(symbol)` | `.current.value` |
| MFI | `self.MFI(symbol, 14)` | `.current.value` |
| VWAP | `self.VWAP(symbol)` | `.current.value` |

### 3. Required Strategy Structure

```python
from AlgorithmImports import *

class StrategyName(QCAlgorithm):
    def initialize(self):
        # Dates (will be patched by CLI)
        self.set_start_date(2025, 1, 1)
        self.set_end_date(2025, 12, 1)
        
        # Account setup
        self.set_account_currency("USDT")
        self.set_cash("USDT", 100000, 1.0)
        self.set_brokerage_model(BrokerageName.BINANCE, AccountType.CASH)
        
        # Add asset (will be patched by CLI)
        self.symbol = self.add_crypto("BTCUSDT", Resolution.Hour).symbol
        
        # Initialize indicators
        self.rsi = self.RSI(self.symbol, 14)
        
        # CRITICAL: Set warmup period (20x longest indicator period)
        self.set_warm_up(280, Resolution.Hour)
    
    def on_data(self, data):
        if not data.contains_key(self.symbol):
            return
        
        # Check indicator readiness
        if not self.rsi.is_ready:
            return
        
        # Trading logic here
        if self.rsi.current.value < 30:
            self.set_holdings(self.symbol, 1.0)
        elif self.rsi.current.value > 70:
            self.liquidate()
```

### 4. Warmup Period Rule

Indicators using exponential smoothing need warmup to stabilize:
```python
# warmup_bars = indicator_period × 20
self.set_warm_up(self.rsi_period * 20, Resolution.Hour)
```

### 5. Supported Resolutions

Only these resolutions are supported:
- `Resolution.Minute` (1m)
- `Resolution.Hour` (1h)  
- `Resolution.Daily` (1d)

### 6. Brokerage Model

Always use Binance for crypto:
```python
self.set_brokerage_model(BrokerageName.BINANCE, AccountType.CASH)
```

### 7. Full Indicator Documentation

See: `/backtesting/docs/LEAN_INDICATORS_REFERENCE.md`
Or: https://www.quantconnect.com/docs/v2/writing-algorithms/indicators/supported-indicators
