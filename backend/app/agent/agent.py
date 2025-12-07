"""
Strategy Builder Agent Integration

Integrates the StrategyBuilderAgent with the WebSocket chat interface.
Handles conversation state and routes messages to the appropriate graph nodes.
Uses SpoonOS GraphAgent for proper state management.
"""
 
import asyncio
import json
import logging
import operator
import uuid
from typing import Annotated, Any, Awaitable, Callable, Dict, TypedDict, List, Optional

from spoon_ai.graph import END, StateGraph
from spoon_ai.chat import ChatBot
from spoon_ai.schema import Message

from app.strategy import BaseStrategy, StrategyConfig, StrategyContext, MarketData, Order, OrderSide


logger = logging.getLogger(__name__)


def _extract_json_object(text: str) -> str:
    if not text:
        return "{}"
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return "{}"
    return text[start : end + 1]


class StrategyState(TypedDict, total=False):
    """State schema for the strategy design graph."""
    # Message history - accumulates with operator.add
    messages: Annotated[List[Dict[str, str]], operator.add]
    
    # Callback for progress updates
    progress_callback: Optional[Callable[[str], Awaitable[None]]]
    
    # Message queue reference for clarify node
    message_queue: Optional[asyncio.Queue]
    
    # Requirements extraction
    strategy_requirements: Dict[str, Any]
    
    # Current strategy specification (single source of truth)
    strategy_spec: Optional[Dict[str, Any]]
    
    # Generated code
    strategy_code: str
    
    # Compile/backtest results
    compile_success: bool
    compile_errors: List[str]
    backtest_metrics: Dict[str, Any]
    backtest_summary: str

    # Control flags
    clarification_required: bool
    awaiting_revision: bool
    awaiting_approval: bool
    user_approved: bool
    
    # Error tracking
    compile_retry_count: int
    last_error_type: str  # 'code', 'symbol', 'data', 'unknown'
    
    # Deduplication
    final_response_sent: bool

    # Final output
    output: str


async def _send_progress(state: StrategyState, message: str, prefix: str = "") -> None:
    """Send progress update via callback if available."""
    callback = state.get("progress_callback")
    if callback:
        try:
            formatted = f"{prefix}{message}" if prefix else f" {message}"
            await callback(formatted)
        except Exception as exc:
            logger.warning("Progress callback failed: %s", exc)


class VibeTraderAgent:
    """
    Main agent for the VibeTrader chat interface.
    
    Uses SpoonOS GraphAgent for state management and graph execution.
    """

    def __init__(self, send_callback: Callable[[str], Awaitable[None]]):
        """
        Initialize the agent.
        
        Args:
            send_callback: Async function to send messages back to the user
        """
        self.send_callback = send_callback
        
        # Build and compile graph with progress callback
        graph = _build_graph(progress_callback=send_callback)
        self.compiled_graph = graph.compile()
        
        # Session management
        self.thread_id = str(uuid.uuid4())
        
        # Producer-consumer pattern
        self.message_queue: asyncio.Queue[str] = asyncio.Queue()
        self.consumer_task: Optional[asyncio.Task] = None
        self.running = False

    async def start(self) -> None:
        """Start the consumer loop."""
        if self.running:
            logger.warning("Consumer already running")
            return
        
        self.running = True
        self.consumer_task = asyncio.create_task(self._consumer_loop())
        logger.info("Agent consumer loop started")
    
    async def stop(self) -> None:
        """Stop the consumer loop."""
        if not self.running:
            return
        
        self.running = False
        if self.consumer_task:
            self.consumer_task.cancel()
            try:
                await self.consumer_task
            except asyncio.CancelledError:
                pass
        logger.info("Agent consumer loop stopped")
    
    async def process_message(self, message: str) -> None:
        """Producer: Add message to queue for consumption."""
        logger.info("Enqueuing message: %s", message[:100])
        await self.message_queue.put(message)
    
    async def _consumer_loop(self) -> None:
        """Consumer: Process messages from queue continuously."""
        logger.info("Consumer loop started for thread_id: %s", self.thread_id)
        
        while self.running:
            try:
                # Wait for next message from queue
                message = await self.message_queue.get()
                logger.info("Consuming message: %s", message[:100])
                
                msg = (message or "").strip()
                config = {"configurable": {"thread_id": self.thread_id}}
                
                try:
                    # Normal execution - pass message and queue reference
                    logger.info("Starting graph invocation")
                    initial_state = {
                        "messages": [{"role": "user", "content": msg}],
                        "progress_callback": self.send_callback,
                        "message_queue": self.message_queue
                    }
                    result = await self.compiled_graph.invoke(initial_state, config=config)

                    # Normal completion
                    logger.info("Graph execution completed successfully")
                    # NOTE: Final output already sent by _respond_node via callback
                    # No need to send again here to avoid duplicates
                
                except Exception as exc:
                    logger.error("Error in graph execution: %s", exc, exc_info=True)
                    await self.send_callback(
                        f"❌ I encountered an error: {exc}\n\nPlease try again or rephrase your request."
                    )
                
                # Mark task as done
                self.message_queue.task_done()
                
            except asyncio.CancelledError:
                logger.info("Consumer loop cancelled")
                break
            except Exception as exc:
                logger.error("Error in consumer loop: %s", exc, exc_info=True)
                await self.send_callback(
                    f"❌ I encountered an error: {exc}\n\nPlease try again or rephrase your request."
                )
                self.message_queue.task_done()

    async def reset_session(self) -> None:
        """Reset the current session and clear state."""
        self.thread_id = str(uuid.uuid4())
        logger.info("Session reset with new thread_id: %s", self.thread_id)

