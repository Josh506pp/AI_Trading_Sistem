#!/usr/bin/env python3
"""Quick import test - doesn't create system instance"""
import sys
try:
    # Just test that the module parses correctly
    import ast
    with open('professional_trading_system.py', 'r', encoding='utf-8') as f:
        source = f.read()
    ast.parse(source)
    print("✓ Syntax is valid")
except SyntaxError as e:
    print(f"✗ Syntax error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
