#!/usr/bin/env python3
"""
MT5 Connection Test Script
Run this to verify your MT5 setup is working correctly
"""

import sys

print("=" * 70)
print("MetaTrader5 Connection Diagnostic Test")
print("=" * 70)

# Step 1: Check if config exists and is set
print("\n[1/4] Checking mt5_config.py...")
try:
    from mt5_config import MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, MT5_PATH
    print("✓ mt5_config.py found")
    
    print(f"  - Login:    {'✓ Set' if MT5_LOGIN else '✗ NOT SET'}")
    print(f"  - Password: {'✓ Set' if MT5_PASSWORD else '✗ NOT SET'}")
    print(f"  - Server:   {'✓ Set' if MT5_SERVER else '✗ NOT SET'}")
    print(f"  - Path:     {MT5_PATH if MT5_PATH else '(auto-detect)'}")
    
    if not all([MT5_LOGIN, MT5_PASSWORD, MT5_SERVER]):
        print("\n❌ ERROR: Missing credentials!")
        print("   Please edit mt5_config.py and set MT5_LOGIN, MT5_PASSWORD, and MT5_SERVER")
        sys.exit(1)
except ImportError as e:
    print(f"❌ ERROR: Could not load mt5_config.py: {e}")
    sys.exit(1)

# Step 2: Check if MetaTrader5 package is installed
print("\n[2/4] Checking MetaTrader5 package...")
try:
    import MetaTrader5 as mt5
    print("✓ MetaTrader5 package is installed")
except ImportError:
    print("❌ ERROR: MetaTrader5 package not installed!")
    print("   Install it with: pip install MetaTrader5")
    sys.exit(1)

# Step 3: Try to initialize MT5
print("\n[3/4] Initializing MT5 connection...")
try:
    if MT5_PATH:
        init_result = mt5.initialize(path=MT5_PATH)
        print(f"  Using custom path: {MT5_PATH}")
    else:
        init_result = mt5.initialize()
        print("  Using auto-detected MT5 path")
    
    if not init_result:
        error = mt5.last_error()
        print(f"❌ ERROR: MT5 initialization failed!")
        print(f"   Error code: {error}")
        print("   Possible causes:")
        print("     - MetaTrader5 is not installed on your PC")
        print("     - MetaTrader5 is not running")
        print("     - Run MT5 as administrator and try again")
        sys.exit(1)
    
    print("✓ MT5 initialization successful")
except Exception as e:
    print(f"❌ ERROR: {e}")
    sys.exit(1)

# Step 4: Try to login
print("\n[4/4] Attempting login...")
try:
    login_result = mt5.login(
        login=int(MT5_LOGIN),
        password=MT5_PASSWORD,
        server=MT5_SERVER
    )
    
    if not login_result:
        error = mt5.last_error()
        print(f"❌ ERROR: MT5 login failed!")
        print(f"   Error code: {error}")
        print("   Possible causes:")
        print(f"     - Wrong login: {MT5_LOGIN}")
        print(f"     - Wrong password (use trading password, not investor password)")
        print(f"     - Wrong server: {MT5_SERVER}")
        print("   Double-check your credentials:")
        print("     1. Open MT5 on your PC")
        print("     2. Look at top-left corner for account number")
        print("     3. Check File → Account Details for server name")
        mt5.shutdown()
        sys.exit(1)
    
    print("✓ MT5 login successful!")
except Exception as e:
    print(f"❌ ERROR: {e}")
    mt5.shutdown()
    sys.exit(1)

# Success! Get account info
print("\n" + "=" * 70)
print("✅ SUCCESS! MT5 Connection is Working!")
print("=" * 70)

account = mt5.account_info()
if account:
    print(f"\nAccount Information:")
    print(f"  Login:    {account.login}")
    print(f"  Balance:  ${account.balance:,.2f}")
    print(f"  Currency: {account.currency}")
    print(f"  Leverage: {account.leverage}:1")
    print(f"  Equity:   ${account.equity:,.2f}")
    print(f"  Margin:   ${account.margin:,.2f}")

# Test data retrieval
print(f"\nTesting data retrieval for {MT5_SERVER}...")
try:
    symbol_info = mt5.symbol_info("EURUSD")
    if symbol_info:
        print(f"✓ EURUSD data available")
        print(f"  Bid: {symbol_info.bid}")
        print(f"  Ask: {symbol_info.ask}")
    else:
        print(f"⚠ EURUSD data not available (symbol may not be tradeable on this account)")
except Exception as e:
    print(f"⚠ Error checking EURUSD: {e}")

# Cleanup
mt5.shutdown()

print("\n" + "=" * 70)
print("Next steps:")
print("  1. Start the dashboard: python dashboard.py")
print("  2. Open http://localhost:5000 in your browser")
print("  3. Click 'Start' to begin trading with live MT5 data")
print("=" * 70)
