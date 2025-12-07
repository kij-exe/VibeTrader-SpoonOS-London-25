"""
WebSocket Connection Manager

Manages WebSocket connections and message routing.
"""

import logging
from typing import Dict, Union, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """
        Accept and register a new WebSocket connection.
        
        Args:
            websocket: The WebSocket connection
            client_id: Unique identifier for the client
        """
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, client_id: str) -> None:
        """
        Remove a client connection.
        
        Args:
            client_id: The client to disconnect
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected. Total connections: {len(self.active_connections)}")

    async def send_message(self, client_id: str, message: Union[str, Dict[str, Any]]) -> None:
        """
        Send a message to a specific client.
        
        Args:
            client_id: The target client
            message: The message to send (string or structured dict)
        """
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                # Support both plain text (legacy) and structured messages
                if isinstance(message, str):
                    payload = {
                        "type": "message",
                        "message_type": "text",
                        "content": message
                    }
                else:
                    # Structured message
                    payload = {
                        "type": "message",
                        **message
                    }
                
                await websocket.send_json(payload)
                logger.debug(f"Sent message to {client_id}: {type(message).__name__}")
            except Exception as e:
                logger.warning(f"Failed to send message to {client_id}: {e}")
                # Client likely disconnected, remove from active connections
                self.disconnect(client_id)

    async def send_raw_message(self, client_id: str, message: str) -> None:
        """
        Send a raw JSON string message to a specific client.
        Used for backtest results that are already JSON formatted.
        
        Args:
            client_id: The target client
            message: The raw JSON string to send
        """
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_text(message)
                logger.debug(f"Sent raw message to {client_id}")
            except Exception as e:
                logger.warning(f"Failed to send raw message to {client_id}: {e}")
                self.disconnect(client_id)

    async def broadcast(self, message: Union[str, Dict[str, Any]]) -> None:
        """
        Broadcast a message to all connected clients.
        
        Args:
            message: The message to broadcast (string or structured dict)
        """
        disconnected = []
        for client_id, websocket in list(self.active_connections.items()):
            try:
                # Support both plain text (legacy) and structured messages
                if isinstance(message, str):
                    payload = {
                        "type": "message",
                        "message_type": "text",
                        "content": message
                    }
                else:
                    payload = {
                        "type": "message",
                        **message
                    }
                
                await websocket.send_json(payload)
            except Exception as e:
                logger.warning(f"Failed to broadcast to {client_id}: {e}")
                disconnected.append(client_id)
        
        # Remove disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)
        
        logger.debug(f"Broadcast message to {len(self.active_connections)} clients")
