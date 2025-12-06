"""
Stub Agent Implementation

This is a placeholder agent that logs incoming messages and responds with "HI".
Will be replaced with actual SpoonOS-based agent implementation.
"""

import logging
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)


class StubAgent:
    """
    Stub agent for initial development.
    Logs messages and sends a simple response.
    """

    def __init__(self, send_callback: Callable[[str], Awaitable[None]]):
        """
        Initialize the stub agent.
        
        Args:
            send_callback: Async function to send messages back to the user
        """
        self.send_callback = send_callback
        logger.info("StubAgent initialized")

    async def process_message(self, message: str) -> None:
        """
        Process an incoming message from the user.
        
        Args:
            message: The user's message
        """
        # Log the incoming message
        logger.info(f"Received message: {message}")
        print(f"[AGENT] Received message: {message}")

        # Send response back to user
        response = "HI"
        logger.info(f"Sending response: {response}")
        print(f"[AGENT] Sending response: {response}")
        
        await self.send_callback(response)
