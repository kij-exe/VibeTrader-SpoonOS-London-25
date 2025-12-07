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

    # Final output
    output: str


async def _send_progress(state: StrategyState, message: str) -> None:
    """Send progress update via callback if available."""
    callback = state.get("progress_callback")
    if callback:
        try:
            await callback(f" {message}")
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
                    logger.info("Graph execution completed: %s", result)
                    response = result.get("output", str(result))
                    await self.send_callback(response)
                
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
    logger.info("Node 'entry' starting with state: %s", state)
    await _send_progress(state, "Analyzing your requirements...")
    
    messages = state.get("messages", [])
    if not messages:
        return {"clarification_required": False}
    
    # Build conversation context from messages
    conversation = "\n".join([
        f"{msg['role']}: {msg['content']}"
        for msg in messages
    ])

    # Use ChatBot with anthropic Haiku for requirement analysis
    bot = ChatBot(
        llm_provider="anthropic",
        model_name="claude-haiku-4-5-20251001",
    )

    analysis_messages = [
        Message(role="user", content=f"Conversation:\n{conversation}"),
        Message(
            role="system",
            content=(
                "Analyze if the user has provided complete trading strategy requirements.\n"
                "Required: symbol, timeframe, entry_conditions, exit_conditions.\n"
                "Respond ONLY with JSON: {\"is_spec_complete\": true/false, \"missing\": [list of missing items], "
                "\"instructions\": \"what to ask user for\", \"extracted\": {symbol, timeframe, entry_conditions, exit_conditions, risk}}"
            ),
        ),
    ]
    
    try:
        resp_text = await bot.ask(analysis_messages)
        analysis = json.loads(_extract_json_object(resp_text))
        logger.info("LLM analysis: %s", analysis)
    except Exception as e:
        logger.error("Failed to analyze requirements: %s", e)
        analysis = {"is_spec_complete": False, "missing": ["all fields"], "instructions": "Please describe your trading strategy."}
    
    is_complete = analysis.get("is_spec_complete", False)
    extracted = analysis.get("extracted", {})
    instructions = analysis.get("instructions", "Please provide more details.")
    
    if not is_complete:
        # Add assistant message with clarification request
        return {
            "messages": [{"role": "assistant", "content": instructions}],
            "strategy_requirements": extracted,
            "clarification_required": True,
        }
    else:
        # Spec complete - proceed to generation
        await _send_progress(state, "Requirements complete. Generating strategy...")
        return {
            "messages": [{"role": "assistant", "content": "Great! I have everything I need. Generating your strategy..."}],
            "strategy_requirements": extracted,
            "clarification_required": False,
        }


async def _clarify_requirements_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Send clarification question and wait for user response from queue."""
    logger.info("Node 'clarify' starting with state: %s", state)
    
    # Get the last assistant message (the clarification question)
    messages = state.get("messages", [])
    question = "Please provide more details."
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
    logger.info("Waiting for user response from queue...")
    user_response = await message_queue.get()
    logger.info("Received user response: %s", user_response[:100])
    
    # Mark as done and add to messages
    message_queue.task_done()
    
    return {
        "messages": [{"role": "user", "content": user_response}]
    }


async def _design_strategy_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate dummy strategy code."""
    logger.info("Node 'design' starting with state: %s", state)
    await _send_progress(state, "Generating strategy code...")
    
    # Get strategy requirements from state
    requirements = state.get("strategy_requirements", {})
    
    # Generate dummy code
    dummy_code = 'print("Hello World")'
    
    logger.info("Generated dummy strategy code")
    await _send_progress(state, "Strategy code generated. Compiling...")

    return {
        "strategy_code": dummy_code,
    }


async def _compile_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Compile and run backtest in simulated environment."""
    logger.info("Node 'compile' starting with state: %s", state)
    await _send_progress(state, "Compiling and running backtest...")
    
    code = state.get("strategy_code") or ""
    if not code:
        return {
            "compile_success": False,
            "compile_errors": ["No strategy code generated."],
            "backtest_metrics": {},
            "backtest_summary": ""
        }

    # Simulate compilation/execution
    import random
    
    # 30% chance of error for testing
    has_error = random.random() < 0.3
    
    if has_error:
        # Simulate compilation/runtime error
        errors = [
            "SyntaxError: invalid syntax on line 1",
            "NameError: name 'undefined_variable' is not defined",
            "RuntimeError: Strategy execution failed"
        ]
        error = random.choice(errors)
        
        logger.info("Backtest failed with error: %s", error)
        await _send_progress(state, f"Compilation failed: {error}")
        
        return {
            "compile_success": False,
            "compile_errors": [error],
            "backtest_metrics": {},
            "backtest_summary": ""
        }
    
    # Success - return backtest metrics
    metrics = {
        "total_return_percent": round(random.uniform(5.0, 25.0), 2),
        "max_drawdown_percent": round(random.uniform(3.0, 15.0), 2),
        "win_rate": round(random.uniform(45.0, 65.0), 1),
        "total_trades": random.randint(50, 150),
        "sharpe_ratio": round(random.uniform(0.8, 2.0), 2),
    }
    
    summary = (
        "Backtest completed successfully: "
        f"return={metrics['total_return_percent']:+.2f}% | "
        f"max_dd={metrics['max_drawdown_percent']:.2f}% | "
        f"win_rate={metrics['win_rate']:.1f}% | "
        f"trades={metrics['total_trades']} | "
        f"sharpe={metrics['sharpe_ratio']:.2f}"
    )

    logger.info("Backtest successful: %s", summary)
    await _send_progress(state, "Backtest complete.")

    return {
        "compile_success": True,
        "compile_errors": [],
        "backtest_metrics": metrics,
        "backtest_summary": summary
    }


async def _respond_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Display final results to user (code + evaluation metrics)."""
    logger.info("Node 'respond' starting with state: %s", state)
    
    code = (state.get("strategy_code") or "").strip()
    backtest_summary = state.get("backtest_summary") or ""
    metrics = state.get("backtest_metrics") or {}
    callback = state.get("progress_callback")

    # Build final message
    parts = []
    
    if backtest_summary:
        parts.append("✅ **Strategy Backtest Results**\n")
        parts.append(backtest_summary)
    
    if code:
        parts.append("\n**Generated Strategy Code:**\n")
        parts.append(f"```python\n{code}\n```")
    
    if metrics:
        parts.append("\n**Detailed Metrics:**")
        for key, value in metrics.items():
            parts.append(f"• {key}: {value}")
    
    final_message = "\n".join(parts)
    
    # Send to user
    if callback:
        await callback(final_message)
    
    logger.info("Final response sent to user")
    
    return {"output": final_message}


def _route_from_entry(state: Dict[str, Any]) -> str:
    """Route from entry based on clarification_required flag."""
    if state.get("clarification_required", False):
        return "clarify"
    return "design"


def _route_from_compile(state: Dict[str, Any]) -> str:
    """Route from compile based on success/failure."""
    if state.get("compile_success", False):
        return "respond"
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

    # Compile routes based on success/failure
    graph.add_conditional_edges(
        "compile",
        _route_from_compile,
        {"design": "design", "respond": "respond"},
    )

    # Terminal
    graph.add_edge("respond", END)
    graph.set_entry_point("entry")
    
    return graph


# Alias for backward compatibility
StubAgent = VibeTraderAgent
