"""
VibeTrader Backend - FastAPI WebSocket Server

Main entry point for the backend server that handles WebSocket connections
and routes messages to the agent.
"""

import logging
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.websocket_manager import ConnectionManager
from app.agent.agent import StubAgent

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
    agent = StubAgent(send_callback=send_to_client)
    
    # Start the consumer loop
    await agent.start()
    
    # Send welcome message
    await manager.send_message(client_id, "Welcome to VibeTrader! Describe your portfolio management strategy and I'll help you build it.")
    
    try:
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
