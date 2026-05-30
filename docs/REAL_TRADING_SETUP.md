# 🤖 Trading Bot - Real MT5 Trading Setup Guide

## ⚠️ CRITICAL: Enable AutoTrading in MT5 FIRST!

**Without this step, the bot CANNOT place any orders on your MT5 account.**

### Step 1: Enable AutoTrading (REQUIRED)

1. **Open your MetaTrader5 Terminal**
2. Go to **Tools → Options**
3. Click on the **"Expert Advisors"** tab (or **"Automated Trading"**)
4. ✅ **Enable "Allow automated trading"** checkbox
5. ✅ **Enable "Allow trading"** checkbox
6. ✅ **Enable "Allow imports"** checkbox
7. Click **OK**
8. **Restart MT5 Terminal completely** (close and reopen)

### Step 2: Verify Your MT5 Account

1. Open your MT5 Terminal
2. Check the **Account** tab to see:
   - Account ID (login number)
   - Account Balance
   - Account Type (Demo or Real)
3. Note these credentials - you'll need them

### Step 3: Configure Bot Credentials

Edit the file: `mt5_config.py`

```python
MT5_LOGIN = "YOUR_ACCOUNT_ID"        # e.g., 123456789
MT5_PASSWORD = "YOUR_PASSWORD"        # Your MT5 password
MT5_SERVER = "YOUR_SERVER_NAME"       # e.g., "MetaQuotes-Demo" or broker name
MT5_PATH = None                        # Leave as None unless MT5 is in custom location
TRADING_SYMBOL = "EURUSD"             # Symbol to trade
DEFAULT_VOLUME = 0.01                 # Starting lot size
USE_REAL_ACCOUNT = True               # Set to True for REAL trading
```

**Example:**
```python
MT5_LOGIN = "104895062"
MT5_PASSWORD = "mypassword123"
MT5_SERVER = "MetaQuotes-Demo"  # or your broker demo/live server
MT5_PATH = None
TRADING_SYMBOL = "EURUSD"
DEFAULT_VOLUME = 0.01
USE_REAL_ACCOUNT = True
```

### Step 4: Start the Bot

1. **Open Dashboard:** http://localhost:5000 in your browser

2. **Login to MT5:**
   - Fill in your MT5 credentials:
     - Account ID (login)
     - Password
     - Server name
   - Click "🔓 Login to MT5"
   - You should see: **"Connected to MT5 account XXXXX"**

3. **Start the Bot:**
   - Click the **"▶ Start Bot"** button
   - Watch for trading signals in the logs

4. **Monitor Real Trades:**
   - Open your MT5 Terminal
   - Go to **"Positions"** tab
   - You should see NEW positions opening as the bot trades
   - Check **"Trade History"** to see closed positions

## 🔍 Real Trading Verification

Once started, you should see:

### In Flask Server Logs:
```
📊 Using REAL MT5 account balance: $102253.00
✅ MT5 ORDER PLACED: BUY 0.01 EURUSD @ 1.1005 | Ticket: 123456789
✅ MT5 POSITION CLOSED: Ticket 123456789 | Volume: 0.01
```

### In MT5 Terminal:
- **"Positions"** tab will show LIVE BUY/SELL positions
- **"Trade History"** will show closed trades with profit/loss
- **"Account"** balance will update with realized P&L

### In Dashboard:
- **"💰 MT5 Account"** card shows:
  - Balance: $102,253.00
  - Equity: $102,500.00 (balance + unrealized profit)
  - Profit: +$247.00 (green if positive, red if negative)
- **"📊 Summary"** card shows:
  - Total Trades completed
  - Open Positions count
  - Average Confidence %
  - Total P&L
  - Win Rate %
- **"⚡ Live Status"** shows:
  - Bot running: YES ✅
  - Active positions: N positions
  - Closed trades: N trades

## ⚠️ Critical Configuration Tips

