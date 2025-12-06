"""
Example Strategy Implementations

Demonstrates how to implement the BaseStrategy interface.
These can be used as templates or for testing the backtest engine.
"""

from typing import Any, Dict, List, Optional

from app.strategy.interface import (
    BaseStrategy,
    MarketData,
    Order,
    OrderSide,
    StrategyConfig,
    StrategyContext,
)


class SimpleMomentumStrategy(BaseStrategy):
    """
    Simple momentum strategy.
    
    Buys when price is above the moving average (upward momentum).
    Sells when price drops below the moving average.
    """
    
    name = "simple_momentum"
    version = "1.0.0"
    description = "Momentum strategy based on moving average crossover"
    
    def __init__(self):
        self.config: Optional[StrategyConfig] = None
        self.lookback_period: int = 10
        self.entry_threshold: float = 0.005  # 0.5% above MA to buy
        self.exit_threshold: float = -0.005  # 0.5% below MA to sell
    
    def configure(self, config: StrategyConfig) -> None:
        self.config = config
        self.lookback_period = config.get("lookback_period", 20)
        self.entry_threshold = config.get("entry_threshold", 0.02)
        self.exit_threshold = config.get("exit_threshold", -0.01)
    
    async def on_data(self, data: MarketData, ctx: StrategyContext) -> None:
        closes = data.closes(self.lookback_period)
        
        if len(closes) < self.lookback_period:
            return  # Not enough data
        
        # Calculate simple moving average
        sma = sum(closes) / len(closes)
        current_price = data.close
        
        # Calculate momentum (% distance from MA)
        momentum = (current_price - sma) / sma
        
        position = await ctx.get_position(data.symbol)
        
        if momentum > self.entry_threshold and not position:
            # Buy signal
            cash = await ctx.get_cash()
            # Use 98% to account for slippage and commission
            max_position = min(self.config.max_position_size if self.config else 0.95, 0.98)
            qty = (cash * max_position) / current_price
            
            if qty > 0:
                ctx.log(f"BUY signal: momentum={momentum:.4f}, price={current_price:.2f}")
                await ctx.place_order(Order(
                    symbol=data.symbol,
                    side=OrderSide.BUY,
                    quantity=qty,
                    stop_loss=current_price * (1 - 0.05) if self.config and self.config.stop_loss_percent else None,
                ))
        
        elif momentum < self.exit_threshold and position:
            # Sell signal
            ctx.log(f"SELL signal: momentum={momentum:.4f}, price={current_price:.2f}")
            await ctx.place_order(Order(
                symbol=data.symbol,
                side=OrderSide.SELL,
                quantity=position.quantity,
            ))


class MeanReversionStrategy(BaseStrategy):
    """
    Mean reversion strategy.
    
    Buys when price is significantly below the moving average (oversold).
    Sells when price returns to or exceeds the moving average.
    """
    
    name = "mean_reversion"
    version = "1.0.0"
    description = "Mean reversion strategy - buy oversold, sell at mean"
    
    def __init__(self):
        self.config: Optional[StrategyConfig] = None
        self.lookback_period: int = 20
        self.entry_zscore: float = -2.0  # Buy when 2 std devs below
        self.exit_zscore: float = 0.0  # Sell at mean
    
    def configure(self, config: StrategyConfig) -> None:
        self.config = config
        self.lookback_period = config.get("lookback_period", 20)
        self.entry_zscore = config.get("entry_zscore", -2.0)
        self.exit_zscore = config.get("exit_zscore", 0.0)
    
    def _calculate_zscore(self, closes: List[float]) -> float:
        """Calculate z-score of current price relative to history"""
        if len(closes) < 2:
            return 0.0
        
        mean = sum(closes) / len(closes)
        variance = sum((x - mean) ** 2 for x in closes) / len(closes)
        std = variance ** 0.5
        
        if std == 0:
            return 0.0
        
        return (closes[0] - mean) / std
    
    async def on_data(self, data: MarketData, ctx: StrategyContext) -> None:
        closes = data.closes(self.lookback_period)
        
        if len(closes) < self.lookback_period:
            return
        
        zscore = self._calculate_zscore(closes)
        position = await ctx.get_position(data.symbol)
        
        if zscore < self.entry_zscore and not position:
            # Oversold - buy
            cash = await ctx.get_cash()
            max_position = min(self.config.max_position_size if self.config else 0.95, 0.98)
            qty = (cash * max_position) / data.close
            
            if qty > 0:
                ctx.log(f"BUY (oversold): zscore={zscore:.2f}, price={data.close:.2f}")
                await ctx.place_order(Order(
                    symbol=data.symbol,
                    side=OrderSide.BUY,
                    quantity=qty,
                ))
        
        elif zscore > self.exit_zscore and position:
            # Mean reached - sell
            ctx.log(f"SELL (mean reached): zscore={zscore:.2f}, price={data.close:.2f}")
            await ctx.place_order(Order(
                symbol=data.symbol,
                side=OrderSide.SELL,
                quantity=position.quantity,
            ))


