"""
Results parser for Lean backtest output.

Parses Lean JSON output and converts to structured BacktestReport.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .models import (
    BacktestMetrics,
    BacktestReport,
    EquityPoint,
    RiskMetrics,
    TradeDirection,
    TradeRecord,
    TradeStatus,
)


logger = logging.getLogger(__name__)


class ResultsParser:
    """
    Parses Lean QuantConnect backtest results.
    
    Handles the JSON output format from Lean Engine and converts
    it to structured BacktestReport objects.
    """
    
    def parse_file(self, filepath: Union[str, Path]) -> BacktestReport:
        """
        Parse results from a JSON file.
        
        Args:
            filepath: Path to Lean results JSON file
        
        Returns:
            BacktestReport object
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"Results file not found: {filepath}")
        
        with open(filepath, "r") as f:
            data = json.load(f)
        
        return self.parse_dict(data, strategy_name=filepath.stem)
    
    def parse_dict(
        self,
        data: Dict[str, Any],
        strategy_name: str = "Unknown",
    ) -> BacktestReport:
        """
        Parse results from a dictionary.
        
        Args:
            data: Lean results dictionary
            strategy_name: Name of the strategy
        
        Returns:
            BacktestReport object
        """
        # Extract main sections (handle both camelCase and PascalCase)
        statistics = data.get("statistics", data.get("Statistics", {}))
        runtime_stats = data.get("runtimeStatistics", data.get("RuntimeStatistics", {}))
        orders = data.get("orders", data.get("Orders", {}))
        profit_loss = data.get("profitLoss", data.get("ProfitLoss", {}))
        
        # Parse metrics
        metrics = self._parse_metrics(statistics, runtime_stats)
        
        # Parse trades
        trades = self._parse_trades(orders, profit_loss)
        
        # Parse equity curve if available
        equity_curve = self._parse_equity_curve(
            data.get("charts", data.get("Charts", {}))
        )
        
        # Extract capital from statistics (Start Equity and End Equity)
        initial_capital = self._parse_currency(
            statistics.get("Start Equity", "100000")
        )
        final_equity = self._parse_currency(
            statistics.get("End Equity", runtime_stats.get("Equity", "0"))
        )
        
        # Extract dates from algorithmConfiguration or totalPerformance
        algo_config = data.get("algorithmConfiguration", {})
        total_perf = data.get("totalPerformance", {})
        trade_stats = total_perf.get("tradeStatistics", {})
        
        start_date_str = algo_config.get("startDate", trade_stats.get("startDateTime"))
        end_date_str = algo_config.get("endDate", trade_stats.get("endDateTime"))
        
        start_date = self._parse_datetime(start_date_str)
        end_date = self._parse_datetime(end_date_str)
        
        # Count trades from actual filled orders (more accurate than Lean's tradeStatistics
        # which can count dust positions from fee deductions as separate trades)
        if orders:
            filled_orders = [o for o in orders.values() if o.get("status") == 3]  # 3 = Filled
            buy_orders = len([o for o in filled_orders if o.get("direction") == 0])  # 0 = Buy
            sell_orders = len([o for o in filled_orders if o.get("direction") == 1])  # 1 = Sell
            # Round-trip trades = min(buys, sells)
            metrics.total_trades = min(buy_orders, sell_orders)
        elif trade_stats.get("totalNumberOfTrades"):
            # Fallback to Lean's count if no orders available
            metrics.total_trades = int(trade_stats.get("totalNumberOfTrades", 0))
        
        # Get win/loss from tradeStatistics (these are still useful)
        if trade_stats:
            metrics.winning_trades = int(trade_stats.get("numberOfWinningTrades", 0))
            metrics.losing_trades = int(trade_stats.get("numberOfLosingTrades", 0))
        
        # Build report
        report = BacktestReport(
            strategy_name=strategy_name,
            metrics=metrics,
            trades=trades,
            equity_curve=equity_curve,
            initial_capital=initial_capital,
            final_equity=final_equity,
            start_date=start_date,
            end_date=end_date,
            raw_statistics=statistics,
            raw_runtime_statistics=runtime_stats,
        )
        
        return report
    
    def _parse_metrics(
        self,
        statistics: Dict[str, str],
        runtime_stats: Dict[str, str],
    ) -> BacktestMetrics:
        """Parse performance metrics from Lean statistics."""
        metrics = BacktestMetrics()
        
        # Parse returns - use Net Profit for actual return, not annualized
        metrics.total_return_percent = self._parse_percent(
            statistics.get("Net Profit", "0%")  # Actual return, not annualized
        )
        metrics.annual_return_percent = self._parse_percent(
            statistics.get("Compounding Annual Return", "0%")  # Annualized return
        )
        
        net_profit_str = statistics.get("Net Profit", "0%")
        metrics.net_profit = self._parse_percent(net_profit_str)
        metrics.total_return = metrics.net_profit
        
        # Parse trade statistics
        metrics.total_trades = self._parse_int(statistics.get("Total Trades", "0"))
        metrics.win_rate = self._parse_percent(statistics.get("Win Rate", "0%"))
        
        # Calculate winning/losing trades from win rate
        if metrics.total_trades > 0:
            metrics.winning_trades = int(metrics.total_trades * metrics.win_rate / 100)
            metrics.losing_trades = metrics.total_trades - metrics.winning_trades
        
        # Parse P&L statistics
        metrics.average_win = self._parse_percent(statistics.get("Average Win", "0%"))
        metrics.average_loss = abs(self._parse_percent(statistics.get("Average Loss", "0%")))
        
        # Parse ratios
        metrics.profit_factor = self._parse_float(
            statistics.get("Profit-Loss Ratio", "0")
        )
        metrics.expectancy = self._parse_float(statistics.get("Expectancy", "0"))
        
        # Parse fees
        metrics.total_fees = self._parse_currency(statistics.get("Total Fees", "$0"))
        
        # Parse risk metrics
        metrics.risk = self._parse_risk_metrics(statistics)
        
        return metrics
    
    def _parse_risk_metrics(self, statistics: Dict[str, str]) -> RiskMetrics:
        """Parse risk metrics from Lean statistics."""
        risk = RiskMetrics()
        
        # Volatility
        risk.annual_volatility = self._parse_percent(
            statistics.get("Annual Standard Deviation", "0%")
        )
        
        # Drawdown
        risk.max_drawdown_percent = self._parse_percent(
            statistics.get("Drawdown", "0%")
        )
        
        # Risk-adjusted returns
        risk.sharpe_ratio = self._parse_float(statistics.get("Sharpe Ratio", "0"))
        risk.sortino_ratio = self._parse_float(statistics.get("Sortino Ratio", "0"))
        
        # Calculate Calmar ratio
        if risk.max_drawdown_percent > 0:
            annual_return = self._parse_percent(
                statistics.get("Compounding Annual Return", "0%")
            )
            risk.calmar_ratio = annual_return / risk.max_drawdown_percent
        
        # Market correlation
        risk.alpha = self._parse_float(statistics.get("Alpha", "0"))
        risk.beta = self._parse_float(statistics.get("Beta", "0"))
        risk.information_ratio = self._parse_float(
            statistics.get("Information Ratio", "0")
        )
        risk.tracking_error = self._parse_percent(
            statistics.get("Tracking Error", "0%")
        )
        risk.treynor_ratio = self._parse_float(statistics.get("Treynor Ratio", "0"))
        
        return risk
    
    def _parse_trades(
        self,
        orders: Dict[str, Any],
        profit_loss: Dict[str, Any],
    ) -> List[TradeRecord]:
        """Parse trade records from Lean orders."""
        trades = []
        
        # Group orders by symbol to match entries with exits
        # This is a simplified implementation
        for order_id, order in orders.items():
            try:
                symbol = order.get("Symbol", {}).get("Value", "UNKNOWN")
                direction = (
                    TradeDirection.LONG
                    if order.get("Direction") == "Buy"
                    else TradeDirection.SHORT
                )
                
                trade = TradeRecord(
                    id=str(order_id),
                    symbol=symbol,
                    direction=direction,
                    entry_time=self._parse_datetime(order.get("Time", "")),
                    entry_price=order.get("Price", 0),
                    quantity=abs(order.get("Quantity", 0)),
                    fees=order.get("OrderFee", {}).get("Value", {}).get("Amount", 0),
                )
                
                # Try to get P&L from profit_loss dict
                if symbol in profit_loss:
                    trade.pnl = profit_loss[symbol]
                
                trades.append(trade)
                
            except Exception as e:
                logger.warning(f"Failed to parse order {order_id}: {e}")
                continue
        
        return trades
    
    def _parse_equity_curve(
        self,
        charts: Dict[str, Any],
    ) -> List[EquityPoint]:
        """Parse equity curve from Lean charts data."""
        equity_curve = []
        
        # Look for Strategy Equity chart
        strategy_equity = charts.get("Strategy Equity", {})
        series = strategy_equity.get("Series", {})
        equity_series = series.get("Equity", {}).get("Values", [])
        
        peak_equity = 0
        
        for point in equity_series:
            try:
                timestamp = self._parse_timestamp(point.get("x", 0))
                equity = point.get("y", 0)
                
                # Track peak for drawdown calculation
                if equity > peak_equity:
                    peak_equity = equity
                
                drawdown = peak_equity - equity
                drawdown_percent = (drawdown / peak_equity * 100) if peak_equity > 0 else 0
                
                equity_point = EquityPoint(
                    timestamp=timestamp,
                    equity=equity,
                    cash=0,  # Not always available
                    holdings_value=0,
                    drawdown=drawdown,
                    drawdown_percent=drawdown_percent,
                )
                equity_curve.append(equity_point)
                
            except Exception as e:
                logger.warning(f"Failed to parse equity point: {e}")
                continue
        
        return equity_curve
    
    def _parse_percent(self, value: str) -> float:
        """Parse percentage string to float."""
        if not value:
            return 0.0
        
        # Remove % sign and parse
        clean = value.replace("%", "").replace(",", "").strip()
        try:
            return float(clean)
        except ValueError:
            return 0.0
    
    def _parse_currency(self, value: str) -> float:
        """Parse currency string to float."""
        if not value:
            return 0.0
        
        # Remove currency symbols and parse
        clean = re.sub(r"[^\d.-]", "", str(value))
        try:
            return float(clean)
        except ValueError:
            return 0.0
    
    def _parse_float(self, value: str) -> float:
        """Parse float string."""
        if not value:
            return 0.0
        
        clean = str(value).replace(",", "").strip()
        try:
            return float(clean)
        except ValueError:
            return 0.0
    
    def _parse_int(self, value: str) -> int:
        """Parse integer string."""
        if not value:
            return 0
        
        clean = str(value).replace(",", "").strip()
        try:
            return int(float(clean))
        except ValueError:
            return 0
    
    def _parse_datetime(self, value: str) -> Optional[datetime]:
        """Parse datetime string."""
        if not value:
            return None
        
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(str(value)[:19], fmt[:min(len(str(value)), 19)])
            except ValueError:
                continue
        
        return None
    
    def _parse_timestamp(self, value: int) -> datetime:
        """Parse Unix timestamp (seconds or milliseconds)."""
        if value > 1e12:  # Milliseconds
            return datetime.fromtimestamp(value / 1000)
        return datetime.fromtimestamp(value)
    
    def generate_summary_text(self, report: BacktestReport) -> str:
        """
        Generate a human-readable summary of backtest results.
        
        Args:
            report: BacktestReport to summarize
        
        Returns:
            Formatted text summary
        """
        m = report.metrics
        r = m.risk
        
        lines = [
            "=" * 60,
            f"  BACKTEST RESULTS: {report.strategy_name}",
            "=" * 60,
            "",
            f"  Period: {report.start_date or 'N/A'} to {report.end_date or 'N/A'}",
            f"  Initial Capital: ${report.initial_capital:,.2f}",
            f"  Final Equity:    ${report.final_equity:,.2f}",
            "",
            "  RETURNS",
            f"    Total Return:      {m.total_return_percent:+.2f}%",
            f"    Net Profit:        ${m.net_profit:,.2f}",
            "",
            "  RISK METRICS",
            f"    Sharpe Ratio:      {r.sharpe_ratio:.2f}",
            f"    Max Drawdown:      {r.max_drawdown_percent:.2f}%",
            f"    Annual Volatility: {r.annual_volatility:.2f}%",
            "",
            "  TRADE STATISTICS",
            f"    Total Trades:      {m.total_trades}",
            f"    Win Rate:          {m.win_rate:.1f}%",
            f"    Profit Factor:     {m.profit_factor:.2f}",
            f"    Expectancy:        {m.expectancy:.4f}",
            "",
            "=" * 60,
        ]
        
        return "\n".join(lines)
    
    def compare_reports(
        self,
        reports: List[BacktestReport],
    ) -> Dict[str, Any]:
        """
        Compare multiple backtest reports.
        
        Args:
            reports: List of BacktestReport objects
        
        Returns:
            Comparison summary
        """
        if not reports:
            return {}
        
        comparison = {
            "strategies": [],
            "best_return": None,
            "best_sharpe": None,
            "lowest_drawdown": None,
        }
        
        best_return = float("-inf")
        best_sharpe = float("-inf")
        lowest_dd = float("inf")
        
        for report in reports:
            summary = {
                "name": report.strategy_name,
                "return_percent": report.metrics.total_return_percent,
                "sharpe_ratio": report.metrics.risk.sharpe_ratio,
                "max_drawdown": report.metrics.risk.max_drawdown_percent,
                "total_trades": report.metrics.total_trades,
                "win_rate": report.metrics.win_rate,
            }
            comparison["strategies"].append(summary)
            
            if report.metrics.total_return_percent > best_return:
                best_return = report.metrics.total_return_percent
                comparison["best_return"] = report.strategy_name
            
            if report.metrics.risk.sharpe_ratio > best_sharpe:
                best_sharpe = report.metrics.risk.sharpe_ratio
                comparison["best_sharpe"] = report.strategy_name
            
            if report.metrics.risk.max_drawdown_percent < lowest_dd:
                lowest_dd = report.metrics.risk.max_drawdown_percent
                comparison["lowest_drawdown"] = report.strategy_name
        
        return comparison
