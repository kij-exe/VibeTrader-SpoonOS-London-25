# region imports
from AlgorithmImports import *
# endregion

class BuggyRsi(QCAlgorithm):
    """
    Intentionally buggy RSI strategy for testing error handling.
    
    Contains multiple bugs that will cause runtime errors:
    1. Division by zero
    2. Accessing undefined variable
    3. Wrong attribute access
    """

    def initialize(self):
        """Initialize the algorithm."""
        self.set_start_date(2025, 9, 1)
        self.set_end_date(2025, 12, 1)
        
        self.set_account_currency("USDT")
        self.set_cash("USDT", 100000, 1.0)
        self.set_brokerage_model(BrokerageName.BINANCE, AccountType.CASH)
        
        self.symbol = self.add_crypto("BTCUSDT", Resolution.Hour).symbol
        
        # Strategy parameters
        self.rsi_period = 14
        self.overbought = 70
        self.oversold = 30
        
        # Initialize RSI
        self.rsi = self.RSI(self.symbol, self.rsi_period)
        self.set_warm_up(self.rsi_period * 20, Resolution.Hour)
        
        # BUG: This variable is never defined but used later
        # self.trade_count = 0  # Commented out intentionally
        
    def on_data(self, data):
        """Process incoming data - contains intentional bugs."""
        if not data.contains_key(self.symbol):
            return
        
        if not self.rsi.is_ready:
            return
        
        # BUG 1: Division by zero
        denominator = self.rsi.current.value - self.rsi.current.value  # Always 0
        result = 100 / denominator  # ZeroDivisionError!
        
        # BUG 2: Accessing undefined variable (won't reach here due to bug above)
        self.trade_count += 1  # NameError: trade_count not defined
        
        # BUG 3: Wrong attribute (won't reach here)
        price = data[self.symbol].wrong_attribute  # AttributeError
        
        # Trading logic (won't execute)
        if self.rsi.current.value < self.oversold:
            self.set_holdings(self.symbol, 1.0)
        elif self.rsi.current.value > self.overbought:
            self.liquidate()