class BreakoutStrategy(BaseStrategy):
    """
    Breakout strategy.
    
    Buys when price breaks above recent highs.
    Sells when price breaks below recent lows or hits take-profit.
    """
    
    name = "breakout"
    version = "1.0.0"
    description = "Breakout strategy - trade range breakouts"
    
    def __init__(self):
        self.config: Optional[StrategyConfig] = None
        self.lookback_period: int = 20
        self.breakout_threshold: float = 1.001  # 0.1% above high
        self.stop_loss_percent: float = 0.03
        self.take_profit_percent: float = 0.06
    
    def configure(self, config: StrategyConfig) -> None:
        self.config = config
        self.lookback_period = config.get("lookback_period", 20)
        self.breakout_threshold = config.get("breakout_threshold", 1.001)
        self.stop_loss_percent = config.stop_loss_percent or 0.03
        self.take_profit_percent = config.take_profit_percent or 0.06
    
    async def on_data(self, data: MarketData, ctx: StrategyContext) -> None:
        highs = data.highs(self.lookback_period)
        lows = data.lows(self.lookback_period)
        
        if len(highs) < self.lookback_period:
            return
        
        # Recent high/low (excluding current bar)
        recent_high = max(highs[1:]) if len(highs) > 1 else highs[0]
        recent_low = min(lows[1:]) if len(lows) > 1 else lows[0]
        
        current_price = data.close
        position = await ctx.get_position(data.symbol)
        
        if not position:
            # Look for breakout entry
            if current_price > recent_high * self.breakout_threshold:
                cash = await ctx.get_cash()
                max_position = min(self.config.max_position_size if self.config else 0.95, 0.98)
                qty = (cash * max_position) / current_price
                
                if qty > 0:
                    ctx.log(f"BREAKOUT BUY: price={current_price:.2f} > high={recent_high:.2f}")
                    await ctx.place_order(Order(
                        symbol=data.symbol,
                        side=OrderSide.BUY,
                        quantity=qty,
                        stop_loss=current_price * (1 - self.stop_loss_percent),
                        take_profit=current_price * (1 + self.take_profit_percent),
                    ))
        else:
            # Check for exit
            entry_price = position.entry_price
            pnl_percent = (current_price - entry_price) / entry_price
            
            # Stop loss
            if pnl_percent < -self.stop_loss_percent:
                ctx.log(f"STOP LOSS: pnl={pnl_percent:.2%}")
                await ctx.place_order(Order(
                    symbol=data.symbol,
                    side=OrderSide.SELL,
                    quantity=position.quantity,
                ))
            # Take profit
            elif pnl_percent > self.take_profit_percent:
                ctx.log(f"TAKE PROFIT: pnl={pnl_percent:.2%}")
                await ctx.place_order(Order(
                    symbol=data.symbol,
                    side=OrderSide.SELL,
                    quantity=position.quantity,
                ))


class DCAStrategy(BaseStrategy):
    """
    Dollar-Cost Averaging strategy.
    
    Periodically buys a fixed amount regardless of price.
    Optionally sells when profit target is reached.
    """
    
    name = "dca"
    version = "1.0.0"
    description = "Dollar-cost averaging - periodic fixed purchases"
    
    def __init__(self):
        self.config: Optional[StrategyConfig] = None
        self.buy_interval: int = 24  # Buy every N bars
        self.buy_amount_percent: float = 0.05  # 5% of initial capital per buy
        self.take_profit_percent: float = 0.20  # 20% profit target
        self.bars_since_buy: int = 0
        self.initial_capital: float = 0
    
    def configure(self, config: StrategyConfig) -> None:
        self.config = config
        self.buy_interval = config.get("buy_interval", 24)
        self.buy_amount_percent = config.get("buy_amount_percent", 0.05)
        self.take_profit_percent = config.take_profit_percent or 0.20
        self.initial_capital = config.initial_capital
        self.bars_since_buy = self.buy_interval  # Buy on first bar
    
    async def on_data(self, data: MarketData, ctx: StrategyContext) -> None:
        self.bars_since_buy += 1
        
        position = await ctx.get_position(data.symbol)
        
        # Check take profit if we have a position
        if position:
            pnl_percent = position.unrealized_pnl_percent / 100
            if pnl_percent > self.take_profit_percent:
                ctx.log(f"TAKE PROFIT: pnl={pnl_percent:.2%}")
                await ctx.place_order(Order(
                    symbol=data.symbol,
                    side=OrderSide.SELL,
                    quantity=position.quantity,
                ))
                return
        
        # DCA buy
        if self.bars_since_buy >= self.buy_interval:
            cash = await ctx.get_cash()
            buy_amount = self.initial_capital * self.buy_amount_percent
            
            if cash >= buy_amount:
                qty = buy_amount / data.close
                ctx.log(f"DCA BUY: amount={buy_amount:.2f}, qty={qty:.4f}")
                await ctx.place_order(Order(
                    symbol=data.symbol,
                    side=OrderSide.BUY,
                    quantity=qty,
                ))
                self.bars_since_buy = 0
    
    def get_state(self) -> Dict[str, Any]:
        return {"bars_since_buy": self.bars_since_buy}
    
    def set_state(self, state: Dict[str, Any]) -> None:
        self.bars_since_buy = state.get("bars_since_buy", 0)


# Strategy registry for easy lookup
STRATEGY_REGISTRY: Dict[str, type] = {
    "simple_momentum": SimpleMomentumStrategy,
    "mean_reversion": MeanReversionStrategy,
    "breakout": BreakoutStrategy,
    "dca": DCAStrategy,
}


def get_strategy(name: str) -> BaseStrategy:
    """Get a strategy instance by name"""
    if name not in STRATEGY_REGISTRY:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGY_REGISTRY.keys())}")
    return STRATEGY_REGISTRY[name]()
