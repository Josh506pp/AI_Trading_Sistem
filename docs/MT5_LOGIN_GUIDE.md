# MT5 Account Login - How to Use

## New Feature: Web-Based MT5 Login

You can now login to your MT5 account directly from the dashboard without editing config files!

---

## Step 1: Start the Dashboard

Run:
```bash
python dashboard.py
```

Then open: `http://localhost:5000`

---

## Step 2: See the Login Form

When you open the dashboard, you'll see a **login modal** with three fields:

```
🔐 MT5 Account Login

Account Login (Number): [____________]
Password:              [____________]
MT5 Server:           [____________]

        [🔓 Connect to MT5]
```

---

## Step 3: Get Your MT5 Credentials

Open **MetaTrader5** on your PC and find:

1. **Account Login (Number)**
   - Look at the **top-left corner** of MT5
   - Or go to: **File → Account Details**
   - Copy the account number (e.g., 123456789)

2. **Password**
   - Your **trading password** (NOT investor password)
   - You set this when you created the account

3. **MT5 Server**
   - In Account Details, you'll see your broker server
   - Examples: "ICMarkets-Demo", "HotForex-Demo", "Pepperstone-Demo"
   - Copy the exact server name

---

## Step 4: Enter Your Credentials

Paste your information into the login form:

```
Account Login:  123456789
Password:       MyPassword123
MT5 Server:     ICMarkets-Demo
```

---

## Step 5: Click "Connect to MT5"

The bot will:
1. ✓ Try to connect to your MT5 account
2. ✓ Validate your credentials
3. ✓ Store your login session
4. ✓ Show `✓ Connected to MT5 Account 123456789` message

If successful, the login modal closes and you can start trading!

---

## How to Logout

Click the **"🔓 Logout MT5"** button in the control panel.

Next time you open the dashboard, the login form appears again.

---

## Troubleshooting

### "Connection failed"
- Make sure **MetaTrader5 is running** on your PC
- Check credentials are **exactly correct** (case-sensitive)
- Verify your broker server name

### "Wrong password"
- Use your **trading password**, NOT investor password
- Copy from MT5 exactly (spaces, capital letters matter)

### "Account number wrong"
- Check the number in MT5 top-left corner
- Make sure it's the right account if you have multiple

---

## How It Works

Once logged in:

1. **Real Data**: Bot gets live prices from your MT5 account
2. **Real Orders**: Bot places actual orders in your account
3. **Real P&L**: Your profit/loss is tracked in MT5
4. **Dashboard**: Shows your current positions and trades

---

## Security Note

Your credentials are **stored in memory only** while the bot is running.
They are **NOT saved** to disk or config files.
When you close the bot, you need to login again next time.

---

## Quick Test

After logging in, you can test by:

1. Click **"▶ Start"** to begin trading
2. Watch the **"📊 Summary"** card update with trades
3. Check your MT5 terminal - you should see **real orders** appearing!
4. Click **"⏹ Stop"** to stop trading
5. Verify orders are **closed** in MT5

---

## Next: Start Trading!

✅ Login with your credentials  
✅ Click Start  
✅ Monitor live trades  
✅ Check MT5 for real order activity  
✅ Watch P&L update in real-time  

Good luck! 📈💰
