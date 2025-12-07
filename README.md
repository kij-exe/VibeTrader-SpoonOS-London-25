# VibeTrader - AI-Powered Trading Strategy Platform

LLM-driven trading strategy generator with automated backtesting using QuantConnect Lean and real-time market data from Binance.

## 🏗️ Architecture

The system uses a **state graph-based agent** with multiple specialized sub-agents and a **message queue consumer** for interactive user communication.

```
┌──────────────┐  WebSocket   ┌──────────────────────────────────────┐
│   Frontend   │◄────────────►│  FastAPI Backend                     │
│ React + Vite │              │  ┌────────────────────────────────┐  │
│              │              │  │  VibeTraderAgent (State Graph) │  │
│              │              │  │  • Message Queue Consumer      │  │
│              │              │  │  • Graph Executor (SpoonOS)    │  │
│              │  ┌───────────┼──┤                                │  │
│              │  │ Messages  │  │  States: clarify → design →    │  │
│              │  │ Enqueued  │  │          compile → respond →   │  │
│              │  │           │  │          await_feedback        │  │
│              │  └───────────┼──┤                                │  │
│              │              │  │  Sub-agents:                   │  │
│              │              │  │  • Intent Classifier           │  │
│              │              │  │  • QuantStrategyAgent          │  │
│              │              │  └────────────────────────────────┘  │
└──────────────┘              │                 │                    │
                              │                 ▼                    │
                              │  ┌──────────────────────────────┐    │
                              │  │  Backtesting Engine          │    │
                              │  │  • QuantConnect Lean (Docker)│    │
                              │  │  • Binance Market Data API   │    │
                              │  │  • Strategy Compilation      │    │
                              │  └──────────────────────────────┘    │
                              └──────────────────────────────────────┘
```

## 📁 Project Structure

### `/backend` - FastAPI + Agent System
- **`app/agent/agent.py`**: Main state graph agent with message queue consumer
- **`app/agent/quant_agent.py`**: Specialized LLM agent for strategy code generation
- **`app/main.py`**: FastAPI server with WebSocket endpoints
- **`app/websocket_manager.py`**: Connection management and message routing
- **`app/message_types.py`**: Structured message schemas (Pydantic)

### `/backtesting` - QuantConnect Lean Integration
- **`agent/backtesting_agent.py`**: Orchestrates backtest workflow
- **`data/binance_fetcher.py`**: Real-time and historical data from Binance API
- **`data/converter/lean_converter.py`**: Converts Binance data to Lean format
- **`engine/lean_runner.py`**: Docker-based Lean execution
- **`docs/`**: Lean API reference and indicator documentation for LLM context

### `/frontend` - React UI
- **`src/components/Chat.jsx`**: Main chat interface
- **`src/components/MessageRenderer.jsx`**: Structured message rendering
- **`src/hooks/useWebSocket.jsx`**: WebSocket connection management

## 🧠 Agent State Graph & Message Queue

The agent operates as a **state machine** using SpoonOS Graph:

1. **State Graph Nodes**:
   - `clarify_requirements`: Extracts strategy details from conversation
   - `design`: Generates strategy code using QuantStrategyAgent
   - `compile`: Runs backtest via Lean engine
   - `respond`: Sends results to user
   - `await_feedback`: Waits for user input via message queue

2. **Message Queue Consumer**:
   - Runs async loop consuming `asyncio.Queue`
   - User messages enqueued via WebSocket → Queue
   - Agent consumes from queue → processes → sends response
   - Enables **interactive feedback loop** for strategy refinement

3. **Conditional Routing**:
   - Intent classification (modify spec / rerun backtest / modify code)
   - Error-based routing (symbol errors → clarify, code errors → design)
   - Feedback-based routing (user request → appropriate state)

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI (async WebSocket support)
- **Agent System**: SpoonOS SDK (state graphs, LLM orchestration)
- **LLMs**: OpenAI GPT-4/5.1 (via spoon-ai-sdk), Anthropic Claude
- **Backtesting**: QuantConnect Lean (Docker)
- **Market Data**: Binance API (REST + WebSocket)

### Frontend
- **Framework**: React + Vite
- **Styling**: TailwindCSS
- **Components**: Lucide Icons, custom structured message renderers
- **State**: React hooks (WebSocket, message history)

### Infrastructure
- **Containerization**: Docker + docker-compose (backend + frontend)
- **Lean Engine**: QuantConnect Lean runs in ephemeral Docker containers (spawned on-demand per backtest)
- **Data Storage**: File-based caching (JSON) for market data
- **Message Protocol**: WebSocket (JSON-RPC style)

