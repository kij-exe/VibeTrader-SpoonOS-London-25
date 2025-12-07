"""Documentation reader tools for accessing backtesting documentation."""

from pathlib import Path
from typing import Dict
from spoon_ai.tools.base import BaseTool


class DocsReaderTool(BaseTool):
    """Read backtesting strategy writing documentation."""
    
    name: str = "read_strategy_docs"
    description: str = """Read comprehensive documentation about writing Lean QuantConnect trading strategies.
    Use this when you need to understand:
    - How to properly structure strategies
    - Which indicators to use (Lean's built-in)
    - Warmup period requirements
    - Best practices for strategy development
    Returns the full QUANT_AGENT_CONTEXT.md documentation."""
    
    parameters: dict = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    def _get_docs_dir(self) -> Path:
        """Get path to docs directory."""
        # Path from backend to backtesting docs
        return Path(__file__).parent.parent.parent.parent.parent / "backtesting" / "docs"
    
    async def execute(self) -> str:
        """Read and return documentation content."""
        try:
            docs_dir = self._get_docs_dir()
            context_file = docs_dir / "QUANT_AGENT_CONTEXT.md"
            
            if not context_file.exists():
                return f"❌ Documentation not found at {context_file}"
            
            with open(context_file, "r") as f:
                content = f.read()
            
            return f"""📚 Lean QuantConnect Strategy Writing Guide

{content}

Remember: ALWAYS use Lean's built-in indicators. NEVER implement custom calculations."""
        except Exception as e:
            return f"❌ Error reading documentation: {str(e)}"


class IndicatorReferenceTool(BaseTool):
    """Get detailed Lean indicator reference."""
    
    name: str = "get_lean_indicators"
    description: str = """Get comprehensive reference for Lean QuantConnect indicators.
    Use this when you need to know:
    - Available indicators (RSI, MACD, Bollinger Bands, etc.)
    - How to initialize indicators in Lean
    - Correct parameter usage
    - How to access indicator values
    Returns the full LEAN_INDICATORS_REFERENCE.md with all indicators."""
    
    parameters: dict = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    def _get_docs_dir(self) -> Path:
        """Get path to docs directory."""
        return Path(__file__).parent.parent.parent.parent.parent / "backtesting" / "docs"
    
    async def execute(self) -> str:
        """Read and return indicator reference."""
        try:
            docs_dir = self._get_docs_dir()
            reference_file = docs_dir / "LEAN_INDICATORS_REFERENCE.md"
            
            if not reference_file.exists():
                return f"❌ Indicator reference not found at {reference_file}"
            
            with open(reference_file, "r") as f:
                content = f.read()
            
            return f"""📊 Lean Indicators Complete Reference

{content}

Key Rule: Use Lean's built-in indicators via self.INDICATOR_NAME(symbol, parameters)"""
            
        except Exception as e:
            return f"❌ Error reading indicator reference: {str(e)}"
