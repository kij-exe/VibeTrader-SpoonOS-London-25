"""
Backtest Engine

Simulates strategy execution against historical data.
Implements StrategyContext for the simulation environment.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from app.strategy.interface import (
    BaseStrategy,
    MarketData,
    OHLCV,
    Order,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    Portfolio,
    Position,
    StrategyConfig,
    StrategyContext,
    StrategyMetrics,
)

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Record of a completed trade"""
    id: str
    symbol: str
    side: OrderSide
    entry_price: float
    exit_price: float
    quantity: float
    entry_time: datetime
    exit_time: datetime
    pnl: float
    pnl_percent: float
    commission: float = 0.0


@dataclass
class BacktestConfig:
    """Configuration for backtest execution"""
    initial_capital: float = 10000.0
    commission_rate: float = 0.001  # 0.1% per trade
    slippage_rate: float = 0.0005  # 0.05% slippage
    history_bars: int = 100  # Bars of history to provide to strategy


@dataclass
class BacktestResult:
    """Complete results from a backtest run"""
    metrics: StrategyMetrics
    trades: List[Trade]
    equity_curve: List[Dict[str, Any]]
    config: BacktestConfig
    strategy_name: str
    strategy_version: str
    start_time: datetime
    end_time: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": {
                "name": self.strategy_name,
                "version": self.strategy_version,
            },
            "period": {
                "start": self.start_time.isoformat(),
                "end": self.end_time.isoformat(),
            },
            "metrics": self.metrics.to_dict(),
            "total_trades": len(self.trades),
            "equity_curve_points": len(self.equity_curve),
        }


