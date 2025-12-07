"""
Message type definitions for frontend-backend communication.

Supports structured messages with code blocks, progress updates, and rich formatting.
"""

from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel


class CodeBlock(BaseModel):
    """Code block with syntax highlighting metadata."""
    language: str = "python"
    code: str
    filename: Optional[str] = None
    highlighted_lines: Optional[List[int]] = None


class MessageContent(BaseModel):
    """Structured message content."""
    type: Literal["text", "code", "progress", "results", "error"] = "text"
    text: Optional[str] = None
    code_block: Optional[CodeBlock] = None
    metadata: Optional[Dict[str, Any]] = None


class StructuredMessage(BaseModel):
    """Structured message format for WebSocket communication."""
    message_type: Literal["text", "code", "progress", "results", "error", "system"]
    content: str  # Markdown-formatted text
    code_blocks: Optional[List[CodeBlock]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "message_type": "code",
                    "content": "Here's your generated strategy:",
                    "code_blocks": [{
                        "language": "python",
                        "code": "from AlgorithmImports import *\n\nclass MyStrategy(QCAlgorithm):\n    pass",
                        "filename": "strategy.py"
                    }],
                    "metadata": {"strategy_name": "MyStrategy"}
                }
            ]
        }


def create_text_message(content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a simple text message."""
    return {
        "message_type": "text",
        "content": content,
        "metadata": metadata or {}
    }


def create_code_message(
    content: str,
    code: str,
    language: str = "python",
    filename: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a message with code block."""
    return {
        "message_type": "code",
        "content": content,
        "code_blocks": [{
            "language": language,
            "code": code,
            "filename": filename
        }],
        "metadata": metadata or {}
    }


def create_progress_message(content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a progress update message."""
    return {
        "message_type": "progress",
        "content": content,
        "metadata": metadata or {}
    }


def create_results_message(
    content: str,
    code: Optional[str] = None,
    language: str = "python",
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a results message with optional code."""
    msg = {
        "message_type": "results",
        "content": content,
        "metadata": metadata or {}
    }
    if code:
        msg["code_blocks"] = [{
            "language": language,
            "code": code
        }]
    return msg


def create_error_message(content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create an error message."""
    return {
        "message_type": "error",
        "content": content,
        "metadata": metadata or {}
    }


def create_backtest_replay_message(
    content: str,
    backtest_data: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a message with full backtest results for order replay."""
    return {
        "message_type": "backtest_replay",
        "content": content,
        "backtest_data": backtest_data,
        "metadata": metadata or {}
    }
