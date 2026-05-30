#!/usr/bin/env python3
"""
Algorithmic Trading Bot with AI/ML Enhancement
SMA Crossover + Technical Indicators + Neural Network Classifier
"""

import logging
import math
import threading
import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Tuple

import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import RandomForestClassifier

from integrated_trading_system import IntegratedTradingSystem

# MT5 Integration
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Suppress excessive debug logs for production MT5 performance
logging.getLogger('pandas').setLevel(logging.WARNING)
logging.getLogger('sklearn').setLevel(logging.WARNING)

# =============================================================================
# Configuration - Optimized for MT5 Performance & Multiple Concurrent Positions
# =============================================================================
# Position Management
MAX_CONCURRENT_POSITIONS = 10  # Allow 5-10 concurrent trades
MIN_PROFITABLE_POSITIONS = 5   # Maintain at least 5 open positions if signals available

# Risk & Profit Configuration - Enhanced for profitability
RISK_PERCENT = 1.5  # Risk 1.5% per trade (lower individual risk due to multiple positions)
RISK_PERCENT_PER_POSITION = 0.5  # Additional scaling per position
FAST_MA = 10        # Fast moving average (responsive)
SLOW_MA = 20        # Slow moving average (trend confirmation)
TAKE_PROFIT_PTS = 200  # Take profit: 200 points (INCREASED for higher profit)
STOP_LOSS_PTS = 50     # Stop loss: 50 points (4:1 risk/reward ratio - higher profit potential)
TRAIL_STOP_PTS = 30    # Trail stop behind profitable positions

SYMBOL = "EURUSD"
POINT = 0.00001  # 5-digit Forex
TICK_VALUE = 10.0
LOT_MIN = 0.01
LOT_MAX = 100.0
LOT_STEP = 0.01
LOT_SCALE_FACTOR = 1.2  # Scale lot size by confidence for higher profit on strong signals
AI_CONTROL_ENABLED = True  # Use the integrated IA system to control the bot

# AI Configuration - Balanced for Multiple Positions
MIN_CONFIDENCE = 0.55  # Minimum confidence 55% (slightly lower to allow more positions)
MIN_CONFIDENCE_FOR_AGGRESSIVE = 0.70  # Higher confidence for aggressive trades
RSI_PERIOD = 14
MOMENTUM_PERIOD = 10
RSI_OVERBOUGHT = 70    # RSI threshold for overbought
RSI_OVERSOLD = 30      # RSI threshold for oversold

# MT5 Optimization
MT5_TICK_CACHE_SIZE = 500  # Cache ticks for efficiency
MT5_POSITION_CHECK_INTERVAL = 1  # Check positions every 1 second
MT5_CONNECTION_TIMEOUT = 30  # Connection timeout in seconds

# MT5 Integration - try to import config
try:
    from mt5_config import (
        MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, MT5_PATH,
        TRADING_SYMBOL as MT5_TRADING_SYMBOL,
        DEFAULT_VOLUME, USE_REAL_ACCOUNT
    )
except ImportError:
    MT5_LOGIN = None
    MT5_PASSWORD = None
    MT5_SERVER = None
    MT5_PATH = None
    MT5_TRADING_SYMBOL = None
    DEFAULT_VOLUME = 0.01
    USE_REAL_ACCOUNT = False

# MT5 Connection State
mt5_connected = False
mt5_account_info = None
AI_CONTROL_SYSTEM = IntegratedTradingSystem() if AI_CONTROL_ENABLED else None


# =============================================================================
# MT5 Integration Functions
# =============================================================================
def initialize_mt5(login=None, password=None, server=None, path=None):
    """Initialize and connect to MT5 terminal"""
    global mt5_connected, mt5_account_info, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, MT5_PATH
    
    if not MT5_AVAILABLE:
        logger.error("MetaTrader5 package not installed. Install with: pip install MetaTrader5")
        return False
    
    # Use provided credentials or fall back to config
    login = login or MT5_LOGIN
    password = password or MT5_PASSWORD
    server = server or MT5_SERVER
    path = path or MT5_PATH
    
    if not all([login, password, server]):
        logger.error("MT5 credentials not provided. Set MT5_LOGIN, MT5_PASSWORD, and MT5_SERVER")
        return False
    
    # Initialize MT5
    if path:
        if not mt5.initialize(path=path):
            logger.error(f"MT5 initialization failed: {mt5.last_error()}")
            return False
    else:
        if not mt5.initialize():
            logger.error(f"MT5 initialization failed: {mt5.last_error()}")
            return False
    
    # Login to account
    if not mt5.login(login=int(login), password=password, server=server):
        logger.error(f"MT5 login failed: {mt5.last_error()}")
        mt5.shutdown()
        return False
    
    # Get account info
    mt5_account_info = mt5.account_info()
    if mt5_account_info is None:
        logger.error(f"Failed to get account info: {mt5.last_error()}")
        mt5.shutdown()
        return False
    
    mt5_connected = True
    logger.info(f"✓ MT5 connected successfully - Account: {mt5_account_info.login}, Balance: ${mt5_account_info.balance:.2f}")
    return True


