# region imports
from AlgorithmImports import *
# endregion

class DefaultRsi(QCAlgorithm):
    """
    RSI Strategy: Buy when RSI < 30, Sell when RSI > 80
    
    More extreme thresholds for fewer but higher-conviction trades.
    """

    def initialize(self):
        """Initialize the algorithm."""
        # Set dates - will be overridden by CLI parameters
        self.set_start_date(2025, 9, 1)
        self.set_end_date(2025, 12, 1)
        
        # Set account currency to USDT for crypto trading
        self.set_account_currency("USDT")
        
        # Set cash in USDT
        self.set_cash("USDT", 100000, 1.0)
        
        # Set brokerage model for crypto
        self.set_brokerage_model(BrokerageName.BINANCE, AccountType.CASH)
        
        # Add crypto asset
        self.symbol = self.add_crypto("BNBUSDT", Resolution.Hour).symbol
        
        # Strategy parameters
        self.rsi_period = 14
        self.overbought = 70  # Sell when RSI > 70
        self.oversold = 30    # Buy when RSI < 30
        
        # Initialize indicators
        self.rsi = self.RSI(self.symbol, self.rsi_period)
        
        # Set warmup period: RSI uses Wilder's smoothing (exponential),
        # so it needs ~20x the period to fully stabilize and match TradingView
        # This ensures the "seed" error has decayed before trading starts
        self.set_warm_up(self.rsi_period * 20, Resolution.Hour)
        
        # Track state
        self._last_action = None
        
    def on_data(self, data: Slice):
        """Process incoming data."""
        if not data.contains_key(self.symbol):
            return
        
        if not self._indicators_ready():
            return
        
        # Get current price
        price = data[self.symbol].close
        
        # Strategy logic
        # Entry conditions
        if not self.portfolio.invested:
            if self.rsi.current.value < self.oversold:
                self.set_holdings(self.symbol, 1.0)
                self._last_action = "BUY"
                self.debug(f"BUY: RSI={self.rsi.current.value:.2f}")

        # Exit conditions
        elif self.portfolio.invested:
            if self.rsi.current.value > self.overbought:
                self.liquidate(self.symbol)
                self._last_action = "SELL"
                self.debug(f"SELL: RSI={self.rsi.current.value:.2f}")
    
    def _indicators_ready(self) -> bool:
        """Check if all indicators are ready."""
        if not self.rsi.is_ready:
            return False
        return True
    
    def on_order_event(self, order_event: OrderEvent):
        """Handle order events."""
        if order_event.status == OrderStatus.FILLED:
            self.debug(f"Order filled: {order_event}")
