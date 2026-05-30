# MT5 Integration Setup Guide

## Quick Start (3 Steps)

### Step 1: Get Your MT5 Credentials
1. **Open MetaTrader 5** on your PC
2. Look at the **top-left corner** - you'll see your account number
3. Go to **File → Account Details** to see your complete credentials:
   - **Login**: Your account number (e.g., 123456789)
   - **Password**: Your trading password (NOT the investor password)
   - **Server**: Your broker server name (e.g., "ICMarkets-Demo", "HotForex-Demo")

### Step 2: Configure Your Credentials
1. Open `mt5_config.py` in VS Code
2. Fill in your credentials:
   ```python
   MT5_LOGIN = 123456789          # Your account number
   MT5_PASSWORD = "YourPassword"   # Your trading password
   MT5_SERVER = "ICMarkets-Demo"   # Your broker server
   ```
3. Save the file

### Step 3: Install MetaTrader5 Python Package
Open terminal and run:
```bash
pip install MetaTrader5
```

---

## Verify the Connection Works

### Option A: Test via Dashboard
1. Start the bot: `python dashboard.py`
2. Open browser: `http://localhost:5000`
3. Look for **"MT5 Status"** section
4. You should see:
   - ✓ **Connected** (green) - if MT5 is connected
   - ✗ **Disconnected** (red) - if connection failed

### Option B: Test via Command Line
Run this in a terminal:
```bash
python -c "
from trading_bot import initialize_mt5, test_mt5_connection
from mt5_config import MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, MT5_PATH

# Try to connect
success = initialize_mt5(MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, MT5_PATH)
print('Connection:', 'SUCCESS ✓' if success else 'FAILED ✗')

# Show diagnostics
diag = test_mt5_connection()
print('Connected:', diag['mt5_connected'])
print('Has Credentials:', diag['mt5_has_credentials'])
if diag['error_message']:
    print('Error:', diag['error_message'])
"
```

---

## Troubleshooting

### Problem: "MetaTrader5 package not installed"
**Solution:**
```bash
pip install MetaTrader5
```

### Problem: "MT5 initialization failed"
**Causes & Solutions:**
- ❌ **MetaTrader5 is not running**: Start MT5 on your PC
- ❌ **MT5 not installed**: Install MetaTrader5 (free from your broker)
- ❌ **Wrong path**: If on Windows, leave `MT5_PATH = None` (auto-detects)

### Problem: "MT5 login failed"
**Causes & Solutions:**
- ❌ **Wrong login**: Double-check your account number in MT5
- ❌ **Wrong password**: Use your **trading password**, NOT investor password
- ❌ **Wrong server**: Copy exact server name from MT5 (e.g., "ICMarkets-Demo")
- ❌ **Account locked**: Log in to MT5 web terminal to check account status

### Problem: "MT5 credentials not configured"
**Solution:**
Edit `mt5_config.py` and fill in:
```python
MT5_LOGIN = your_account_number
MT5_PASSWORD = "your_password"
MT5_SERVER = "your_server"
```

### Problem: "Orders not executing in MT5"
**Causes & Solutions:**
- ❌ **Insufficient balance**: Check your account balance in MT5
- ❌ **Margin requirement**: Your balance must cover margin for position size
- ❌ **Market closed**: Some symbols/times not tradeable
- ❌ **Permission issue**: Check account restrictions in MT5

---

## How It Works

Once connected, the bot will:

1. **Get Live Data** from MT5 (actual market prices)
2. **Analyze with AI** (moving averages, RSI, confidence scoring)
3. **Place Real Orders** in your MT5 account automatically
4. **Close Positions** when profit targets or stop losses hit
5. **Track P&L** in real account

### Important Safeguards

- Start with **demo account** (`USE_REAL_ACCOUNT = False` in mt5_config.py)
- Use **small position size** (`DEFAULT_VOLUME = 0.01`)
- **Monitor logs** - check terminal output for errors
- **Test thoroughly** before using real money

---

## Advanced Configuration

Edit `mt5_config.py` for more options:

```python
# Symbol to trade (default: EURUSD)
TRADING_SYMBOL = "EURUSD"

# Position size (lot) - start small!
DEFAULT_VOLUME = 0.01  # 0.01 = 1,000 units

# Risk percentage per trade
RISK_PERCENT = 2.0

# Use real account? (False = Demo, True = Real Money)
USE_REAL_ACCOUNT = False

# Timeframe for analysis (minutes)
TIMEFRAME_MINUTES = 1

# Number of candles to analyze
CANDLE_COUNT = 100
```

---

## Dashboard MT5 Features

Once connected, the dashboard shows:

### **MT5 Connection Status Card**
- Connection status (Connected/Disconnected)
- Account login number
- Current account balance
- Leverage
- Currency

### **Real Trades in MT5**
- All orders placed show MT5 ticket numbers
- Positions auto-close at TP/SL on MT5
- P&L calculated from actual MT5 exit prices
- Dashboard shows live MT5 position data

---

## Still Having Issues?

1. **Check the terminal logs** - detailed error messages are shown
2. **Verify MT5 is running** as an administrator
3. **Try the diagnostic test** above
4. **Check broker support** - confirm credentials with your broker
5. **Restart both** MT5 and the Python bot

---

## Demo vs Real Account

### Demo Account (Recommended for testing)
- Use paper money for practice
- No real money at risk
- Same API connection
- Good for debugging

### Real Account (Use after testing)
1. Test thoroughly on demo first
2. In `mt5_config.py` set: `USE_REAL_ACCOUNT = True`
3. Start with **very small position sizes**
4. Monitor everything closely
5. Consider using risk controls (max loss per day, etc.)

---

## Next Steps

✅ Configure `mt5_config.py` with your credentials  
✅ Install MetaTrader5 package: `pip install MetaTrader5`  
✅ Start dashboard: `python dashboard.py`  
✅ Check MT5 Status in browser  
✅ If connected, start trading!  

Good luck! 📈💰