class BacktestContext(StrategyContext):
    """
    StrategyContext implementation for backtesting.
    Simulates order execution and portfolio management.
    """
    
    def __init__(
        self,
        config: BacktestConfig,
        data: List[OHLCV],
        on_log: Optional[Callable[[str, str], None]] = None,
    ):
        self.config = config
        self.data = data
        self.on_log = on_log
        
        # State
        self.cash = config.initial_capital
        self.positions: Dict[str, Position] = {}
        self.open_orders: List[Order] = []
        self.completed_trades: List[Trade] = []
        self.equity_curve: List[Dict[str, Any]] = []
        
        # Current simulation state
        self.current_index = 0
        self.current_bar: Optional[OHLCV] = None
        
        # Build symbol -> data index map for historical lookups
        self._data_by_symbol: Dict[str, List[OHLCV]] = {}
        for bar in data:
            if bar.symbol not in self._data_by_symbol:
                self._data_by_symbol[bar.symbol] = []
            self._data_by_symbol[bar.symbol].append(bar)
    
    def _get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol"""
        if self.current_bar and self.current_bar.symbol == symbol:
            return self.current_bar.close
        # Look up in positions
        if symbol in self.positions:
            return self.positions[symbol].current_price
        return 0.0
    
    def _apply_slippage(self, price: float, side: OrderSide) -> float:
        """Apply slippage to execution price"""
        slippage = price * self.config.slippage_rate
        if side == OrderSide.BUY:
            return price + slippage
        return price - slippage
    
    def _calculate_commission(self, quantity: float, price: float) -> float:
        """Calculate commission for a trade"""
        return abs(quantity * price * self.config.commission_rate)
    
    def set_current_bar(self, index: int, bar: OHLCV) -> None:
        """Set current simulation bar (called by engine)"""
        self.current_index = index
        self.current_bar = bar
        
        # Update position prices
        if bar.symbol in self.positions:
            self.positions[bar.symbol].current_price = bar.close
            self.positions[bar.symbol].timestamp = bar.timestamp
    
    def record_equity(self) -> None:
        """Record current equity for equity curve"""
        if self.current_bar:
            portfolio = Portfolio(
                cash=self.cash,
                positions=self.positions.copy(),
                timestamp=self.current_bar.timestamp,
            )
            self.equity_curve.append({
                "timestamp": self.current_bar.timestamp.isoformat(),
                "equity": portfolio.total_value,
                "cash": self.cash,
                "positions_value": portfolio.total_value - self.cash,
            })
    
    # StrategyContext implementation
    
    async def get_portfolio(self) -> Portfolio:
        return Portfolio(
            cash=self.cash,
            positions=self.positions.copy(),
            timestamp=self.current_bar.timestamp if self.current_bar else None,
        )
    
    async def get_position(self, symbol: str) -> Optional[Position]:
        return self.positions.get(symbol)
    
    async def get_cash(self) -> float:
        return self.cash
    
    async def place_order(self, order: Order) -> OrderResult:
        """Execute order immediately (market orders) or queue (limit orders)"""
        order.id = str(uuid.uuid4())
        order.timestamp = self.current_bar.timestamp if self.current_bar else datetime.now()
        
        self.log(f"Placing order: {order.side.value} {order.quantity:.4f} {order.symbol}", "debug")
        
        if order.order_type == OrderType.MARKET:
            result = await self._execute_market_order(order)
            self.log(f"Order result: {result.status.value}, filled={result.filled_quantity:.4f} @ {result.filled_price:.2f} msg={result.message}", "debug")
            return result
        else:
            # Queue limit orders for later processing
            self.open_orders.append(order)
            return OrderResult(
                order_id=order.id,
                status=OrderStatus.PENDING,
                filled_quantity=0,
                filled_price=0,
                timestamp=order.timestamp,
            )
    
    async def _execute_market_order(self, order: Order) -> OrderResult:
        """Execute a market order immediately"""
        if not self.current_bar:
            return OrderResult(
                order_id=order.id,
                status=OrderStatus.REJECTED,
                filled_quantity=0,
                filled_price=0,
                timestamp=datetime.now(),
                message="No current market data",
            )
        
        base_price = self.current_bar.close
        exec_price = self._apply_slippage(base_price, order.side)
        commission = self._calculate_commission(order.quantity, exec_price)
        
        if order.side == OrderSide.BUY:
            total_cost = (order.quantity * exec_price) + commission
            if total_cost > self.cash:
                return OrderResult(
                    order_id=order.id,
                    status=OrderStatus.REJECTED,
                    filled_quantity=0,
                    filled_price=0,
                    timestamp=self.current_bar.timestamp,
                    message="Insufficient funds",
                )
            
            self.cash -= total_cost
            
            # Update or create position
            if order.symbol in self.positions:
                pos = self.positions[order.symbol]
                total_qty = pos.quantity + order.quantity
                avg_price = (
                    (pos.entry_price * pos.quantity) + (exec_price * order.quantity)
                ) / total_qty
                pos.quantity = total_qty
                pos.entry_price = avg_price
                pos.current_price = exec_price
            else:
                self.positions[order.symbol] = Position(
                    symbol=order.symbol,
                    quantity=order.quantity,
                    entry_price=exec_price,
                    current_price=exec_price,
                    timestamp=self.current_bar.timestamp,
                )
        
        else:  # SELL
            if order.symbol not in self.positions:
                return OrderResult(
                    order_id=order.id,
                    status=OrderStatus.REJECTED,
                    filled_quantity=0,
                    filled_price=0,
                    timestamp=self.current_bar.timestamp,
                    message="No position to sell",
                )
            
            pos = self.positions[order.symbol]
            sell_qty = min(order.quantity, pos.quantity)
            
            proceeds = (sell_qty * exec_price) - commission
            self.cash += proceeds
            
            # Record trade
            pnl = (exec_price - pos.entry_price) * sell_qty - commission
            pnl_percent = ((exec_price - pos.entry_price) / pos.entry_price) * 100
            
            trade = Trade(
                id=str(uuid.uuid4()),
                symbol=order.symbol,
                side=OrderSide.SELL,
                entry_price=pos.entry_price,
                exit_price=exec_price,
                quantity=sell_qty,
                entry_time=pos.timestamp,
                exit_time=self.current_bar.timestamp,
                pnl=pnl,
                pnl_percent=pnl_percent,
                commission=commission,
            )
            self.completed_trades.append(trade)
            
            # Update or remove position
            pos.quantity -= sell_qty
            if pos.quantity <= 0:
                del self.positions[order.symbol]
        
        return OrderResult(
            order_id=order.id,
            status=OrderStatus.FILLED,
            filled_quantity=order.quantity,
            filled_price=exec_price,
            timestamp=self.current_bar.timestamp,
            commission=commission,
        )
    
    async def cancel_order(self, order_id: str) -> bool:
        for i, order in enumerate(self.open_orders):
            if order.id == order_id:
                self.open_orders.pop(i)
                return True
        return False
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        if symbol:
            return [o for o in self.open_orders if o.symbol == symbol]
        return self.open_orders.copy()
    
    async def get_historical_data(
        self, symbol: str, periods: int, timeframe: str = "1h"
    ) -> List[OHLCV]:
        """Get historical data up to current simulation time"""
        if symbol not in self._data_by_symbol:
            return []
        
        symbol_data = self._data_by_symbol[symbol]
        
        # Find current position in symbol data
        current_time = self.current_bar.timestamp if self.current_bar else datetime.now()
        
        # Get bars before current time
        historical = [bar for bar in symbol_data if bar.timestamp < current_time]
        
        # Return most recent 'periods' bars
        return historical[-periods:] if len(historical) > periods else historical
    
    def get_current_time(self) -> datetime:
        if self.current_bar:
            return self.current_bar.timestamp
        return datetime.now()
    
    def log(self, message: str, level: str = "info") -> None:
        if self.on_log:
            self.on_log(message, level)
        else:
            log_func = getattr(logger, level, logger.info)
            log_func(f"[Strategy] {message}")


class BacktestEngine:
    """
    Engine that runs backtests against historical data.
    """
    
    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()
        self.logs: List[Dict[str, Any]] = []
    
    def _on_log(self, message: str, level: str) -> None:
        """Capture strategy logs"""
        self.logs.append({
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
        })
    
    def _calculate_metrics(
        self,
        ctx: BacktestContext,
        start_time: datetime,
        end_time: datetime,
    ) -> StrategyMetrics:
        """Calculate performance metrics from backtest results"""
        metrics = StrategyMetrics(start_time=start_time, end_time=end_time)
        
        trades = ctx.completed_trades
        equity_curve = ctx.equity_curve
        
        if not equity_curve:
            return metrics
        
        initial_equity = self.config.initial_capital
        final_equity = equity_curve[-1]["equity"] if equity_curve else initial_equity
        
        # Returns
        metrics.total_return = final_equity - initial_equity
        metrics.total_return_percent = (
            (final_equity - initial_equity) / initial_equity
        ) * 100
        
        # Trade statistics
        metrics.total_trades = len(trades)
        if trades:
            winning = [t for t in trades if t.pnl > 0]
            losing = [t for t in trades if t.pnl <= 0]
            
            metrics.winning_trades = len(winning)
            metrics.losing_trades = len(losing)
            metrics.win_rate = len(winning) / len(trades) * 100
            
            if winning:
                metrics.average_win = sum(t.pnl for t in winning) / len(winning)
            if losing:
                metrics.average_loss = abs(sum(t.pnl for t in losing) / len(losing))
            
            gross_profit = sum(t.pnl for t in winning) if winning else 0
            gross_loss = abs(sum(t.pnl for t in losing)) if losing else 0
            
            if gross_loss > 0:
                metrics.profit_factor = gross_profit / gross_loss
            
            metrics.expectancy = sum(t.pnl for t in trades) / len(trades)
        
        # Drawdown calculation
        if len(equity_curve) > 1:
            equities = [e["equity"] for e in equity_curve]
            peak = equities[0]
            max_dd = 0
            max_dd_pct = 0
            
            for equity in equities:
                if equity > peak:
                    peak = equity
                dd = peak - equity
                dd_pct = (dd / peak) * 100 if peak > 0 else 0
                
                if dd > max_dd:
                    max_dd = dd
                if dd_pct > max_dd_pct:
                    max_dd_pct = dd_pct
            
            metrics.max_drawdown = max_dd
            metrics.max_drawdown_percent = max_dd_pct
        
        # Volatility and Sharpe (simplified)
        if len(equity_curve) > 1:
            returns = []
            for i in range(1, len(equity_curve)):
                prev = equity_curve[i - 1]["equity"]
                curr = equity_curve[i]["equity"]
                if prev > 0:
                    returns.append((curr - prev) / prev)
            
            if returns:
                import statistics
                metrics.volatility = statistics.stdev(returns) * 100 if len(returns) > 1 else 0
                
                avg_return = statistics.mean(returns)
                if metrics.volatility > 0:
                    # Annualized Sharpe (assuming daily data, 252 trading days)
                    metrics.sharpe_ratio = (avg_return / (metrics.volatility / 100)) * (252 ** 0.5)
        
        return metrics
    
    async def run(
        self,
        strategy: BaseStrategy,
        data: List[OHLCV],
        config: StrategyConfig,
    ) -> BacktestResult:
        """
        Run backtest for a strategy against historical data.
        
        Args:
            strategy: Strategy instance to test
            data: Historical OHLCV data (sorted by timestamp)
            config: Strategy configuration
        
        Returns:
            BacktestResult with metrics, trades, and equity curve
        """
        if not data:
            raise ValueError("No data provided for backtest")
        
        # Sort data by timestamp
        data = sorted(data, key=lambda x: x.timestamp)
        
        # Initialize context
        ctx = BacktestContext(
            config=self.config,
            data=data,
            on_log=self._on_log,
        )
        
        # Configure and start strategy
        strategy.configure(config)
        await strategy.on_start(ctx)
        
        start_time = data[0].timestamp
        end_time = data[-1].timestamp
        
        # Build history buffer
        history_buffer: List[OHLCV] = []
        
        # Process each bar
        for i, bar in enumerate(data):
            ctx.set_current_bar(i, bar)
            
            # Build market data with history
            market_data = MarketData(
                current=bar,
                history=history_buffer[-self.config.history_bars:].copy(),
            )
            
            # Call strategy
            try:
                await strategy.on_data(market_data, ctx)
            except Exception as e:
                ctx.log(f"Error in on_data: {e}", "error")
            
            # Record equity
            ctx.record_equity()
            
            # Add to history buffer
            history_buffer.append(bar)
            if len(history_buffer) > self.config.history_bars:
                history_buffer.pop(0)
        
        # Stop strategy
        await strategy.on_stop(ctx)
        
        # Calculate metrics
        metrics = self._calculate_metrics(ctx, start_time, end_time)
        
        return BacktestResult(
            metrics=metrics,
            trades=ctx.completed_trades,
            equity_curve=ctx.equity_curve,
            config=self.config,
            strategy_name=strategy.name,
            strategy_version=strategy.version,
            start_time=start_time,
            end_time=end_time,
        )
