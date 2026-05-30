#!/usr/bin/env python3
"""
Bot Manager
Handles trading bot operations, status tracking, and threading
"""

import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional
from trading_bot import (
    run_simulation, stop_event, open_positions, trade_history,
    training_data_x, logger, print_status
)

class BotManager:
    """Manages trading bot operations and status"""

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._status = {
            "running": False,
            "open_positions": 0,
            "closed_trades": 0,
            "training_samples": 0,
            "last_update": None,
            "start_time": None
        }

    @property
    def status(self) -> Dict[str, Any]:
        """Get current bot status"""
        self._update_status()
        return self._status.copy()

    def _update_status(self):
        """Update internal status from bot state"""
        self._status.update({
            "running": self._thread is not None and self._thread.is_alive(),
            "open_positions": len(open_positions),
            "closed_trades": len(trade_history),
            "training_samples": len(training_data_x),
            "last_update": datetime.now().isoformat()
        })

    def start(self) -> Dict[str, Any]:
        """Start the trading bot"""
        if self._thread and self._thread.is_alive():
            return {"error": "Bot is already running"}

        try:
            # Reset stop event
            stop_event.clear()

            # Start bot in background thread with continuous trading
            self._thread = threading.Thread(
                target=self._run_bot_loop,
                daemon=True
            )
            self._thread.start()

            self._status["start_time"] = datetime.now().isoformat()
            logger.info("Trading bot started")

            return {"message": "Bot started successfully"}

        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            return {"error": f"Failed to start bot: {str(e)}"}

    def _run_bot_loop(self):
        """Continuous bot trading loop"""
        try:
            account_balance = 10000.0
            cycle = 0
            
            while not stop_event.is_set():
                cycle += 1
                logger.info(f"🔄 Trading cycle {cycle} started")
                
                # Run one simulation cycle
                run_simulation(account_balance=account_balance, stop_event=stop_event)
                
                # Pause between cycles (5 seconds)
                if not stop_event.is_set():
                    time.sleep(5)
                
                # Print status
                self._update_status()
                
        except Exception as e:
            logger.error(f"Bot loop error: {e}")
        finally:
            logger.info("Bot loop ended")

    def stop(self) -> Dict[str, Any]:
        """Stop the trading bot"""
        if not self._thread or not self._thread.is_alive():
            return {"error": "Bot is not running"}

        try:
            # Signal stop
            stop_event.set()

            # Wait for thread to finish (with timeout)
            self._thread.join(timeout=5.0)

            if self._thread.is_alive():
                logger.warning("Bot thread did not stop gracefully")

            self._thread = None
            logger.info("Trading bot stopped")

            return {"message": "Bot stopped successfully"}

        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
            return {"error": f"Failed to stop bot: {str(e)}"}

    def get_summary(self) -> Dict[str, Any]:
        """Get trading summary statistics"""
        try:
            from trading_bot import SYMBOL, training_data_x
            
            # Calculate P&L metrics
            total_pnl = sum(t.pnl for t in trade_history) if trade_history else 0.0
            avg_pnl_per_trade = total_pnl / len(trade_history) if trade_history else 0.0
            
            # Calculate win rate (percentage of profitable trades)
            winning_trades = sum(1 for t in trade_history if t.pnl > 0)
            win_rate = (winning_trades / len(trade_history) * 100) if trade_history else 0.0
            
            # Calculate average confidence
            avg_confidence = sum(t.confidence for t in trade_history) / len(trade_history) if trade_history else 0.0

            return {
                "symbol": SYMBOL,
                "total_trades": len(trade_history),
                "open_positions": len(open_positions),
                "total_pnl": total_pnl,
                "avg_pnl_per_trade": avg_pnl_per_trade,
                "win_rate": win_rate,
                "avg_confidence": avg_confidence * 100,
                "training_samples": len(training_data_x)
            }
        except Exception as e:
            logger.error(f"Error getting summary: {e}")
            return {
                "symbol": "N/A",
                "total_trades": 0,
                "open_positions": 0,
                "total_pnl": 0.0,
                "avg_pnl_per_trade": 0.0,
                "win_rate": 0.0,
                "avg_confidence": 0.0,
                "training_samples": 0
            }

# Global bot manager instance
bot_manager = BotManager()