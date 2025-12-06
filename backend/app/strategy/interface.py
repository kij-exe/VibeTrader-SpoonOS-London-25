"""
Strategy Interface Definition

Abstract interface that all trading strategies must implement.
Compatible with both backtesting and live deployment.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# =============================================================================
# Enums
# =============================================================================

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class Signal(Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class OHLCV:
    """Single candlestick/bar of market data"""
    timestamp: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    bid: Optional[float] = None
    ask: Optional[float] = None


@dataclass
class MarketData:
    """Market data snapshot with history for indicator calculation"""
    current: OHLCV
    history: List[OHLCV] = field(default_factory=list)
    
    @property
    def symbol(self) -> str:
        return self.current.symbol
    
    @property
    def timestamp(self) -> datetime:
        return self.current.timestamp
    
    @property
    def close(self) -> float:
        return self.current.close
    
    @property
    def open(self) -> float:
        return self.current.open
    
    @property
    def high(self) -> float:
        return self.current.high
    
    @property
    def low(self) -> float:
        return self.current.low
    
    @property
    def volume(self) -> float:
        return self.current.volume
    
    def closes(self, periods: int = None) -> List[float]:
        prices = [self.current.close] + [bar.close for bar in self.history]
        return prices[:periods] if periods else prices
    
    def opens(self, periods: int = None) -> List[float]:
        prices = [self.current.open] + [bar.open for bar in self.history]
        return prices[:periods] if periods else prices
    
    def highs(self, periods: int = None) -> List[float]:
        prices = [self.current.high] + [bar.high for bar in self.history]
        return prices[:periods] if periods else prices
    
    def lows(self, periods: int = None) -> List[float]:
        prices = [self.current.low] + [bar.low for bar in self.history]
        return prices[:periods] if periods else prices
    
    def volumes(self, periods: int = None) -> List[float]:
        vols = [self.current.volume] + [bar.volume for bar in self.history]
        return vols[:periods] if periods else vols


@dataclass
class Order:
    """Order to be submitted for execution"""
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType = OrderType.MARKET
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    id: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass
class OrderResult:
    """Result of an order execution"""
    order_id: str
    status: OrderStatus
    filled_quantity: float
    filled_price: float
    timestamp: datetime
    commission: float = 0.0
    message: Optional[str] = None


@dataclass
class Position:
    """Current position in an asset"""
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    timestamp: datetime
    
    @property
    def side(self) -> Optional[OrderSide]:
        if self.quantity > 0:
            return OrderSide.BUY
        elif self.quantity < 0:
            return OrderSide.SELL
        return None
    
    @property
    def unrealized_pnl(self) -> float:
        return (self.current_price - self.entry_price) * self.quantity
    
    @property
    def unrealized_pnl_percent(self) -> float:
        if self.entry_price == 0:
            return 0.0
        return ((self.current_price - self.entry_price) / self.entry_price) * 100
    
    @property
    def market_value(self) -> float:
        return abs(self.quantity * self.current_price)


@dataclass
class Portfolio:
    """Portfolio state snapshot"""
    cash: float
    positions: Dict[str, Position] = field(default_factory=dict)
    timestamp: Optional[datetime] = None
    
    @property
    def total_value(self) -> float:
        positions_value = sum(p.market_value for p in self.positions.values())
        return self.cash + positions_value
    
    @property
    def unrealized_pnl(self) -> float:
        return sum(p.unrealized_pnl for p in self.positions.values())


@dataclass 
class StrategyMetrics:
    """Performance metrics for strategy evaluation"""
    total_return: float = 0.0
    total_return_percent: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_percent: float = 0.0
    volatility: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_return": self.total_return,
            "total_return_percent": self.total_return_percent,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_percent": self.max_drawdown_percent,
            "volatility": self.volatility,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "average_win": self.average_win,
            "average_loss": self.average_loss,
            "profit_factor": self.profit_factor,
            "expectancy": self.expectancy,
        }


@dataclass
class StrategyConfig:
    """Configuration parameters for a strategy"""
    symbol: str
    initial_capital: float
    max_position_size: float = 1.0
    max_drawdown_limit: float = 0.2
    stop_loss_percent: Optional[float] = None
    take_profit_percent: Optional[float] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        return self.parameters.get(key, default)


# =============================================================================
# Strategy Context (Injected by Engine)
# =============================================================================

class StrategyContext(ABC):
    """
    Abstract context injected by execution engine.
    Same strategy code runs in backtest/paper/live mode.
    """
    
    @abstractmethod
    async def get_portfolio(self) -> Portfolio:
        """Get current portfolio state"""
        pass
    
    @abstractmethod
    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for symbol, None if none"""
        pass
    
    @abstractmethod
    async def get_cash(self) -> float:
        """Get available cash"""
        pass
    
    @abstractmethod
    async def place_order(self, order: Order) -> OrderResult:
        """Submit order for execution"""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel pending order"""
        pass
    
    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get list of open/pending orders"""
        pass
    
    @abstractmethod
    async def get_historical_data(
        self, symbol: str, periods: int, timeframe: str = "1h"
    ) -> List[OHLCV]:
        """Fetch historical data (respects simulation time in backtest)"""
        pass
    
    @abstractmethod
    def get_current_time(self) -> datetime:
        """Current time (simulated in backtest, real in live)"""
        pass
    
    @abstractmethod
    def log(self, message: str, level: str = "info") -> None:
        """Log message for debugging/audit"""
        pass


# =============================================================================
# Base Strategy Interface
# =============================================================================

class BaseStrategy(ABC):
    """
    Abstract base for all trading strategies.
    
    Implement to create strategies that can be:
    - Submitted as challenge responses
    - Backtested against historical data
    - Deployed for live trading
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique strategy identifier"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Strategy version"""
        pass
    
    @property
    def description(self) -> str:
        """Human-readable description"""
        return ""
    
    @abstractmethod
    def configure(self, config: StrategyConfig) -> None:
        """Initialize with config. Called once before data processing."""
        pass
    
    @abstractmethod
    async def on_data(self, data: MarketData, ctx: StrategyContext) -> None:
        """
        Main logic - called on each new data point.
        Implement signal generation, order placement, position management.
        """
        pass
    
    async def on_order_filled(
        self, order: Order, result: OrderResult, ctx: StrategyContext
    ) -> None:
        """Called when order fills. Override for post-fill logic."""
        pass
    
    async def on_start(self, ctx: StrategyContext) -> None:
        """Called before first data. Override for init logic."""
        pass
    
    async def on_stop(self, ctx: StrategyContext) -> None:
        """Called on stop. Override for cleanup (e.g., close positions)."""
        pass
    
    def get_state(self) -> Dict[str, Any]:
        """Serialize state for persistence. Override to save custom state."""
        return {}
    
    def set_state(self, state: Dict[str, Any]) -> None:
        """Restore state. Override to load custom state."""
        pass
    
    def validate(self) -> List[str]:
        """Validate config. Returns list of errors (empty if valid)."""
        return []
