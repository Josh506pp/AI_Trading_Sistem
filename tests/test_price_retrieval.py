#!/usr/bin/env python3
"""Test script to diagnose MT5 price data retrieval"""

import sys
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    import MetaTrader5 as mt5
    logger.info("✓ MetaTrader5 module imported successfully")
except ImportError as e:
    logger.error(f"✗ Failed to import MetaTrader5: {e}")
    sys.exit(1)

# Initialize MT5
logger.info("\n" + "="*60)
logger.info("TESTING MT5 PRICE DATA RETRIEVAL")
logger.info("="*60)

logger.info("\n1. Initializing MT5...")
try:
    if mt5.initialize():
        logger.info("✓ MT5 initialized")
    else:
        logger.error("✗ Failed to initialize MT5")
        sys.exit(1)
except Exception as e:
    logger.error(f"✗ Exception during initialize: {e}")
    sys.exit(1)

logger.info("\n2. Checking MT5 connection...")
try:
    account_info = mt5.account_info()
    if account_info:
        logger.info(f"✓ Connected to account: {account_info.login}")
        logger.info(f"   Balance: {account_info.balance}")
        logger.info(f"   Currency: {account_info.currency}")
    else:
        logger.error("✗ Cannot get account info - check if logged in")
except Exception as e:
    logger.error(f"✗ Exception getting account info: {e}")

logger.info("\n3. Checking EURUSD symbol...")
try:
    SYMBOL = "EURUSD"
    symbol_info = mt5.symbol_info(SYMBOL)
    if symbol_info:
        logger.info(f"✓ Symbol {SYMBOL} found")
        logger.info(f"   Description: {symbol_info.description}")
        logger.info(f"   Bid: {symbol_info.bid:.5f}")
        logger.info(f"   Ask: {symbol_info.ask:.5f}")
        logger.info(f"   Volume: {symbol_info.volume}")
    else:
        logger.error(f"✗ Symbol {SYMBOL} not found")
except Exception as e:
    logger.error(f"✗ Exception getting symbol info: {e}")

logger.info("\n4. Getting current tick...")
try:
    current_tick = mt5.symbol_info_tick(SYMBOL)
    if current_tick:
        logger.info(f"✓ Got current tick")
        logger.info(f"   Bid: {current_tick.bid:.5f}")
        logger.info(f"   Ask: {current_tick.ask:.5f}")
        logger.info(f"   Last: {current_tick.last if hasattr(current_tick, 'last') else 'N/A'}")
        logger.info(f"   Time: {current_tick.time}")
    else:
        logger.error(f"✗ Could not get current tick for {SYMBOL}")
except Exception as e:
    logger.error(f"✗ Exception getting tick: {e}")

logger.info("\n5. Testing different timeframes for candle data...")
timeframes = [
    ("M1", mt5.TIMEFRAME_M1),
    ("M5", mt5.TIMEFRAME_M5),
    ("M15", mt5.TIMEFRAME_M15),
    ("M30", mt5.TIMEFRAME_M30),
    ("H1", mt5.TIMEFRAME_H1),
    ("H4", mt5.TIMEFRAME_H4),
    ("D1", mt5.TIMEFRAME_D1),
]

for tf_name, tf_enum in timeframes:
    try:
        logger.info(f"\n   Testing {tf_name}...")
        rates = mt5.copy_rates_from(SYMBOL, tf_enum, 0, 10)
        
        if rates is not None:
            logger.info(f"   ✓ Got {len(rates)} candles from {tf_name}")
            if len(rates) > 0:
                latest = rates[-1]
                logger.info(f"      Latest candle: Open={latest['open']:.5f}, Close={latest['close']:.5f}, High={latest['high']:.5f}, Low={latest['low']:.5f}")
        else:
            logger.warning(f"   ✗ Got None for {tf_name}")
    except Exception as e:
        logger.error(f"   ✗ Exception for {tf_name}: {type(e).__name__}: {e}")

logger.info("\n6. Testing copy_rates_range (alternative method)...")
try:
    from datetime import datetime, timedelta
    now = datetime.now()
    start_time = now - timedelta(hours=1)
    
    logger.info(f"   Requesting rates from {start_time} to {now}")
    rates_range = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_M1, start_time, now)
    
    if rates_range is not None:
        logger.info(f"   ✓ Got {len(rates_range)} candles with copy_rates_range")
        if len(rates_range) > 0:
            latest = rates_range[-1]
            logger.info(f"      Latest: Open={latest['open']:.5f}, Close={latest['close']:.5f}")
    else:
        logger.warning(f"   ✗ copy_rates_range returned None")
except Exception as e:
    logger.error(f"   ✗ Exception with copy_rates_range: {type(e).__name__}: {e}")

logger.info("\n7. Testing copy_ticks_from (tick data)...")
try:
    ticks = mt5.copy_ticks_from(SYMBOL, 0, 10)
    if ticks is not None:
        logger.info(f"   ✓ Got {len(ticks)} ticks")
        if len(ticks) > 0:
            logger.info(f"      Latest tick bid={ticks[-1]['bid']:.5f}, ask={ticks[-1]['ask']:.5f}")
    else:
        logger.warning(f"   ✗ copy_ticks_from returned None")
except Exception as e:
    logger.error(f"   ✗ Exception with copy_ticks_from: {type(e).__name__}: {e}")

logger.info("\n" + "="*60)
logger.info("DIAGNOSIS COMPLETE")
logger.info("="*60)

mt5.shutdown()
logger.info("\n✓ MT5 shutdown")
