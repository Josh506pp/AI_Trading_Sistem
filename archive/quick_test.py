#!/usr/bin/env python3
"""Quick test to identify the price data issue"""
import MetaTrader5 as mt5

mt5.initialize()

print("\n=== YOUR MT5 DATA STATUS ===")
print(f"Account: {mt5.account_info().login}")

# Try each timeframe and report if it returns data
frame_tests = [
    ("M1", mt5.TIMEFRAME_M1),
    ("H1", mt5.TIMEFRAME_H1),
    ("D1", mt5.TIMEFRAME_D1),
]

print("\nCandle data by timeframe:")
for name, frame in frame_tests:
    rates = mt5.copy_rates_from("EURUSD", frame, 0, 10)
    print(f"  {name}: {'✓ Got data' if rates and len(rates) > 0 else '✗ None/Empty'}")

# Check if current ticks work
print("\nCurrent tick data:")
tick = mt5.symbol_info_tick("EURUSD")
print(f"  EURUSD bid/ask: {tick.bid:.5f} / {tick.ask:.5f}" if tick else "  ✗ No tick data")

# Check copy_rates_range with time range
print("\nAlternative methods:")
from datetime import datetime, timedelta
start = datetime.now() - timedelta(hours=2)
range_rates = mt5.copy_rates_range("EURUSD", mt5.TIMEFRAME_M1, start, datetime.now())
print(f"  copy_rates_range: {'✓ Got data' if range_rates and len(range_rates) > 0 else '✗ None/Empty'}")

ticks = mt5.copy_ticks_from("EURUSD", 0, 5)
print(f"  copy_ticks_from: {'✓ Got data' if ticks and len(ticks) > 0 else '✗ None/Empty'}")

mt5.shutdown()
print("\n⚠️  FIX: If all above show ✗, you need to:")
print("   1. Open MT5 terminal")
print("   2. Right-click EURUSD in Market Watch")
print("   3. Click 'Show' or 'Subscribe' to load data")
print("   4. Wait 10 seconds for data to load")
print("   5. Restart the bot")