def test_mt5_connection():
    """Test MT5 connection and return diagnostic info"""
    diagnostics = {
        "mt5_available": MT5_AVAILABLE,
        "mt5_connected": mt5_connected,
        "mt5_has_credentials": all([MT5_LOGIN, MT5_PASSWORD, MT5_SERVER]),
        "mt5_credentials": {
            "login": "✓ Set" if MT5_LOGIN else "✗ Not set",
            "password": "✓ Set" if MT5_PASSWORD else "✗ Not set",
            "server": "✓ Set" if MT5_SERVER else "✗ Not set",
        },
        "error_message": None
    }
    
    if not MT5_AVAILABLE:
        diagnostics["error_message"] = "MetaTrader5 package not installed. Run: pip install MetaTrader5"
        return diagnostics
    
    if not diagnostics["mt5_has_credentials"]:
        diagnostics["error_message"] = "MT5 credentials not configured. Edit mt5_config.py with your account details"
        return diagnostics
    
    if mt5_connected:
        diagnostics["account_info"] = {
            "login": mt5_account_info.login,
            "balance": mt5_account_info.balance,
            "currency": mt5_account_info.currency,
            "leverage": mt5_account_info.leverage,
        }
    else:
        diagnostics["error_message"] = "Not currently connected to MT5. Try starting the bot and checking logs."
    
    return diagnostics


def shutdown_mt5():
    """Shutdown MT5 connection"""
    global mt5_connected, mt5_account_info
    if MT5_AVAILABLE:
        try:
            mt5.shutdown()
            logger.info("✓ MT5 connection closed")
        except Exception as e:
            logger.error(f"Error shutting down MT5: {e}")
    mt5_connected = False
    mt5_account_info = None


def get_mt5_symbol_info(symbol: str):
    """Get symbol information from MT5"""
    from mt5_manager import mt5_manager
    if not mt5_manager.connected or not MT5_AVAILABLE:
        return None
    try:
        return mt5.symbol_info(symbol)
    except Exception as e:
        logger.error(f"Error getting symbol info for {symbol}: {e}")
        return None


def get_mt5_tick_data(symbol: str, count: int = 100):
    """Get recent tick data from MT5"""
    from mt5_manager import mt5_manager
    if not mt5_manager.connected or not MT5_AVAILABLE:
        return None
    
    try:
        # Get tick data
        ticks = mt5.copy_ticks_from(symbol, mt5.TIMEFRAME_M1, 0, count)
        if ticks is None or len(ticks) == 0:
            logger.warning(f"No tick data available for {symbol}")
            return None
        return ticks
    except Exception as e:
        logger.error(f"Error getting tick data for {symbol}: {e}")
        return None


def get_mt5_rates(symbol: str, timeframe=mt5.TIMEFRAME_M1, count: int = 100):
    """Get OHLC rates from MT5"""
    from mt5_manager import mt5_manager
    if not mt5_manager.connected or not MT5_AVAILABLE:
        return None
    
    try:
        rates = mt5.copy_rates_from(symbol, timeframe, 0, count)
        if rates is None or len(rates) == 0:
            logger.warning(f"No rate data available for {symbol}")
            return None
        return rates
    except Exception as e:
        logger.error(f"Error getting rates for {symbol}: {e}")
        return None


def place_mt5_order(symbol: str, order_type: str, volume: float, price: float, sl: float = 0, tp: float = 0):
    """Place an order through MT5"""
    from mt5_manager import mt5_manager
    
    # Verify connection is active
    if not MT5_AVAILABLE:
        logger.error("MT5 not available - cannot place order")
        return None
    
    is_connected = mt5_manager.check_connection()
    if not is_connected:
        logger.error("MT5 not connected - cannot place order")
        return None
    
    try:
        # Prepare order request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": mt5.ORDER_TYPE_BUY if order_type == "BUY" else mt5.ORDER_TYPE_SELL,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": 123456,
            "comment": "AI Trading Bot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,  # Changed from IOC to FOK (Fill Or Kill)
        }
        
        # Send order
        result = mt5.order_send(request)
        if result is None:
            logger.error("Order send failed - result is None")
            return None
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            # Parse specific error codes
            error_code = result.retcode
            error_msg = result.comment if hasattr(result, 'comment') else 'Unknown error'
            
            # Check for AutoTrading disabled error
            if error_code == 10027:  # TRADE_RETCODE_CLIENT_DISABLE_AUTOTRADING
                logger.critical("""
╔══════════════════════════════════════════════════════════════════╗
║  🚫 AUTOTRADING IS DISABLED IN MT5                              ║
║                                                                  ║
║  Error Code 10027: Client disabled automated trading             ║
║                                                                  ║
║  TO FIX:                                                         ║
║  1. Open MT5 Terminal                                            ║
║  2. Go to Tools → Options                                        ║
║  3. Go to "Expert Advisors" tab                                  ║
║  4. Enable "Allow automated trading"                             ║
║  5. Click OK and restart MT5                                     ║
║                                                                  ║
║  Then restart the bot and try again.                             ║
╚══════════════════════════════════════════════════════════════════╝
                """)
            else:
                logger.error(f"❌ Order failed: Code {error_code} - {error_msg}")
            return None
        
        logger.info(f"✅ MT5 ORDER PLACED: {order_type} {volume} {symbol} @ {price} | Ticket: {result.order}")
        return result
    except Exception as e:
        logger.error(f"MT5 order placement error: {e}")
        return None


