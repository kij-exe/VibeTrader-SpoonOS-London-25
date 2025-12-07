"""
BTCUSDTStrategy - Auto-generated Lean QuantConnect Strategy

Requirements:
- Symbol: BTCUSDT
- Timeframe: 1h  
- Entry: RSI < 30
- Exit: RSI > 70
- Risk: 100% position size
"""

from AlgorithmImports import *


class BTCUSDTStrategy(QCAlgorithm):
    """
    Strategy: BTCUSDTStrategy
    
    Entry Conditions: RSI < 30
    Exit Conditions: RSI > 70
    """
    
    def initialize(self):
        """Initialize the algorithm."""
        # ===== Dates (will be patched by backtesting CLI) =====
        self.set_start_date(2025, 1, 1)
        self.set_end_date(2025, 12, 1)
        
        # ===== Account Setup =====
        self.set_account_currency("USDT")
        self.set_cash("USDT", 100000, 1.0)
        self.set_brokerage_model(BrokerageName.BINANCE, AccountType.CASH)
        
        # ===== Add Asset =====
        self.symbol = self.add_crypto("BTCUSDT", Resolution.Hour).symbol
        
        # ===== Initialize Indicators =====
        self.rsi = self.RSI(self.symbol, 14)
        
        # ===== Warmup Period =====
        self.set_warm_up(280, Resolution.Hour)
        
        # ===== Strategy State =====
        self.last_trade_time = None
        self.position_size = 1.0  # 100% position size
    
    def on_data(self, data: Slice):
        """Execute trading logic on each data point."""
        # Check if we have data
        if not data.contains_key(self.symbol):
            return
        
        # Check if indicators are ready
        if not self.indicators_ready():
            return
        
        # Get current price
        price = data[self.symbol].close
        
        # ===== Trading Logic =====
        if self.rsi.current.value < 30 and not self.portfolio.invested:
            self.set_holdings(self.symbol, self.position_size)
            self.debug(f"BUY at {price:.2f}")
        
        elif self.rsi.current.value > 70 and self.portfolio.invested:
            self.liquidate()
            self.debug(f"SELL at {price:.2f}")
    
    def indicators_ready(self) -> bool:
        """Check if all indicators are ready."""
        if not self.rsi.is_ready:
            return False
        return True