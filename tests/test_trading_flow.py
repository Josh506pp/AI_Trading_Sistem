#!/usr/bin/env python3
"""
Test script to diagnose MT5 trading flow
"""

import sys
import logging
from mt5_manager import mt5_manager

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

print("\n" + "="*70)
print("MT5 TRADING FLOW DIAGNOSTIC TEST")
print("="*70)

# Test 1: Check MT5 connection
print("\n[TEST 1] Checking MT5 Connection...")
is_connected = mt5_manager.check_connection()
print(f"  MT5 Connected: {is_connected}")
if is_connected:
    acct = mt5_manager._account_info
    if acct:
        print(f"  Account ID: {acct.login}")
        print(f"  Balance: ${acct.balance}")
        print(f"  Server: {acct.server}")
else:
    print("  ✗ MT5 NOT CONNECTED - Orders cannot be placed!")
    sys.exit(1)

# Test 2: Check trading_bot state
print("\n[TEST 2] Checking trading_bot state...")
try:
    from trading_bot import MT5_AVAILABLE, mt5, SYMBOL, open_positions, trade_history
    print(f"  MT5_AVAILABLE: {MT5_AVAILABLE}")
    print(f"  SYMBOL: {SYMBOL}")
    print(f"  Open Positions: {len(open_positions)}")
    print(f"  Trade History: {len(trade_history)}")
except Exception as e:
    print(f"  ✗ Error importing trading_bot: {e}")
    sys.exit(1)

# Test 3: Try to place a test order
print("\n[TEST 3] Testing order placement flow...")
try:
    from trading_bot import place_mt5_order, submit_order
    
    print("  Attempting to place test BUY order...")
    logger.info("STARTING TEST ORDER PLACEMENT")
    
    # Try place_mt5_order directly
    result = place_mt5_order("EURUSD", "BUY", 0.01, 1.1000, 1.0950, 1.1050)
    
    if result is not None:
        print(f"  ✓ Order placed successfully!")
        print(f"  Order ticket: {result.order if hasattr(result, 'order') else 'N/A'}")
        print(f"  Return code: {result.retcode if hasattr(result, 'retcode') else 'N/A'}")
    else:
        print("  ✗ Order placement returned None")
        
except Exception as e:
    print(f"  ✗ Error during order placement: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Check recent trades
print("\n[TEST 4] Checking trade history...")
try:
    from trading_bot import trade_history, open_positions
    print(f"  Closed trades: {len(trade_history)}")
    print(f"  Open positions: {len(open_positions)}")
    if trade_history:
        print(f"  Last trade: {trade_history[-1]}")
    if open_positions:
        print(f"  Last position: {open_positions[-1]}")
except Exception as e:
    print(f"  ✗ Error checking trades: {e}")

print("\n" + "="*70)
print("DIAGNOSTIC COMPLETE")
print("="*70 + "\n")
