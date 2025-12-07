"""
Data models for backtest results.

Provides structured representations of Lean backtest output.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class TradeDirection(str, Enum):
    """Trade direction."""
    LONG = "long"
    SHORT = "short"


class TradeStatus(str, Enum):
    """Trade status."""
    OPEN = "open"
    CLOSED = "closed"


@dataclass
class TradeRecord:
    """Record of a single trade."""
    id: str
    symbol: str
    direction: TradeDirection
    
    entry_time: datetime
    entry_price: float
    quantity: float
    
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    
    pnl: float = 0.0
    pnl_percent: float = 0.0
    
    fees: float = 0.0
    status: TradeStatus = TradeStatus.CLOSED
    
    # Additional metadata
    duration_hours: Optional[float] = None
    max_favorable_excursion: Optional[float] = None  # Best unrealized P&L
    max_adverse_excursion: Optional[float] = None    # Worst unrealized P&L
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "direction": self.direction.value,
            "entry_time": self.entry_time.isoformat() if self.entry_time else None,
            "entry_price": self.entry_price,
            "quantity": self.quantity,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "exit_price": self.exit_price,
            "pnl": self.pnl,
            "pnl_percent": self.pnl_percent,
            "fees": self.fees,
            "status": self.status.value,
            "duration_hours": self.duration_hours,
        }


@dataclass
class EquityPoint:
    """Single point on the equity curve."""
    timestamp: datetime
    equity: float
    cash: float
    holdings_value: float
    drawdown: float = 0.0
    drawdown_percent: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "equity": self.equity,
            "cash": self.cash,
            "holdings_value": self.holdings_value,
            "drawdown": self.drawdown,
            "drawdown_percent": self.drawdown_percent,
        }


@dataclass
class RiskMetrics:
    """Risk-related metrics."""
    # Volatility
    annual_volatility: float = 0.0
    daily_volatility: float = 0.0
    
    # Drawdown
    max_drawdown: float = 0.0
    max_drawdown_percent: float = 0.0
    max_drawdown_duration_days: int = 0
    average_drawdown: float = 0.0
    
    # Risk-adjusted returns
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # Market correlation
    alpha: float = 0.0
    beta: float = 0.0
    information_ratio: float = 0.0
    tracking_error: float = 0.0
    treynor_ratio: float = 0.0
    
    # Value at Risk
    var_95: float = 0.0  # 95% VaR
    var_99: float = 0.0  # 99% VaR
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "annual_volatility": self.annual_volatility,
            "daily_volatility": self.daily_volatility,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_percent": self.max_drawdown_percent,
            "max_drawdown_duration_days": self.max_drawdown_duration_days,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "calmar_ratio": self.calmar_ratio,
            "alpha": self.alpha,
            "beta": self.beta,
            "var_95": self.var_95,
        }


@dataclass
class BacktestMetrics:
    """Core performance metrics from backtest."""
    # Returns
    total_return: float = 0.0
    total_return_percent: float = 0.0
    annual_return: float = 0.0
    annual_return_percent: float = 0.0
    
    # Trade statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # P&L statistics
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    net_profit: float = 0.0
    
    average_win: float = 0.0
    average_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    # Ratios
    profit_factor: float = 0.0
    expectancy: float = 0.0
    profit_loss_ratio: float = 0.0
    
    # Fees
    total_fees: float = 0.0
    
    # Risk metrics
    risk: RiskMetrics = field(default_factory=RiskMetrics)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "returns": {
                "total_return": self.total_return,
                "total_return_percent": self.total_return_percent,
                "annual_return": self.annual_return,
                "annual_return_percent": self.annual_return_percent,
            },
            "trades": {
                "total_trades": self.total_trades,
                "winning_trades": self.winning_trades,
                "losing_trades": self.losing_trades,
                "win_rate": self.win_rate,
            },
            "pnl": {
                "gross_profit": self.gross_profit,
                "gross_loss": self.gross_loss,
                "net_profit": self.net_profit,
                "average_win": self.average_win,
                "average_loss": self.average_loss,
                "largest_win": self.largest_win,
                "largest_loss": self.largest_loss,
            },
            "ratios": {
                "profit_factor": self.profit_factor,
                "expectancy": self.expectancy,
                "profit_loss_ratio": self.profit_loss_ratio,
            },
            "fees": self.total_fees,
            "risk": self.risk.to_dict(),
        }


@dataclass
class BacktestReport:
    """
    Complete backtest report.
    
    Contains all information from a backtest run in a structured format
    suitable for display, storage, and analysis.
    """
    # Identification
    strategy_name: str
    strategy_version: str = "1.0.0"
    backtest_id: str = ""
    
    # Configuration
    symbol: str = ""
    initial_capital: float = 0.0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Results
    final_equity: float = 0.0
    metrics: BacktestMetrics = field(default_factory=BacktestMetrics)
    
    # Detailed data
    trades: List[TradeRecord] = field(default_factory=list)
    equity_curve: List[EquityPoint] = field(default_factory=list)
    
    # Execution info
    execution_time_seconds: float = 0.0
    generated_at: datetime = field(default_factory=datetime.now)
    
    # Raw data (from Lean)
    raw_statistics: Dict[str, Any] = field(default_factory=dict)
    raw_runtime_statistics: Dict[str, Any] = field(default_factory=dict)
    
    # Status
    success: bool = True
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "strategy": {
                "name": self.strategy_name,
                "version": self.strategy_version,
                "backtest_id": self.backtest_id,
            },
            "configuration": {
                "symbol": self.symbol,
                "initial_capital": self.initial_capital,
                "start_date": self.start_date.isoformat() if self.start_date else None,
                "end_date": self.end_date.isoformat() if self.end_date else None,
            },
            "results": {
                "final_equity": self.final_equity,
                "metrics": self.metrics.to_dict(),
            },
            "trades": {
                "count": len(self.trades),
                "records": [t.to_dict() for t in self.trades[:100]],  # Limit for size
            },
            "equity_curve": {
                "points": len(self.equity_curve),
                "data": [e.to_dict() for e in self.equity_curve[::max(1, len(self.equity_curve)//100)]],  # Sample
            },
            "execution": {
                "time_seconds": self.execution_time_seconds,
                "generated_at": self.generated_at.isoformat(),
            },
            "status": {
                "success": self.success,
                "error_message": self.error_message,
                "warnings": self.warnings,
            },
        }
    
    def to_summary(self) -> Dict[str, Any]:
        """Get a condensed summary for quick display."""
        return {
            "strategy": self.strategy_name,
            "symbol": self.symbol,
            "period": f"{self.start_date.strftime('%Y-%m-%d') if self.start_date else '?'} to {self.end_date.strftime('%Y-%m-%d') if self.end_date else '?'}",
            "initial_capital": f"${self.initial_capital:,.2f}",
            "final_equity": f"${self.final_equity:,.2f}",
            "total_return": f"{self.metrics.total_return_percent:+.2f}%",
            "sharpe_ratio": f"{self.metrics.risk.sharpe_ratio:.2f}",
            "max_drawdown": f"{self.metrics.risk.max_drawdown_percent:.2f}%",
            "total_trades": self.metrics.total_trades,
            "win_rate": f"{self.metrics.win_rate:.1f}%",
            "profit_factor": f"{self.metrics.profit_factor:.2f}",
            "success": self.success,
        }
    
    def get_evaluation_score(self) -> Dict[str, Any]:
        """
        Generate evaluation scores for the strategy.
        
        Returns scores on 1-3 scale for different aspects.
        """
        # Performance score (based on returns and Sharpe)
        if self.metrics.total_return_percent > 20 and self.metrics.risk.sharpe_ratio > 1.5:
            performance_score = 3
        elif self.metrics.total_return_percent > 5 and self.metrics.risk.sharpe_ratio > 0.5:
            performance_score = 2
        else:
            performance_score = 1
        
        # Risk score (based on drawdown and volatility)
        if self.metrics.risk.max_drawdown_percent < 10:
            risk_score = 3  # Low risk
        elif self.metrics.risk.max_drawdown_percent < 25:
            risk_score = 2  # Medium risk
        else:
            risk_score = 1  # High risk
        
        # Consistency score (based on win rate and profit factor)
        if self.metrics.win_rate > 55 and self.metrics.profit_factor > 1.5:
            consistency_score = 3
        elif self.metrics.win_rate > 45 and self.metrics.profit_factor > 1.0:
            consistency_score = 2
        else:
            consistency_score = 1
        
        return {
            "performance_score": performance_score,
            "risk_score": risk_score,
            "consistency_score": consistency_score,
            "overall_score": round((performance_score + risk_score + consistency_score) / 3, 1),
            "evaluation_text": self._generate_evaluation_text(
                performance_score, risk_score, consistency_score
            ),
        }
    
    def _generate_evaluation_text(
        self,
        performance: int,
        risk: int,
        consistency: int,
    ) -> str:
        """Generate human-readable evaluation text."""
        texts = []
        
        # Performance
        if performance == 3:
            texts.append("Excellent returns with strong risk-adjusted performance.")
        elif performance == 2:
            texts.append("Moderate returns with acceptable risk-adjusted metrics.")
        else:
            texts.append("Below-average returns or poor risk-adjusted performance.")
        
        # Risk
        if risk == 3:
            texts.append("Low drawdown indicates good risk management.")
        elif risk == 2:
            texts.append("Moderate drawdown within acceptable limits.")
        else:
            texts.append("High drawdown suggests significant risk exposure.")
        
        # Consistency
        if consistency == 3:
            texts.append("Consistent winning trades with favorable profit factor.")
        elif consistency == 2:
            texts.append("Reasonable trade consistency.")
        else:
            texts.append("Inconsistent results or unfavorable profit factor.")
        
        return " ".join(texts)