async def _entry_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze conversation to determine if spec is complete."""
    logger.info("\n" + "="*60)
    logger.info("NODE: Entry - Analyzing user requirements")
    logger.info("="*60)
    await _send_progress(state, "Analyzing your requirements...")
    
    messages = state.get("messages", [])
    if not messages:
        return {"clarification_required": False}
    
    # Build conversation context from messages
    conversation = "\n".join([
        f"{msg['role']}: {msg['content']}"
        for msg in messages
    ])

    # Use ChatBot with OpenAI GPT-5.1 for requirement analysis
    bot = ChatBot(
        llm_provider="openai",
        model_name="gpt-5.1-2025-11-13",
    )

    analysis_messages = [
        Message(role="user", content=f"Conversation:\n{conversation}"),
        Message(
            role="system",
            content=(
                "Analyze if the user has provided a complete trading strategy description.\n"
                "REQUIRED: entry_conditions (buy signals), exit_conditions (sell signals).\n"
                "OPTIONAL: symbol (default BTCUSDT), timeframe (default 1h), risk (default moderate), start_date (default 2025-01-01), end_date (default 2025-06-30).\n\n"
                "TIMEFRAME VALIDATION: Only these are valid: 1m, 1h, 1d.\n"
                "If user specifies invalid timeframe (like 1.5h, 90m), suggest the closest valid one (e.g., 1.5h -> 1h or 2h).\n\n"
                "If user describes a strategy but doesn't specify a trading pair, that's OK - we'll use BTCUSDT.\n"
                "If user specifies a pair but it seems invalid (like BTCUSDC, XAUUSD), suggest BTCUSDT instead.\n"
                "Extract dates if mentioned (e.g., 'backtest from Jan to June 2025' -> start_date: 2025-01-01, end_date: 2025-06-30).\n\n"
                "Respond ONLY with JSON: {\"is_spec_complete\": true/false, \"missing\": [list], "
                "\"instructions\": \"what to ask\", \"extracted\": {symbol, timeframe, entry_conditions, exit_conditions, risk, start_date, end_date}, "
                "\"needs_confirmation\": true/false, \"confirmation_message\": \"message to confirm auto-selected values\"}"
            ),
        ),
    ]
    
    try:
        resp_text = await bot.ask(analysis_messages)
        analysis = json.loads(_extract_json_object(resp_text))
        logger.info("Requirements complete: %s", analysis.get("is_spec_complete", False))
    except Exception as e:
        logger.error("❌ Failed to analyze requirements: %s", e)
        analysis = {"is_spec_complete": False, "missing": ["all fields"], "instructions": "Please describe your trading strategy."}
    
    is_complete = analysis.get("is_spec_complete", False)
    extracted = analysis.get("extracted", {})
    instructions = analysis.get("instructions", "Please provide more details.")
    needs_confirmation = analysis.get("needs_confirmation", False)
    confirmation_msg = analysis.get("confirmation_message", "")
    
    # Auto-fill defaults for optional fields
    if "symbol" not in extracted or not extracted.get("symbol"):
        extracted["symbol"] = "BTCUSDT"  # Default to BTC/USDT
    if "timeframe" not in extracted or not extracted.get("timeframe"):
        extracted["timeframe"] = "1h"  # Default to 1 hour
    if "risk" not in extracted or not extracted.get("risk"):
        extracted["risk"] = "moderate risk management"
    if "start_date" not in extracted or not extracted.get("start_date"):
        extracted["start_date"] = "2025-01-01"  # Default start date
    if "end_date" not in extracted or not extracted.get("end_date"):
        extracted["end_date"] = "2025-06-30"  # Default end date
    
    # Validate and normalize timeframe
    valid_timeframes = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]
    timeframe = extracted.get("timeframe", "1h").lower()
    if timeframe not in valid_timeframes:
        logger.warning(f"Invalid timeframe '{timeframe}', defaulting to 1h")
        extracted["timeframe"] = "1h"
    
    if not is_complete:
        # Need more info about strategy logic
        logger.info("→ Routing to CLARIFY node (incomplete requirements)")
        return {
            "messages": [{"role": "assistant", "content": instructions}],
            "strategy_requirements": extracted,
            "clarification_required": True,
        }
    elif needs_confirmation and confirmation_msg:
        # Strategy complete but confirm auto-selected values
        logger.info("→ Routing to CLARIFY node (needs confirmation)")
        return {
            "messages": [{"role": "assistant", "content": confirmation_msg}],
            "strategy_requirements": extracted,
            "clarification_required": True,  # Wait for user confirmation
        }
    else:
        # Everything ready - proceed
        symbol = extracted.get('symbol', 'BTCUSDT')
        timeframe = extracted.get('timeframe', '1h')
        start_date = extracted.get('start_date', '2025-01-01')
        end_date = extracted.get('end_date', '2025-06-30')
        logger.info("✓ Requirements complete: %s @ %s (%s to %s)", symbol, timeframe, start_date, end_date)
        logger.info("→ Routing to DESIGN node")
        await _send_progress(state, 
            f"📋 **Requirements Confirmed**\n"
            f"  • Symbol: {symbol}\n"
            f"  • Timeframe: {timeframe}\n"
            f"  • Period: {start_date} to {end_date}\n\n"
            f"🛠️ Generating strategy code...",
            prefix="")
        return {
            "messages": [{"role": "assistant", "content": f"Perfect! Generating your strategy for {symbol} on {timeframe} timeframe (backtesting {start_date} to {end_date})..."}],
            "strategy_requirements": extracted,
            "strategy_spec": extracted.copy(),  # Set as single source of truth
            "clarification_required": False,
            "compile_retry_count": 0,  # Reset retry counter
            "last_error_type": "",
            "final_response_sent": False,  # Reset dedup flag
            "strategy_code": "",  # Clear old code
            "compile_errors": [],  # Clear old errors
        }


async def _clarify_requirements_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Send clarification question and wait for user response from queue."""
    logger.info("\n" + "="*60)
    logger.info("NODE: Clarify - Waiting for user input")
    logger.info("="*60)
    
    # Check if we're here due to a symbol error
    error_type = state.get("last_error_type", "")
    compile_errors = state.get("compile_errors", [])
    
    # Get the last assistant message (the clarification question)
    messages = state.get("messages", [])
    question = "Please provide more details."
    
    if error_type == "symbol":
        # Symbol error - ask for valid trading pair
        strategy_spec = state.get("strategy_spec", {})
        current_symbol = strategy_spec.get("symbol", "unknown")
        error_msg = compile_errors[0] if compile_errors else "Invalid symbol"
        question = (
            f"⚠️ The trading pair '{current_symbol}' is not available on Binance.\n\n"
            f"Error: {error_msg}\n\n"
            "Please specify a valid Binance trading pair (e.g., BTCUSDT, ETHUSDT, SOLUSDT). "
            "You can also say 'use BTCUSDT' to continue with Bitcoin."
        )
        logger.info("📝 Asking user for valid symbol (current: %s)", current_symbol)
    elif "Invalid timeframe" in compile_errors[0] if compile_errors else "":
        # Timeframe error - ask for valid timeframe
        strategy_spec = state.get("strategy_spec", {})
        current_timeframe = strategy_spec.get("timeframe", "unknown")
        question = (
            f"⚠️ The timeframe '{current_timeframe}' is not valid.\n\n"
            f"Valid timeframes: 1m, 1h, 1d\n\n"
            "Please specify a valid timeframe (e.g., '1h' for hourly, '1d' for daily)."
        )
        logger.info("📝 Asking user for valid timeframe (current: %s)", current_timeframe)
    else:
        # Normal clarification
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                question = msg.get("content", question)
                break
    
    # Send question to user via callback
    callback = state.get("progress_callback")
    if callback:
        await callback(question)
    
    # Get message queue reference
    message_queue = state.get("message_queue")
    if not message_queue:
        logger.error("No message queue available in state")
        return {"messages": [{"role": "user", "content": "error: no queue"}]}
    
    # Wait for next message from queue
    logger.info("⏳ Waiting for user response...")
    user_response = await message_queue.get()
    logger.info("✓ Received: %s", user_response[:80] + ("..." if len(user_response) > 80 else ""))
    logger.info("→ Routing back to ENTRY node for re-analysis")
    
    # Mark as done and add to messages
    message_queue.task_done()
    
    return {
        "messages": [{"role": "user", "content": user_response}]
    }