### For DEMO Trading (Recommended First):
- Use server: **"MetaQuotes-Demo"**
- Set `USE_REAL_ACCOUNT = False`
- You'll trade on demo money (no real loss)

### For REAL Trading:
- Use your broker's **LIVE server** name
- Set `USE_REAL_ACCOUNT = True`
- ⚠️ **You WILL lose real money if strategy fails** ⚠️
- Start with SMALL lot sizes (0.01)
- Monitor closely first 24 hours

### Risk Settings (Conservative):
- **MIN_CONFIDENCE**: 60% (minimum AI confidence for trade)
- **RISK_PERCENT**: 2.0% (risk 2% of account per trade)
- **STOP_LOSS_PTS**: 50 points
- **TAKE_PROFIT_PTS**: 100 points (2:1 reward/risk)
- **LOT_MIN**: 0.01 (minimum lot size)
- **LOT_MAX**: 100.0 (maximum lot size)

## 🐛 Troubleshooting

### Problem: "❌ AUTOTRADING IS DISABLED"
- Follow Step 1 above
- Make sure MT5 is fully restarted after enabling
- Check that "Allow automated trading" checkbox is CHECKED

### Problem: "MT5 not connected - cannot place order"
- Verify credentials in mt5_config.py are correct
- Make sure MT5 Terminal is open and logged in
- Check server name matches exactly

### Problem: "Order failed: Code 10000+"
- 10007 = Broker is offline/connection lost
- 10014 = Invalid symbol name
- 10016 = Insufficient funds
- 10020 = Account is disabled
- 10027 = AutoTrading disabled ← **Follow Step 1**

### Problem: No orders placed, bot runs but shows "📊 SIMULATION ORDER"
- This means bot is NOT connected to MT5
- Check login status in dashboard
- Verify MT5 Terminal is actually open

## 📊 Real-Time Monitoring

### Dashboard Updates Every 2 Seconds:
- Account balance and profit
- Open positions with Entry price, SL, TP
- Recent 10 trades with P&L
- Bot status (running/stopped)
- Average AI confidence

### MT5 Terminal Real-Time:
- New orders appear immediately
- Position profit/loss updates tick-by-tick
- Trade history populated as positions close

## 🎯 Getting Ready

**Before you start REAL trading, verify:**

1. ✅ AutoTrading is ENABLED in MT5
2. ✅ Dashboard loads at http://localhost:5000
3. ✅ MT5 login succeeds (green status indicator)
4. ✅ You can see "💰 MT5 Account" card with real balance
5. ✅ Bot starts without errors
6. ✅ You see "✅ MT5 ORDER PLACED" in logs (not simulation orders)
7. ✅ Positions appear in MT5 Terminal
8. ✅ You understand the risk settings and are comfortable with them

## ⚡ Quick Start (Real Trading)

```bash
# 1. Configure credentials
# Edit mt5_config.py with your account details

# 2. Start the bot
python dashboard.py

# 3. Open dashboard
# http://localhost:5000

# 4. Login to MT5
# Click login button, enter credentials

# 5. Start bot
# Click "▶ Start Bot"

# 6. Monitor in MT5 Terminal
# Watch "Positions" tab for live trades
```

## 📈 Expected Behavior

**After clicking "Start Bot":**

1. Bot analyzes last 100 price bars (fast process)
2. Bot checks SMA crossover signals
3. Bot validates with AI confidence scoring
4. Bot places REAL orders on MT5 if confidence ≥ 60%
5. Bot closes positions when Take Profit or Stop Loss hit
6. All positions show in MT5 Terminal in real-time
7. Profit displays in Dashboard and MT5

## 🚀 You're Ready!

The bot will now:
- ✅ Trade REAL money on your MT5 account
- ✅ Place and close orders automatically
- ✅ Track profit/loss in real-time
- ✅ Save all trades for analysis
- ✅ Display everything on the dashboard

**Good luck! Start small, monitor closely.** 🎯
