"""
Strategy Builder Agent Integration

Integrates the StrategyBuilderAgent with the WebSocket chat interface.
Handles conversation state and routes messages to the appropriate graph nodes.
"""
 
import json
import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict

from spoon_ai.graph import END, StateGraph
from spoon_ai.llm.manager import get_llm_manager
from spoon_ai.schema import Message

from app.backtest.data_loader import DataLoader
from app.backtest.runner import BacktestRunner
from app.strategy import BaseStrategy, StrategyConfig, StrategyContext, MarketData, Order, OrderSide


logger = logging.getLogger(__name__)


async def _design_strategy_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LLM node: turn user description into strategy code."""
    llm = get_llm_manager()
    user_prompt = state.get("user_prompt", "")

    messages = [
        Message(
            role="system",
            content=(
                "You generate Python trading strategies for the VibeTrader backtest engine. "
                "Output ONLY Python code, no explanations or markdown. "
                "Implement a class GeneratedStrategy(BaseStrategy) using StrategyConfig, MarketData, and StrategyContext."
            ),
        ),
        Message(role="user", content=user_prompt),
    ]

    try:
        response = await llm.chat(messages)
        content = response.content or ""
    except Exception as exc:
        logger.error("LLM error in design node: %s", exc)
        return {
            "strategy_code": "",
            "design_summary": f"Failed to generate strategy code: {exc}",
        }

    code = content
    if "```" in content:
        start = content.find("```")
        end = content.rfind("```")
        block = content[start + 3 : end] if end > start else content[start + 3 :]
        lines = block.splitlines()
        if lines and lines[0].strip().lower().startswith("python"):
            lines = lines[1:]
        code = "\n".join(lines).strip()

    return {
        "strategy_code": code,
        "design_summary": "Draft strategy implementation generated.",
    }


async def _backtest_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Backtest stub: return example metrics (no engine call for now)."""
    code = state.get("strategy_code") or ""
    if not code:
        return {"backtest_summary": "No strategy code generated.", "metrics": {}}

    # Stubbed metrics
    metrics = {
        "total_return_percent": 12.7,
        "max_drawdown_percent": 6.4,
        "win_rate": 53.2,
        "total_trades": 87,
        "sharpe_ratio": 1.12,
    }
    summary = (
        "Backtest (stub) completed: "
        f"return={metrics['total_return_percent']:+.2f}% | "
        f"max_dd={metrics['max_drawdown_percent']:.2f}% | "
        f"win_rate={metrics['win_rate']:.1f}% | trades={metrics['total_trades']}"
    )

    return {"metrics": metrics, "backtest_summary": summary}


async def _respond_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare final response for the chat interface (clarify/errors/results)."""
    code = (state.get("strategy_code") or "").strip()
    compile_errors = state.get("compile_errors") or []
    sufficient = state.get("sufficient_data", True)
    clarify = state.get("clarification_message") or ""
    backtest = state.get("backtest_summary") or ""
    metrics = state.get("metrics") or {}

    parts: list[str] = []

    if not sufficient and clarify:
        parts.append("I need a bit more detail to proceed:")
        parts.append(clarify)
        parts.append("Please reply with the missing items (symbol, timeframe, entry/exit rules, risk limits).")
        return {
            "chat_response": "\n\n".join(parts),
            "awaiting_clarification": True,
        }

    if compile_errors:
        parts.append("Your strategy didn't pass verification:")
        for err in compile_errors[:5]:
            parts.append(f"- {err}")
        parts.append("Please describe the changes you'd like and I'll regenerate the code.")
        return {
            "chat_response": "\n".join(parts),
            "awaiting_revision": True,
        }

    if metrics and backtest:
        parts.append(backtest)
        if code:
            parts.append("Here is the generated strategy code (Python):\n\n```python\n" + code + "\n```")
        parts.append('Type "approve" to deploy (stub), or reply with changes to iterate.')
        return {
            "chat_response": "\n\n".join(parts),
            "awaiting_approval": True,
        }

    # Fallback
    return {"chat_response": "I could not generate a strategy. Please refine your request."}

 
async def _entry_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """No-op entry node; routing decides next step."""
    return {}


async def _analyze_requirements_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze if prompt has enough info; set sufficient_data and clarification message."""
    prompt = (state.get("user_prompt") or "").strip()
    revision = (state.get("revision_prompt") or state.get("user_feedback") or "").strip()
    text = prompt if not revision else f"Original:\n{prompt}\n\nRevision:\n{revision}"

    llm = get_llm_manager()
    messages = [
        Message(
            role="system",
            content=(
                "Extract minimal fields for trading strategy generation. Respond only JSON: "
                "{symbol, timeframe, entry_conditions:[], exit_conditions:[], risk:{max_drawdown_percent?, min_win_rate_percent?, min_total_return_percent?}}"
            ),
        ),
        Message(role="user", content=text),
    ]
    try:
        resp = await llm.chat(messages)
        data = json.loads(resp.content or "{}") if resp.content else {}
    except Exception:
        data = {}

    missing: list[str] = []
    symbol = data.get("symbol")
    timeframe = data.get("timeframe")
    entries = data.get("entry_conditions") or []
    exits = data.get("exit_conditions") or []
    if not symbol:
        missing.append("symbol (e.g., BTC/USDC)")
    if not timeframe:
        missing.append("timeframe (e.g., 1h)")
    if not entries:
        missing.append("entry_conditions (clear rules)")
    if not exits:
        missing.append("exit_conditions (clear rules)")

    sufficient = len(missing) == 0
    clarification = "Missing: " + ", ".join(missing) if missing else ""
    return {
        "strategy_requirements": data,
        "sufficient_data": sufficient,
        "clarification_message": clarification,
    }


