"""
Quant Strategy Agent using SpoonOS SpoonReactMCP.

This agent generates Lean QuantConnect trading strategies using:
- Custom tools (docs reader, indicator reference, strategy generator)
- Web search (optional, via Tavily MCP)
- SpoonOS ChatBot for LLM interactions
"""

import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from spoon_ai.agents import SpoonReactMCP
from spoon_ai.chat import ChatBot
from spoon_ai.tools import ToolManager
from spoon_ai.tools.mcp_tool import MCPTool

from .tools import DocsReaderTool, IndicatorReferenceTool, StrategyGeneratorTool


load_dotenv()
logger = logging.getLogger(__name__)


class QuantStrategyAgent(SpoonReactMCP):
    """
    Quant strategy generation agent with custom tools and web search.
    
    Uses SpoonOS SpoonReactMCP for agentic behavior with tool calling.
    """
    
    name: str = "QuantStrategyAgent"
    
    system_prompt: str = """You are an expert quantitative trading strategist specializing in cryptocurrency trading strategies.

Your role is to generate Lean QuantConnect trading strategies based on user requirements.

AVAILABLE TOOLS:
1. **read_strategy_docs** - Read comprehensive documentation about Lean QuantConnect strategy development
2. **get_lean_indicators** - Get detailed reference for Lean's built-in indicators
3. **generate_lean_strategy** - Generate complete strategy code from requirements
4. **web_search** - Search the web for trading strategies and quant research (if available)

CRITICAL RULES:
- ALWAYS use Lean's built-in indicators (RSI, MACD, Bollinger Bands, etc.)
- NEVER implement custom indicator calculations
- ALWAYS set proper warmup periods (20x indicator period)
- ALWAYS use Binance brokerage model for crypto
- Generate complete, runnable code with all required imports

WORKFLOW:
1. When asked to create a strategy, first read the docs if you need guidance
2. Look up indicator reference if you need specific indicator details
3. Generate the strategy code using generate_lean_strategy with extracted requirements
4. The generated code will be compiled and backtested automatically
5. If compilation fails, you'll receive errors and should fix the code

Be helpful, accurate, and always generate production-ready code following Lean best practices."""
    
    def __init__(self, **kwargs):
        """Initialize the quant strategy agent with tools."""
        super().__init__(**kwargs)
        
        # Initialize LLM
        self.llm = ChatBot(
            llm_provider="openai",
            model_name="gpt-5.1-2025-11-13",
        )
        
        # Create custom tools
        custom_tools = [
            DocsReaderTool(),
            IndicatorReferenceTool(),
            StrategyGeneratorTool(),
        ]
        
        # Add web search if Tavily API key is available
        tavily_key = os.getenv("TAVILY_API_KEY")
        if tavily_key:
            try:
                web_search_tool = MCPTool(
                    name="web_search",
                    description="Search the web for trading strategies, quant research, and cryptocurrency information",
                    mcp_config={
                        "command": "npx",
                        "args": ["--yes", "tavily-mcp"],
                        "env": {"TAVILY_API_KEY": tavily_key},
                        "timeout": 30,
                        "retry_attempts": 2
                    }
                )
                custom_tools.append(web_search_tool)
                logger.info("Web search tool enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize web search tool: {e}")
        else:
            logger.info("TAVILY_API_KEY not set - web search disabled")
        
        # Initialize tool manager
        self.available_tools = ToolManager(custom_tools)
        logger.info(f"Initialized {len(custom_tools)} tools")
    
    async def generate_strategy_code(
        self,
        strategy_name: str,
        requirements: Dict[str, Any],
        conversation_history: Optional[list] = None
    ) -> str:
        """
        Generate strategy code given requirements.
        
        Args:
            strategy_name: Name for the strategy class
            requirements: Dict with symbol, timeframe, entry_conditions, exit_conditions
            conversation_history: Optional list of previous messages for context
        
        Returns:
            Generated strategy code as string
        """
        # Build prompt from requirements
        prompt = f"""Generate a Lean QuantConnect trading strategy with these requirements:

Strategy Name: {strategy_name}
Symbol: {requirements.get('symbol', 'BTCUSDT')}
Timeframe: {requirements.get('timeframe', '1h')}
Entry Conditions: {requirements.get('entry_conditions', 'Buy when conditions are met')}
Exit Conditions: {requirements.get('exit_conditions', 'Sell when conditions are met')}
Risk Management: {requirements.get('risk_management', 'Standard position sizing')}

Generate complete, runnable Lean QuantConnect Python code following best practices.
Use the generate_lean_strategy tool with these requirements."""
        
        logger.info("🤖 Quant agent generating strategy: %s", strategy_name)
        
        # Run agent to generate code (SpoonReactMCP.run only takes the prompt)
        try:
            response = await self.run(prompt)
            
            # Extract code from response
            # The strategy generator tool returns the code directly
            # If wrapped in markdown, extract it
            if "```python" in response:
                code_start = response.find("```python") + 9
                code_end = response.find("```", code_start)
                code = response[code_start:code_end].strip()
            elif "```" in response:
                code_start = response.find("```") + 3
                code_end = response.find("```", code_start)
                code = response[code_start:code_end].strip()
            else:
                # Assume entire response is code if it contains "from AlgorithmImports"
                if "from AlgorithmImports" in response:
                    code = response
                else:
                    # Last resort: hope it's in there somewhere
                    code = response
            
            return code
            
        except Exception as e:
            logger.error("❌ Failed to generate strategy code: %s", str(e)[:100])
            # Fallback to direct tool call if agent fails
            generator = StrategyGeneratorTool()
            code = await generator.execute(
                strategy_name=strategy_name,
                requirements=requirements
            )
            return code
    
    async def fix_strategy_code(
        self,
        original_code: str,
        errors: list,
        conversation_history: Optional[list] = None
    ) -> str:
        """
        Fix strategy code based on compilation/runtime errors.
        
        Args:
            original_code: The code that failed
            errors: List of error messages
            conversation_history: Optional conversation history
        
        Returns:
            Fixed strategy code
        """
        error_text = "\n".join(errors)
        
        prompt = f"""The following Lean QuantConnect strategy failed to compile/run:

```python
{original_code}
```

Errors:
{error_text}

Please fix the code to resolve these errors. Use the documentation and indicator reference tools if needed.
Return complete, corrected code."""
        
        logger.info("🔧 Quant agent fixing code (%d error(s))", len(errors) if isinstance(errors, list) else 1)
        
        try:
            response = await self.run(prompt)
            
            # Extract fixed code
            if "```python" in response:
                code_start = response.find("```python") + 9
                code_end = response.find("```", code_start)
                code = response[code_start:code_end].strip()
            elif "```" in response:
                code_start = response.find("```") + 3
                code_end = response.find("```", code_start)
                code = response[code_start:code_end].strip()
            else:
                if "from AlgorithmImports" in response:
                    code = response
                else:
                    code = original_code  # Return original if can't extract
            
            return code
            
        except Exception as e:
            logger.error("❌ Failed to fix strategy code: %s", str(e)[:100])
            return original_code  # Return original on error


# Create singleton instance for use in graph nodes
_quant_agent_instance: Optional[QuantStrategyAgent] = None


def get_quant_agent() -> QuantStrategyAgent:
    """Get or create the singleton quant agent instance."""
    global _quant_agent_instance
    
    if _quant_agent_instance is None:
        logger.info("Creating QuantStrategyAgent instance")
        _quant_agent_instance = QuantStrategyAgent()
    
    return _quant_agent_instance