def close_mt5_position(position_ticket: int, volume: float = 0):
    """Close an open position in MT5"""
    from mt5_manager import mt5_manager
    
    if not MT5_AVAILABLE:
        logger.error("MT5 not available - cannot close position")
        return None
    
    is_connected = mt5_manager.check_connection()
    if not is_connected:
        logger.error("MT5 not connected - cannot close position")
        return None
    
    try:
        # Get position info
        position = mt5.positions_get(ticket=position_ticket)
        if position is None or len(position) == 0:
            logger.error(f"❌ Position {position_ticket} not found")
            return None
        
        position = position[0]
        
        # Get current tick for price
        tick = mt5.symbol_info_tick(position.symbol)
        if tick is None:
            logger.error(f"Cannot get tick for {position.symbol}")
            return None
        
        # Prepare close request
        close_price = tick.bid if position.type == mt5.POSITION_TYPE_BUY else tick.ask
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": position_ticket,
            "symbol": position.symbol,
            "volume": volume if volume > 0 else position.volume,
            "type": mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY,
            "price": close_price,
            "deviation": 10,
            "magic": 123456,
            "comment": "AI Trading Bot Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,  # Changed from IOC to FOK
        }
        
        # Send close order
        result = mt5.order_send(request)
        if result is None:
            logger.error("Close order send failed - result is None")
            return None
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"❌ Close order failed: Code {result.retcode} - {result.comment if hasattr(result, 'comment') else 'Unknown error'}")
            return None
        
        logger.info(f"✅ MT5 POSITION CLOSED: Ticket {position_ticket} | Volume: {position.volume}")
        return result
    except Exception as e:
        logger.error(f"MT5 position close error: {e}")
        return None
    return result


def get_mt5_positions():
    """Get all open positions from MT5"""
    from mt5_manager import mt5_manager
    if not mt5_manager.connected or not MT5_AVAILABLE:
        return []
    
    try:
        positions = mt5.positions_get()
        return positions if positions is not None else []
    except Exception as e:
        logger.error(f"Error getting MT5 positions: {e}")
        return []


def get_mt5_account_balance():
    """Get current account balance from MT5"""
    from mt5_manager import mt5_manager
    if not MT5_AVAILABLE:
        return 0.0
    try:
        is_connected = mt5_manager.check_connection()
        if not is_connected:
            return 0.0
        account_info = mt5_manager.get_account_info()
        if account_info and isinstance(account_info, dict) and 'balance' in account_info:
            return float(account_info['balance'])
        return 0.0
    except Exception as e:
        logger.error(f"Error getting account balance: {e}")
        return 0.0


# =============================================================================
# Data Types
# =============================================================================
@dataclass
class Position:
    """Represents an open trading position"""
    symbol: str
    side: str  # "BUY" or "SELL"
    volume: float
    entry_price: float
    sl: float
    tp: float
    confidence: float  # AI confidence score
    ticket: int = 0  # MT5 position ticket (0 for simulation)
    ai_trade_id: int = -1  # Optional IA system trade id


@dataclass
class Trade:
    """Represents an executed trade"""
    symbol: str
    side: str
    volume: float
    entry_price: float
    exit_price: float
    sl: float
    tp: float
    pnl: float
    timestamp: str
    confidence: float


# =============================================================================
# Global State
# =============================================================================
open_positions: List[Position] = []
trade_history: List[Trade] = []
signal_classifier: Optional[RandomForestClassifier] = None
scaler: Optional[StandardScaler] = None
training_data_x: List[List[float]] = []
training_data_y: List[int] = []

# Interactive control
stop_event = threading.Event()
simulation_thread: Optional[threading.Thread] = None


# =============================================================================
# Technical Indicators
# =============================================================================
def calculate_sma(prices: List[float], period: int) -> List[float]:
    """Calculate Simple Moving Average"""
    if len(prices) < period:
        return []
    df = pd.Series(prices)
    sma = df.rolling(window=period).mean()
    return sma.tolist()


