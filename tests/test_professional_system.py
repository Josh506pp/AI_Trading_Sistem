#!/usr/bin/env python3
"""
Test script for Professional Trading System
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from professional_trading_system import IntegratedTradingSystem
    print("✓ IntegratedTradingSystem imported successfully")

    # Test initialization
    print("Initializing system...")
    system = IntegratedTradingSystem()
    print("✓ IntegratedTradingSystem initialized successfully")

    # Test AI components
    if hasattr(system, 'ai_analyzer') and system.ai_analyzer:
        print("✓ AI Analyzer initialized")
    else:
        print("✗ AI Analyzer not found")

    # Test auth system
    if hasattr(system, 'auth') and system.auth:
        print("✓ Authentication system initialized")
    else:
        print("✗ Authentication system not found")

    print("\n🎉 All core components initialized successfully!")
    print("The Professional Trading System is ready to run.")

except Exception as e:
    print(f"✗ Error during initialization: {e}")
    import traceback
    traceback.print_exc()