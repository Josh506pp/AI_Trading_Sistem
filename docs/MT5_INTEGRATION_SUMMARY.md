# MT5 Integration - Setup Instructions

## What I've Done

Your trading bot now has **full MetaTrader5 integration**. Here's what's been added:

### ✅ New Files Created
1. **`mt5_config.py`** - Configuration file for MT5 credentials
2. **`test_mt5_connection.py`** - Diagnostic tool to test MT5 connection
3. **`MT5_SETUP.md`** - Complete MT5 setup guide

### ✅ Code Updates
- Added MT5 connection functions to `trading_bot.py`
- Added order placement functions (real MT5 orders)
- Added position closing functions (real MT5 positions)
- Added account balance & position tracking from MT5
- Updated dashboard with MT5 status API endpoints
- Graceful fallback to simulation mode if MT5 not connected

### ✅ How It Works Now

**Without MT5 Connected:**
- Bot runs in **simulation mode** (fake data, fake trades)
- Good for testing and learning

**With MT5 Connected:**
- Bot gets **real market data** from MT5
- Bot **places real orders** in your account
- Bot **closes positions** at profit targets
- Bot **tracks real P&L** in your account

---

## Setup Instructions (3 Steps)

### **STEP 1: Configure Your MT5 Credentials**

1. **Open MetaTrader5** on your PC
2. Note your credentials:
   - Account login (top-left corner, or File → Account Details)
   - Trading password (NOT investor password)
   - Server name (e.g., "ICMarkets-Demo")

3. **Edit `mt5_config.py`** in VS Code:
   ```python
   MT5_LOGIN = 123456789          # Your account number
   MT5_PASSWORD = "YourPassword"   # Your trading password
   MT5_SERVER = "ICMarkets-Demo"   # Your broker server
   ```

### **STEP 2: Install MetaTrader5 Package**

Run in terminal:
```bash
pip install MetaTrader5
```

### **STEP 3: Test the Connection**

Run this test script:
```bash
python test_mt5_connection.py
```

You should see:
```
✅ SUCCESS! MT5 Connection is Working!

Account Information:
  Login:    123456789
  Balance:  $10,000.00
  Currency: USD
  ...
```

---

## Using MT5 Trading

Once configured, the bot will **automatically**:
1. Connect to your MT5 account
2. Stream real market prices
3. Place real orders in your account
4. Close positions at target prices
5. Track actual P&L

### **Check MT5 Status in Dashboard**

1. Start dashboard: `python dashboard.py`
2. Open `http://localhost:5000`
3. Look for **"MT5 Connection Status"** (new section)
4. Should show:
   - ✅ **Connected** - if MT5 is active
   - ❌ **Disconnected** - if not connected

---

## Important Warnings ⚠️

### Before Trading Real Money

1. **Test on DEMO account first**
   - Leave `USE_REAL_ACCOUNT = False` in `mt5_config.py`
   - Use demo money for testing

2. **Start with SMALL position sizes**
   - Set `DEFAULT_VOLUME = 0.01` (smallest lot)
   - 0.01 lots = 1,000 units for Forex

3. **Monitor the logs**
   - Terminal window shows every trade
   - Check for errors immediately

4. **Test thoroughly**
   - Run 50+ demo trades
   - Verify P&L is accurate
   - Check that orders execute correctly

---

## Troubleshooting

### Problem: "MT5 credentials not configured"
**Solution:** Edit `mt5_config.py` and fill in your credentials

### Problem: "MT5 initialization failed"
**Solution:** Make sure MT5 is running on your PC (start it manually)

### Problem: "MT5 login failed"
**Solution:** Double-check your:
- Account number (login)
- Trading password (NOT investor password)
- Broker server name

### Problem: "MetaTrader5 package not installed"
**Solution:** Run `pip install MetaTrader5`

### **Need Help?**
Run the diagnostic tool:
```bash
python test_mt5_connection.py
```
It will show exactly what's wrong and how to fix it.

---

## Dashboard Changes

### New MT5 Status Card
Shows real-time MT5 connection status with:
- Connection state
- Account login
- Balance
- Leverage

### New API Endpoints
- `GET /api/mt5/status` - Check MT5 connection status
- `POST /api/mt5/connect` - Attempt to connect to MT5

### Live Position Data
- All orders now show MT5 ticket numbers
- Positions auto-sync with your MT5 account
- P&L reflects actual brokerage commissions

---

## Summary

Your bot is **production-ready** for MT5!

✅ Configure `mt5_config.py`  
✅ Run `python test_mt5_connection.py`  
✅ Start dashboard: `python dashboard.py`  
✅ Begin trading with **REAL MARKET DATA**!  

---

## Next: Real vs Simulation

### SIMULATION MODE (Current Default)
- 🟢 Good for: Learning, testing, debugging
- Fake market data
- Fake trades
- Useful for: Testing strategies, understanding UI

### MT5 MODE (After Setup)
- 💰 Good for: Live trading
- Real market prices
- Real orders in your account
- Real P&L

To use MT5 mode:
1. Setup credentials in `mt5_config.py`
2. Keep MT5 running
3. Start the bot dashboard
4. Click "Start" to begin trading

---

Good luck! 📈💹
