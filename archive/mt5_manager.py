#!/usr/bin/env python3
"""
MT5 Connection Manager
Handles MT5 initialization, connection status, and session management
"""

import os
import logging
from typing import Optional, Dict, Any
from trading_bot import mt5, MT5_AVAILABLE, logger

class MT5Manager:
    """Manages MT5 connection state and operations"""

    def __init__(self):
        self._connected = False
        self._account_info = None
        self._login = None
        self._server = None
        self._path = None

    @property
    def connected(self) -> bool:
        """Check if MT5 is currently connected (verifies actively)"""
        # Always verify the connection status by attempting to get account info
        return self.check_connection()

    @property
    def account_info(self) -> Optional[Any]:
        """Get current account information"""
        return self._account_info

    def check_connection(self) -> bool:
        """Check current MT5 connection status"""
        if not MT5_AVAILABLE:
            return False

        try:
            # Initialize if not already done
            if not mt5.initialize():
                self._connected = False
                return False

            # Get account info to verify connection
            account_info = mt5.account_info()
            if account_info is not None:
                self._connected = True
                self._account_info = account_info
                return True
            else:
                self._connected = False
                return False
        except Exception as e:
            logger.error(f"Error checking MT5 connection: {e}")
            self._connected = False
            return False

    def connect(self, login: str, password: str, server: str, path: Optional[str] = None) -> Dict[str, Any]:
        """Connect to MT5 with provided credentials"""
        if not MT5_AVAILABLE:
            return {"success": False, "error": "MetaTrader5 package not available"}

        try:
            # Initialize MT5
            if path and not mt5.initialize(path=path):
                return {"success": False, "error": f"Failed to initialize MT5 with path: {path}"}
            elif not mt5.initialize():
                return {"success": False, "error": "Failed to initialize MT5"}

            # Login to account
            if not mt5.login(login=int(login), password=password, server=server):
                mt5.shutdown()
                return {"success": False, "error": "Login failed. Check credentials."}

            # Get account info
            account_info = mt5.account_info()
            if account_info is None:
                mt5.shutdown()
                return {"success": False, "error": "Failed to get account information"}

            # Update state
            self._connected = True
            self._account_info = account_info
            self._login = login
            self._server = server
            self._path = path

            logger.info(f"✓ MT5 connected successfully - Account: {account_info.login}")
            return {
                "success": True,
                "message": f"Connected to MT5 account {login}",
                "account": login
            }

        except Exception as e:
            logger.error(f"MT5 connection error: {e}")
            try:
                mt5.shutdown()
            except:
                pass
            return {"success": False, "error": f"Connection error: {str(e)}"}

    def disconnect(self) -> Dict[str, Any]:
        """Disconnect from MT5"""
        try:
            if MT5_AVAILABLE and self._connected:
                mt5.shutdown()
                logger.info("MT5 connection closed")
            self._connected = False
            self._account_info = None
            self._login = None
            self._server = None
            self._path = None
            logger.info("MT5 disconnected")
            return {"message": "Disconnected from MT5"}
        except Exception as e:
            logger.error(f"Error disconnecting from MT5: {e}")
            self._connected = False
            return {"error": f"Disconnect error: {str(e)}"}

    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information"""
        if not self.check_connection():
            return {"logged_in": False, "login": None, "server": None}

        return {
            "logged_in": True,
            "login": str(self._account_info.login) if self._account_info else None,
            "server": self._account_info.server if self._account_info else None
        }

    def get_account_info(self) -> Dict[str, Any]:
        """Get detailed MT5 account information (balance, profit, equity)"""
        if not self.check_connection() or not self._account_info:
            return {
                "logged_in": False,
                "balance": 0.0,
                "equity": 0.0,
                "profit": 0.0,
                "currency": "USD"
            }
        
        info = self._account_info
        balance = float(info.balance) if hasattr(info, 'balance') else 0.0
        equity = float(info.equity) if hasattr(info, 'equity') else 0.0
        profit = equity - balance  # Profit = Equity - Balance
        currency = str(info.currency) if hasattr(info, 'currency') else "USD"
        
        return {
            "logged_in": True,
            "login": str(info.login),
            "server": str(info.server),
            "balance": balance,
            "equity": equity,
            "profit": profit,
            "currency": currency
        }

# Global MT5 manager instance
mt5_manager = MT5Manager()