**Note:** `quantconnect/lean:latest` is not in docker-compose. It's pulled automatically by Docker when the first backtest runs.

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Start all services
docker-compose up --build

# Or use the helper script
./docker-start.sh
```

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- WebSocket: `ws://localhost:8000/ws/{client_id}`

### Manual Setup

#### Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Add your API keys: ANTHROPIC_API_KEY, BINANCE_API_KEY, etc.

# Run
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

## 🐳 Deploy to DockerHub

```bash
# Build and tag images
docker build -f Dockerfile.backend -t yourusername/vibetrader-backend:latest .
docker build -f Dockerfile.frontend -t yourusername/vibetrader-frontend:latest .

# Login to DockerHub
docker login

# Push images
docker push yourusername/vibetrader-backend:latest
docker push yourusername/vibetrader-frontend:latest

# Update docker-compose.yml to use remote images
# Change:
#   build: ...
# To:
#   image: yourusername/vibetrader-backend:latest
```

## 🔑 Key Design Patterns

### Multiple Agent Pattern
- **VibeTraderAgent**: Orchestrates workflow, manages state
- **QuantStrategyAgent**: Specializes in strategy code generation
- **Intent Classifier**: Analyzes user feedback for routing
- **Benefits**: Clean separation of concerns, focused context per agent

### Error Enrichment
- Backtest errors enriched with context + fix suggestions
- LLM receives actionable guidance (e.g., "Use Resolution.Daily for 1d timeframe")
- Reduces retry loops, improves fix success rate

### Feedback Loop
- User can refine strategy after seeing results
- Automatic intent classification (modify spec / rerun / modify code)
- Parameter extraction (LLM extracts timeframe, date range from natural language)
- Loops back to appropriate state node

## �️ SpoonOS Tools Integration

The system leverages **SpoonOS SDK** for agent orchestration and custom tools:

### SpoonOS Components Used
- **SpoonReactMCP**: Agentic framework with tool calling (QuantStrategyAgent extends this)
- **ChatBot**: LLM abstraction layer (supports OpenAI, Anthropic)
- **ToolManager**: Tool registration and execution
- **BaseTool**: Base class for custom tool definitions
- **State Graphs**: Node-based workflow orchestration with conditional routing

### Custom Tools Defined

**1. `DocsReaderTool`** (`read_strategy_docs`)
- **Purpose**: Reads Lean QuantConnect strategy documentation
- **Input**: None
- **Output**: Full `QUANT_AGENT_CONTEXT.md` content
- **Use Case**: LLM retrieves best practices for strategy structure, indicators, warmup periods

**2. `IndicatorReferenceTool`** (`get_lean_indicators`)
- **Purpose**: Provides comprehensive indicator reference (100+ indicators)
- **Input**: None
- **Output**: Full `LEAN_INDICATORS_REFERENCE.md` with usage examples
- **Use Case**: LLM looks up available indicators (RSI, MACD, BB) and their parameters

**3. `StrategyGeneratorTool`** (`generate_lean_strategy`)
- **Purpose**: Generates complete Lean strategy code from requirements
- **Input**: 
  - `strategy_name`: PascalCase class name
  - `requirements`: {symbol, timeframe, entry_conditions, exit_conditions, risk_management}
- **Output**: Complete Python code with imports, indicators, trading logic
- **Use Case**: Transforms natural language requirements into executable Lean code

**4. `MCPTool` (Optional)** (`web_search`)
- **Purpose**: Web search via Tavily MCP for trading strategies/research
- **Input**: Search query
- **Output**: Relevant web results
- **Use Case**: LLM can research trading patterns, indicators, market conditions
- **Note**: Only enabled if `TAVILY_API_KEY` is set

### Tool Workflow

```
User: "Create RSI strategy"
  ↓
QuantStrategyAgent receives request
  ↓
Calls get_lean_indicators() → Retrieves RSI documentation
  ↓
Calls generate_lean_strategy(
  strategy_name="RSIMeanReversion",
  requirements={
    symbol: "BTCUSDT",
    entry_conditions: "RSI < 30",
    exit_conditions: "RSI > 70"
  }
) → Returns complete Python code
  ↓
Code sent to compile node for backtesting
```

## �� Supported Features

- **Timeframes**: 1m (minute), 1h (hourly), 1d (daily)
- **Indicators**: 100+ Lean built-in indicators (RSI, MACD, Bollinger Bands, etc.)
- **Assets**: Crypto pairs on Binance (BTCUSDT, ETHUSDT, etc.)
- **Backtesting**: Historical data from 2020-01-01 to present
- **Metrics**: Total return, max drawdown, win rate, Sharpe ratio, total trades
