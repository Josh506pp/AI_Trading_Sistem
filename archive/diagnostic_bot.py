#!/usr/bin/env python3
"""Diagnostic script to test bot with real MT5 data"""

import sys
import logging
from trading_bot import run_simulation, open_positions, trade_history, MT5_AVAILABLE
from mt5_manager import mt5_manager
import threading

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

print("\n" + "="*70)
print("TRADING BOT DIAGNOSTIC - TESTING WITH REAL MT5 DATA")
print("="*70)

# Check connection
print("\n[1] Checking MT5 Connection...")
is_connected = mt5_manager.check_connection()
print(f"    Connected: {is_connected}")
if not is_connected:
    print("    ERROR: Cannot connect to MT5!")
    sys.exit(1)

# Check MT5 available
print(f"\n[2] MT5 Available: {MT5_AVAILABLE}")

# Test signal generation with real data
print("\n[3] Running bot with REAL MT5 data...")
print("    (Watch for: BUY SIGNAL or SELL SIGNAL messages)")
print("    (Watch for: Order placed messages)")

stop_event = threading.Event()

# Run one cycle
run_simulation(account_balance=10000.0, stop_event=stop_event)

# Check results
print("\n[4] Results:")
print(f"    Open positions: {len(open_positions)}")
print(f"    Closed trades: {len(trade_history)}")

if trade_history:
    print(f"\n    Last trade:")
    t = trade_history[-1]
    print(f"      Side: {t.side}")
    print(f"      Volume: {t.volume}")
    print(f"      Entry: {t.entry_price:.5f}")
    print(f"      Exit: {t.exit_price:.5f}")
    print(f"      P&L: {t.pnl:.4f}")
else:
    print("    ⚠️  No trades generated")

print("\n" + "="*70 + "\n")
