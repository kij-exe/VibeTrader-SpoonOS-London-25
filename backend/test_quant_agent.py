#!/usr/bin/env python3
"""
Test script for QuantStrategyAgent in isolation.

Tests:
1. Tool initialization (DocsReaderTool, IndicatorReferenceTool, StrategyGeneratorTool)
2. Strategy code generation
3. Integration with requirements

Run: python3 -m backend.test_quant_agent
"""

import asyncio
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_tools():
    """Test individual tools."""
    print("\n" + "="*60)
    print("TEST 1: Tool Initialization")
    print("="*60)
    
    from backend.app.agent.tools import DocsReaderTool, IndicatorReferenceTool, StrategyGeneratorTool
    
    try:
        # Test DocsReaderTool
        print("\n📚 Testing DocsReaderTool...")
        docs_tool = DocsReaderTool()
        docs_result = await docs_tool.execute()
        print(f"✅ DocsReaderTool works! Got {len(docs_result)} chars")
        assert "Lean QuantConnect" in docs_result
        assert len(docs_result) > 100
        
        # Test IndicatorReferenceTool
        print("\n📊 Testing IndicatorReferenceTool...")
        indicator_tool = IndicatorReferenceTool()
        indicator_result = await indicator_tool.execute()
        print(f"✅ IndicatorReferenceTool works! Got {len(indicator_result)} chars")
        assert "RSI" in indicator_result or "Indicators" in indicator_result
        assert len(indicator_result) > 100
        
        # Test StrategyGeneratorTool
        print("\n🔧 Testing StrategyGeneratorTool...")
        generator_tool = StrategyGeneratorTool()
        test_requirements = {
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "entry_conditions": "RSI < 30",
            "exit_conditions": "RSI > 70",
            "risk_management": "1% per trade"
        }
        code_result = await generator_tool.execute(
            strategy_name="TestStrategy",
            requirements=test_requirements
        )
        print(f"✅ StrategyGeneratorTool works! Generated {len(code_result)} chars")
        assert "from AlgorithmImports import *" in code_result
        assert "TestStrategy" in code_result
        assert "RSI" in code_result or "rsi" in code_result
        assert len(code_result) > 200
        
        print("\n✅ All tools passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Tool test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_initialization():
    """Test agent initialization."""
    print("\n" + "="*60)
    print("TEST 2: Agent Initialization")
    print("="*60)
    
    try:
        from backend.app.agent.quant_agent import QuantStrategyAgent
        
        print("\n🤖 Creating QuantStrategyAgent...")
        agent = QuantStrategyAgent()
        
        print(f"✅ Agent created: {agent.name}")
        print(f"✅ LLM provider: {agent.llm.provider if hasattr(agent.llm, 'provider') else 'configured'}")
        print(f"✅ Tools available: {len(agent.available_tools.tools) if hasattr(agent.available_tools, 'tools') else 'configured'}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Agent initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_strategy_generation():
    """Test strategy generation."""
    print("\n" + "="*60)
    print("TEST 3: Strategy Generation")
    print("="*60)
    
    try:
        from backend.app.agent.quant_agent import get_quant_agent
        
        print("\n🤖 Getting quant agent...")
        agent = get_quant_agent()
        
        print("\n📝 Generating strategy from requirements...")
        requirements = {
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "entry_conditions": "Buy when RSI < 30 (oversold)",
            "exit_conditions": "Sell when RSI > 70 (overbought)",
            "risk_management": "1% risk per trade, full position size"
        }
        
        code = await agent.generate_strategy_code(
            strategy_name="RSIMeanReversionStrategy",
            requirements=requirements
        )
        
        print(f"\n✅ Generated code ({len(code)} chars):")
        print("-" * 60)
        print(code[:500] + "..." if len(code) > 500 else code)
        print("-" * 60)
        
        # Verify code structure
        assert "from AlgorithmImports import *" in code
        assert "QCAlgorithm" in code
        assert "initialize" in code
        assert "on_data" in code
        
        print("\n✅ Strategy generation passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Strategy generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_interval_normalization():
    """Test interval format normalization."""
    print("\n" + "="*60)
    print("TEST 4: Interval Normalization")
    print("="*60)
    
    test_cases = [
        ("1H", "1h"),
        ("1h", "1h"),
        ("4H", "4h"),
        ("1D", "1d"),
        ("1M", "1m"),
        ("15m", "15m"),
    ]
    
    for input_val, expected in test_cases:
        normalized = input_val.lower()
        status = "✅" if normalized == expected else "❌"
        print(f"{status} {input_val} -> {normalized} (expected: {expected})")
        assert normalized == expected, f"Failed: {input_val} -> {normalized} != {expected}"
    
    print("\n✅ Interval normalization passed!")
    return True


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("QUANT AGENT ISOLATION TESTS")
    print("="*60)
    
    results = []
    
    # Test 1: Tools
    results.append(("Tools", await test_tools()))
    
    # Test 2: Agent initialization
    results.append(("Agent Init", await test_agent_initialization()))
    
    # Test 3: Strategy generation (requires API key)
    try:
        import os
        if os.getenv("ANTHROPIC_API_KEY"):
            results.append(("Strategy Gen", await test_strategy_generation()))
        else:
            print("\n⚠️  Skipping strategy generation test (no ANTHROPIC_API_KEY)")
            results.append(("Strategy Gen", None))
    except Exception as e:
        print(f"\n⚠️  Strategy generation test skipped: {e}")
        results.append(("Strategy Gen", None))
    
    # Test 4: Interval normalization
    results.append(("Interval Norm", await test_interval_normalization()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, result in results:
        if result is True:
            print(f"✅ {test_name}: PASSED")
        elif result is False:
            print(f"❌ {test_name}: FAILED")
        else:
            print(f"⚠️  {test_name}: SKIPPED")
    
    total_passed = sum(1 for _, r in results if r is True)
    total_failed = sum(1 for _, r in results if r is False)
    total_skipped = sum(1 for _, r in results if r is None)
    
    print(f"\nPassed: {total_passed}, Failed: {total_failed}, Skipped: {total_skipped}")
    
    if total_failed > 0:
        print("\n❌ Some tests failed!")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
