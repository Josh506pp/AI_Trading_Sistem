#!/usr/bin/env python3
"""
MetaTrader5 Configuration File
Configure your MT5 account credentials here to enable live trading
"""

# =============================================================================
# MT5 ACCOUNT CREDENTIALS - EDIT THESE VALUES
# =============================================================================

# Your MT5 account login (account number)
# Example: 123456789
MT5_LOGIN = None

# Your MT5 account password
# Example: "password123"
MT5_PASSWORD = None

# Your MT5 broker server
# Example: "ICMarkets-Demo" or check your account details in MT5
MT5_SERVER = None

# Path to MT5 terminal (optional - leave None to auto-detect)
# Example: r"C:\Program Files\MetaTrader 5\terminal64.exe"
# On Windows, usually auto-detected. On Mac/Linux, might need explicit path
MT5_PATH = None


# =============================================================================
# INSTRUCTIONS TO SET UP MT5 CONNECTION
# =============================================================================
"""
STEP 1: Get your MT5 credentials
   1. Open MetaTrader 5
   2. Click "File" → "Account Details" or check at top-left corner
   3. Note your:
      - Login number (account number)
      - Password (trading password, NOT investor password)
      - Server name (e.g., "ICMarkets-Demo", "HotForex-Demo", etc.)

STEP 2: Edit this file
   1. Replace MT5_LOGIN with your account number (as integer, no quotes)
   2. Replace MT5_PASSWORD with your password (as string, in quotes)
   3. Replace MT5_SERVER with your broker server (as string, in quotes)
   
   Example:
   MT5_LOGIN = 123456789
   MT5_PASSWORD = "MyPassword123"
   MT5_SERVER = "ICMarkets-Demo"

STEP 3: Save this file

STEP 4: Install MetaTrader5 Python package
   In terminal run:
   pip install MetaTrader5

STEP 5: Start the bot
   python dashboard.py
   
   When you start the bot, it will try to connect to MT5.
   Check the logs to see if connection is successful.

STEP 6: Check MT5 Connection Status
   - Open the dashboard at http://localhost:5000
   - Look for "MT5 Status" showing "Connected" or "Disconnected"
   - If disconnected, check the terminal logs for error messages

TROUBLESHOOTING:
   - "MT5 initialization failed": MT5 terminal not running or not installed
     Fix: Make sure MT5 is installed and running
   
   - "MT5 login failed": Wrong credentials
     Fix: Double-check your login, password, and server name
   
   - "No module named 'MetaTrader5'": Package not installed
     Fix: Run: pip install MetaTrader5
   
   - Orders not placed: Check if account has sufficient balance
     Fix: Check your MT5 account balance and margin
"""

# =============================================================================
# ADVANCED SETTINGS (Optional)
# =============================================================================

# Symbol to trade (default: EURUSD)
TRADING_SYMBOL = "EURUSD"

# Position size (volume/lot) - start small!
# 0.01 = 1,000 units of base currency (smallest typical lot)
# Test thoroughly before increasing
DEFAULT_VOLUME = 0.01

# Risk percentage per trade
RISK_PERCENT = 2.0

# Whether to use real money (True) or demo account (False)
# WARNING: Only set to True if you're confident in the bot!
USE_REAL_ACCOUNT = False

# Timeframe for analysis (in minutes)
# 1 = M1 (1-minute), 5 = M5, 15 = M15, 60 = H1, etc.
TIMEFRAME_MINUTES = 1

# Number of candles to analyze
CANDLE_COUNT = 100