async def _design_strategy_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate or fix strategy code using QuantStrategyAgent."""
    logger.info("\n" + "="*60)
    logger.info("NODE: Design - Code generation")
    logger.info("="*60)
    
    # Get state data - use strategy_spec as single source of truth
    strategy_spec = state.get("strategy_spec", {})
    requirements = strategy_spec if strategy_spec else state.get("strategy_requirements", {})
    messages = state.get("messages", [])
    compile_errors = state.get("compile_errors", [])
    previous_code = state.get("strategy_code", "")
    
    # Validate timeframe immediately
    timeframe = requirements.get("timeframe", "1h")
    valid_timeframes = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]
    if timeframe not in valid_timeframes:
        logger.error(f"Invalid timeframe '{timeframe}' - should have been caught in entry node!")
        return {
            "compile_success": False,
            "compile_errors": [f"Invalid timeframe: '{timeframe}'. Valid: {', '.join(valid_timeframes)}"],
            "compile_retry_count": state.get("compile_retry_count", 0) + 1,
            "last_error_type": "code",
        }
    
    # Import here to avoid circular import
    from .quant_agent import get_quant_agent
    
    try:
        # Get quant agent instance
        quant_agent = get_quant_agent()
        
        # Check if this is a revision (has compile errors)
        if compile_errors:
            # Fixing existing code
            error_count = len(compile_errors)
            logger.info(" FIXING CODE - %d error(s) from previous backtest", error_count)
            logger.info("First error: %s", compile_errors[0][:100] if compile_errors else "unknown")
            await _send_progress(state, " Fixing strategy code based on errors...")
            
            # Use quant agent to fix code
            code = await quant_agent.fix_strategy_code(
                original_code=previous_code,
                errors=compile_errors,
                conversation_history=messages
            )
            
            logger.info(" Fixed code generated (%d chars)", len(code))
            logger.info("→ Routing to COMPILE node for retry")
            await _send_progress(state, 
                f"🔧 **Code Fixed** ({len(code)} chars)\n"
                f"  • Addressed {len(compile_errors)} error(s)\n"
                f"  • Retrying backtest...",
                prefix="")
        else:
            # Generating new code
            symbol = requirements.get("symbol", "BTCUSDT")
            timeframe = requirements.get("timeframe", "1h")
            entry = requirements.get("entry_conditions", "unknown")
            exit_cond = requirements.get("exit_conditions", "unknown")
            
            logger.info(" GENERATING NEW CODE")
            logger.info("   Symbol: %s", symbol)
            logger.info("   Timeframe: %s", timeframe)
            logger.info("   Entry: %s", entry[:60] + ("..." if len(str(entry)) > 60 else ""))
            logger.info("   Exit: %s", exit_cond[:60] + ("..." if len(str(exit_cond)) > 60 else ""))
            await _send_progress(state, 
                f"🤖 **Calling Strategy Generator**\n"
                f"  • Analyzing entry/exit conditions\n"
                f"  • Generating Lean QuantConnect code\n"
                f"  • Configuring indicators and risk management",
                prefix="")
            
            # Clean symbol for use in strategy name (remove hyphens, slashes, spaces, etc.)
            clean_symbol = symbol.replace("-", "").replace("_", "").replace("/", "").replace(" ", "")
            strategy_name = f"{clean_symbol}Strategy"
            
            # Use quant agent to generate code
            code = await quant_agent.generate_strategy_code(
                strategy_name=strategy_name,
                requirements=requirements,
                conversation_history=messages
            )
            
            logger.info("✓ Code generated (%d chars, class: %s)", len(code), strategy_name)
            logger.info("→ Routing to COMPILE node")
            await _send_progress(state,
                f"✅ **Strategy Code Generated**\n"
                f"  • Class: {strategy_name}\n"
                f"  • Size: {len(code)} characters\n\n"
                f"🧪 Starting backtest...",
                prefix="")
            
            return {"strategy_code": code}
        
        return {
            "strategy_code": code,
            "compile_errors": [],  # Clear errors for new attempt
        }
        
    except Exception as e:
        logger.error("Failed to generate strategy code: %s", e, exc_info=True)
        await _send_progress(state, f" Strategy generation failed: {e}")
        
        # Return fallback simple code
        fallback_code = '''from AlgorithmImports import *

class SimpleStrategy(QCAlgorithm):
    def initialize(self):
        self.set_start_date(2025, 1, 1)
        self.set_end_date(2025, 12, 1)
        self.set_account_currency("USDT")
        self.set_cash("USDT", 100000, 1.0)
        self.set_brokerage_model(BrokerageName.BINANCE, AccountType.CASH)
        self.symbol = self.add_crypto("BTCUSDT", Resolution.Hour).symbol
        self.rsi = self.RSI(self.symbol, 14)
        self.set_warm_up(280, Resolution.Hour)
    
    def on_data(self, data):
        if not data.contains_key(self.symbol):
            return
        if not self.rsi.is_ready:
            return
        if self.rsi.current.value < 30 and not self.portfolio.invested:
            self.set_holdings(self.symbol, 1.0)
        elif self.rsi.current.value > 70 and self.portfolio.invested:
            self.liquidate()
'''
        
        return {
            "strategy_code": fallback_code,
            "compile_errors": [f"Strategy generation error: {str(e)}"]
        }


async def _compile_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Compile and backtest the strategy code."""
    logger.info("\n" + "="*60)
    logger.info("NODE: Compile - Running backtest")
    logger.info("="*60)
    
    # Get requirements and code from state - use strategy_spec as single source of truth
    strategy_spec = state.get("strategy_spec", {})
    requirements = strategy_spec if strategy_spec else state.get("strategy_requirements", {})
    code = state.get("strategy_code") or ""
    if not code:
        return {
            "compile_success": False,
            "compile_errors": ["No strategy code generated."],
            "backtest_metrics": {},
            "backtest_summary": ""
        }
    
    # Extract symbol and timeframe from strategy_spec (single source of truth)
    symbol = requirements.get("symbol", "BTCUSDT")
    timeframe = requirements.get("timeframe", "1h")
    
    # Validate timeframe before proceeding
    valid_timeframes = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]
    if timeframe not in valid_timeframes:
        logger.error(f"Invalid timeframe '{timeframe}' detected in compile node")
        return {
            "compile_success": False,
            "compile_errors": [f"Invalid timeframe: '{timeframe}'. Valid options: {', '.join(valid_timeframes[:5])}... etc. Please specify a valid timeframe."],
            "backtest_metrics": {},
            "backtest_summary": "",
            "compile_retry_count": state.get("compile_retry_count", 0) + 1,
            "last_error_type": "code",
        }
    
    # Clean and validate symbol
    original_symbol = symbol
    symbol = symbol.replace("-", "").replace("_", "").replace("/", "").replace(" ", "")
    
    # Validate symbol - common pairs on Binance
    if symbol.upper() in ["BTC", "BTCUSDC"]:
        symbol = "BTCUSDT"
    elif symbol.upper() in ["ETH", "ETHUSDC"]:
        symbol = "ETHUSDT"
    elif not symbol.upper().endswith("USDT"):
        symbol = f"{symbol}USDT"
    
    symbol = symbol.upper()  # Binance uses uppercase
    if original_symbol != symbol:
        logger.info("Symbol normalized: %s → %s", original_symbol, symbol)
    
    # Normalize interval format (1H -> 1h, 1M -> 1m, 1D -> 1d)
    timeframe = timeframe.lower()
    
    # Get date range from requirements or use defaults
    start_date_str = requirements.get("start_date", "2025-01-01")
    end_date_str = requirements.get("end_date", "2025-06-30")
    
    logger.info("📊 BACKTEST PARAMETERS:")
    logger.info("   Symbol: %s", symbol)
    logger.info("   Timeframe: %s", timeframe)
    logger.info("   Start Date: %s", start_date_str)
    logger.info("   End Date: %s", end_date_str)
    logger.info("   Capital: $100,000")
    
    await _send_progress(state,
        f"📊 **Running Backtest**\n"
        f"  • Symbol: {symbol}\n"
        f"  • Timeframe: {timeframe}\n"
        f"  • Period: {start_date_str} to {end_date_str}\n"
        f"  • Initial Capital: $100,000\n\n"
        f"⏳ This may take a few seconds...",
        prefix="")
    
    try:
        # Import backtesting components
        import sys
        import os
        import tempfile
        from pathlib import Path
        from datetime import datetime, timedelta
        
        # Add backtesting to path
        backend_dir = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(backend_dir.parent))
        
        from backtesting.agent import BacktestingAgent, BacktestRequest
        
        # Save strategy to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            strategy_file = f.name
        
        try:
            # Parse date range from requirements
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            except ValueError:
                # Fallback to defaults if parsing fails
                logger.warning("Invalid date format, using defaults: 2025-01-01 to 2025-06-30")
                start_date = datetime(2025, 1, 1)
                end_date = datetime(2025, 6, 30)
            
            logger.info("🚀 Starting backtest: %s to %s", start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            await _send_progress(state, "Running backtest on real data...")
            
            request = BacktestRequest(
                symbol=symbol,
                interval=timeframe,
                start_date=start_date,
                end_date=end_date,
                initial_capital=100000.0,
                strategy_file=Path(strategy_file)
            )
            
            # Run backtest
            agent = BacktestingAgent()
            response = await agent.run_backtest(request)
            
            logger.info("Backtest completed: success=%s", response.success)
            
            if not response.success:
                # Backtest failed
                error_msg = response.error_message or "Unknown error"
                error_stage = response.error_stage or "unknown"
                
                logger.error(" BACKTEST FAILED")
                logger.error("   Stage: %s", error_stage)
                logger.error("   Error: %s", error_msg[:200])
                logger.info("→ Routing back to DESIGN node for code fix")
                await _send_progress(state, f" Backtest failed: {error_msg}")
                
                # Categorize error type
                error_type = "unknown"
                if "Invalid symbol" in error_msg or "code=-1121" in error_msg:
                    error_type = "symbol"
                    logger.error("⚠️ ERROR TYPE: Invalid Symbol - this is NOT a code issue!")
                elif "not a valid BinanceInterval" in error_msg or "Invalid timeframe" in error_msg:
                    error_type = "code"  # Timeframe issues are requirements issues
                    logger.error("⚠️ ERROR TYPE: Invalid Timeframe - this is a requirements issue!")
                elif "syntax" in error_msg.lower() or "indentation" in error_msg.lower():
                    error_type = "code"
                elif "no data" in error_msg.lower() or "insufficient data" in error_msg.lower():
                    error_type = "data"
                
                retry_count = state.get("compile_retry_count", 0) + 1
                logger.info("🔄 Retry count: %d", retry_count)
                
                return {
                    "compile_success": False,
                    "compile_errors": [f"{error_stage}: {error_msg}"],
                    "backtest_metrics": {},
                    "backtest_summary": "",
                    "compile_retry_count": retry_count,
                    "last_error_type": error_type,
                }
            
            # Success - extract metrics from report
            if not response.report or not response.report.metrics:
                logger.error("Backtest succeeded but no metrics in report")
                return {
                    "compile_success": False,
                    "compile_errors": ["Backtest completed but no metrics available"],
                    "backtest_metrics": {},
                    "backtest_summary": ""
                }
            
            metrics_obj = response.report.metrics
            metrics = {
                "total_return": metrics_obj.total_return_percent,
                "max_drawdown": metrics_obj.risk.max_drawdown_percent,
                "win_rate": metrics_obj.win_rate,
                "total_trades": metrics_obj.total_trades,
                "sharpe_ratio": metrics_obj.risk.sharpe_ratio,
            }
            
            # Format summary
            total_return = metrics.get("total_return", 0.0)
            max_dd = metrics.get("max_drawdown", 0.0)
            win_rate = metrics.get("win_rate", 0.0)
            total_trades = metrics.get("total_trades", 0)
            sharpe = metrics.get("sharpe_ratio", 0.0)
            
            summary = (
                f"✅ Backtest completed successfully:\n"
                f"  • Return: {total_return:+.2f}%\n"
                f"  • Max Drawdown: {max_dd:.2f}%\n"
                f"  • Win Rate: {win_rate:.1f}%\n"
                f"  • Total Trades: {total_trades}\n"
                f"  • Sharpe Ratio: {sharpe:.2f}"
            )
            
            logger.info("✅ BACKTEST SUCCESS")
            logger.info("   Return: %s", metrics.get('total_return', 'N/A'))
            logger.info("   Trades: %s", metrics.get('total_trades', 'N/A'))
            logger.info("   Win Rate: %s", metrics.get('win_rate', 'N/A'))
            logger.info("   Sharpe: %s", metrics.get('sharpe_ratio', 'N/A'))
            logger.info("→ Routing to RESPOND node")
            
            await _send_progress(state, 
                f"✅ **Backtest Complete!**\n"
                f"  • Return: {metrics.get('total_return', 'N/A')}\n"
                f"  • Trades: {metrics.get('total_trades', 'N/A')}\n"
                f"  • Win Rate: {metrics.get('win_rate', 'N/A')}\n\n"
                f"📝 Preparing full results...",
                prefix="")
            
            # Find and send the results JSON for order replay visualization
            backtest_data = None
            callback = state.get("progress_callback")
            
            try:
                # Find the results folder (pattern: custom_strategy_<hash>)
                results_base = backend_dir.parent / "backtesting" / "results"
                if results_base.exists():
                    # Find most recent custom_strategy folder
                    strategy_folders = sorted(
                        [f for f in results_base.iterdir() if f.is_dir() and f.name.startswith("custom_strategy_")],
                        key=lambda x: x.stat().st_mtime,
                        reverse=True
                    )
                    
                    if strategy_folders:
                        # Get the most recent one
                        results_folder = strategy_folders[0]
                        json_file = results_folder / "BasicTemplateFrameworkAlgorithm.json"
                        
                        if json_file.exists():
                            with open(json_file, 'r') as f:
                                backtest_data = json.load(f)
                            logger.info("✓ Loaded backtest results JSON for order replay")
                        else:
                            logger.warning("Results JSON not found: %s", json_file)
                    else:
                        logger.warning("No custom_strategy folders found in results")
            except Exception as e:
                logger.warning("Failed to load backtest results JSON: %s", str(e))
            
            # Send backtest replay message if we have the data
            if backtest_data and callback:
                from app.message_types import create_backtest_replay_message
                replay_message = create_backtest_replay_message(
                    content="🎬 **Order Replay Ready**\n\nClick to view animated backtest execution",
                    backtest_data=backtest_data,
                    metadata={
                        "metrics": metrics,
                        "symbol": symbol,
                        "timeframe": timeframe
                    }
                )
                await callback(replay_message)
                logger.info("✓ Sent backtest replay data to frontend")
            
            return {
                "compile_success": True,
                "compile_errors": [],
                "backtest_metrics": metrics,
                "backtest_summary": summary
            }
            
        finally:
            # Clean up temp file
            try:
                os.unlink(strategy_file)
            except:
                pass
    
    except Exception as e:
        logger.error("❌ BACKTEST EXCEPTION: %s", str(e)[:200], exc_info=False)
        logger.info("→ Routing back to DESIGN node")
        error_msg = f"Backtest error: {str(e)}"
        await _send_progress(state, f"❌ {error_msg}")
        
        retry_count = state.get("compile_retry_count", 0) + 1
        logger.info("🔄 Retry count: %d", retry_count)
        
        return {
            "compile_success": False,
            "compile_errors": [error_msg],
            "backtest_metrics": {},
            "backtest_summary": "",
            "compile_retry_count": retry_count,
            "last_error_type": "unknown",
        }


async def _respond_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Display final results to user (code + evaluation metrics)."""
    logger.info("\n" + "="*60)
    logger.info("NODE: Respond - Sending final results to user")
    logger.info("="*60)
    
    # Check if already sent to prevent duplicates
    if state.get("final_response_sent", False):
        logger.warning("⚠️ Final response already sent - skipping to prevent duplicate")
        return {"output": "", "final_response_sent": True}
    
    code = (state.get("strategy_code") or "").strip()
    backtest_summary = state.get("backtest_summary") or ""
    metrics = state.get("backtest_metrics") or {}
    strategy_spec = state.get("strategy_spec", {})
    callback = state.get("progress_callback")

    # Build structured message with code block
    from app.message_types import create_results_message
    
    # Create content text
    content = "✅ **Strategy Backtest Results**\n\n" + backtest_summary if backtest_summary else "Strategy generated."
    
    # Create structured message with code block
    structured_message = create_results_message(
        content=content,
        code=code if code else None,
        language="python",
        metadata={
            "metrics": metrics,
            "strategy_spec": strategy_spec
        }
    )
    
    # Send structured message (only once)
    if callback:
        await callback(structured_message)
        logger.info("✓ Final response sent to user (structured with code block)")
    else:
        logger.warning("No callback - not sending")
    
    logger.info("="*60)
    logger.info("WORKFLOW COMPLETE")
    logger.info("="*60)
    
    return {"output": content, "final_response_sent": True}


def _route_from_entry(state: Dict[str, Any]) -> str:
    """Route from entry based on clarification_required flag."""
    if state.get("clarification_required", False):
        return "clarify"
    return "design"


def _route_from_compile(state: Dict[str, Any]) -> str:
    """Route from compile based on success/failure and error type."""
    if state.get("compile_success", False):
        return "respond"
    
    # Check error type and retry count
    error_type = state.get("last_error_type", "unknown")
    retry_count = state.get("compile_retry_count", 0)
    
    logger.info("🛤️ ROUTING DECISION: error_type=%s, retry_count=%d", error_type, retry_count)
    
    # Check for timeframe errors in compile_errors
    compile_errors = state.get("compile_errors", [])
    has_timeframe_error = any("Invalid timeframe" in str(err) or "not a valid BinanceInterval" in str(err) for err in compile_errors)
    
    # Timeframe errors are requirements issues - ask user
    if has_timeframe_error:
        logger.info("→ Routing to CLARIFY (invalid timeframe - need user input)")
        return "clarify_symbol"
    
    # Symbol errors are NOT code issues - ask user for valid symbol
    if error_type == "symbol":
        logger.info("→ Routing to CLARIFY (invalid symbol - need user input)")
        return "clarify_symbol"
    
    # Too many retries - ask user for help
    if retry_count >= 5:
        logger.warning("⚠️ Too many retries (%d) - routing to CLARIFY for user assistance", retry_count)
        return "clarify_symbol"
    
    # Code/unknown errors - try to fix code
    logger.info("→ Routing to DESIGN (code fix attempt #%d)", retry_count)
    return "design"


def _build_graph(progress_callback: Optional[Callable[[str], Awaitable[None]]] = None) -> StateGraph:
    """
    Build the strategy design graph.
    
    Args:
        progress_callback: Optional callback for per-node progress updates
        
    Returns:
        Uncompiled StateGraph instance
    """
    graph: StateGraph = StateGraph(StrategyState)
    
    # Store callback in graph metadata
    if progress_callback:
        graph.metadata = {"progress_callback": progress_callback}
    
    # Nodes
    graph.add_node("entry", _entry_node)
    graph.add_node("clarify", _clarify_requirements_node)
    graph.add_node("design", _design_strategy_node)
    graph.add_node("compile", _compile_node)
    graph.add_node("respond", _respond_node)

    # Entry analyzes and routes to clarify or design
    graph.add_conditional_edges(
        "entry",
        _route_from_entry,
        {"clarify": "clarify", "design": "design"},
    )
    
    # Clarify always loops back to entry with updated messages
    graph.add_edge("clarify", "entry")

    # Design -> Compile
    graph.add_edge("design", "compile")

    # Compile routes based on success/failure and error type
    graph.add_conditional_edges(
        "compile",
        _route_from_compile,
        {"design": "design", "respond": "respond", "clarify_symbol": "clarify"},
    )

    # Terminal
    graph.add_edge("respond", END)
    graph.set_entry_point("entry")
    
    return graph


# Alias for backward compatibility
StubAgent = VibeTraderAgent