async def _clarify_requirements_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Forward clarification to responder; flag awaiting clarification."""
    return {"awaiting_clarification": True}


async def _verify_strategy_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Compile and verify generated strategy implements BaseStrategy."""
    code = state.get("strategy_code") or ""
    errors: list[str] = []
    interface_valid = False
    try:
        if not code:
            raise ValueError("No code produced")
        env: Dict[str, Any] = {
            "BaseStrategy": BaseStrategy,
            "StrategyConfig": StrategyConfig,
            "MarketData": MarketData,
            "StrategyContext": StrategyContext,
            "Order": Order,
            "OrderSide": OrderSide,
        }
        local_ns: Dict[str, Any] = {}
        compiled = compile(code, "<generated_strategy>", "exec")
        exec(compiled, env, local_ns)
        strategy_cls = None
        for v in local_ns.values():
            if isinstance(v, type) and issubclass(v, BaseStrategy) and v is not BaseStrategy:
                strategy_cls = v
                break
        if not strategy_cls:
            errors.append("No BaseStrategy subclass found in generated code.")
        else:
            interface_valid = True
    except Exception as exc:
        errors.append(str(exc))

    return {
        "compile_passed": interface_valid and not errors,
        "interface_valid": interface_valid,
        "compile_errors": errors,
        "validation_notes": "OK" if not errors else "; ".join(errors),
    }


async def _deploy_strategy_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Stub deployment: print to console/log and confirm."""
    code = (state.get("strategy_code") or "")
    logger.info("[DEPLOY] Deploying strategy (stub). Code length=%d", len(code))
    return {"chat_response": "✅ Strategy deployed (stub).", "deployment_ready": True}


def _route_from_entry(state: Dict[str, Any]) -> str:
    action = str(state.get("user_action") or "").lower()
    if action.startswith("approve") or state.get("approved"):
        return "deploy"
    if state.get("revision_prompt") or state.get("user_feedback"):
        return "generate"
    return "analyze"


def _build_graph():
    graph: StateGraph = StateGraph(dict)
    # Nodes
    graph.add_node("entry", _entry_node)
    graph.add_node("analyze", _analyze_requirements_node)
    graph.add_node("clarify", _clarify_requirements_node)
    graph.add_node("generate", _design_strategy_node)
    graph.add_node("verify", _verify_strategy_node)
    graph.add_node("backtest", _backtest_node)
    graph.add_node("deploy", _deploy_strategy_node)
    graph.add_node("respond", _respond_node)

    # Routing from entry
    graph.add_conditional_edges(
        "entry",
        _route_from_entry,
        {"analyze": "analyze", "generate": "generate", "deploy": "deploy"},
    )

    # Analyze -> Generate or Clarify (edge-attached conditions)
    graph.add_edge("analyze", "generate", condition=lambda s: s.get("sufficient_data", False))
    graph.add_edge("analyze", "clarify", condition=lambda s: not s.get("sufficient_data", False))

    # Clarify -> Respond -> END
    graph.add_edge("clarify", "respond")

    # Implementation loop: Generate -> Verify
    graph.add_edge("generate", "verify")

    # Verify -> Backtest or Respond (ask for revision)
    graph.add_edge(
        "verify",
        "backtest",
        condition=lambda s: bool(s.get("compile_passed") and s.get("interface_valid")),
    )
    graph.add_edge(
        "verify",
        "respond",
        condition=lambda s: not bool(s.get("compile_passed") and s.get("interface_valid")),
    )

    # Backtest -> Respond (results + ask approve/revise)
    graph.add_edge("backtest", "respond")

    # Deploy -> Respond
    graph.add_edge("deploy", "respond")

    # Terminal
    graph.add_edge("respond", END)
    graph.set_entry_point("entry")
    return graph.compile()


_COMPILED_GRAPH = _build_graph()


class VibeTraderAgent:
    """
    Main agent for the VibeTrader chat interface.
    
    Wraps the StrategyBuilderAgent graph and manages conversation flow.
    """

    def __init__(self, send_callback: Callable[[str], Awaitable[None]]):
        """
        Initialize the agent.
        
        Args:
            send_callback: Async function to send messages back to the user
        """
        self.send_callback = send_callback
        self.state: Dict[str, Any] = {}

    async def process_message(self, message: str) -> None:
        """Process an incoming message from the user."""
        logger.info("Processing message: %s", message[:100])
        try:
            msg = (message or "").strip()
            lower = msg.lower()

            # Determine user action/context
            if not self.state:
                # Fresh session
                self.state = {"user_prompt": msg, "conversation_started": True}
            else:
                if self.state.get("awaiting_clarification"):
                    self.state.pop("awaiting_clarification", None)
                    self.state["user_feedback"] = msg
                elif self.state.get("awaiting_revision"):
                    self.state.pop("awaiting_revision", None)
                    self.state["revision_prompt"] = msg
                elif self.state.get("awaiting_approval") and ("approve" in lower or "deploy" in lower):
                    self.state.pop("awaiting_approval", None)
                    self.state["user_action"] = "approve"
                else:
                    # Default to revision flow
                    self.state["revision_prompt"] = msg

            result = await _COMPILED_GRAPH.invoke(self.state, {"max_iterations": 20})
            # Persist state across turns
            if isinstance(result, dict):
                self.state.update(result)

            response = self.state.get("chat_response") or result.get("chat_response") or "I could not proceed."
            await self.send_callback(response)
        except Exception as exc:
            logger.error("Error processing message: %s", exc, exc_info=True)
            await self.send_callback(
                f"❌ I encountered an error: {exc}\n\nPlease try again or rephrase your request."
            )

    async def reset_session(self) -> None:
        """Reset the current session and clear state."""
        self.state = {}
        logger.info("Session reset")


# Alias for backward compatibility
StubAgent = VibeTraderAgent

