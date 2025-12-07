# Backend - FastAPI + State Graph Agent

State graph-based agent with WebSocket communication and message queue consumer pattern.

## Architecture

```
WebSocket → ConnectionManager → VibeTraderAgent
                                    ↓
                              Message Queue (asyncio.Queue)
                                    ↓
                              Consumer Loop
                                    ↓
                              State Graph (SpoonOS)
                                    ↓
                    entry → clarify → design → compile → respond → await_feedback
                                                                        ↓
                                                                    (loop back)
```

## Core Components

### `app/main.py` - FastAPI Server
- WebSocket endpoint: `/ws/{client_id}`
- One agent instance per client
- Consumer loop runs as async task

```python
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket, client_id):
    agent = VibeTraderAgent(progress_callback)
    consumer_task = asyncio.create_task(agent.start_consumer())
    
    async for message in websocket.iter_text():
        await agent.enqueue_message(message)  # → Queue
```

### `app/websocket_manager.py` - ConnectionManager
- Track active connections per client
- Serialize Pydantic models → JSON
- Handle disconnections

### `app/agent/agent.py` - VibeTraderAgent

**State Schema:**
```python
StrategyState = {
    messages: List[dict],           # Conversation history
    message_queue: asyncio.Queue,   # User messages
    strategy_spec: Dict,            # {symbol, timeframe, conditions, dates}
    strategy_code: str,             # Generated Python code
    compile_errors: List[str],      # Enriched with fixes
    backtest_metrics: Dict,         # Results
    awaiting_feedback: bool,
    feedback_intent: str            # modify_spec/rerun_backtest/modify_code/end
}
```

**Message Queue Pattern:**
- WebSocket (fast) → Queue → Agent (slow LLM)
- Decouples I/O from processing
- Enables blocking wait in `await_feedback` node

**State Graph Nodes:**

1. **entry**: Route to clarify or respond
2. **clarify**: Extract strategy params via GPT-5.1, validate timeframe/symbol
3. **design**: Generate/fix code via QuantStrategyAgent
4. **compile**: Run backtest, enrich errors
5. **respond**: Send results, set awaiting_feedback=True
6. **await_feedback**: Block on queue.get(), classify intent via GPT-4, extract params

**Conditional Routing:**
```python
# From compile:
if success: → respond
elif symbol_error: → clarify
elif retry_count >= 5: → respond (give up)
else: → design (fix code)

# From feedback:
if modify_spec: → clarify
elif rerun_backtest: → compile
elif modify_code: → design
else: → END
```

### `app/agent/quant_agent.py` - QuantStrategyAgent
- Specialized SpoonOS agent for Lean code generation
- Tools: `get_lean_indicators()`, `get_lean_context()`
- Modes: Generate new / Fix existing

### Error Enrichment (`_enrich_error_message`)
Transforms cryptic Lean errors into actionable guidance:

```
Input: "Unable to create consolidator for Daily data"
Output:
  ❗ CONSOLIDATOR ERROR
  1. Resolution Mismatch: Daily data can't be consolidated
  2. Fix: Remove consolidator calls, use Resolution.Daily
  3. Example: self.add_crypto('BTCUSDT', Resolution.Daily)
```

Handles: consolidator, import, symbol, attribute, syntax, warmup errors.

## Message Types (`app/message_types.py`)

```python
StructuredMessage = {
    message_type: "text" | "code" | "metrics" | "backtest_replay",
    content: str,
    metadata: Dict,
    metrics: Dict,          # For "metrics" type
    backtest_data: Dict     # For "backtest_replay" type
}
```

Frontend renders each type differently (code blocks, charts, etc.)

## Data Flow

```
User: "RSI strategy, buy <30, sell >70"
  → WebSocket → enqueue_message()
  → Consumer: queue.get()
  → Graph: entry → clarify
  → GPT-5.1: Extract {entry: "RSI<30", exit: "RSI>70", symbol: "BTCUSDT"}
  → design → QuantStrategyAgent generates code
  → compile → Backtest runs, returns metrics
  → respond → Send results to frontend
  → await_feedback → Block on queue

User: "Rerun for 2024"
  → GPT-4: Classify intent="rerun_backtest"
  → Extract: {start_date: "2024-01-01", end_date: "2024-12-31"}
  → Route: feedback → compile (with new dates)
  → respond → Send new results
```

## Tech Stack

- **FastAPI**: Async WebSocket server
- **SpoonOS SDK**: State graphs, agent orchestration
- **LLMs**: GPT-4/5.1 (OpenAI), Claude (Anthropic)
- **WebSocket**: Real-time bidirectional communication
- **asyncio**: Queue-based message processing

## Configuration

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
BINANCE_API_KEY=...
BINANCE_API_SECRET=...
```

## Development

```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Test WebSocket:**
```bash
wscat -c ws://localhost:8000/ws/test-client
> {"type": "chat", "content": "RSI strategy"}
```

## Key Design Patterns

1. **Multiple Agents**: VibeTraderAgent (orchestration) + QuantStrategyAgent (code gen) + Intent Classifier (routing)
2. **Message Queue**: Decouples WebSocket I/O from slow LLM processing
3. **Error Enrichment**: LLM receives context + fixes, not raw errors
4. **Feedback Loop**: User refines strategy after results via intent classification
