#!/usr/bin/env python3
"""Test strategy name and symbol sanitization."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.app.agent.tools.strategy_generator import StrategyGeneratorTool


async def test_sanitization():
    """Test that generated code has valid Python syntax."""
    
    print("\n" + "="*60)
    print("TESTING SYMBOL & CLASS NAME SANITIZATION")
    print("="*60)
    
    generator = StrategyGeneratorTool()
    
    # Test case 1: Symbol with slash (BTC/USDC)
    print("\n📝 Test 1: BTC/USDC (with slash)")
    requirements = {
        "symbol": "BTC/USDC",
        "timeframe": "1H",
        "entry_conditions": "RSI < 30",
        "exit_conditions": "RSI > 70",
        "risk_management": "1% per trade"
    }
    
    code = await generator.execute(
        strategy_name="BTC/USDCStrategy",  # Also has slash
        requirements=requirements
    )
    
    # Check for invalid syntax
    has_slash_in_class = "class BTC/USDC" in code or "class BTC/" in code
    has_slash_in_symbol = 'add_crypto("BTC/USDC"' in code or 'add_crypto("BTC/' in code
    
    if has_slash_in_class:
        print("❌ FAIL: Class name still has slash!")
        print(f"   Found: {[line for line in code.split('\\n') if 'class ' in line]}")
    else:
        print("✅ PASS: Class name is clean (no slashes)")
        class_line = [line for line in code.split('\n') if 'class ' in line][0]
        print(f"   {class_line.strip()}")
    
    if has_slash_in_symbol:
        print("❌ FAIL: Symbol still has slash in add_crypto()!")
        print(f"   Found: {[line for line in code.split('\\n') if 'add_crypto' in line]}")
    else:
        print("✅ PASS: Symbol is clean in add_crypto()")
        symbol_line = [line for line in code.split('\n') if 'add_crypto' in line][0]
        print(f"   {symbol_line.strip()}")
    
    # Try to compile the code
    print("\n🔍 Testing Python syntax validation...")
    try:
        compile(code, '<string>', 'exec')
        print("✅ PASS: Code compiles without syntax errors!")
    except SyntaxError as e:
        print(f"❌ FAIL: Syntax error - {e}")
        print(f"   Line {e.lineno}: {e.text}")
        return False
    
    # Test case 2: Clean symbol (BTCUSDT)
    print("\n📝 Test 2: BTCUSDT (already clean)")
    requirements2 = {
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "entry_conditions": "RSI < 30",
        "exit_conditions": "RSI > 70"
    }
    
    code2 = await generator.execute(
        strategy_name="BTCUSDTStrategy",
        requirements=requirements2
    )
    
    try:
        compile(code2, '<string>', 'exec')
        print("✅ PASS: Clean symbol code also compiles!")
    except SyntaxError as e:
        print(f"❌ FAIL: Syntax error - {e}")
        return False
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED!")
    print("="*60)
    return True


if __name__ == "__main__":
    result = asyncio.run(test_sanitization())
    sys.exit(0 if result else 1)