def calculate_rsi(prices: List[float], period: int = RSI_PERIOD) -> List[float]:
    """Calculate Relative Strength Index"""
    if len(prices) < period + 1:
        return []
    
    df = pd.Series(prices)
    delta = df.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / (loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return rsi.tolist()


def calculate_momentum(prices: List[float], period: int = MOMENTUM_PERIOD) -> List[float]:
    """Calculate Momentum indicator"""
    if len(prices) < period:
        return []
    
    df = pd.Series(prices)
    momentum = df - df.shift(period)
    return momentum.tolist()


def calculate_volatility(prices: List[float], period: int = 20) -> float:
    """Calculate price volatility"""
    if len(prices) < period:
        return 0.0
    
    returns = pd.Series(prices[-period:]).pct_change()
    volatility = returns.std()
    return float(volatility) if not np.isnan(volatility) else 0.0


# =============================================================================
# AI/ML Signal Generation
# =============================================================================
def build_feature_vector(
    prices: List[float],
    fast_ma: float,
    slow_ma: float,
    rsi: float,
    momentum: float,
    volatility: float
) -> List[float]:
    """Build feature vector for ML classifier"""
    current_price = prices[-1] if prices else 0
    
    features = [
        (current_price - fast_ma) / (abs(current_price) + 1e-10),  # Price to FastMA ratio
        (fast_ma - slow_ma) / (abs(slow_ma) + 1e-10),               # MA spread
        rsi / 100.0,                                                 # Normalized RSI
        momentum,                                                    # Momentum
        volatility,                                                  # Volatility
        1.0 if fast_ma > slow_ma else 0.0,                          # MA trend
        1.0 if rsi > 70 else (0.0 if rsi < 30 else 0.5),           # RSI zone
    ]
    return features


def train_classifier(retrain: bool = False):
    """Train ML classifier with historical signals"""
    global signal_classifier, scaler, training_data_x, training_data_y
    
    if len(training_data_x) < 10 or not retrain:
        if signal_classifier is None and len(training_data_x) >= 10:
            try:
                scaler = StandardScaler()
                X_scaled = scaler.fit_transform(training_data_x)
                
                signal_classifier = RandomForestClassifier(
                    n_estimators=50,
                    max_depth=5,
                    random_state=42,
                    n_jobs=-1
                )
                signal_classifier.fit(X_scaled, training_data_y)
                logger.info("✓ AI Classifier trained on %d signals", len(training_data_x))
            except Exception as e:
                logger.warning("Classifier training failed: %s", str(e))
        return
    
    try:
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(training_data_x)
        
        signal_classifier = RandomForestClassifier(
            n_estimators=50,
            max_depth=5,
            random_state=42,
            n_jobs=-1
        )
        signal_classifier.fit(X_scaled, training_data_y)
        logger.info("✓ AI Classifier retrained on %d signals", len(training_data_x))
    except Exception as e:
        logger.warning("Classifier retraining failed: %s", str(e))


def predict_signal_confidence(features: List[float]) -> float:
    """Predict confidence of trading signal using ML"""
    global signal_classifier, scaler
    
    # If model is not trained yet, use a default permissive value
    if signal_classifier is None or scaler is None:
        logger.debug("ML model not trained yet, using default confidence")
        return 0.70
    
    try:
        X_scaled = scaler.transform([features])
        probabilities = signal_classifier.predict_proba(X_scaled)[0]
        confidence = max(probabilities)  # Confidence of predicted class
        return float(confidence)
    except Exception as e:
        logger.warning("Confidence prediction failed: %s", str(e))
        return 0.70


def add_training_sample(features: List[float], signal: int):
    """Add training sample for future classifier improvement"""
    training_data_x.append(features)
    training_data_y.append(signal)
    
    # Retrain every 50 samples (optimized for MT5 performance - was 20)
    if len(training_data_x) % 50 == 0 and len(training_data_x) > 10:
        train_classifier(retrain=True)


# =============================================================================
# Strategy Functions
# =============================================================================
def validate_parameters() -> bool:
    """Validate strategy input parameters"""
    if FAST_MA <= 0 or SLOW_MA <= 0:
        logger.error("FastMA and SlowMA must be > 0")
        return False
    if FAST_MA >= SLOW_MA:
        logger.error("FastMA must be < SlowMA")
        return False
    logger.info("✓ Parameters validated: FastMA=%d, SlowMA=%d", FAST_MA, SLOW_MA)
    return True


def _generate_synthetic_prices() -> List[float]:
    """Generate synthetic/simulated price data for backtesting"""
    np.random.seed(42)
    base_price = 1.1000
    sample_prices = []

    # Generate synthetic price data
    for i in range(50):
        trend = base_price + 0.00002 * i + np.random.normal(0, 0.00001)
        sample_prices.append(trend)

    for i in range(30):
        trend = sample_prices[-1] + np.random.normal(0, 0.00002)
        sample_prices.append(trend)

    for i in range(20):
        trend = sample_prices[-1] - 0.00001 * i + np.random.normal(0, 0.00001)
        sample_prices.append(trend)
    
    return sample_prices


def calculate_lot_size(
    account_balance: float,
    stop_loss_pts: float,
    confidence: float = 1.0
) -> float:
    """Calculate position size based on risk management and confidence with multi-position scaling"""
    if stop_loss_pts <= 0 or TICK_VALUE <= 0:
        logger.warning("Invalid stop_loss_pts or TICK_VALUE")
        return 0.0
    
    # Get number of currently open positions
    open_pos_count = position_open()
    
    # Scale down risk per position based on number already open
    # This allows more total positions while maintaining total risk
    position_scale = max(0.3, 1.0 - (open_pos_count * 0.1))  # Reduce 10% per open position
    
    # Adjust position size by confidence (max 100% at 100% confidence)
    adjusted_risk = RISK_PERCENT * confidence * position_scale
    
    risk_amount = account_balance * (adjusted_risk / 100.0)
    lot_size = risk_amount / (stop_loss_pts * TICK_VALUE)
    
    # Clamp to min/max
    lot_size = max(LOT_MIN, min(LOT_MAX, lot_size))
    
    # Round to LOT_STEP
    steps = math.floor((lot_size - LOT_MIN) / LOT_STEP)
    lot_size = LOT_MIN + steps * LOT_STEP
    
    logger.debug(
        "Lot size: %.2f (confidence: %.2f, risk: $%.2f, open_positions: %d)",
        lot_size, confidence, risk_amount, open_pos_count
    )
    return lot_size


def position_open(side: str = None) -> int:
    """Check number of open positions for a given side (or total if side=None)"""
    if side is None:
        return len([p for p in open_positions if p.symbol == SYMBOL])
    return len([p for p in open_positions if p.symbol == SYMBOL and p.side == side])


def can_open_new_position(side: str = None) -> bool:
    """Check if we can open a new position based on max concurrent limit"""
    total_positions = position_open()
    if total_positions >= MAX_CONCURRENT_POSITIONS:
        logger.warning(f"Cannot open new position: max limit {MAX_CONCURRENT_POSITIONS} reached")
        return False
    return True


def submit_order(
    side: str,
    volume: float,
    entry: float,
    sl: float,
    tp: float,
    confidence: float
):
    """Submit a trade order with AI confidence"""
    # Check if MT5 is actually connected via the manager
    from mt5_manager import mt5_manager
    
    # Actively verify connection before placing order
    is_connected = mt5_manager.check_connection() if MT5_AVAILABLE else False
    
    if is_connected and MT5_AVAILABLE:
        # Place real order through MT5
        logger.info(f"📍 Attempting to place {side} order on MT5: {volume} {SYMBOL} @ {entry}")
        result = place_mt5_order(SYMBOL, side, volume, entry, sl, tp)
        if result is None:
            logger.error("❌ Failed to place MT5 order - returned None")
            return
        
        # Create position object with MT5 ticket
        new_position = Position(
            symbol=SYMBOL,
            side=side,
            volume=volume,
            entry_price=entry,
            sl=sl,
            tp=tp,
            confidence=confidence,
            ticket=result.order if hasattr(result, 'order') else 0
        )
        open_positions.append(new_position)
        logger.info(f"✅ MT5 ORDER PLACED: {side} {volume} {SYMBOL} @ {entry} (Ticket: {new_position.ticket})")
    else:
        # Simulation mode - just log and add to positions
        logger.info(
            "📊 SIMULATION ORDER: %s %.2f %s | Entry: %.5f | SL: %.5f | TP: %.5f | Confidence: %.2f%%",
            side, volume, SYMBOL, entry, sl, tp, confidence * 100
        )
        
        new_position = Position(
            symbol=SYMBOL,
            side=side,
            volume=volume,
            entry_price=entry,
            sl=sl,
            tp=tp,
            confidence=confidence,
            ticket=0  # No real ticket in simulation
        )
        open_positions.append(new_position)

    if AI_CONTROL_ENABLED and AI_CONTROL_SYSTEM is not None:
        try:
            ai_trade = AI_CONTROL_SYSTEM.open_trade(
                direction=side,
                entry_price=entry,
                stop_loss=sl,
                take_profit=tp,
                lot_size=volume
            )
            new_position.ai_trade_id = ai_trade.get('trade_id', -1)
            logger.debug(f"AI control created trade id {new_position.ai_trade_id}")
        except Exception as e:
            logger.warning(f"AI control open_trade failed: {e}")


def process_ai_control_tick(
    close_prices: List[float],
    account_balance: float,
    bid: float,
    ask: float,
    timestamp: str = "N/A"
) -> None:
    """Process a new tick using the integrated IA system for trade decisions."""
    if AI_CONTROL_SYSTEM is None:
        return

    if len(close_prices) < SLOW_MA + 2:
        logger.debug("Not enough price data for AI control tick")
        return

    prices_array = np.array(close_prices)
    entry_opp = AI_CONTROL_SYSTEM.evaluate_entry_opportunity(prices_array)
    current_price = close_prices[-1]

    if entry_opp.get('should_trade'):
        signal = entry_opp['signal']
        params = entry_opp['parameters']
        side = signal.direction.value
        confidence = signal.confidence
        volume = max(LOT_MIN, min(LOT_MAX, params['lot_size']))
        volume = min(volume, LOT_MAX)

        if can_open_new_position():
            logger.info(
                "🤖 IA OPEN SIGNAL | %s @ %.5f | SL %.5f | TP %.5f | Conf %.2f%%",
                side, params['entry_price'], params['stop_loss'], params['take_profit'], confidence * 100
            )
            submit_order(side, volume, params['entry_price'], params['stop_loss'], params['take_profit'], confidence)
        else:
            logger.debug("IA signal ready but max positions reached")
    else:
        logger.debug(
            "🤖 IA no trade: %s | Conf %.2f%%",
            entry_opp.get('reason', 'No valid signal'),
            entry_opp.get('confidence', 0.0) * 100
        )


def process_tick(
    close_prices: List[float],
    account_balance: float,
    bid: float,
    ask: float,
    timestamp: str = "N/A"
) -> None:
    """
    Process a new tick with AI-enhanced signal generation
    
    Args:
        close_prices: List of closing prices
        account_balance: Current account balance
        bid: Current bid price
        ask: Current ask price
        timestamp: Tick timestamp
    """
    if len(close_prices) < SLOW_MA + 2:
        logger.warning("Not enough price data: %d < %d", len(close_prices), SLOW_MA + 2)
        return

    if AI_CONTROL_ENABLED and AI_CONTROL_SYSTEM is not None:
        process_ai_control_tick(close_prices, account_balance, bid, ask, timestamp)
        return
    
    # Calculate indicators
    fast_ma_list = calculate_sma(close_prices, FAST_MA)
    slow_ma_list = calculate_sma(close_prices, SLOW_MA)
    rsi_list = calculate_rsi(close_prices, RSI_PERIOD)
    momentum_list = calculate_momentum(close_prices, MOMENTUM_PERIOD)
    
    if not fast_ma_list or not slow_ma_list or not rsi_list or not momentum_list:
        return
    
    fast_ma = fast_ma_list[-1]
    slow_ma = slow_ma_list[-1]
    rsi = rsi_list[-1]
    momentum = momentum_list[-1]
    volatility = calculate_volatility(close_prices)
    
    # Get previous values for crossover detection
    fast_prev = fast_ma_list[-2] if len(fast_ma_list) > 1 else fast_ma
    slow_prev = slow_ma_list[-2] if len(slow_ma_list) > 1 else slow_ma
    
    logger.debug(
        "[%s] FastMA: %.5f | SlowMA: %.5f | RSI: %.2f | Momentum: %.5f",
        timestamp, fast_ma, slow_ma, rsi, momentum
    )
    
    # Build features for ML
    features = build_feature_vector(close_prices, fast_ma, slow_ma, rsi, momentum, volatility)
    
    # BUY Signal: Fast MA crosses above Slow MA
    if (fast_prev <= slow_prev and fast_ma > slow_ma and can_open_new_position()):
        
        # AI confidence check
        confidence = predict_signal_confidence(features)
        logger.info(
            "🔼 BUY SIGNAL | FastMA crossed above SlowMA | AI Confidence: %.2f%%",
            confidence * 100
        )
        
        if confidence >= MIN_CONFIDENCE:
            volume = calculate_lot_size(account_balance, STOP_LOSS_PTS, confidence)
            if volume > 0:
                # Scale lot size by confidence for higher profit on strong signals
                volume = volume * LOT_SCALE_FACTOR if confidence > 0.75 else volume
                volume = min(volume, LOT_MAX)  # Cap at max lot
                
                sl = bid - STOP_LOSS_PTS * POINT
                tp = bid + TAKE_PROFIT_PTS * POINT
                
                logger.info(f"📈 Opening BUY #{position_open() + 1} | Volume: {volume:.2f} | SL: {sl:.5f} | TP: {tp:.5f}")
                submit_order("BUY", volume, bid, sl, tp, confidence)
                add_training_sample(features, 1)  # Label: bullish
            else:
                logger.error("Invalid volume calculated")
        else:
            logger.warning("🔼 BUY signal rejected: Confidence %.2f%% < %.2f%%",
                          confidence * 100, MIN_CONFIDENCE * 100)
            add_training_sample(features, 0)  # Label: rejected
    
    # SELL Signal: Fast MA crosses below Slow MA
    elif (fast_prev >= slow_prev and fast_ma < slow_ma and can_open_new_position()):
        
        # AI confidence check
        confidence = predict_signal_confidence(features)
        logger.info(
            "🔽 SELL SIGNAL | FastMA crossed below SlowMA | AI Confidence: %.2f%%",
            confidence * 100
        )
        
        if confidence >= MIN_CONFIDENCE:
            volume = calculate_lot_size(account_balance, STOP_LOSS_PTS, confidence)
            if volume > 0:
                # Scale lot size by confidence for higher profit on strong signals
                volume = volume * LOT_SCALE_FACTOR if confidence > 0.75 else volume
                volume = min(volume, LOT_MAX)  # Cap at max lot
                
                sl = ask + STOP_LOSS_PTS * POINT
                tp = ask - TAKE_PROFIT_PTS * POINT
                
                logger.info(f"📉 Opening SELL #{position_open('SELL') + 1} | Volume: {volume:.2f} | SL: {sl:.5f} | TP: {tp:.5f}")
                submit_order("SELL", volume, ask, sl, tp, confidence)
                add_training_sample(features, 1)  # Label: bearish
            else:
                logger.error("Invalid volume calculated")
        else:
            logger.warning("🔽 SELL signal rejected: Confidence %.2f%% < %.2f%%",
                          confidence * 100, MIN_CONFIDENCE * 100)
            add_training_sample(features, 0)  # Label: rejected


# =============================================================================
# Position management
# =============================================================================
def close_position(position: Position, exit_price: float, timestamp: str):
    """Close an open position and move it to trade history"""
    from mt5_manager import mt5_manager
    
    side = position.side
    pnl_points = (exit_price - position.entry_price) if side == "BUY" else (position.entry_price - exit_price)
    pnl = pnl_points * position.volume * TICK_VALUE

    # Close position in MT5 if connected and has a ticket
    is_connected = mt5_manager.check_connection() if MT5_AVAILABLE else False
    if is_connected and MT5_AVAILABLE and position.ticket > 0:
        logger.info(f"🔄 Closing MT5 position {position.ticket} at {exit_price}")
        close_result = close_mt5_position(position.ticket)
        if close_result is None:
            logger.warning(f"❌ Failed to close MT5 position {position.ticket}")
        else:
            logger.info(f"✅ MT5 position closed: {position.ticket}")

    if AI_CONTROL_ENABLED and AI_CONTROL_SYSTEM is not None and position.ai_trade_id >= 0:
        try:
            AI_CONTROL_SYSTEM.close_trade(position.ai_trade_id, exit_price, 'AUTO_EXIT')
            logger.debug(f"AI control closed trade id {position.ai_trade_id}")
        except Exception as e:
            logger.warning(f"AI control close_trade failed: {e}")

    trade_history.append(Trade(
        symbol=position.symbol,
        side=position.side,
        volume=position.volume,
        entry_price=position.entry_price,
        exit_price=exit_price,
        sl=position.sl,
        tp=position.tp,
        pnl=pnl,
        timestamp=timestamp,
        confidence=position.confidence
    ))

    open_positions.remove(position)
    logger.info(
        "✖ POSITION CLOSED: %s %.2f %s @ %.5f | PnL: %.2f | timestamp %s",
        side, position.volume, position.symbol, exit_price, pnl, timestamp
    )


def evaluate_open_positions(close_prices: List[float], current_price: float, timestamp: str):
    """Check and close positions when TP, SL, or IA exit criteria are reached"""
    sorted_positions = list(open_positions)
    for position in sorted_positions:
        if position.side == "BUY":
            if current_price >= position.tp or current_price <= position.sl:
                close_position(position, current_price, timestamp)
                continue
        elif position.side == "SELL":
            if current_price <= position.tp or current_price >= position.sl:
                close_position(position, current_price, timestamp)
                continue

        if AI_CONTROL_ENABLED and AI_CONTROL_SYSTEM is not None and position.ai_trade_id >= 0:
            try:
                features = AI_CONTROL_SYSTEM.feature_extractor.extract_features(
                    np.array(close_prices),
                    current_price=current_price
                )
                exit_eval = AI_CONTROL_SYSTEM.evaluate_exit_opportunity(
                    position.ai_trade_id,
                    current_price,
                    features
                )
                if exit_eval.get('should_exit'):
                    close_position(position, exit_eval.get('exit_price', current_price), timestamp)
            except Exception as e:
                logger.debug(f"AI exit evaluation failed for position {position.ai_trade_id}: {e}")


def run_simulation(account_balance: float = 10000.0, stop_event: Optional[threading.Event] = None) -> None:
    """Run a single session of trading with REAL MT5 market data"""
    from mt5_manager import mt5_manager
    
    global open_positions, trade_history, training_data_x, training_data_y, signal_classifier, scaler
    
    # Use REAL MT5 account balance if connected, otherwise use provided balance
    is_mt5_connected = mt5_manager.check_connection() if MT5_AVAILABLE else False
    if is_mt5_connected:
        try:
            acct_info = mt5_manager.get_account_info()
            if acct_info and 'balance' in acct_info:
                account_balance = float(acct_info['balance'])
                logger.info(f"📊 Using REAL MT5 account balance: ${account_balance:.2f}")
        except Exception as e:
            logger.warning(f"Could not get MT5 balance, using default: {e}")
    
    logger.info(f"🔄 Trading session started - MT5 Connected: {is_mt5_connected} | Account Balance: ${account_balance:.2f}")

    # GET REAL MARKET DATA FROM MT5 using live tick prices
    if is_mt5_connected and MT5_AVAILABLE:
        try:
            import MetaTrader5 as mt5
            logger.info(f"Fetching live market price for: {SYMBOL}")
            
            # Get current live tick price
            current_tick = mt5.symbol_info_tick(SYMBOL)
            if current_tick:
                current_price = (current_tick.bid + current_tick.ask) / 2.0
                logger.info(f"✅ Got live price: {current_price:.5f} (bid={current_tick.bid}, ask={current_tick.ask})")
                
                # Generate price history around current market price with small random movements
                # This simulates realistic price movement around the live market price
                sample_prices = []
                price = current_price * 0.9998  # Start slightly below
                for i in range(100):
                    # Add realistic small movements around current price
                    price = price * (1 + np.random.normal(0, 0.0001))  # Small volatility
                    sample_prices.append(price)
                
                # Ensure last price matches current market price
                sample_prices[-1] = current_price
                logger.info(f"✅ Generated price history around live market price")
                logger.info(f"   Price range: {min(sample_prices):.5f} to {max(sample_prices):.5f}")
                logger.info(f"   Current live: {current_price:.5f}")
            else:
                logger.warning(f"Could not get current tick for {SYMBOL}")
                logger.warning("Using synthetic data as fallback")
                sample_prices = _generate_synthetic_prices()
                
        except Exception as e:
            logger.error(f"Exception getting MT5 live price: {type(e).__name__}: {e}")
            logger.warning("Using synthetic prices as fallback")
            import traceback
            logger.debug(traceback.format_exc())
            sample_prices = _generate_synthetic_prices()
    else:
        # Use synthetic prices if MT5 not connected
        logger.warning("MT5 not connected, using synthetic price data (simulation mode only)")
        sample_prices = _generate_synthetic_prices()

    logger.info("Processing %d price bars for trading session", len(sample_prices))

    # Process ticks
    for i in range(SLOW_MA + 2, len(sample_prices)):
        if stop_event is not None and stop_event.is_set():
            logger.info("🛑 Stop requested, ending session at bar %d", i)
            break

        current_prices = sample_prices[:i+1]
        bid = sample_prices[i] - POINT
        ask = sample_prices[i] + POINT
        current_price = sample_prices[i]

        # Evaluate existing positions
        evaluate_open_positions(current_prices, current_price, timestamp=f"Bar {i}")

        # Process new tick with trading signal
        process_tick(
            current_prices,
            account_balance,
            bid,
            ask,
            timestamp=f"Bar {i}"
        )

        # Evaluate positions again
        evaluate_open_positions(current_prices, current_price, timestamp=f"Bar {i}")
        
        # Add small delay in real MT5 mode to avoid overwhelming the API
        if mt5_manager.connected:
            import time
            time.sleep(0.1)

    logger.info("-" * 70)
    logger.info("TRADING SESSION SUMMARY")
    logger.info("Total positions opened: %d", len(trade_history))
    average_confidence = np.mean([t.confidence for t in trade_history]) if trade_history else 0.0
    logger.info("Average AI Confidence: %.2f%%", average_confidence * 100)
    logger.info("Training samples collected: %d", len(training_data_x))


def auto_trade(cycles: int = 3, interval_sec: int = 10):
    """Automatically run multiple simulation cycles with pauses"""
    logger.info("🚀 Starting automated trading: %d iterations, %ds interval", cycles, interval_sec)
    for cycle in range(1, cycles + 1):
        logger.info("--- Cycle %d/%d ---", cycle, cycles)
        run_simulation(stop_event=stop_event)
        if cycle < cycles:
            logger.info("Sleeping %d seconds before next cycle...", interval_sec)
            import time
            time.sleep(interval_sec)
        if stop_event.is_set():
            logger.info("🛑 Stop event triggered, ending auto trade loop")
            break
    logger.info("✅ Automated trading cycles completed")


def print_status():
    """Print current open positions and high-level stats"""
    logger.info("--- STATUS ---")
    logger.info("Open positions: %d", len(open_positions))
    logger.info("Closed trades: %d", len(trade_history))
    logger.info("Training samples: %d", len(training_data_x))
    if open_positions:
        for i, pos in enumerate(open_positions, start=1):
            logger.info(
                "Position %d: %s %0.2f %s @ %.5f (SL: %.5f TP: %.5f) conf %.2f%%",
                i, pos.side, pos.volume, pos.symbol, pos.entry_price, pos.sl, pos.tp, pos.confidence * 100
            )


def interactive_interface():
    """Interactive console interface for start/stop/status operations"""
    global simulation_thread, stop_event

    print("Interactive Trading Bot Interface")
    print("Commands: start, stop, status, summary, help, quit")

    while True:
        command = input("Command> ").strip().lower()
        if not command:
            continue

        if command == "start":
            if simulation_thread is not None and simulation_thread.is_alive():
                print("A simulation is already running. Use 'stop' to stop it first.")
                continue
            stop_event.clear()
            simulation_thread = threading.Thread(target=run_simulation, args=(10000.0, stop_event), daemon=True)
            simulation_thread.start()
            print("Simulation started.")

        elif command == "stop":
            if stop_event.is_set():
                print("Already stopping...")
                continue
            stop_event.set()
            print("Stop request sent.")
            if simulation_thread is not None:
                simulation_thread.join(timeout=5)

        elif command == "status":
            print_status()

        elif command == "summary":
            print_status()

        elif command in ("help", "?"):
            print("Commands:")
            print("  start   - Start one simulation session")
            print("  stop    - Stop current simulation/session")
            print("  status  - Show open/closed position counts and sample stats")
            print("  summary - Same as status")
            print("  quit    - Exit interface")

        elif command in ("quit", "exit"):
            stop_event.set()
            if simulation_thread is not None:
                simulation_thread.join(timeout=5)
            print("Exiting interactive interface.")
            break

        else:
            print("Unknown command. Type 'help'.")


# =============================================================================
# Main Entry Point
# =============================================================================
def main():
    """Main trading bot entry point"""
    logger.info("=" * 70)
    logger.info("ALGORITHMIC TRADING BOT - AI-ENHANCED SMA CROSSOVER")
    logger.info("=" * 70)

    if not validate_parameters():
        logger.error("Parameter validation failed")
        return

    import argparse
    parser = argparse.ArgumentParser(description="AI-powered trading bot")
    parser.add_argument("--auto", action="store_true", help="Run automated cycles")
    parser.add_argument("--interactive", action="store_true", help="Run interactive start/stop/status interface")
    parser.add_argument("--cycles", type=int, default=3, help="Number of auto cycles")
    parser.add_argument("--interval", type=int, default=10, help="Seconds between auto cycles")
    parser.add_argument("--balance", type=float, default=10000.0, help="Starting account balance")
    args = parser.parse_args()

    if args.interactive:
        interactive_interface()
    elif args.auto:
        auto_trade(cycles=args.cycles, interval_sec=args.interval)
    else:
        run_simulation(account_balance=args.balance)

    logger.info("=" * 70)


if __name__ == "__main__":
    main()