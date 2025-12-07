# Lean QuantConnect Indicators Reference

This document provides context for the Quant Agent to generate strategies using Lean's built-in indicators.

## CRITICAL: Use Lean's Built-in Indicators

**DO NOT implement your own indicator calculations.** Lean provides 100+ pre-built, optimized indicators that:
- Use proper smoothing algorithms (e.g., Wilder's smoothing for RSI)
- Handle warmup periods automatically
- Are battle-tested and production-ready

## How to Use Indicators

### Basic Pattern
```python
from AlgorithmImports import *

class MyStrategy(QCAlgorithm):
    def initialize(self):
        self.symbol = self.add_crypto("BTCUSDT", Resolution.Hour).symbol
        
        # Create indicator using self.INDICATOR_NAME(symbol, period)
        self.rsi = self.RSI(self.symbol, 14)
        self.macd = self.MACD(self.symbol, 12, 26, 9)
        self.bb = self.BB(self.symbol, 20, 2)
        
        # Set warmup period (20x the longest indicator period)
        self.set_warm_up(280, Resolution.Hour)
    
    def on_data(self, data):
        # Check if indicator is ready before using
        if not self.rsi.is_ready:
            return
        
        # Access current value
        rsi_value = self.rsi.current.value
        
        # For composite indicators like MACD
        macd_value = self.macd.current.value
        signal_value = self.macd.signal.current.value
        histogram = self.macd.histogram.current.value
        
        # For Bollinger Bands
        upper = self.bb.upper_band.current.value
        middle = self.bb.middle_band.current.value
        lower = self.bb.lower_band.current.value
```

## Warmup Period

Indicators using exponential smoothing (RSI, EMA, MACD) need warmup:
```python
# Rule: warmup = indicator_period * 20
self.set_warm_up(self.rsi_period * 20, Resolution.Hour)
```

## Common Indicators Reference

### Trend Indicators
| Indicator | Method | Parameters | Usage |
|-----------|--------|------------|-------|
| SMA | `self.SMA(symbol, period)` | period: int | `self.sma.current.value` |
| EMA | `self.EMA(symbol, period)` | period: int | `self.ema.current.value` |
| MACD | `self.MACD(symbol, fast, slow, signal)` | fast=12, slow=26, signal=9 | `.current.value`, `.signal.current.value`, `.histogram.current.value` |
| ADX | `self.ADX(symbol, period)` | period: int | `self.adx.current.value` |
| Parabolic SAR | `self.PSAR(symbol)` | - | `self.psar.current.value` |
| Ichimoku | `self.ICHIMOKU(symbol, tenkan, kijun, senkou)` | 9, 26, 52 | `.tenkan.current.value`, `.kijun.current.value` |

### Momentum Indicators
| Indicator | Method | Parameters | Usage |
|-----------|--------|------------|-------|
| RSI | `self.RSI(symbol, period)` | period: int (default 14) | `self.rsi.current.value` (0-100) |
| Stochastic | `self.STO(symbol, period, kPeriod, dPeriod)` | 14, 3, 3 | `.stoch_k.current.value`, `.stoch_d.current.value` |
| CCI | `self.CCI(symbol, period)` | period: int | `self.cci.current.value` |
| Williams %R | `self.WILR(symbol, period)` | period: int | `self.wilr.current.value` |
| ROC | `self.ROC(symbol, period)` | period: int | `self.roc.current.value` |
| MOM | `self.MOM(symbol, period)` | period: int | `self.mom.current.value` |

### Volatility Indicators
| Indicator | Method | Parameters | Usage |
|-----------|--------|------------|-------|
| Bollinger Bands | `self.BB(symbol, period, k)` | period=20, k=2 | `.upper_band`, `.middle_band`, `.lower_band` |
| ATR | `self.ATR(symbol, period)` | period: int | `self.atr.current.value` |
| Keltner Channels | `self.KCH(symbol, period, k)` | period=20, k=1.5 | `.upper_band`, `.middle_band`, `.lower_band` |
| Donchian Channel | `self.DCH(symbol, period)` | period: int | `.upper_band`, `.lower_band` |
| Standard Deviation | `self.STD(symbol, period)` | period: int | `self.std.current.value` |

### Volume Indicators
| Indicator | Method | Parameters | Usage |
|-----------|--------|------------|-------|
| OBV | `self.OBV(symbol)` | - | `self.obv.current.value` |
| MFI | `self.MFI(symbol, period)` | period: int | `self.mfi.current.value` |
| VWAP | `self.VWAP(symbol)` | - | `self.vwap.current.value` |
| AD | `self.AD(symbol)` | - | `self.ad.current.value` |
| CMF | `self.CMF(symbol, period)` | period: int | `self.cmf.current.value` |

### Moving Averages (All Types)
| Type | Method |
|------|--------|
| Simple | `self.SMA(symbol, period)` |
| Exponential | `self.EMA(symbol, period)` |
| Double Exponential | `self.DEMA(symbol, period)` |
| Triple Exponential | `self.TEMA(symbol, period)` |
| Triangular | `self.TRIMA(symbol, period)` |
| Weighted | `self.LWMA(symbol, period)` |
| Hull | `self.HMA(symbol, period)` |
| Kaufman Adaptive | `self.KAMA(symbol, period)` |
| Wilder | `self.WWMA(symbol, period)` |

## Full Indicator List (100+)

### Technical Indicators
- Absolute Price Oscillator (APO)
- Acceleration Bands
- Accumulation Distribution (AD)
- Accumulation Distribution Oscillator
- Advance Decline Difference
- Advance Decline Ratio
- Arnaud Legoux Moving Average (ALMA)
- Aroon Oscillator
- Average Directional Index (ADX)
- Average True Range (ATR)
- Awesome Oscillator
- Balance Of Power
- Beta
- Bollinger Bands (BB)
- Chaikin Money Flow (CMF)
- Chaikin Oscillator
- Chande Momentum Oscillator (CMO)
- Commodity Channel Index (CCI)
- Connors RSI
- Coppock Curve
- Correlation
- DeMarker Indicator
- Derivative Oscillator
- Detrended Price Oscillator (DPO)
- Donchian Channel (DCH)
- Double Exponential Moving Average (DEMA)
- Ease Of Movement
- Exponential Moving Average (EMA)
- Fisher Transform
- Force Index
- Fractal Adaptive Moving Average (FRAMA)
- Heikin Ashi
- Hilbert Transform
- Hull Moving Average (HMA)
- Hurst Exponent
- Ichimoku Kinko Hyo
- Implied Volatility
- Internal Bar Strength
- Intraday VWAP
- Kaufman Adaptive Moving Average (KAMA)
- Kaufman Efficiency Ratio
- Keltner Channels (KCH)
- Klinger Volume Oscillator
- Know Sure Thing (KST)
- Least Squares Moving Average
- Linear Weighted Moving Average (LWMA)
- Log Return
- Mass Index
- Maximum
- McClellan Oscillator
- McClellan Summation Index
- McGinley Dynamic
- Mean Absolute Deviation
- Mesa Adaptive Moving Average (MAMA)
- Mid Point
- Mid Price
- Minimum
- Momentum (MOM)
- Momentum Percent
- Money Flow Index (MFI)
- Moving Average Convergence Divergence (MACD)
- Normalized Average True Range
- On Balance Volume (OBV)
- Parabolic Stop And Reverse (PSAR)
- Percentage Price Oscillator (PPO)
- Pivot Points High Low
- Premier Stochastic Oscillator
- Rate Of Change (ROC)
- Rate Of Change Percent
- Regression Channel
- Relative Daily Volume
- Relative Moving Average
- Relative Strength Index (RSI)
- Relative Vigor Index
- Rogers Satchell Volatility
- Schaff Trend Cycle
- Sharpe Ratio
- Simple Moving Average (SMA)
- Smoothed On Balance Volume
- Sortino Ratio
- Squeeze Momentum
- Standard Deviation (STD)
- Stochastic (STO)
- Stochastic RSI
- Sum
- Super Trend
- Swiss Army Knife
- T3 Moving Average
- Target Downside Deviation
- Time Series Forecast
- Tom Demark Sequential
- Triangular Moving Average (TRIMA)
- Triple Exponential Moving Average (TEMA)
- TRIX
- True Range
- True Strength Index (TSI)
- Ultimate Oscillator
- Value At Risk
- Variable Index Dynamic Average (VIDYA)
- Variance
- Volume Weighted Average Price (VWAP)
- Volume Weighted Moving Average (VWMA)
- Vortex
- Wilder Accumulative Swing Index
- Wilder Moving Average (WWMA)
- Wilder Swing Index
- Williams Percent R (WILR)
- Zero Lag Exponential Moving Average (ZLEMA)
- Zig Zag

### Candlestick Patterns (60+)
All return 1 (bullish), -1 (bearish), or 0 (no pattern):
- Abandoned Baby
- Advance Block
- Belt Hold
- Breakaway
- Dark Cloud Cover
- Doji / Doji Star / Dragonfly Doji / Gravestone Doji
- Engulfing
- Evening Star / Morning Star
- Hammer / Hanging Man / Inverted Hammer
- Harami / Harami Cross
- Kicking
- Marubozu
- Piercing
- Shooting Star
- Spinning Top
- Three Black Crows / Three White Soldiers
- And many more...

## Example Strategies

### RSI Mean Reversion
```python
self.rsi = self.RSI(self.symbol, 14)
self.set_warm_up(280, Resolution.Hour)

def on_data(self, data):
    if not self.rsi.is_ready:
        return
    if self.rsi.current.value < 30 and not self.portfolio.invested:
        self.set_holdings(self.symbol, 1.0)
    elif self.rsi.current.value > 70 and self.portfolio.invested:
        self.liquidate()
```

### MACD Crossover
```python
self.macd = self.MACD(self.symbol, 12, 26, 9)
self.set_warm_up(520, Resolution.Hour)

def on_data(self, data):
    if not self.macd.is_ready:
        return
    if self.macd.current.value > self.macd.signal.current.value:
        self.set_holdings(self.symbol, 1.0)
    else:
        self.liquidate()
```

### Bollinger Band Breakout
```python
self.bb = self.BB(self.symbol, 20, 2)
self.set_warm_up(400, Resolution.Hour)

def on_data(self, data):
    if not self.bb.is_ready:
        return
    price = data[self.symbol].close
    if price > self.bb.upper_band.current.value:
        self.set_holdings(self.symbol, 1.0)
    elif price < self.bb.lower_band.current.value:
        self.liquidate()
```

## Documentation Links
- Full indicator docs: https://www.quantconnect.com/docs/v2/writing-algorithms/indicators/supported-indicators
- Candlestick patterns: https://www.quantconnect.com/docs/v2/writing-algorithms/indicators/supported-indicators/candlestick-patterns
