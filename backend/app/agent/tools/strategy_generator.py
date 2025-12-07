"""Strategy code generation tool using strategy requirements."""

from typing import Dict, List
from spoon_ai.tools.base import BaseTool


class StrategyGeneratorTool(BaseTool):
    """Generate complete Lean QuantConnect strategy code from requirements."""
    
    name: str = "generate_lean_strategy"
    description: str = """Generate complete, runnable Lean QuantConnect strategy code.
    Provide the strategy requirements and this will generate properly structured Python code with:
    - Correct imports and class structure
    - Indicator initialization
    - Trading logic based on entry/exit conditions  
    - Proper warmup periods
    - All required Lean boilerplate
    
    Parameters:
    - strategy_name: Name for the strategy class (PascalCase, e.g., "RSIMeanReversion")
    - requirements: Dict with symbol, timeframe, entry_conditions, exit_conditions, risk_management"""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "strategy_name": {
                "type": "string",
                "description": "Strategy class name in PascalCase (e.g., RSIMeanReversion)"
            },
            "requirements": {
                "type": "object",
                "description": "Strategy requirements with symbol, timeframe, entry_conditions, exit_conditions",
                "properties": {
                    "symbol": {"type": "string"},
                    "timeframe": {"type": "string"},
                    "entry_conditions": {"type": "string"},
                    "exit_conditions": {"type": "string"},
                    "risk_management": {"type": "string"}
                }
            }
        },
        "required": ["strategy_name", "requirements"]
    }
    
    async def execute(self, strategy_name: str, requirements: Dict) -> str:
        """Generate strategy code from requirements."""
        
        symbol = requirements.get("symbol", "BTCUSDT")
        timeframe = requirements.get("timeframe", "1h")
        entry_conditions = requirements.get("entry_conditions", "Buy when RSI < 30")
        exit_conditions = requirements.get("exit_conditions", "Sell when RSI > 70")
        risk = requirements.get("risk_management", "100% position size")
        
        # Sanitize symbol for use in code (remove hyphens, underscores, slashes)
        clean_symbol = symbol.replace("-", "").replace("_", "").replace("/", "").replace(" ", "")
        
        # Validate symbol - common pairs on Binance
        # If user says "BTC" or similar, default to BTCUSDT
        if clean_symbol.upper() in ["BTC", "BTCUSDC"]:
            clean_symbol = "BTCUSDT"
        elif clean_symbol.upper() in ["ETH", "ETHUSDC"]:
            clean_symbol = "ETHUSDT"
        elif not clean_symbol.endswith("USDT"):
            # If doesn't end with USDT, append it
            clean_symbol = f"{clean_symbol}USDT"
        
        clean_symbol = clean_symbol.upper()  # Binance uses uppercase
        
        # Sanitize strategy name for Python class (remove hyphens, slashes, and special chars)
        clean_strategy_name = strategy_name.replace("-", "").replace("_", "").replace("/", "").replace(" ", "")
        
        # Map timeframe to Lean Resolution
        resolution_map = {
            "1m": "Resolution.Minute",
            "1h": "Resolution.Hour", 
            "1d": "Resolution.Daily",
            "hour": "Resolution.Hour",
            "hourly": "Resolution.Hour",
            "daily": "Resolution.Daily",
            "minute": "Resolution.Minute",
        }
        resolution = resolution_map.get(timeframe.lower(), "Resolution.Hour")
        
        # Extract indicators needed from conditions
        indicators = self._extract_indicators(entry_conditions, exit_conditions)
        indicator_init = self._generate_indicator_init(indicators, symbol)
        warmup = self._calculate_warmup(indicators)
        trading_logic = self._generate_trading_logic(entry_conditions, exit_conditions, indicators)
        
        code = f'''"""
{clean_strategy_name} - Auto-generated Lean QuantConnect Strategy

Requirements:
- Symbol: {clean_symbol}
- Timeframe: {timeframe}  
- Entry: {entry_conditions}
- Exit: {exit_conditions}
- Risk: {risk}
"""

from AlgorithmImports import *


class {clean_strategy_name}(QCAlgorithm):
    """
    Strategy: {clean_strategy_name}
    
    Entry Conditions: {entry_conditions}
    Exit Conditions: {exit_conditions}
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
        self.symbol = self.add_crypto("{clean_symbol}", {resolution}).symbol
        
        # ===== Initialize Indicators =====
{indicator_init}
        
        # ===== Warmup Period =====
        self.set_warm_up({warmup}, {resolution})
        
        # ===== Strategy State =====
        self.last_trade_time = None
        self.position_size = 1.0  # {risk}
    
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
{trading_logic}
    
    def indicators_ready(self) -> bool:
        """Check if all indicators are ready."""
{self._generate_ready_checks(indicators)}
'''
        
        return code
    
    def _extract_indicators(self, entry: str, exit: str) -> List[str]:
        """Extract indicator names from conditions."""
        conditions = (entry + " " + exit).upper()
        indicators = []
        
        indicator_keywords = {
            "RSI": "RSI",
            "MACD": "MACD",
            "BOLLINGER": "BB",
            "SMA": "SMA",
            "EMA": "EMA",
            "ATR": "ATR",
            "STOCHASTIC": "STO",
            "ADX": "ADX",
            "CCI": "CCI",
        }
        
        for keyword, indicator in indicator_keywords.items():
            if keyword in conditions:
                indicators.append(indicator)
        
        # Default to RSI if nothing found
        if not indicators:
            indicators.append("RSI")
        
        return list(set(indicators))  # Remove duplicates
    
    def _generate_indicator_init(self, indicators: List[str], symbol: str) -> str:
        """Generate indicator initialization code."""
        indicator_map = {
            "RSI": "        self.rsi = self.RSI(self.symbol, 14)",
            "MACD": "        self.macd = self.MACD(self.symbol, 12, 26, 9)",
            "BB": "        self.bb = self.BB(self.symbol, 20, 2)",
            "SMA": "        self.sma = self.SMA(self.symbol, 20)",
            "EMA": "        self.ema = self.EMA(self.symbol, 20)",
            "ATR": "        self.atr = self.ATR(self.symbol, 14)",
            "STO": "        self.sto = self.STO(self.symbol, 14, 3, 3)",
            "ADX": "        self.adx = self.ADX(self.symbol, 14)",
            "CCI": "        self.cci = self.CCI(self.symbol, 20)",
        }
        
        lines = []
        for ind in indicators:
            if ind in indicator_map:
                lines.append(indicator_map[ind])
        
        return "\n".join(lines) if lines else "        # No indicators needed"
    
    def _calculate_warmup(self, indicators: List[str]) -> int:
        """Calculate warmup period."""
        warmup_map = {
            "RSI": 280,
            "MACD": 520,
            "BB": 400,
            "SMA": 400,
            "EMA": 400,
            "ATR": 280,
            "STO": 280,
            "ADX": 280,
            "CCI": 400,
        }
        
        max_warmup = 280
        for ind in indicators:
            if ind in warmup_map:
                max_warmup = max(max_warmup, warmup_map[ind])
        
        return max_warmup
    
    def _generate_trading_logic(self, entry: str, exit: str, indicators: List[str]) -> str:
        """Generate trading logic based on conditions."""
        entry_lower = entry.lower()
        exit_lower = exit.lower()
        
        # Simple pattern matching for common strategies
        if "rsi" in entry_lower and "30" in entry_lower:
            entry_code = "        if self.rsi.current.value < 30 and not self.portfolio.invested:"
        elif "rsi" in entry_lower and "oversold" in entry_lower:
            entry_code = "        if self.rsi.current.value < 30 and not self.portfolio.invested:"
        elif "macd" in entry_lower and "cross" in entry_lower:
            entry_code = "        if self.macd.current.value > self.macd.signal.current.value and not self.portfolio.invested:"
        else:
            entry_code = "        # TODO: Implement entry logic based on: " + entry + "\n        if not self.portfolio.invested:"
        
        if "rsi" in exit_lower and "70" in exit_lower:
            exit_code = "        elif self.rsi.current.value > 70 and self.portfolio.invested:"
        elif "rsi" in exit_lower and "overbought" in exit_lower:
            exit_code = "        elif self.rsi.current.value > 70 and self.portfolio.invested:"
        elif "macd" in exit_lower and "cross" in exit_lower:
            exit_code = "        elif self.macd.current.value < self.macd.signal.current.value and self.portfolio.invested:"
        else:
            exit_code = "        # TODO: Implement exit logic based on: " + exit + "\n        elif self.portfolio.invested:"
        
        return f'''{entry_code}
            self.set_holdings(self.symbol, self.position_size)
            self.debug(f"BUY at {{price:.2f}}")
        
{exit_code}
            self.liquidate()
            self.debug(f"SELL at {{price:.2f}}")'''
    
    def _generate_ready_checks(self, indicators: List[str]) -> str:
        """Generate indicator ready checks."""
        checks = []
        for ind in indicators:
            ind_lower = ind.lower()
            checks.append(f"        if not self.{ind_lower}.is_ready:")
            checks.append(f"            return False")
        
        if checks:
            return "\n".join(checks) + "\n        return True"
        return "        return True"
