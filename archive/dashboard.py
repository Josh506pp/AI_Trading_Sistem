#!/usr/bin/env python3
"""
Web Dashboard for Trading Bot
Flask-based UI for MT5 login, bot control, and trading metrics
"""

import os
from flask import Flask, render_template, jsonify, request
from datetime import datetime
from mt5_manager import mt5_manager
from bot_manager import bot_manager
from trading_bot import logger
from chat_interface import TradingBotChatInterface

# Configuration
SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'trading_bot_secret_2026')
DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Global chat interface instance
chat_interface = None

def get_chat_interface():
    """Get or create chat interface instance"""
    global chat_interface
    if chat_interface is None:
        try:
            from trading_bot import AI_CONTROL_SYSTEM
            trading_system = AI_CONTROL_SYSTEM if AI_CONTROL_SYSTEM is not None else IntegratedTradingSystem()
        except Exception:
            trading_system = IntegratedTradingSystem()
        chat_interface = TradingBotChatInterface(trading_system)
    return chat_interface


# Routes

@app.route("/")
def index():
    """Serve dashboard HTML"""
    return render_template("dashboard.html")


@app.route("/api/mt5/is_logged_in", methods=["GET"])
def is_logged_in():
    """Check if user is logged into MT5"""
    return jsonify({"logged_in": mt5_manager.connected})


@app.route("/api/mt5/login", methods=["POST"])
def mt5_login():
    """Login to MT5 with provided credentials"""
    try:
        data = request.get_json()
        login = data.get("login", "").strip()
        password = data.get("password", "").strip()
        server = data.get("server", "").strip()
        path = data.get("path", "").strip() or None

        if not all([login, password, server]):
            return jsonify({"error": "Missing required fields: login, password, server"}), 400

        result = mt5_manager.connect(login, password, server, path)
        return jsonify(result), 200 if result.get("success") else 401

    except Exception as e:
        logger.error(f"MT5 login error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/mt5/logout", methods=["POST"])
def mt5_logout():
    """Logout from MT5"""
    try:
        result = mt5_manager.disconnect()
        return jsonify(result)
    except Exception as e:
        logger.error(f"MT5 logout error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/mt5/session", methods=["GET"])
def mt5_session_info():
    """Get current MT5 session info"""
    try:
        return jsonify(mt5_manager.get_session_info())
    except Exception as e:
        logger.error(f"Error getting MT5 session info: {e}")
        return jsonify({"logged_in": False, "login": None, "server": None}), 500


@app.route("/api/mt5/account", methods=["GET"])
def mt5_account_info():
    """Get MT5 account balance, profit, and equity"""
    try:
        return jsonify(mt5_manager.get_account_info())
    except Exception as e:
        logger.error(f"Error getting MT5 account info: {e}")
        return jsonify({
            "logged_in": False,
            "balance": 0.0,
            "equity": 0.0,
            "profit": 0.0,
            "currency": "USD"
        }), 500


@app.route("/api/status", methods=["GET"])
def status_api():
    """Get current bot status"""
    try:
        from trading_bot import open_positions, trade_history
        
        status = bot_manager.status
        
        # Format positions
        positions_data = [
            {
                "side": p.side,
                "symbol": p.symbol,
                "volume": p.volume,
                "entry_price": p.entry_price,
                "sl": p.sl,
                "tp": p.tp,
                "confidence": p.confidence * 100
            }
            for p in open_positions
        ]
        
        # Format last 10 trades
        trades_data = [
            {
                "side": t.side,
                "symbol": t.symbol,
                "volume": t.volume,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "pnl": t.pnl,
                "timestamp": t.timestamp,
                "confidence": t.confidence * 100
            }
            for t in trade_history[-10:]
        ]
        
        return jsonify({
            "status": status,
            "open_positions": positions_data,
            "recent_trades": trades_data
        })
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/summary", methods=["GET"])
def summary_api():
    """Get trading summary"""
    try:
        summary = bot_manager.get_summary()
        return jsonify(summary)
    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/start", methods=["POST"])
def start_bot():
    """Start the trading bot"""
    try:
        result = bot_manager.start()
        return jsonify(result), 200 if "message" in result else 400
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/stop", methods=["POST"])
def stop_bot():
    """Stop the trading bot"""
    try:
        result = bot_manager.stop()
        return jsonify(result), 200 if "message" in result else 400
    except Exception as e:
        logger.error(f"Error stopping bot: {e}")
        return jsonify({"error": "Internal server error"}), 500


# =============================================================================
# CHAT API ENDPOINTS
# =============================================================================

@app.route("/api/chat/command", methods=["POST"])
def process_chat_command():
    """Process a chat command"""
    try:
        data = request.get_json()
        command = data.get("command", "").strip()

        if not command:
            return jsonify({"error": "No command provided"}), 400

        # Get chat interface
        chat = get_chat_interface()

        # Process command
        response = chat.process_command(command)

        return jsonify({
            "command": command,
            "response": response,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Chat command error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/chat/history", methods=["GET"])
def get_chat_history():
    """Get chat command history"""
    try:
        chat = get_chat_interface()
        history = chat.command_history[-50:]  # Last 50 commands

        # Format history
        formatted_history = [
            {
                "command": item["command"],
                "response": item["response"],
                "timestamp": item["timestamp"].isoformat()
            }
            for item in history
        ]

        return jsonify({"history": formatted_history})

    except Exception as e:
        logger.error(f"Chat history error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/chat/commands", methods=["GET"])
def get_available_commands():
    """Get list of available chat commands"""
    try:
        chat = get_chat_interface()

        commands = []
        for cmd_name, cmd_obj in chat.registered_commands.items():
            commands.append({
                "name": cmd_name,
                "category": cmd_obj.category.value,
                "description": cmd_obj.description,
                "usage": cmd_obj.usage,
                "aliases": cmd_obj.aliases
            })

        # Group by category
        categories = {}
        for cmd in commands:
            cat = cmd["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(cmd)

        return jsonify({"commands": categories})

    except Exception as e:
        logger.error(f"Available commands error: {e}")
        return jsonify({"error": "Internal server error"}), 500


# Error handlers

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    print("Starting Trading Bot Dashboard...")
    print("Open http://localhost:5000 in your browser")
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=DEBUG,
        threaded=True
    )
