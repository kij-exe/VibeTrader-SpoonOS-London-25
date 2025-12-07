"""
VibeTrader Backend - FastAPI WebSocket Server

Main entry point for the backend server that handles WebSocket connections
and routes messages to the agent.
"""

import asyncio
import json
import logging
import uuid
import sys
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.websocket_manager import ConnectionManager
from app.agent.agent import VibeTraderAgent

# Add backtesting module to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="VibeTrader API",
    description="AI-powered portfolio management strategy platform",
    version="0.1.0"
)

# Configure CORS for frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize connection manager
manager = ConnectionManager()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "VibeTrader API"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/api/backtest")
async def run_backtest_endpoint(
    symbol: str = "BTCUSDT",
    timeframe: str = "1h",
    strategy_path: str = None
):
    """
    Run a backtest using an existing strategy file and return results.
    
    The strategy_path points to the original strategy file from the chat backtest.
    We read it, modify the symbol/timeframe, run Docker, and read results.
    """
    import json
    from pathlib import Path
    from backtesting.agent.backtesting_agent import BacktestingAgent, BacktestRequest
    
    if not strategy_path:
        return {"success": False, "error": "No strategy path provided"}
    
    strategy_file = Path(strategy_path)
    if not strategy_file.exists():
        return {"success": False, "error": f"Strategy file not found: {strategy_path}"}
    
    try:
        logger.info(f"Running backtest: {symbol} {timeframe} using {strategy_path}")
        
        # Read the original strategy code
        with open(strategy_file, 'r') as f:
            strategy_code = f.read()
        
        # Modify strategy code for the new symbol
        modified_code = strategy_code
        # Replace common symbols with the target symbol
        for old_sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT"]:
            if old_sym != symbol:
                modified_code = modified_code.replace(old_sym, symbol)
                modified_code = modified_code.replace(old_sym.lower(), symbol.lower())
        
        # Run backtest
        bt_agent = BacktestingAgent()
        request = BacktestRequest(
            strategy_code=modified_code,
            symbol=symbol,
            interval=timeframe,
            start_date="2025-01-01",
            end_date="2025-06-30",
            initial_capital=100000.0,
        )
        
        result = await bt_agent.run_backtest(request)
        
        logger.info(f"Backtest result: success={result.success}, results_dir={result.results_dir}")
        
        if not result.success:
            logger.error(f"Backtest failed: {result.error_message}")
            return {
                "success": False,
                "error": result.error_message,
                "symbol": symbol,
                "timeframe": timeframe
            }
        
        # Read results from the EXACT results folder for this backtest run
        backtest_data = None
        
        logger.info(f"Looking for results in: {result.results_dir}")
        
        if result.results_dir and result.results_dir.exists():
            # List all files in results dir
            files = list(result.results_dir.iterdir())
            logger.info(f"Files in results dir: {[f.name for f in files]}")
            
            # Find the main results JSON file (not order-events, summary, data-monitor, etc.)
            json_file = None
            for f in files:
                if f.suffix == '.json':
                    # Skip auxiliary files
                    if any(skip in f.name for skip in ['order-events', 'summary', 'data-monitor', 'log', 'config']):
                        continue
                    json_file = f
                    break
            
            if json_file and json_file.exists():
                logger.info(f"Loading results from: {json_file}")
                with open(json_file, 'r') as f:
                    backtest_data = json.load(f)
                
                # Log key metrics from the loaded data
                if backtest_data:
                    total_perf = backtest_data.get("totalPerformance", {})
                    trade_stats = total_perf.get("tradeStatistics", {})
                    portfolio_stats = total_perf.get("portfolioStatistics", {})
                    runtime_stats = backtest_data.get("runtimeStatistics", {})
                    
                    logger.info(f"Loaded backtest data:")
                    logger.info(f"  - Total trades: {trade_stats.get('totalNumberOfTrades', 'N/A')}")
                    logger.info(f"  - Net Profit: {runtime_stats.get('Net Profit', 'N/A')}")
                    logger.info(f"  - Return: {runtime_stats.get('Return', 'N/A')}")
                    logger.info(f"  - Compounding Annual Return: {portfolio_stats.get('compoundingAnnualReturn', 'N/A')}")
                    
                    # Check profitLoss
                    profit_loss = backtest_data.get("profitLoss", {})
                    logger.info(f"  - profitLoss entries: {len(profit_loss)}")
                    
                    # Check orders
                    orders = backtest_data.get("orders", {})
                    logger.info(f"  - orders: {len(orders)}")
                    
                    # Check charts
                    charts = backtest_data.get("charts", {})
                    equity_chart = charts.get("Strategy Equity", {})
                    equity_series = equity_chart.get("series", {}).get("Equity", {})
                    equity_values = equity_series.get("values", [])
                    logger.info(f"  - Equity curve points: {len(equity_values) if isinstance(equity_values, list) else len(equity_values.keys())}")
            else:
                logger.warning(f"No results JSON file found in: {result.results_dir}")
        else:
            logger.warning(f"Results directory not found or doesn't exist: {result.results_dir}")
        
        logger.info(f"Backtest complete: {symbol} {timeframe}")
        
        return {
            "success": True,
            "backtest_data": backtest_data,
            "symbol": symbol,
            "timeframe": timeframe
        }
        
    except Exception as e:
        logger.error(f"Backtest failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "symbol": symbol,
            "timeframe": timeframe
        }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for chat communication.
    
    Accepts connections, creates an agent instance for each client,
    and routes messages to/from the agent.
    """
    # Generate unique client ID
    client_id = str(uuid.uuid4())
    
    # Connect the client
    await manager.connect(websocket, client_id)
    logger.info(f"New WebSocket connection: {client_id}")
    
    # Create send callback for this client
    async def send_to_client(message: str):
        await manager.send_message(client_id, message)
    
    # Initialize agent for this client
    agent = VibeTraderAgent(send_callback=send_to_client)
    
    # Start the consumer loop
    await agent.start()
    
    try:
        # Send welcome message
        await manager.send_message(client_id, "Welcome to VibeTrader! Describe your portfolio management strategy and I'll help you build it.")
        
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message = data.get("content", "")
            
            if message:
                logger.info(f"Received from {client_id}: {message}")
                # Producer: add message to agent's queue
                await agent.process_message(message)
                
    except WebSocketDisconnect:
        await agent.stop()
        manager.disconnect(client_id)
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"Error with client {client_id}: {e}")
        await agent.stop()
        manager.disconnect(client_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
