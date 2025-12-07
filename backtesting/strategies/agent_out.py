from AlgorithmImports import *


class BTCUSDTStrategy(QCAlgorithm):
    """
    Strategy: BTCUSDTStrategy

    Symbol: BTCUSDT
    Timeframe: 1h

    Entry:
        - Enter long when RSI > 30 and not already invested.

    Exit:
        - Exit (close the position) when:
            * RSI < 70
            OR
            * Unrealized loss is greater than or equal to 15% from entry.

    Risk Management:
        - Standard position sizing via SetHoldings (here: full exposure to BTC when in position).
    """

    def Initialize(self):
        # ===== Dates (adjust these as needed when backtesting) =====
        self.SetStartDate(2023, 1, 1)
        self.SetEndDate(2023, 12, 31)

        # ===== Account Setup =====
        self.SetAccountCurrency("USDT")
        self.SetCash("USDT", 100000)  # starting capital in USDT
        self.SetBrokerageModel(BrokerageName.Binance, AccountType.Cash)

        # ===== Add Asset (1h timeframe) =====
        self.symbol = self.AddCrypto("BTCUSDT", Resolution.Hour).Symbol

        # ===== Indicators =====
        # Standard 14-period RSI on close
        self.rsi = self.RSI(self.symbol, 14, MovingAverageType.Wilders, Resolution.Hour)

        # ===== Warmup =====
        # Slightly more than RSI period to ensure readiness
        self.SetWarmUp(28, Resolution.Hour)

        # ===== Risk / Position State =====
        self.position_size = 1.0  # 100% of portfolio when in a position (standard SetHoldings sizing)
        self.entry_price = None   # track entry price to compute unrealized P&L
        self.stop_loss_pct = -0.15  # -15% (unrealized loss threshold)

    def OnData(self, data: Slice):
        # Ensure we have data for the symbol
        if self.symbol not in data or data[self.symbol] is None:
            return

        # Wait until indicators are fully ready
        if self.IsWarmingUp or not self.IndicatorsReady():
            return

        price = data[self.symbol].Close
        rsi_value = self.rsi.Current.Value
        invested = self.Portfolio[self.symbol].Invested

        # ===== Entry Logic =====
        # Enter long when RSI > 30 and we're not already invested
        if not invested:
            if rsi_value > 30:
                self.SetHoldings(self.symbol, self.position_size)
                self.entry_price = price
                self.Debug(f"[ENTRY] BUY BTCUSDT at {price:.2f}, RSI={rsi_value:.2f}")
            return  # if not invested, no need to check exit conditions

        # ===== Exit Logic =====
        # 1) RSI-based exit: RSI < 70
        rsi_exit = rsi_value < 70

        # 2) Unrealized loss exit: loss >= 15% from entry
        pnl_pct = None
        loss_exit = False
        if self.entry_price is not None and self.entry_price > 0:
            pnl_pct = (price - self.entry_price) / self.entry_price
            loss_exit = pnl_pct <= self.stop_loss_pct  # e.g., <= -0.15

        if rsi_exit or loss_exit:
            reason = []
            if rsi_exit:
                reason.append(f"RSI exit (RSI={rsi_value:.2f} < 70)")
            if loss_exit and pnl_pct is not None:
                reason.append(f"Loss exit (P/L={pnl_pct*100:.2f}%)")

            self.Liquidate(self.symbol)
            self.Debug(f"[EXIT] SELL BTCUSDT at {price:.2f} | " + " | ".join(reason))
            self.entry_price = None  # reset entry reference

    def IndicatorsReady(self) -> bool:
        """Check if all indicators used in logic are ready."""
        return self.rsi.IsReady