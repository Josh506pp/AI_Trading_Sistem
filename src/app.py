#!/usr/bin/env python3
"""
TRADING SYSTEM - APLICACIÓN WEB SIMPLE Y FUNCIONAL
Versión limpia sin dependencias complicadas
"""

from flask import Flask, render_template_string, request, redirect, jsonify, session, make_response
import os
import json
import time
import random
import threading
import socket
import webbrowser
import secrets
import requests
from datetime import datetime, timedelta

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False

try:
    from .professional_trading_system import AIAnalyzer as ProAIAnalyzer
    PROFESSIONAL_AVAILABLE = True
except ImportError:
    ProAIAnalyzer = None
    PROFESSIONAL_AVAILABLE = False

try:
    from .mt5_integration import BotAITrader
    INTEGRATION_AVAILABLE = True
except ImportError:
    BotAITrader = None
    INTEGRATION_AVAILABLE = False

try:
    from .mt5_config import (
        MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, MT5_PATH,
        TRADING_SYMBOL, DEFAULT_VOLUME, USE_REAL_ACCOUNT
    )
except ImportError:
    MT5_LOGIN = None
    MT5_PASSWORD = None

try:
    from .prediction_system import prediction_engine
    PREDICTION_AVAILABLE = True
except ImportError:
    prediction_engine = None
    PREDICTION_AVAILABLE = False
    MT5_SERVER = None
    MT5_PATH = None
    TRADING_SYMBOL = 'EURUSD'
    DEFAULT_VOLUME = 0.01
    USE_REAL_ACCOUNT = False

MT5_LOGIN = os.environ.get('MT5_LOGIN', MT5_LOGIN)
MT5_PASSWORD = os.environ.get('MT5_PASSWORD', MT5_PASSWORD)
MT5_SERVER = os.environ.get('MT5_SERVER', MT5_SERVER)
MT5_PATH = os.environ.get('MT5_PATH', MT5_PATH)
TRADING_SYMBOL = os.environ.get('TRADING_SYMBOL', TRADING_SYMBOL).upper()
if TRADING_SYMBOL not in ('EURUSD', 'XAUUSD'):
    TRADING_SYMBOL = 'EURUSD'
DEFAULT_VOLUME = float(os.environ.get('DEFAULT_VOLUME', DEFAULT_VOLUME))
USE_REAL_ACCOUNT = os.environ.get('USE_REAL_ACCOUNT', str(USE_REAL_ACCOUNT)).lower() in ('1', 'true', 'yes')

MT5_CREDENTIALS = {}
if all([MT5_LOGIN, MT5_PASSWORD, MT5_SERVER]):
    MT5_CREDENTIALS = {
        'login': MT5_LOGIN,
        'password': MT5_PASSWORD,
        'server': MT5_SERVER,
        'path': MT5_PATH
    }

# External AI API configuration
NV_API_URL = os.environ.get('NV_API_URL', 'https://api.nvapi.io/v1/chat')
NV_API_KEY = os.environ.get('NV_API_KEY')
NV_MODEL = os.environ.get('NV_MODEL', 'gpt-4')
NV_MAX_TOKENS = int(os.environ.get('NV_MAX_TOKENS', '900'))
NV_TEMPERATURE = float(os.environ.get('NV_TEMPERATURE', '0.7'))
NV_USE_EXTERNAL_AI = os.environ.get('NV_USE_EXTERNAL_AI', 'true').lower() in ('1', 'true', 'yes', 'on')

EXTERNAL_AI_CACHE = {'key': None, 'value': None, 'ts': 0.0}

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'trading-system-secret-2026')
app.config.update({
    'SESSION_COOKIE_HTTPONLY': True,
    'SESSION_COOKIE_SAMESITE': 'Lax',
    'SESSION_COOKIE_SECURE': os.environ.get('FLASK_ENV') == 'production'
})

FLASK_HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
FLASK_PORT = int(os.environ.get('FLASK_PORT', os.environ.get('PORT', '5000')))

# ====================================================================
# DATOS GLOBALES
# ====================================================================

MARKET_DATA = {
    'EURUSD': {
        'price': 1.0850,
        'price_history': [1.0850 + i * 0.0001 + random.uniform(-0.0005, 0.0005) for i in range(50)],
        'volatility': 0.00008,
        'min_price': 0.8,
        'max_price': 1.5
    },
    'XAUUSD': {
        'price': 1950.00,
        'price_history': [1950.00 + i * 0.12 + random.uniform(-0.35, 0.35) for i in range(50)],
        'volatility': 0.24,
        'min_price': 1500.0,
        'max_price': 2500.0
    }
}

TRADING_DATA = {
    'symbol': TRADING_SYMBOL,
    'price': MARKET_DATA[TRADING_SYMBOL]['price'],
    'price_history': MARKET_DATA[TRADING_SYMBOL]['price_history'].copy(),
    'balance': 10000.0,
    'equity': 10000.0,
    'trades_open': 0,
    'trades': [],
    'closed_trades': [],
    'auto_enabled': False,
    'use_prediction': True,
    'signal': {'action': 'HOLD', 'confidence': 0.0},
    'volatility_alert': {
        'level': 'NORMAL',
        'direction': 'LATERAL',
        'color': 'neutral',
        'strength': 0.0,
        'message': 'Mercado estable'
    },
    'analysis_cache': {'ts': 0.0, 'symbol': TRADING_SYMBOL, 'data': {'action': 'ESPERA', 'confidence': 0.0}},
    'last_one_shot_prediction_ts': 0.0,
    'chat_history': [{'sender': 'IA', 'text': 'Hola! Bienvenido al sistema de trading. Soy tu asistente de IA.'}]
}

PRICE_LOCK = threading.Lock()
MT5_CONNECTED = False
MT5_ACCOUNT_INFO = None

# IA Profesional Mejorada
if PROFESSIONAL_AVAILABLE:
    PRO_AI_ANALYZER = ProAIAnalyzer()
else:
    PRO_AI_ANALYZER = None

# ======== BOT + IA + MT5 INTEGRADO ========
BOT_TRADER = None
BOT_THREAD = None

def initialize_bot_trader():
    """Inicializa el sistema integrado Bot + IA + MT5"""
    global BOT_TRADER
    if INTEGRATION_AVAILABLE and BotAITrader:
        try:
            BOT_TRADER = BotAITrader(MT5_LOGIN, MT5_PASSWORD, MT5_SERVER)
            return True
        except Exception as e:
            print(f"Error inicializando BotAITrader: {e}")
            return False
    return False


# ====================================================================
# SISTEMA INTELIGENTE DE ANÁLISIS Y APRENDIZAJE DE IA
# ====================================================================

# Base de datos de aprendizaje
AI_LEARNING_DB = {
    'successful_patterns': [],
    'trade_history': [],
    'professional_patterns': [],
    'user_interactions': [],
    'user_preferences': {
        'preferred_direction': 'neutral',
        'risk_tolerance': 'balanced',
        'favorite_symbol': TRADING_SYMBOL
    },
    'market_memory': {},
    'global_market_bias': {'trend': 'NEUTRAL', 'score': 0.0, 'updated_at': None},
    'last_global_history_refresh': 0.0,
    'learning_score': 0.0,
    'confidence_threshold': 0.65
}

CHAT_MEMORY_FILE = os.path.join(os.path.dirname(__file__), 'data', 'chat_memory.json')


def load_chat_memory():
    """Carga la memoria persistente del chat desde disco."""
    try:
        os.makedirs(os.path.dirname(CHAT_MEMORY_FILE), exist_ok=True)
        if os.path.exists(CHAT_MEMORY_FILE):
            with open(CHAT_MEMORY_FILE, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return {'entries': [], 'preferences': {}, 'summary': ''}


def save_chat_memory(memory):
    """Guarda la memoria persistente del chat."""
    try:
        os.makedirs(os.path.dirname(CHAT_MEMORY_FILE), exist_ok=True)
        with open(CHAT_MEMORY_FILE, 'w', encoding='utf-8') as fh:
            json.dump(memory, fh, indent=2)
    except Exception:
        pass


def build_market_context():
    """Construye un resumen breve del mercado actual para la IA."""
    with PRICE_LOCK:
        symbol = TRADING_SYMBOL
        price = TRADING_DATA.get('price', 0)
        prices = TRADING_DATA.get('price_history', [])
        signal = TRADING_DATA.get('signal', {'action': 'HOLD', 'confidence': 0.0})
        if len(prices) >= 10:
            trend = 'ALZA' if price > prices[-10] else 'BAJA'
            change = round(price - prices[-5], 6)
            momentum = round((price - prices[-10]) / max(prices[-10], 1e-9), 6)
        else:
            trend = 'NEUTRA'
            change = 0.0
            momentum = 0.0
        return {
            'symbol': symbol,
            'price': round(price, 6),
            'trend': trend,
            'change': round(change, 6),
            'momentum': round(momentum, 6),
            'signal': signal.get('action', 'HOLD'),
            'confidence': round(float(signal.get('confidence', 0.0)) * 100, 1),
            'volatility_alert': TRADING_DATA.get('volatility_alert', {'level': 'NORMAL', 'direction': 'LATERAL'}),
            'global_trend': AI_LEARNING_DB.get('global_market_bias', {}).get('trend', 'NEUTRAL')
        }


def learn_from_market_cycle():
    """Aprendizaje continuo del mercado para reforzar la memoria de la IA."""
    try:
        # No usar build_market_context aquí para evitar adquirir PRICE_LOCK dentro del mismo lock.
        symbol = TRADING_DATA.get('symbol', TRADING_SYMBOL)
        price = TRADING_DATA.get('price', 0)
        prices = TRADING_DATA.get('price_history', [])
        signal = TRADING_DATA.get('signal', {'action': 'HOLD', 'confidence': 0.0})

        if len(prices) >= 10:
            trend = 'ALZA' if price > prices[-10] else 'BAJA'
        else:
            trend = 'NEUTRA'

        market = {
            'symbol': symbol,
            'trend': trend,
            'signal': signal.get('action', 'HOLD')
        }

        AI_LEARNING_DB['learning_score'] += 0.008
        if market['trend'] == 'ALZA':
            AI_LEARNING_DB['learning_score'] += 0.002
        elif market['trend'] == 'BAJA':
            AI_LEARNING_DB['learning_score'] += 0.002
        if market['signal'] != 'HOLD':
            AI_LEARNING_DB['learning_score'] += 0.003
    except Exception:
        pass


def build_memory_context(message, memory):
    """Resume la memoria reciente y preferencias del usuario."""
    entries = memory.get('entries', [])[-6:]
    prefs = memory.get('preferences', {})
    summary = memory.get('summary', '')
    if entries:
        recent = '; '.join([e.get('text', '') for e in entries if e.get('text')])
    else:
        recent = 'Sin interacción previa'
    return {
        'recent': recent[:220],
        'summary': summary[:220],
        'prefs': prefs
    }


def normalize_trade_action(action):
    """Convierte acciones del sistema IA a la forma esperada por MT5."""
    if not action:
        return 'BUY'
    action = str(action).upper()
    mapping = {
        'COMPRA': 'BUY',
        'BUY': 'BUY',
        'VENTA': 'SELL',
        'SELL': 'SELL',
        'ALCISTA': 'BUY',
        'BAJISTA': 'SELL',
        'LONG': 'BUY',
        'SHORT': 'SELL'
    }
    return mapping.get(action, 'BUY')


def learn_from_user_interaction(message, response, action=None):
    """Aprende de las interacciones del usuario para mejorar las respuestas y señales futuras."""
    try:
        with PRICE_LOCK:
            text = (message or '').strip().lower()
            if not text:
                return
            entry = {
                'message': text,
                'response': (response or '')[:180],
                'timestamp': datetime.now().isoformat(),
                'action': action
            }
            AI_LEARNING_DB['user_interactions'].append(entry)
            if len(AI_LEARNING_DB['user_interactions']) > 40:
                AI_LEARNING_DB['user_interactions'] = AI_LEARNING_DB['user_interactions'][-40:]

            if 'compra' in text or 'buy' in text or 'alcista' in text:
                AI_LEARNING_DB['user_preferences']['preferred_direction'] = 'buy'
            elif 'venta' in text or 'sell' in text or 'bajista' in text:
                AI_LEARNING_DB['user_preferences']['preferred_direction'] = 'sell'

            if 'riesgo' in text or 'conserv' in text or 'seguro' in text:
                AI_LEARNING_DB['user_preferences']['risk_tolerance'] = 'conservative'
            elif 'agres' in text or 'rápido' in text or 'alta' in text:
                AI_LEARNING_DB['user_preferences']['risk_tolerance'] = 'aggressive'

            if TRADING_SYMBOL in text:
                AI_LEARNING_DB['user_preferences']['favorite_symbol'] = TRADING_SYMBOL

            AI_LEARNING_DB['learning_score'] += 0.04
            if action:
                AI_LEARNING_DB['learning_score'] += 0.03
    except Exception:
        pass


def calculate_rsi(prices, period=14):
    """Calcula RSI (Índice de Fuerza Relativa)"""
    if len(prices) < period:
        return 50
    
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    seed = deltas[:period]
    up = sum([d for d in seed if d > 0])
    down = sum([-d for d in seed if d < 0])
    
    rs = up / down if down != 0 else 0
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calcula MACD (Moving Average Convergence Divergence)"""
    if len(prices) < slow:
        return {'macd': 0, 'signal': 0, 'histogram': 0}
    
    ema_fast = prices[-fast:]
    ema_slow = prices[-slow:]
    
    macd = sum(ema_fast) / len(ema_fast) - sum(ema_slow) / len(ema_slow)
    signal_line = macd
    histogram = macd - signal_line
    
    return {'macd': macd, 'signal': signal_line, 'histogram': histogram}

def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """Calcula Bandas de Bollinger"""
    if len(prices) < period:
        return {'upper': 0, 'middle': 0, 'lower': 0}
    
    recent = prices[-period:]
    middle = sum(recent) / len(recent)
    variance = sum([(x - middle) ** 2 for x in recent]) / len(recent)
    std = variance ** 0.5
    
    return {
        'upper': middle + (std * std_dev),
        'middle': middle,
        'lower': middle - (std * std_dev)
    }

def analyze_signal(prices):
    """Análisis inteligente y mejorado con múltiples indicadores"""
    if len(prices) < 20:
        return {'action': 'ESPERA', 'confidence': 0.0}
    
    # Indicadores técnicos
    rsi = calculate_rsi(prices)
    macd_data = calculate_macd(prices)
    bb_data = calculate_bollinger_bands(prices)
    
    current = prices[-1]
    prev = prices[-2]
    sma_short = sum(prices[-5:]) / 5
    sma_long = sum(prices[-20:]) / 20
    
    trend = 'ALZA' if current > sma_long else 'BAJA'
    momentum = 'FUERTE' if abs(current - prev) > 0.0005 else 'DÉBIL'
    
    # Aprendizaje: Aprender de patrones históricos exitosos y preferencias del usuario
    learned_bonus = 0.0
    user_pref = AI_LEARNING_DB['user_preferences']
    if user_pref.get('preferred_direction') == 'buy':
        learned_bonus += 0.06
    elif user_pref.get('preferred_direction') == 'sell':
        learned_bonus += 0.06
    if user_pref.get('risk_tolerance') == 'conservative':
        learned_bonus += 0.03
    elif user_pref.get('risk_tolerance') == 'aggressive':
        learned_bonus += 0.04

    if AI_LEARNING_DB['successful_patterns']:
        # Buscar patrones similares en el histórico
        for pattern in AI_LEARNING_DB['successful_patterns'][-20:]:
            if pattern['trend'] == trend and pattern['momentum'] == momentum:
                weight = 0.15 + min(0.25, (pattern.get('confidence', 0) or 0) * 0.15)
                learned_bonus += weight * (pattern.get('success_rate', 0.5) or 0.5)
            elif pattern['trend'] == trend:
                learned_bonus += 0.08 * (pattern.get('success_rate', 0.5) or 0.5)

    # Señal de trading inteligente
    confidence = 0.0
    action = 'ESPERA'

    if rsi < 45 and current < bb_data['middle'] and macd_data['histogram'] < 0:
        confidence = min(0.95, 0.45 + (45 - rsi) / 70 + learned_bonus)
        action = 'COMPRA'
    elif rsi > 55 and current > bb_data['middle'] and macd_data['histogram'] > 0:
        confidence = min(0.95, 0.45 + (rsi - 55) / 50 + learned_bonus)
        action = 'VENTA'
    elif (current > bb_data['upper']) and rsi > 55:
        confidence = min(0.95, 0.35 + (rsi - 55) / 40 + learned_bonus)
        action = 'VENTA'
    elif (current < bb_data['lower']) and rsi < 45:
        confidence = min(0.95, 0.35 + (45 - rsi) / 40 + learned_bonus)
        action = 'COMPRA'
    elif trend == 'BAJA' and current < sma_short and rsi > 48:
        confidence = min(0.88, 0.32 + (rsi - 48) / 60 + learned_bonus)
        action = 'VENTA'
    elif trend == 'ALZA' and current > sma_short and rsi < 52:
        confidence = min(0.88, 0.32 + (52 - rsi) / 60 + learned_bonus)
        action = 'COMPRA'

    # Validar confianza mínima para evitar señales demasiado débiles
    if confidence > 0 and confidence < AI_LEARNING_DB['confidence_threshold'] * 0.8:
        action = 'ESPERA'
        confidence = round(confidence * 0.7, 4)

    # Registrar patrón para futuro aprendizaje
    pattern_record = {
        'rsi': rsi,
        'trend': trend,
        'momentum': momentum,
        'action': action,
        'confidence': confidence
    }
    
    return {
        'action': action,
        'confidence': confidence,
        'rsi': rsi,
        'trend': trend,
        'macd': macd_data['histogram'],
        'bb': f"{bb_data['lower']:.4f}-{bb_data['upper']:.4f}",
        'pattern': pattern_record
    }


def build_volatility_alert(symbol, prices):
    """Calcula alerta de volatilidad direccional para el símbolo actual."""
    if len(prices) < 30:
        return {
            'level': 'NORMAL',
            'direction': 'LATERAL',
            'color': 'neutral',
            'strength': 0.0,
            'message': f'{symbol}: histórico insuficiente'
        }

    recent = prices[-12:]
    baseline = prices[-60:] if len(prices) >= 60 else prices[:-1]
    if len(baseline) < 10:
        baseline = prices[:-1]

    recent_abs_moves = [abs(recent[i] - recent[i - 1]) for i in range(1, len(recent))]
    base_abs_moves = [abs(baseline[i] - baseline[i - 1]) for i in range(1, len(baseline))]

    recent_avg_move = sum(recent_abs_moves) / max(1, len(recent_abs_moves))
    base_avg_move = sum(base_abs_moves) / max(1, len(base_abs_moves))
    ratio = recent_avg_move / max(base_avg_move, 1e-9)

    drift = recent[-1] - recent[0]
    min_drift = max(base_avg_move * 2.5, 0.0002 if symbol == 'EURUSD' else 0.2)

    if ratio >= 1.6 and drift >= min_drift:
        return {
            'level': 'ALTA',
            'direction': 'ALCISTA',
            'color': 'blue',
            'strength': min(1.0, (ratio - 1.0) / 2.0),
            'message': f'{symbol}: volatilidad alcista detectada'
        }

    if ratio >= 1.6 and drift <= -min_drift:
        return {
            'level': 'ALTA',
            'direction': 'BAJISTA',
            'color': 'red',
            'strength': min(1.0, (ratio - 1.0) / 2.0),
            'message': f'{symbol}: volatilidad bajista detectada'
        }

    return {
        'level': 'NORMAL',
        'direction': 'LATERAL',
        'color': 'neutral',
        'strength': min(0.4, max(0.0, ratio - 1.0)),
        'message': f'{symbol}: volatilidad estable'
    }


def fetch_symbol_history(symbol, days=5):
    """Obtiene histórico de días previos desde MT5 (H1) y usa fallback local si no está disponible."""
    points = []
    try:
        # Evita bloqueos: no intentes reconectar MT5 desde el ciclo global de aprendizaje.
        if MT5_AVAILABLE and MT5_CONNECTED:
            bars = max(24, int(days) * 24)
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, bars)
            if rates is not None and len(rates) > 0:
                points = [float(r['close']) for r in rates if 'close' in r.dtype.names]
    except Exception:
        points = []

    if points:
        return points

    # Fallback simulado: expandir el histórico local para no dejar el aprendizaje vacío.
    local = MARKET_DATA.get(symbol, {}).get('price_history', [])
    if not local:
        return []
    replicated = (local * max(1, (24 * max(1, days)) // max(1, len(local)) + 1))
    return replicated[-(24 * max(1, days)):]


def refresh_global_market_memory(force=False):
    """Actualiza memoria de mercado para múltiples símbolos y días previos."""
    now = time.time()
    if not force and (now - AI_LEARNING_DB.get('last_global_history_refresh', 0.0) < 180):
        return

    snapshots = {}
    trend_votes = []
    for symbol in MARKET_DATA.keys():
        hist = fetch_symbol_history(symbol, days=5)
        if len(hist) < 20:
            continue
        short = sum(hist[-12:]) / 12
        long = sum(hist[-48:]) / 48 if len(hist) >= 48 else sum(hist) / len(hist)
        slope = short - long
        direction = 'ALZA' if slope > 0 else 'BAJA'
        vol = build_volatility_alert(symbol, hist)
        snapshots[symbol] = {
            'samples': len(hist),
            'direction': direction,
            'slope': float(slope),
            'volatility': vol,
            'last_price': float(hist[-1])
        }
        trend_votes.append(1 if direction == 'ALZA' else -1)

    if snapshots:
        score = sum(trend_votes) / max(1, len(trend_votes))
        AI_LEARNING_DB['market_memory'] = snapshots
        AI_LEARNING_DB['global_market_bias'] = {
            'trend': 'ALCISTA' if score > 0.15 else ('BAJISTA' if score < -0.15 else 'NEUTRAL'),
            'score': float(score),
            'updated_at': datetime.now().isoformat()
        }
        AI_LEARNING_DB['learning_score'] += 0.01

    AI_LEARNING_DB['last_global_history_refresh'] = now


def generate_one_shot_prediction(symbol, prices):
    """Prediccion avanzada bajo demanda usando consenso de patrones y contexto global."""
    if len(prices) < 30:
        return {
            'success': False,
            'error': 'Datos insuficientes para prediccion avanzada (minimo 30 muestras).'
        }

    base = analyze_signal(prices)
    volatility = build_volatility_alert(symbol, prices)
    global_bias = AI_LEARNING_DB.get('global_market_bias', {'trend': 'NEUTRAL', 'score': 0.0})

    pred_price = prices[-1]
    direction = 'LATERAL'
    model_conf = float(base.get('confidence', 0.35))

    try:
        if PREDICTION_AVAILABLE and prediction_engine:
            pred = prediction_engine.predict_next_price(prices, periods=8)
            pred_price = float(pred.get('predicted_price', prices[-1]))
            direction = str(pred.get('direction', 'LATERAL')).upper()
            model_conf = float(pred.get('confidence', model_conf))
        else:
            delta = 0.00025 if symbol == 'EURUSD' else 0.65
            if base['action'] == 'COMPRA':
                pred_price = prices[-1] + delta
                direction = 'ALCISTA'
            elif base['action'] == 'VENTA':
                pred_price = prices[-1] - delta
                direction = 'BAJISTA'
    except Exception:
        pass

    # Construccion de consenso: tecnica + modelo + sesgo global + volatilidad direccional.
    score = model_conf
    reasons = []

    if base['action'] == 'COMPRA':
        reasons.append('Indicadores tecnicos favorecen COMPRA')
    elif base['action'] == 'VENTA':
        reasons.append('Indicadores tecnicos favorecen VENTA')
    else:
        reasons.append('Mercado sin sesgo tecnico claro')

    if global_bias.get('trend') == 'ALCISTA' and ('ALCISTA' in direction or base['action'] == 'COMPRA'):
        score += 0.08
        reasons.append('Tendencia global multiactivo alineada al alza')
    elif global_bias.get('trend') == 'BAJISTA' and ('BAJISTA' in direction or base['action'] == 'VENTA'):
        score += 0.08
        reasons.append('Tendencia global multiactivo alineada a la baja')
    else:
        score -= 0.05
        reasons.append('Tendencia global no alineada')

    if volatility.get('level') == 'ALTA':
        if volatility.get('direction') == 'ALCISTA' and ('ALCISTA' in direction or base['action'] == 'COMPRA'):
            score += 0.06
            reasons.append('Volatilidad alcista confirma escenario')
        elif volatility.get('direction') == 'BAJISTA' and ('BAJISTA' in direction or base['action'] == 'VENTA'):
            score += 0.06
            reasons.append('Volatilidad bajista confirma escenario')
        else:
            score -= 0.06
            reasons.append('Volatilidad contradice escenario')

    if base.get('rsi', 50) < 30 or base.get('rsi', 50) > 70:
        score += 0.03
        reasons.append('RSI en zona de movimiento fuerte')

    confidence = max(0.2, min(0.95, score))
    meets_target = confidence >= 0.70

    current_price = float(prices[-1])
    decimals = 2 if symbol == 'XAUUSD' else 5
    if symbol == 'XAUUSD':
        atr_like_move = max(0.8, volatility.get('strength', 0.0) * 0.6)
    else:
        atr_like_move = max(0.00035, volatility.get('strength', 0.0) * 0.00002)

    if 'ALCISTA' in direction or base['action'] == 'COMPRA':
        entry = current_price + (atr_like_move * 0.15)
        stop_loss = entry - (atr_like_move * 1.0)
        take_profit = entry + (atr_like_move * (1.8 if meets_target else 1.2))
    elif 'BAJISTA' in direction or base['action'] == 'VENTA':
        entry = current_price - (atr_like_move * 0.15)
        stop_loss = entry + (atr_like_move * 1.0)
        take_profit = entry - (atr_like_move * (1.8 if meets_target else 1.2))
    else:
        entry = current_price
        stop_loss = current_price - atr_like_move
        take_profit = current_price + atr_like_move

    entry = round(float(entry), decimals)
    stop_loss = round(float(stop_loss), decimals)
    take_profit = round(float(take_profit), decimals)

    action = 'ESPERA'
    if meets_target:
        if 'ALCISTA' in direction or base['action'] == 'COMPRA':
            action = 'COMPRA'
        elif 'BAJISTA' in direction or base['action'] == 'VENTA':
            action = 'VENTA'

    return {
        'success': True,
        'symbol': symbol,
        'current_price': current_price,
        'predicted_price': float(pred_price),
        'direction': direction,
        'action': action,
        'confidence': float(confidence),
        'confidence_percent': round(confidence * 100, 2),
        'target_confidence': 70.0,
        'target_met': bool(meets_target),
        'entry': entry,
        'stop_loss': stop_loss,
        'take_profit': take_profit,
        'levels': {
            'entry': entry,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'risk_reward': round(abs(take_profit - entry) / max(abs(entry - stop_loss), 1e-9), 2)
        },
        'volatility': volatility,
        'global_bias': global_bias,
        'reasons': reasons[:5],
        'timestamp': datetime.now().isoformat()
    }

# ====================================================================
# ACTUALIZACIÓN DE PRECIOS
# ====================================================================

def update_prices():
    """Actualiza precios en tiempo real con análisis inteligente"""
    last_prediction_ts = 0.0
    last_error_log_ts = 0.0
    while True:
        try:
            # Refresco periódico de memoria global con histórico de días previos.
            refresh_global_market_memory(force=False)

            with PRICE_LOCK:
                market = MARKET_DATA[TRADING_SYMBOL]
                last = market['price_history'][-1]
                if TRADING_SYMBOL == 'XAUUSD':
                    change = random.uniform(-market['volatility'] * 1.2, market['volatility'] * 1.2)
                else:
                    change = random.uniform(-market['volatility'], market['volatility'])

                trend_bias = random.uniform(-market['volatility'] * 0.2, market['volatility'] * 0.2)
                new_price = last + change + trend_bias
                new_price = max(market['min_price'], min(market['max_price'], new_price))

                market['price_history'].append(new_price)
                if len(market['price_history']) > 200:
                    market['price_history'].pop(0)
                market['price'] = new_price

                TRADING_DATA['price'] = new_price
                TRADING_DATA['price_history'] = market['price_history']
                TRADING_DATA['symbol'] = TRADING_SYMBOL

                # Alerta de volatilidad direccional para vigilancia visual del mercado.
                TRADING_DATA['volatility_alert'] = build_volatility_alert(TRADING_SYMBOL, TRADING_DATA['price_history'])

                # Caché de análisis para acelerar endpoints y UI.
                analysis = {'action': 'ESPERA', 'confidence': 0.0, 'rsi': 50.0, 'macd': 0.0, 'bb': '0-0', 'trend': 'LATERAL', 'pattern': {}}
                if len(TRADING_DATA['price_history']) >= 50:
                    analysis = analyze_signal(TRADING_DATA['price_history'])

                    # Ajustar señal con contexto global multi-símbolo.
                    global_bias = AI_LEARNING_DB.get('global_market_bias', {})
                    bias_trend = global_bias.get('trend', 'NEUTRAL')
                    if bias_trend == 'ALCISTA' and analysis['action'] == 'COMPRA':
                        analysis['confidence'] = min(0.99, analysis['confidence'] + 0.03)
                    elif bias_trend == 'BAJISTA' and analysis['action'] == 'VENTA':
                        analysis['confidence'] = min(0.99, analysis['confidence'] + 0.03)

                TRADING_DATA['analysis_cache'] = {
                    'ts': time.time(),
                    'symbol': TRADING_SYMBOL,
                    'data': analysis
                }
                TRADING_DATA['signal'] = {'action': analysis['action'], 'confidence': analysis['confidence']}
                
                # Aprendizaje continuo desde el mercado
                learn_from_market_cycle()

                # Registrar análisis para aprendizaje con refuerzo más rápido
                AI_LEARNING_DB['learning_score'] += analysis['confidence'] * 0.07
                if analysis['action'] != 'ESPERA':
                    pattern = analysis['pattern'].copy()
                    pattern['success_rate'] = min(1.0, 0.55 + analysis['confidence'] * 0.45)
                    AI_LEARNING_DB['successful_patterns'].append(pattern)

                # Sistema automático de trading inteligente (solo cuando auto está activo)
                auto_mode = TRADING_DATA['auto_enabled'] and len(TRADING_DATA['price_history']) >= 50
                if auto_mode:
                    prediction_signal = None
                    try:
                        if TRADING_DATA.get('use_prediction', True) and PREDICTION_AVAILABLE and prediction_engine and (time.time() - last_prediction_ts) > 2.0:
                            pred_sig = prediction_engine.get_prediction_signal(
                                TRADING_DATA['price_history'],
                                analysis['rsi'],
                                analysis['macd'],
                                float(analysis['bb'].split('-')[1]),
                                float(analysis['bb'].split('-')[0])
                            )
                            prediction_signal = pred_sig
                            last_prediction_ts = time.time()
                    except Exception:
                        prediction_signal = None

                    # Combinar señales: si concuerdan, subir confianza; si no, ajustar según modelo predictivo.
                    combined_confidence = analysis['confidence']
                    combined_source = 'ANALYSIS'

                    if prediction_signal:
                        pred_dir = str(prediction_signal.get('direction', '')).upper()
                        if any(term in pred_dir for term in ('ALCISTA', 'ALZA', 'UP', 'COMPRA', 'BUY')):
                            pred_action = 'COMPRA'
                        elif any(term in pred_dir for term in ('BAJISTA', 'BAJA', 'DOWN', 'VENTA', 'SELL')):
                            pred_action = 'VENTA'
                        else:
                            pred_action = None

                        if not pred_action:
                            sigtxt = str(prediction_signal.get('signal', '')).upper()
                            if 'COMPRA' in sigtxt or 'BUY' in sigtxt:
                                pred_action = 'COMPRA'
                            elif 'VENTA' in sigtxt or 'SELL' in sigtxt:
                                pred_action = 'VENTA'

                        pred_conf = min(0.99, float(prediction_signal.get('confidence', 0) or 0))
                        if pred_action and pred_action == analysis['action']:
                            combined_confidence = min(0.99, max(analysis['confidence'], pred_conf) * 0.95)
                            combined_source = 'MIX'
                        elif pred_action:
                            combined_confidence = min(0.99, max(0.15, (analysis['confidence'] + pred_conf) / 2 * 0.8))
                            combined_source = 'MIX_PARTIAL'
                        else:
                            combined_confidence = min(0.99, analysis['confidence'] * 0.8)
                            combined_source = 'ANALYSIS_ONLY'

                    # Ejecutar operación automática solo si la confianza combinada supera el umbral
                    if analysis['action'] != 'ESPERA' and combined_confidence > AI_LEARNING_DB['confidence_threshold']:
                        trade_info = None
                        # Priorizar ejecución por MT5 cuando esté disponible
                        if MT5_AVAILABLE and ensure_mt5_connected():
                            mt5_action = normalize_trade_action(analysis['action'])
                            result = place_mt5_order(mt5_action)
                            if result.get('success'):
                                trade_info = {
                                    'id': len(TRADING_DATA['trades']) + len(TRADING_DATA['closed_trades']) + 1,
                                    'action': analysis['action'],
                                    'entry': result['price'],
                                    'size': result['volume'],
                                    'pl': 0,
                                    'confidence': combined_confidence,
                                    'ticket': result.get('ticket'),
                                    'source': 'MT5',
                                    'note': combined_source
                                }
                        if trade_info is None:
                            trade_info = {
                                'id': len(TRADING_DATA['trades']) + len(TRADING_DATA['closed_trades']) + 1,
                                'action': analysis['action'],
                                'entry': TRADING_DATA['price'],
                                'size': 0.1,
                                'pl': 0,
                                'confidence': combined_confidence,
                                'source': 'SIM',
                                'note': combined_source
                            }
                        TRADING_DATA['trades'].append(trade_info)
                        TRADING_DATA['trades_open'] = len(TRADING_DATA['trades'])
                        AI_LEARNING_DB['trade_history'].append(trade_info)

                        # Registrar en histórico
                        TRADING_DATA['chat_history'].append({
                            'timestamp': datetime.now().isoformat(),
                            'sender': 'IA',
                            'text': f'Operación automática: {analysis["action"]} a {trade_info["entry"]:.4f} (Confianza combinada: {combined_confidence:.1%}). Fuente: {combined_source}'
                        })
            
        except Exception as e:
            now = time.time()
            # Evitar spam de logs y bucles calientes en caso de error continuo.
            if now - last_error_log_ts > 3:
                print(f"Error actualizando precios: {e}")
                last_error_log_ts = now
        finally:
            time.sleep(1)


def find_mt5_terminal_path():
    """Detecta rutas de instalación de MetaTrader 5 en Windows de forma automática."""
    roots = []
    for env_var in ['PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA', 'USERPROFILE']:
        value = os.environ.get(env_var)
        if value:
            roots.append(value)

    for root in roots:
        if not root:
            continue
        for base_dir in [os.path.join(root, 'MetaTrader 5'), os.path.join(root, 'MetaTrader5'), root]:
            if not os.path.isdir(base_dir):
                continue
            for dirpath, _, filenames in os.walk(base_dir):
                for filename in filenames:
                    if filename.lower() in {'terminal64.exe', 'terminal.exe'}:
                        full_path = os.path.join(dirpath, filename)
                        if os.path.isfile(full_path):
                            return full_path

    candidates = [
        os.path.join(os.environ.get('PROGRAMFILES', ''), 'MetaTrader 5', 'terminal64.exe'),
        os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'MetaTrader 5', 'terminal64.exe'),
        os.path.join(os.environ.get('PROGRAMFILES', ''), 'MetaTrader 5', 'terminal.exe'),
        os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'MetaTrader 5', 'terminal.exe'),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'MetaTrader 5', 'terminal64.exe'),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'MetaTrader 5', 'terminal.exe'),
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    return None


def resolve_mt5_terminal_path(path_value):
    """Normaliza la ruta de MT5 al ejecutable del terminal que espera MetaTrader5.initialize()."""
    if not path_value:
        return None

    candidate = str(path_value).strip().strip('"').strip("'")
    if not candidate:
        return None

    if os.path.isfile(candidate):
        return candidate

    if os.path.isdir(candidate):
        for exe_name in ['terminal64.exe', 'terminal.exe']:
            exe_path = os.path.join(candidate, exe_name)
            if os.path.isfile(exe_path):
                return exe_path
        return candidate

    return candidate


def mt5_initialize_with_fallback(path=None):
    """Inicializa MT5 usando la ruta indicada y cae a inicialización estándar si hay autorización fallida."""
    try:
        if path:
            result = mt5.initialize(path=path)
            if result:
                return True
            last_error = mt5.last_error()
            error_text = ' '.join(map(str, last_error)) if isinstance(last_error, tuple) else str(last_error)
            if 'Authorization failed' in error_text or (isinstance(last_error, tuple) and last_error[0] == -6):
                try:
                    mt5.shutdown()
                except Exception:
                    pass
                return mt5.initialize()
            return False
        return mt5.initialize()
    except Exception:
        return False


def initialize_mt5(login=None, password=None, server=None, path=None):
    """Inicializa MT5 conectándose directamente al terminal abierto sin login."""
    global MT5_CONNECTED, MT5_ACCOUNT_INFO, MT5_CREDENTIALS
    if not MT5_AVAILABLE:
        return {'success': False, 'error': 'MetaTrader5 package no instalado'}

    try:
        # Reinicia cualquier sesión MT5 anterior para evitar estados inválidos
        try:
            mt5.shutdown()
        except Exception:
            pass

        # Intenta inicializar con la ruta si está disponible
        if path:
            normalized_path = resolve_mt5_terminal_path(path)
            if normalized_path and os.path.isfile(normalized_path):
                result_init = mt5_initialize_with_fallback(normalized_path)
            else:
                result_init = mt5.initialize()
        else:
            auto_path = find_mt5_terminal_path()
            if auto_path:
                normalized_path = resolve_mt5_terminal_path(auto_path)
                result_init = mt5_initialize_with_fallback(normalized_path)
            else:
                result_init = mt5.initialize()

        if not result_init:
            last_error = mt5.last_error()
            if isinstance(last_error, tuple):
                last_error = ' - '.join(map(str, last_error))
            msg = 'Error inicializando MT5. Asegúrate de que MetaTrader 5 está abierto y logueado en tu PC.'
            if last_error:
                msg += f' Detalle: {last_error}'
            return {'success': False, 'error': msg}

        # Obtener info de cuenta sin hacer login
        account_info = mt5.account_info()
        if account_info is None:
            return {'success': False, 'error': 'MT5 está iniciado pero no logueado. Por favor, abre MetaTrader 5 y entra a tu cuenta.'}

        MT5_CONNECTED = True
        MT5_ACCOUNT_INFO = account_info
        MT5_CREDENTIALS = {
            'login': str(account_info.login),
            'path': path or find_mt5_terminal_path()
        }
        return {'success': True, 'message': f'Conectado a MT5 cuenta {account_info.login}'}
    except Exception as e:
        try:
            mt5.shutdown()
        except Exception:
            pass
        return {'success': False, 'error': f'Error MT5: {str(e)}'}


def ensure_mt5_connected():
    """Verifica el estado MT5 y reconecta si es necesario usando credenciales configuradas."""
    global MT5_CONNECTED, MT5_ACCOUNT_INFO

    if not MT5_AVAILABLE:
        return False

    if MT5_CONNECTED:
        if MT5_ACCOUNT_INFO is not None:
            return True
        try:
            info = mt5.account_info()
            if info is not None:
                MT5_ACCOUNT_INFO = info
                return True
        except Exception:
            pass
        MT5_CONNECTED = False
        MT5_ACCOUNT_INFO = None

    if not MT5_CREDENTIALS.get('login') or not MT5_CREDENTIALS.get('password') or not MT5_CREDENTIALS.get('server'):
        return False

    result = initialize_mt5()
    return result.get('success', False)


def get_candle_data(max_candles=40, use_mt5=False):
    """Devuelve datos de velas para el gráfico."""
    if use_mt5 and MT5_AVAILABLE and MT5_CONNECTED:
        try:
            symbol = TRADING_SYMBOL or 'EURUSD'
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, max_candles)
            if rates is not None and len(rates) > 0:
                candles = []
                for rate in rates:
                    candles.append({
                        'x': datetime.fromtimestamp(rate.time).isoformat(),
                        'o': float(rate.open),
                        'h': float(rate.high),
                        'l': float(rate.low),
                        'c': float(rate.close)
                    })
                return candles[::-1]
        except Exception:
            pass

    prices = TRADING_DATA['price_history'][-max_candles * 4:]
    if not prices:
        return []

    candles = []
    for i in range(0, len(prices), 4):
        chunk = prices[i:i+4]
        if len(chunk) < 4:
            break
        candles.append({
            'x': datetime.now().isoformat(),
            'o': float(chunk[0]),
            'h': float(max(chunk)),
            'l': float(min(chunk)),
            'c': float(chunk[-1])
        })
    return candles[-max_candles:]


def mt5_status(auto_reconnect=False, cached_only=False):
    """Devuelve estado y datos de la cuenta MT5"""
    global MT5_CONNECTED, MT5_ACCOUNT_INFO
    if not MT5_AVAILABLE:
        return {'connected': False, 'error': 'MetaTrader5 package no instalado'}

    if auto_reconnect and not MT5_CONNECTED and MT5_CREDENTIALS.get('login'):
        ensure_mt5_connected()

    if not MT5_CONNECTED:
        return {'connected': False, 'error': 'No conectado a MT5'}

    if MT5_ACCOUNT_INFO is not None:
        info = MT5_ACCOUNT_INFO
        return {
            'connected': True,
            'login': str(info.login),
            'server': str(info.server),
            'balance': float(info.balance),
            'equity': float(info.equity),
            'profit': float(info.profit) if hasattr(info, 'profit') else float(info.equity - info.balance),
            'currency': str(info.currency)
        }

    if cached_only:
        return {'connected': bool(MT5_CONNECTED), 'error': 'Estado MT5 en caché'}

    try:
        info = mt5.account_info()
        if info is None:
            MT5_CONNECTED = False
            return {'connected': False, 'error': 'Sesión MT5 cerrada'}
        MT5_ACCOUNT_INFO = info
        return {
            'connected': True,
            'login': str(info.login),
            'server': str(info.server),
            'balance': float(info.balance),
            'equity': float(info.equity),
            'profit': float(info.profit) if hasattr(info, 'profit') else float(info.equity - info.balance),
            'currency': str(info.currency)
        }
    except Exception as e:
        if MT5_ACCOUNT_INFO is not None:
            info = MT5_ACCOUNT_INFO
            return {
                'connected': True,
                'login': str(info.login),
                'server': str(info.server),
                'balance': float(info.balance),
                'equity': float(info.equity),
                'profit': float(info.profit) if hasattr(info, 'profit') else float(info.equity - info.balance),
                'currency': str(info.currency)
            }
        MT5_CONNECTED = False
        return {'connected': False, 'error': f'Error al obtener info MT5: {str(e)}'}


def place_mt5_order(action):
    """Envía orden a MT5"""
    if not MT5_AVAILABLE:
        return {'success': False, 'error': 'MetaTrader5 no disponible'}

    if not ensure_mt5_connected():
        return {'success': False, 'error': 'No conectado a MT5. Verifica las credenciales y la ruta de MT5.'}

    symbol = TRADING_SYMBOL or 'EURUSD'
    volume = DEFAULT_VOLUME or 0.01
    if not mt5.symbol_select(symbol, True):
        return {'success': False, 'error': f'No se pudo seleccionar el símbolo {symbol} en MT5'}
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return {'success': False, 'error': f'No hay ticks disponibles para {symbol}'}
    price = float(tick.ask) if action == 'BUY' else float(tick.bid)
    order_type = mt5.ORDER_TYPE_BUY if action == 'BUY' else mt5.ORDER_TYPE_SELL
    deviation = 20

    request = {
        'action': mt5.TRADE_ACTION_DEAL,
        'symbol': symbol,
        'volume': float(volume),
        'type': order_type,
        'price': float(price),
        'deviation': deviation,
        'magic': 234000,
        'comment': f'AI {action}',
        'type_time': mt5.ORDER_TIME_GTC,
        'type_filling': mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result is None:
        last_error = mt5.last_error()
        last_error = ' - '.join(map(str, last_error)) if isinstance(last_error, tuple) else str(last_error)
        return {'success': False, 'error': f'Orden MT5 no enviada. Error MT5: {last_error}'}

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        error_comment = getattr(result, 'comment', '')
        last_error = mt5.last_error()
        last_error = ' - '.join(map(str, last_error)) if isinstance(last_error, tuple) else str(last_error)
        return {
            'success': False,
            'error': f'Orden MT5 fallida: {result.retcode} - {error_comment}'.strip(),
            'mt5_error': last_error
        }

    return {'success': True, 'ticket': int(result.order), 'price': float(price), 'volume': float(volume)}


def get_current_price_for_symbol(symbol):
    """Devuelve el precio actual utilizable para calcular P/L (ask/bid según dirección)."""
    try:
        if MT5_AVAILABLE and MT5_CONNECTED:
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                return float(tick.bid), float(tick.ask)
    except Exception:
        pass
    # Fallback a los datos simulados
    s = MARKET_DATA.get(symbol, {})
    price = s.get('price') if s else TRADING_DATA.get('price')
    if price is None:
        price = TRADING_DATA.get('price', 0)
    # Return bid, ask as same value
    return float(price), float(price)


def compute_trade_profit(trade):
    """Calcula el P/L aproximado de un trade (USD). Usa tamaño, símbolo y precios actuales.
    Retorna un float con la ganancia (positivo si hay beneficio para cerrar ahora).
    """
    try:
        symbol = trade.get('symbol', TRADING_SYMBOL)
        action = trade.get('action', 'BUY').upper()
        entry = float(trade.get('entry', 0.0))
        size = float(trade.get('size', DEFAULT_VOLUME or 0.01))

        bid, ask = get_current_price_for_symbol(symbol)
        # price to use when closing: if we are long (BUY) we would sell at bid; if short, buy at ask
        price_now = bid if action == 'BUY' else ask

        # Determine contract size: prefer MT5 symbol info if available
        contract_size = None
        try:
            if MT5_AVAILABLE and MT5_CONNECTED:
                info = mt5.symbol_info(symbol)
                if info and hasattr(info, 'trade_contract_size'):
                    contract_size = float(info.trade_contract_size)
        except Exception:
            contract_size = None

        if contract_size is None:
            # reasonable defaults
            contract_size = 100000.0 if symbol.endswith('USD') and symbol != 'XAUUSD' else 100.0

        # profit calculation
        if action == 'BUY':
            profit = (price_now - entry) * size * contract_size
        else:
            profit = (entry - price_now) * size * contract_size

        return float(profit)
    except Exception:
        return 0.0


def close_all_mt5_positions():
    """Cierra todas las posiciones abiertas en MT5 para el símbolo configurado"""
    if not MT5_AVAILABLE or not MT5_CONNECTED:
        return {'success': False, 'error': 'MT5 no conectado'}

    symbol = TRADING_SYMBOL or 'EURUSD'
    positions = mt5.positions_get(symbol=symbol)
    if positions is None or len(positions) == 0:
        return {'success': True, 'closed': 0}

    closed = 0
    closed_tickets = []
    # Only close positions that have at least $1 profit
    for pos in positions:
        try:
            profit = float(getattr(pos, 'profit', 0.0))
        except Exception:
            profit = 0.0
        if profit < 1.0:
            # Skip positions that do not reach minimum profit threshold
            continue

        order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            continue
        price = float(tick.bid) if order_type == mt5.ORDER_TYPE_SELL else float(tick.ask)
        request = {
            'action': mt5.TRADE_ACTION_DEAL,
            'symbol': symbol,
            'volume': float(pos.volume),
            'type': order_type,
            'position': int(pos.ticket),
            'price': float(price),
            'deviation': 20,
            'magic': 234000,
            'comment': f'Close pos {pos.ticket}',
            'type_time': mt5.ORDER_TIME_GTC,
            'type_filling': mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result and getattr(result, 'retcode', None) == mt5.TRADE_RETCODE_DONE:
            closed += 1
            try:
                closed_tickets.append(int(pos.ticket))
            except Exception:
                pass

    return {'success': True, 'closed': closed, 'closed_tickets': closed_tickets}


def close_mt5_position_by_ticket(ticket):
    """Cierra una posición específica por ticket si cumple el umbral mínimo de ganancia ($1)."""
    try:
        if not MT5_AVAILABLE or not MT5_CONNECTED:
            return {'success': False, 'error': 'MT5 no conectado'}

        positions = mt5.positions_get()
        if not positions:
            return {'success': False, 'error': 'No hay posiciones abiertas'}

        for pos in positions:
            if int(pos.ticket) == int(ticket):
                profit = float(getattr(pos, 'profit', 0.0))
                if profit < 1.0:
                    return {'success': False, 'error': 'La posición no alcanza el mínimo de $1 de ganancia'}

                order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
                symbol = pos.symbol
                tick = mt5.symbol_info_tick(symbol)
                if not tick:
                    return {'success': False, 'error': 'No se pudo obtener precio para cerrar'}
                price = float(tick.bid) if order_type == mt5.ORDER_TYPE_SELL else float(tick.ask)
                request = {
                    'action': mt5.TRADE_ACTION_DEAL,
                    'symbol': symbol,
                    'volume': float(pos.volume),
                    'type': order_type,
                    'position': int(pos.ticket),
                    'price': float(price),
                    'deviation': 20,
                    'magic': 234000,
                    'comment': f'Close pos {pos.ticket}',
                    'type_time': mt5.ORDER_TIME_GTC,
                    'type_filling': mt5.ORDER_FILLING_IOC,
                }
                result = mt5.order_send(request)
                if result and getattr(result, 'retcode', None) == mt5.TRADE_RETCODE_DONE:
                    return {'success': True, 'ticket': int(pos.ticket)}
                return {'success': False, 'error': f'Error cerrando posición: {getattr(result, "comment", "")}' }
        return {'success': False, 'error': 'Ticket no encontrado'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_mt5_positions_snapshot(symbol=None):
    """Obtiene posiciones abiertas desde MT5 con metadatos útiles para UI."""
    try:
        if not MT5_AVAILABLE:
            return {'success': False, 'error': 'MetaTrader5 no disponible', 'positions': [], 'count': 0}

        if not ensure_mt5_connected():
            return {'success': False, 'error': 'MT5 no conectado', 'positions': [], 'count': 0}

        positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
        if positions is None:
            return {'success': False, 'error': 'No se pudieron obtener posiciones MT5', 'positions': [], 'count': 0}

        items = []
        for pos in positions:
            pos_symbol = str(getattr(pos, 'symbol', TRADING_SYMBOL))
            pos_type = int(getattr(pos, 'type', mt5.ORDER_TYPE_BUY))
            action = 'BUY' if pos_type == mt5.ORDER_TYPE_BUY else 'SELL'
            profit = float(getattr(pos, 'profit', 0.0))
            items.append({
                'ticket': int(getattr(pos, 'ticket', 0)),
                'symbol': pos_symbol,
                'action': action,
                'volume': float(getattr(pos, 'volume', 0.0)),
                'entry': float(getattr(pos, 'price_open', 0.0)),
                'current_price': float(getattr(pos, 'price_current', 0.0)),
                'profit': profit,
                'can_close': profit >= 1.0,
            })

        return {'success': True, 'positions': items, 'count': len(items)}
    except Exception as e:
        return {'success': False, 'error': str(e), 'positions': [], 'count': 0}


def _first_business_day(year, month):
    d = datetime(year, month, 1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def _last_business_day(year, month):
    if month == 12:
        d = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        d = datetime(year, month + 1, 1) - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def _first_friday(year, month):
    d = datetime(year, month, 1)
    while d.weekday() != 4:
        d += timedelta(days=1)
    return d


def _next_year_month(year, month):
    return (year + 1, 1) if month == 12 else (year, month + 1)


def _scheduled_event_datetime(kind, now_utc):
    year, month = now_utc.year, now_utc.month

    if kind == 'NFP':
        base = _first_friday(year, month)
        event = datetime(base.year, base.month, base.day, 12, 30)
        if event <= now_utc:
            y2, m2 = _next_year_month(year, month)
            base = _first_friday(y2, m2)
            event = datetime(base.year, base.month, base.day, 12, 30)
        return event

    if kind == 'ADP':
        base = _first_friday(year, month) - timedelta(days=2)
        event = datetime(base.year, base.month, base.day, 12, 15)
        if event <= now_utc:
            y2, m2 = _next_year_month(year, month)
            base = _first_friday(y2, m2) - timedelta(days=2)
            event = datetime(base.year, base.month, base.day, 12, 15)
        return event

    if kind == 'CPI':
        base = datetime(year, month, 12)
        while base.weekday() >= 5:
            base += timedelta(days=1)
        event = datetime(base.year, base.month, base.day, 12, 30)
        if event <= now_utc:
            y2, m2 = _next_year_month(year, month)
            base = datetime(y2, m2, 12)
            while base.weekday() >= 5:
                base += timedelta(days=1)
            event = datetime(base.year, base.month, base.day, 12, 30)
        return event

    if kind == 'PCE':
        base = _last_business_day(year, month)
        event = datetime(base.year, base.month, base.day, 12, 30)
        if event <= now_utc:
            y2, m2 = _next_year_month(year, month)
            base = _last_business_day(y2, m2)
            event = datetime(base.year, base.month, base.day, 12, 30)
        return event

    if kind == 'ISM':
        base = _first_business_day(year, month)
        event = datetime(base.year, base.month, base.day, 14, 0)
        if event <= now_utc:
            y2, m2 = _next_year_month(year, month)
            base = _first_business_day(y2, m2)
            event = datetime(base.year, base.month, base.day, 14, 0)
        return event

    if kind == 'FOMC':
        fomc_dates = [
            datetime(2026, 1, 28, 19, 0),
            datetime(2026, 3, 18, 18, 0),
            datetime(2026, 4, 29, 18, 0),
            datetime(2026, 6, 17, 18, 0),
            datetime(2026, 7, 29, 18, 0),
            datetime(2026, 9, 16, 18, 0),
            datetime(2026, 11, 4, 19, 0),
            datetime(2026, 12, 16, 19, 0),
        ]
        for d in fomc_dates:
            if d > now_utc:
                return d
        return datetime(now_utc.year + 1, 1, 28, 19, 0)

    return now_utc + timedelta(days=1)


def build_macro_news_snapshot():
    now_utc = datetime.utcnow()
    macro_defs = [
        {
            'code': 'NFP',
            'label': 'NFP - Nonfarm Payrolls',
            'impact': 'ALTO',
            'hint': 'NFP fuerte suele favorecer USD y aumentar volatilidad en FX.'
        },
        {
            'code': 'CPI',
            'label': 'CPI - Inflación al Consumidor',
            'impact': 'ALTO',
            'hint': 'CPI alto puede elevar expectativas de tasas (sesgo USD alcista).'
        },
        {
            'code': 'PCE',
            'label': 'PCE - Inflación preferida de la FED',
            'impact': 'ALTO',
            'hint': 'PCE guía política monetaria; sorpresas mueven al dólar.'
        },
        {
            'code': 'FOMC/FED',
            'label': 'FOMC/FED - Decisión de Tasas',
            'impact': 'MUY ALTO',
            'hint': 'Evento clave de tasas y tono de la FED; riesgo de spikes fuertes.'
        },
        {
            'code': 'ISM',
            'label': 'ISM - Actividad Manufacturera',
            'impact': 'MEDIO',
            'hint': 'ISM mide ciclo económico y puede impactar apetito de riesgo.'
        },
        {
            'code': 'ADP',
            'label': 'ADP - Empleo Privado',
            'impact': 'MEDIO-ALTO',
            'hint': 'ADP suele anticipar sesgo laboral antes de NFP.'
        },
    ]

    kind_map = {
        'NFP': 'NFP',
        'CPI': 'CPI',
        'PCE': 'PCE',
        'FOMC/FED': 'FOMC',
        'ISM': 'ISM',
        'ADP': 'ADP',
    }

    events = []
    for item in macro_defs:
        dt = _scheduled_event_datetime(kind_map[item['code']], now_utc)
        eta_mins = max(0, int((dt - now_utc).total_seconds() // 60))
        events.append({
            'code': item['code'],
            'label': item['label'],
            'impact': item['impact'],
            'hint': item['hint'],
            'next_release_utc': dt.strftime('%Y-%m-%d %H:%M UTC'),
            'eta_minutes': eta_mins
        })

    events.sort(key=lambda e: e.get('eta_minutes', 10**9))
    return {
        'updated_at_utc': now_utc.strftime('%Y-%m-%d %H:%M:%S UTC'),
        'events': events
    }


price_thread = None

def start_background_services():
    global price_thread
    if price_thread is None or not price_thread.is_alive():
        price_thread = threading.Thread(target=update_prices, daemon=True)
        price_thread.start()

# ====================================================================
# RUTAS
# ====================================================================

@app.route('/')
def index():
    """Dashboard principal"""
    return render_dashboard_response()


@app.route('/dashboard')
def dashboard():
    """Ruta alternativa para el panel de control"""
    return render_dashboard_response()


@app.route('/dashboard-live')
def dashboard_live():
    """Ruta explícita para evitar caches antiguas de intermediarios."""
    return render_dashboard_response()


@app.route('/api/news/macro')
def api_news_macro():
    """Panel de noticias macro relevantes para FX y metales."""
    return jsonify({'success': True, 'news': build_macro_news_snapshot()})


def render_dashboard_response():
    response = make_response(render_template_string(DASHBOARD_HTML))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/api/status')
def api_status():
    """Obtener estado del trading"""
    # Endpoint ultra-rápido y con datos serializables explícitos.
    symbol = str(TRADING_DATA.get('symbol', TRADING_SYMBOL))
    prices = TRADING_DATA.get('price_history', [])
    price_value = TRADING_DATA.get('price', MARKET_DATA.get(symbol, {}).get('price', 0))
    analysis_cache = TRADING_DATA.get('analysis_cache', {'ts': 0.0, 'data': {'action': 'ESPERA', 'confidence': 0.0}})

    try:
        candles = get_candle_data(40, use_mt5=False)
    except Exception:
        candles = []

    raw_trades = TRADING_DATA.get('trades', [])
    trades = []
    for t in raw_trades[-60:]:
        trades.append({
            'id': int(t.get('id', 0)) if isinstance(t, dict) else 0,
            'action': str(t.get('action', '')) if isinstance(t, dict) else '',
            'entry': float(t.get('entry', 0.0)) if isinstance(t, dict) else 0.0,
            'size': float(t.get('size', 0.0)) if isinstance(t, dict) else 0.0,
            'pl': float(t.get('pl', 0.0)) if isinstance(t, dict) else 0.0,
            'ticket': int(t.get('ticket', 0)) if isinstance(t, dict) and t.get('ticket') else None,
            'symbol': str(t.get('symbol', symbol)) if isinstance(t, dict) else symbol,
            'source': str(t.get('source', 'SIM')) if isinstance(t, dict) else 'SIM',
        })

    mt5_state = {
        'connected': bool(MT5_CONNECTED),
        'login': str(getattr(MT5_ACCOUNT_INFO, 'login', '-')) if MT5_ACCOUNT_INFO else '-',
        'balance': float(getattr(MT5_ACCOUNT_INFO, 'balance', 0.0)) if MT5_ACCOUNT_INFO else 0.0,
        'equity': float(getattr(MT5_ACCOUNT_INFO, 'equity', 0.0)) if MT5_ACCOUNT_INFO else 0.0,
    }

    return jsonify({
        'symbol': symbol,
        'price': float(price_value) if price_value is not None else 0.0,
        'balance': float(TRADING_DATA.get('balance', 0.0)),
        'equity': float(TRADING_DATA.get('equity', 0.0)),
        'trades_open': int(TRADING_DATA.get('trades_open', 0)),
        'trades': trades,
        'auto_enabled': bool(TRADING_DATA.get('auto_enabled', False)),
        'use_prediction': bool(TRADING_DATA.get('use_prediction', True)),
        'signal': TRADING_DATA.get('signal', {'action': 'ESPERA', 'confidence': 0.0}),
        'analysis': analysis_cache.get('data', {}),
        'analysis_ts': float(analysis_cache.get('ts', 0.0) or 0.0),
        'volatility_alert': TRADING_DATA.get('volatility_alert', {}),
        'global_market_bias': AI_LEARNING_DB.get('global_market_bias', {'trend': 'NEUTRAL', 'score': 0.0}),
        'prices': [float(p) for p in (prices[-30:] if prices else [])],
        'candles': candles,
        'closed_count': int(len(TRADING_DATA.get('closed_trades', []))),
        'mt5': mt5_state
    })


@app.route('/api/ping')
def api_ping():
    return jsonify({'ok': True, 'ts': time.time()})


@app.route('/api/symbol', methods=['GET', 'POST'])
def api_symbol():
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        # Blindaje: evita cambios no intencionales provenientes de requests externos.
        if data.get('manual') is not True:
            return jsonify({'success': False, 'error': 'Cambio de símbolo rechazado: requiere acción manual.'}), 400

        symbol = str(data.get('symbol', '')).upper()
        if symbol not in MARKET_DATA:
            return jsonify({'success': False, 'error': 'Símbolo inválido'}), 400

        global TRADING_SYMBOL
        with PRICE_LOCK:
            TRADING_SYMBOL = symbol
            TRADING_DATA['symbol'] = symbol
            TRADING_DATA['price'] = MARKET_DATA[symbol]['price']
            TRADING_DATA['price_history'] = MARKET_DATA[symbol]['price_history']

            # Precalcular respuesta para que el frontend actualice el gráfico al instante.
            status_payload = {
                'success': True,
                'symbol': symbol,
                'price': TRADING_DATA['price'],
                'prices': TRADING_DATA['price_history'][-30:],
                'candles': get_candle_data(40)
            }

        return jsonify(status_payload)

    return jsonify({'symbol': TRADING_SYMBOL, 'available_symbols': list(MARKET_DATA.keys())})


@app.route('/api/mt5/connect', methods=['POST'])
def api_mt5_connect():
    """Conecta a MT5 directamente sin credenciales - asume que MT5 ya está abierto y logueado."""
    result = initialize_mt5()
    if result.get('success'):
        mt5_state = mt5_status() if MT5_AVAILABLE else {'connected': False, 'error': 'MetaTrader5 package no instalado'}
        response = {**result, 'mt5': mt5_state}
        return jsonify(response)
    return jsonify(result), 400


@app.route('/api/mt5/status')
def api_mt5_status():
    return jsonify(mt5_status(auto_reconnect=True, cached_only=False))


@app.route('/api/mt5/positions')
def api_mt5_positions():
    symbol = request.args.get('symbol', '').upper() or None
    data = get_mt5_positions_snapshot(symbol=symbol)
    if data.get('success'):
        return jsonify(data)
    return jsonify(data), 400


@app.route('/api/mt5/close-position', methods=['POST'])
def api_mt5_close_position():
    data = request.get_json(silent=True) or {}
    ticket = data.get('ticket')
    if not ticket:
        return jsonify({'success': False, 'error': 'Falta ticket'}), 400

    result = close_mt5_position_by_ticket(ticket)
    if result.get('success'):
        # synchronize TRADING_DATA
        with PRICE_LOCK:
            TRADING_DATA['trades'] = [t for t in TRADING_DATA['trades'] if not (t.get('ticket') and int(t.get('ticket')) == int(ticket))]
            TRADING_DATA['trades_open'] = len(TRADING_DATA['trades'])
        return jsonify({'success': True, 'ticket': int(ticket)})
    return jsonify(result), 400


def save_mt5_config_file(login, password, server, path=None):
    """Guarda las credenciales MT5 en el archivo mt5_config.py para uso persistente."""
    global MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, MT5_PATH, MT5_CREDENTIALS
    cfg_path = os.path.join(os.path.dirname(__file__), 'mt5_config.py')
    try:
        # Decide si login es numérico
        try:
            login_val = int(str(login).strip())
            login_repr = str(login_val)
        except Exception:
            login_repr = '"' + str(login).strip().replace('"', '\\"') + '"'

        password_repr = '"' + str(password).replace('"', '\\"') + '"'
        server_repr = '"' + str(server).replace('"', '\\"') + '"'
        if not path:
            auto_path = find_mt5_terminal_path()
            if auto_path:
                path = resolve_mt5_terminal_path(auto_path)
                path_repr = 'r"' + str(path).replace('"', '\\"') + '"'
            else:
                path_repr = 'None'
        else:
            path = resolve_mt5_terminal_path(path)
            path_repr = 'r"' + str(path).replace('"', '\\"') + '"'

        content = (
            "#!/usr/bin/env python3\n"
            '"""MetaTrader5 Configuration File (auto-generated)"""\n\n'
            "# Auto-generated MT5 config\n"
            f"MT5_LOGIN = {login_repr}\n"
            f"MT5_PASSWORD = {password_repr}\n"
            f"MT5_SERVER = {server_repr}\n"
            f"MT5_PATH = {path_repr}\n\n"
            "# Defaults (preserved from original template)\n"
            "TRADING_SYMBOL = \"EURUSD\"\n"
            "DEFAULT_VOLUME = 0.01\n"
            "USE_REAL_ACCOUNT = False\n"
            "TIMEFRAME_MINUTES = 1\n"
            "CANDLE_COUNT = 100\n"
        )

        with open(cfg_path, 'w', encoding='utf-8') as fh:
            fh.write(content)

        MT5_LOGIN = str(login).strip()
        MT5_PASSWORD = str(password)
        MT5_SERVER = str(server).strip()
        MT5_PATH = str(path).strip() if path else MT5_PATH
        MT5_CREDENTIALS = {
            'login': MT5_LOGIN,
            'password': MT5_PASSWORD,
            'server': MT5_SERVER,
            'path': MT5_PATH
        }

        return True, f'Archivo actualizado: {cfg_path}'
    except Exception as e:
        return False, str(e)


@app.route('/api/mt5/save-config', methods=['POST'])
def api_mt5_save_config():
    data = request.get_json(silent=True) or {}
    login = data.get('login')
    password = data.get('password')
    server = data.get('server')
    path = data.get('path')

    if not all([login, password, server]):
        return jsonify({'success': False, 'error': 'Faltan campos: login, password o server'}), 400

    ok, msg = save_mt5_config_file(login, password, server, path)
    if ok:
        return jsonify({'success': True, 'message': msg})
    return jsonify({'success': False, 'error': msg}), 500


@app.route('/api/professional-analysis')
def api_professional_analysis():
    """Análisis profesional inteligente con indicadores técnicos avanzados y aprendizaje"""
    with PRICE_LOCK:
        prices = TRADING_DATA['price_history']
        cached = TRADING_DATA.get('analysis_cache', {}).get('data')
        
        if len(prices) < 20:
            return jsonify({
                'available': False,
                'reason': 'Insuficientes datos históricos (se necesitan 20+ precios)',
                'learning_progress': 0.0
            })
        
        # Usar caché si existe para reducir latencia de IA en frontend.
        if isinstance(cached, dict) and cached.get('action'):
            analysis = cached
        else:
            analysis = analyze_signal(prices)
        
        # Calcular indicadores avanzados
        rsi = analysis['rsi']
        learning_pct = min(100.0, AI_LEARNING_DB['learning_score'] * 10)
        
        volatility = 'ALTA' if abs(prices[-1] - prices[-5]) > 0.002 else 'BAJA'
        return jsonify({
            'available': True,
            'current_price': TRADING_DATA['price'],
            'signal': analysis['action'],
            'confidence': analysis['confidence'],
            'confidence_percent': round(analysis['confidence'] * 100, 1),
            'learning_progress': learning_pct,
            'global_market_trend': AI_LEARNING_DB.get('global_market_bias', {}).get('trend', 'NEUTRAL'),
            'volatility_alert': TRADING_DATA.get('volatility_alert', {}),
            'indicators': {
                'rsi': round(rsi, 2),
                'trend': analysis['trend'],
                'momentum': 'FUERTE' if abs(prices[-1] - prices[-5]) > 0.002 else 'DÉBIL',
                'bb_range': analysis['bb'],
                'macd_histogram': round(analysis['macd'], 6)
            },
            'volatility': volatility,
            'pattern': analysis['trend'],
            'successful_trades': len([t for t in AI_LEARNING_DB['trade_history'] if t.get('pl', 0) > 0]),
            'total_trades': len(AI_LEARNING_DB['trade_history']),
            'timestamp': datetime.now().isoformat()
        })


@app.route('/api/predict')
def api_predict():
    """Predicción de precio futuro y dirección usando PredictionEngine."""
    with PRICE_LOCK:
        prices = TRADING_DATA['price_history']
        try:
            if PREDICTION_AVAILABLE and prediction_engine:
                pred = prediction_engine.predict_next_price(prices, periods=5)
            else:
                # Fallback simple: usar analyze_signal para dar una predicción básica
                basic = analyze_signal(prices)
                const_move = 0.0002 if TRADING_DATA['symbol'] == 'EURUSD' else 0.5
                trend = 'BAJA' if prices[-1] < prices[-5] else 'ALZA'

                if basic['action'] == 'COMPRA':
                    pred_price = prices[-1] + const_move
                    direction = 'ALCISTA'
                    percent = round((const_move / prices[-1]) * 100, 4)
                elif basic['action'] == 'VENTA':
                    pred_price = prices[-1] - const_move
                    direction = 'BAJISTA'
                    percent = round((-const_move / prices[-1]) * 100, 4)
                elif trend == 'BAJA':
                    pred_price = prices[-1] - const_move
                    direction = 'BAJISTA'
                    percent = round((-const_move / prices[-1]) * 100, 4)
                else:
                    pred_price = prices[-1] + const_move
                    direction = 'ALCISTA'
                    percent = round((const_move / prices[-1]) * 100, 4)

                pred = {
                    'current_price': prices[-1],
                    'predicted_price': pred_price,
                    'price_change': pred_price - prices[-1],
                    'change_percent': percent,
                    'direction': direction,
                    'confidence': max(0.25, basic.get('confidence', 0.3)),
                    'methods': {'fallback': True},
                    'periods': 5,
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

        return jsonify({'success': True, 'prediction': pred})


@app.route('/api/predict/levels')
def api_predict_levels():
    """Devuelve niveles clave (soportes/resistencias, entry, SL, TP)."""
    with PRICE_LOCK:
        prices = TRADING_DATA['price_history']
        try:
            if PREDICTION_AVAILABLE and prediction_engine:
                levels = prediction_engine.get_trading_levels(prices)
            else:
                # Fallback: calcular niveles simples
                recent = prices[-50:] if len(prices) >= 50 else prices
                high = max(recent)
                low = min(recent)
                pivot = (high + low + recent[-1]) / 3 if recent else 0
                levels = {
                    'support': round((2 * pivot) - high, 6),
                    'resistance': round((2 * pivot) - low, 6),
                    'pivot': round(pivot, 6),
                    'entry': round(recent[-1], 6) if recent else 0,
                    'stop_loss': round(recent[-1] - 0.001, 6) if recent else 0,
                    'take_profit': round(recent[-1] + 0.002, 6) if recent else 0,
                }
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

        return jsonify({'success': True, 'levels': levels})


@app.route('/api/predict/signal')
def api_predict_signal():
    """Combina predicción y indicadores para una señal operativa recomendada."""
    with PRICE_LOCK:
        prices = TRADING_DATA['price_history']
        try:
            # Extraer indicadores básicos
            rsi = calculate_rsi(prices)
            macd = calculate_macd(prices)['histogram']
            bb = calculate_bollinger_bands(prices)

            if PREDICTION_AVAILABLE and prediction_engine:
                signal = prediction_engine.get_prediction_signal(prices, rsi, macd, bb['upper'], bb['lower'])
            else:
                basic = analyze_signal(prices)
                direction = 'NEUTRAL'
                if basic['action'] == 'COMPRA':
                    direction = 'ALCISTA'
                elif basic['action'] == 'VENTA':
                    direction = 'BAJISTA'

                signal = {
                    'signal': direction,
                    'direction': direction,
                    'strength': basic.get('confidence', 0.3) * 100,
                    'confidence': basic.get('confidence', 0.3),
                    'reasons': ['Fallback analysis used']
                }
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

        return jsonify({'success': True, 'prediction_signal': signal})


@app.route('/api/predict/one-shot', methods=['POST'])
def api_predict_one_shot():
    """Genera una prediccion avanzada unica, orientada a alta confianza y uso manual."""
    with PRICE_LOCK:
        now = time.time()
        last_ts = float(TRADING_DATA.get('last_one_shot_prediction_ts', 0.0) or 0.0)
        if now - last_ts < 4.0:
            wait_s = round(4.0 - (now - last_ts), 1)
            return jsonify({'success': False, 'error': f'Espera {wait_s}s antes de generar otra prediccion avanzada.'}), 429

        TRADING_DATA['last_one_shot_prediction_ts'] = now
        symbol = TRADING_DATA.get('symbol', TRADING_SYMBOL)
        prices = list(TRADING_DATA.get('price_history', []))

    result = generate_one_shot_prediction(symbol, prices)
    if not result.get('success'):
        return jsonify(result), 400
    return jsonify(result)


@app.route('/api/buy', methods=['POST'])
def api_buy():
    """Ejecutar compra"""
    with PRICE_LOCK:
        if MT5_AVAILABLE:
            if ensure_mt5_connected():
                result = place_mt5_order('BUY')
                if result.get('success'):
                    trade = {
                        'id': len(TRADING_DATA['trades']) + 1,
                        'symbol': TRADING_SYMBOL,
                        'action': 'BUY',
                        'entry': result['price'],
                        'size': result['volume'],
                        'pl': 0,
                        'ticket': result['ticket'],
                        'source': 'MT5'
                    }
                    TRADING_DATA['trades'].append(trade)
                    TRADING_DATA['trades_open'] = len(TRADING_DATA['trades'])
                    return jsonify({'success': True, 'trade': trade, 'price': result['price']})
                return jsonify({'success': False, 'error': result.get('error')}), 400
            return jsonify({'success': False, 'error': 'MT5 disponible pero no conectado. Conecta MT5 antes de ejecutar órdenes.'}), 400

        trade = {
            'id': len(TRADING_DATA['trades']) + 1,
            'symbol': TRADING_SYMBOL,
            'action': 'BUY',
            'entry': TRADING_DATA['price'],
            'size': 0.1,
            'pl': 0,
            'source': 'SIM'
        }
        TRADING_DATA['trades'].append(trade)
        TRADING_DATA['trades_open'] = len(TRADING_DATA['trades'])
        return jsonify({'success': True, 'trade': trade, 'price': TRADING_DATA['price']})


@app.route('/api/sell', methods=['POST'])
def api_sell():
    """Ejecutar venta"""
    with PRICE_LOCK:
        if MT5_AVAILABLE:
            if ensure_mt5_connected():
                result = place_mt5_order('SELL')
                if result.get('success'):
                    trade = {
                        'id': len(TRADING_DATA['trades']) + 1,
                        'symbol': TRADING_SYMBOL,
                        'action': 'SELL',
                        'entry': result['price'],
                        'size': result['volume'],
                        'pl': 0,
                        'ticket': result['ticket'],
                        'source': 'MT5'
                    }
                    TRADING_DATA['trades'].append(trade)
                    TRADING_DATA['trades_open'] = len(TRADING_DATA['trades'])
                    return jsonify({'success': True, 'trade': trade, 'price': result['price']})
                return jsonify({'success': False, 'error': result.get('error')}), 400
            return jsonify({'success': False, 'error': 'MT5 disponible pero no conectado. Conecta MT5 antes de ejecutar órdenes.'}), 400

        trade = {
            'id': len(TRADING_DATA['trades']) + 1,
            'symbol': TRADING_SYMBOL,
            'action': 'SELL',
            'entry': TRADING_DATA['price'],
            'size': 0.1,
            'pl': 0,
            'source': 'SIM'
        }
        TRADING_DATA['trades'].append(trade)
        TRADING_DATA['trades_open'] = len(TRADING_DATA['trades'])
        return jsonify({'success': True, 'trade': trade, 'price': TRADING_DATA['price']})


@app.route('/api/close-all', methods=['POST'])
def api_close_all():
    """Cerrar todos los trades"""
    with PRICE_LOCK:
        closed_total = 0
        closed_items = []

        # If MT5 is available and connected, ask MT5 to close qualifying positions
        if MT5_AVAILABLE:
            if not ensure_mt5_connected():
                return jsonify({'success': False, 'error': 'MT5 disponible pero no conectado. Conecta MT5 antes de cerrar posiciones.'}), 400

            result = close_all_mt5_positions()
            if not result.get('success'):
                return jsonify({'success': False, 'error': result.get('error')}), 400

            closed_total += int(result.get('closed', 0))
            closed_tickets = result.get('closed_tickets', [])

            # Remove closed trades from TRADING_DATA if they match ticket numbers
            remaining = []
            for t in TRADING_DATA['trades']:
                if 'ticket' in t and int(t.get('ticket', -1)) in closed_tickets:
                    closed_items.append(t)
                else:
                    remaining.append(t)

            TRADING_DATA['trades'] = remaining
            TRADING_DATA['closed_trades'].extend(closed_items)
            TRADING_DATA['trades_open'] = len(TRADING_DATA['trades'])

        else:
            # Simulated trades: only close those that reach minimum profit
            remaining = []
            for t in TRADING_DATA['trades']:
                profit = compute_trade_profit(t)
                if profit >= 1.0:
                    closed_items.append(t)
                    closed_total += 1
                else:
                    remaining.append(t)

            TRADING_DATA['trades'] = remaining
            TRADING_DATA['closed_trades'].extend(closed_items)
            TRADING_DATA['trades_open'] = len(TRADING_DATA['trades'])

        return jsonify({'success': True, 'closed': closed_total, 'closed_tickets': closed_tickets if MT5_AVAILABLE else [], 'closed_items': closed_items})


@app.route('/api/toggle-auto', methods=['POST'])
def api_toggle_auto():
    """Alternar modo IA automática"""
    with PRICE_LOCK:
        TRADING_DATA['auto_enabled'] = not TRADING_DATA['auto_enabled']
        return jsonify({'success': True, 'auto_enabled': TRADING_DATA['auto_enabled']})


@app.route('/api/toggle-prediction', methods=['POST'])
def api_toggle_prediction():
    """Alternar uso de predicciones en el trading automático"""
    with PRICE_LOCK:
        TRADING_DATA['use_prediction'] = not TRADING_DATA.get('use_prediction', True)
        status = TRADING_DATA['use_prediction']
        TRADING_DATA['chat_history'].append({
            'sender': 'IA',
            'text': f"Uso de predicción automática {'activado' if status else 'desactivado'}."
        })
        return jsonify({'success': True, 'use_prediction': status})


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Procesar mensajes del chat"""
    data = request.get_json()
    message = data.get('message', '').strip().lower()
    
    response = process_chat_message(message)
    
    with PRICE_LOCK:
        TRADING_DATA['chat_history'].append({'sender': 'Yo', 'text': data.get('message', '')})
        TRADING_DATA['chat_history'].append({'sender': 'IA', 'text': response})
    
    return jsonify({'response': response})


@app.route('/api/chat/command', methods=['POST'])
def api_chat_command():
    """Procesar comando de chat"""
    data = request.get_json()
    if not data or 'command' not in data:
        return jsonify({'error': 'Missing command'}), 400
    
    command = data['command'].strip()
    
    # Procesar comando
    response = process_chat_message(command.lower())
    
    # Agregar al historial
    with PRICE_LOCK:
        TRADING_DATA['chat_history'].append({
            'timestamp': datetime.now().isoformat(),
            'command': command,
            'response': response
        })
    
    return jsonify({'response': response})


@app.route('/api/chat/history')
def api_chat_history():
    """Obtener historial de chat"""
    with PRICE_LOCK:
        return jsonify({
            'history': TRADING_DATA['chat_history']
        })


def query_external_ai(message: str) -> str:
    """Query the external AI API using the configured API key."""
    if not NV_API_KEY or not NV_USE_EXTERNAL_AI:
        return None
    cached_key = message[:700]
    now = time.time()
    if EXTERNAL_AI_CACHE.get('key') == cached_key and (now - EXTERNAL_AI_CACHE.get('ts', 0.0)) < 20:
        return EXTERNAL_AI_CACHE.get('value')

    try:
        headers = {
            'Authorization': f'Bearer {NV_API_KEY}',
            'Content-Type': 'application/json'
        }
        payload = {
            'input': message,
            'model': NV_MODEL,
            'temperature': NV_TEMPERATURE,
            'max_tokens': NV_MAX_TOKENS,
            'top_p': 0.95,
            'frequency_penalty': 0.0,
            'presence_penalty': 0.0
        }
        response = requests.post(NV_API_URL, json=payload, headers=headers, timeout=10)
        if response.status_code != 200:
            return None

        data = response.json()
        if isinstance(data, dict):
            if 'response' in data and data['response']:
                EXTERNAL_AI_CACHE.update({'key': cached_key, 'value': data['response'], 'ts': now})
                return data['response']
            if 'text' in data and data['text']:
                EXTERNAL_AI_CACHE.update({'key': cached_key, 'value': data['text'], 'ts': now})
                return data['text']
            if 'message' in data and data['message']:
                EXTERNAL_AI_CACHE.update({'key': cached_key, 'value': data['message'], 'ts': now})
                return data['message']
            if 'choices' in data and isinstance(data['choices'], list) and len(data['choices']) > 0:
                first = data['choices'][0]
                if isinstance(first, dict):
                    if 'message' in first and isinstance(first['message'], dict):
                        val = first['message'].get('content') or first['message'].get('text')
                        EXTERNAL_AI_CACHE.update({'key': cached_key, 'value': val, 'ts': now})
                        return val
                    val = first.get('text') or first.get('message')
                    EXTERNAL_AI_CACHE.update({'key': cached_key, 'value': val, 'ts': now})
                    return val
        return None
    except Exception:
        return None


def process_chat_message(message):
    """Procesa mensajes del chat con IA inteligente, memoria y contexto de mercado."""
    if not message:
        return "Por favor escribe un comando o pregunta."

    message_lower = message.lower()
    memory = load_chat_memory()
    memory_entries = memory.get('entries', [])
    market = build_market_context()
    memory_ctx = build_memory_context(message, memory)

    if NV_API_KEY:
        prompt = (
            f"Eres un asistente de trading con memoria. Contexto actual: símbolo {market['symbol']}, "
            f"precio {market['price']}, tendencia {market['trend']}, cambio {market['change']}, "
            f"momento {market['momentum']}, señal {market['signal']} con {market['confidence']}% de confianza. "
            f"Alerta volatilidad: {market.get('volatility_alert', {}).get('direction', 'LATERAL')} / {market.get('volatility_alert', {}).get('level', 'NORMAL')}. "
            f"Tendencia global multiactivo: {market.get('global_trend', 'NEUTRAL')}. "
            f"Memoria reciente: {memory_ctx['recent']}. Preferencias: {memory_ctx['prefs']}. "
            f"Mensaje del usuario: {message}. Usa el contexto del mercado y la memoria para responder de forma útil, práctica y con aprendizaje continuo."
        )
        external_response = query_external_ai(prompt)
        if external_response:
            memory.setdefault('entries', []).append({'text': message, 'response': external_response[:220]})
            if len(memory['entries']) > 40:
                memory['entries'] = memory['entries'][-40:]
            memory['summary'] = external_response[:220]
            save_chat_memory(memory)
            return external_response

    if 'predic' in message_lower or 'forecast' in message_lower or 'pronost' in message_lower:
        analysis = TRADING_DATA.get('analysis_cache', {}).get('data') or analyze_signal(TRADING_DATA['price_history'])
        direction = 'ALCISTA' if analysis['action'] == 'COMPRA' else 'BAJISTA' if analysis['action'] == 'VENTA' else 'NEUTRAL'
        const_move = 0.0002 if market['symbol'] == 'EURUSD' else 0.5
        predicted_price = market['price'] + const_move if direction == 'ALCISTA' else market['price'] - const_move
        response = (
            f"Predicción solicitada para {market['symbol']}: señal {analysis['action']} con {analysis['confidence']:.1%} de confianza. "
            f"Dirección estimada: {direction}. Precio actual {market['price']:.6f}, precio previsto {predicted_price:.6f} y tendencia {market['trend']}."
        )
        memory.setdefault('entries', []).append({'text': message, 'response': response[:220]})
        memory['summary'] = response[:220]
        save_chat_memory(memory)
        return response

    if 'compra' in message_lower or 'buy' in message_lower or 'comprar' in message_lower:
        learn_from_user_interaction(message, 'Compra solicitada', 'BUY')
        with PRICE_LOCK:
            trade = {
                'id': len(TRADING_DATA['trades']) + len(TRADING_DATA['closed_trades']) + 1,
                'action': 'COMPRA',
                'entry': TRADING_DATA['price'],
                'size': 0.1,
                'pl': 0
            }
            TRADING_DATA['trades'].append(trade)
            TRADING_DATA['trades_open'] = len(TRADING_DATA['trades'])
            AI_LEARNING_DB['trade_history'].append(trade)
        memory.setdefault('entries', []).append({'text': message, 'response': f'Compra solicitada para {TRADING_SYMBOL}'})
        memory['summary'] = f'El usuario pidió comprar en {TRADING_SYMBOL}'
        save_chat_memory(memory)
        return f"Operación de compra ejecutada a: {TRADING_DATA['price']:.4f}. Identificador #{trade['id']}."
    
    elif 'venta' in message_lower or 'sell' in message_lower or 'vender' in message_lower:
        learn_from_user_interaction(message, 'Venta solicitada', 'SELL')
        with PRICE_LOCK:
            trade = {
                'id': len(TRADING_DATA['trades']) + len(TRADING_DATA['closed_trades']) + 1,
                'action': 'VENTA',
                'entry': TRADING_DATA['price'],
                'size': 0.1,
                'pl': 0
            }
            TRADING_DATA['trades'].append(trade)
            TRADING_DATA['trades_open'] = len(TRADING_DATA['trades'])
            AI_LEARNING_DB['trade_history'].append(trade)
        memory.setdefault('entries', []).append({'text': message, 'response': f'Venta solicitada para {TRADING_SYMBOL}'})
        memory['summary'] = f'El usuario pidió vender en {TRADING_SYMBOL}'
        save_chat_memory(memory)
        return f"Operación de venta ejecutada a: {TRADING_DATA['price']:.4f}. Identificador #{trade['id']}."
    
    elif 'estado' in message_lower or 'status' in message_lower:
        learn_from_user_interaction(message, 'Consulta de estado', None)
        with PRICE_LOCK:
            ia_status = 'ACTIVA' if TRADING_DATA['auto_enabled'] else 'INACTIVA'
            response = (
                f"Estado actual - Precio: {TRADING_DATA['price']:.4f}, Símbolo: {TRADING_SYMBOL}, IA: {ia_status}, "
                f"Señal: {TRADING_DATA['signal']['action']} con {TRADING_DATA['signal']['confidence']:.1%} de confianza. "
                f"Tendencia: {market['trend']}"
            )
            memory.setdefault('entries', []).append({'text': message, 'response': response[:220]})
            memory['summary'] = response[:220]
            save_chat_memory(memory)
            return response
    
    elif 'analizar' in message_lower or 'analyze' in message_lower or 'señal' in message_lower:
        learn_from_user_interaction(message, 'Consulta de señal', None)
        signal = TRADING_DATA['signal']
        response = (
            f"Señal actual: {signal['action']} (Confianza: {signal['confidence']:.1%}). "
            f"Mercado {market['symbol']} con tendencia {market['trend']} y momentum {market['momentum']}. "
            f"Estoy combinando tu instrucción con el análisis del mercado para darte un contexto más útil."
        )
        memory.setdefault('entries', []).append({'text': message, 'response': response[:220]})
        memory['summary'] = response[:220]
        save_chat_memory(memory)
        return response
    
    elif 'auto' in message_lower:
        if 'on' in message_lower or 'activar' in message_lower or 'encender' in message_lower:
            TRADING_DATA['auto_enabled'] = True
            return "IA automática ACTIVADA. El sistema operará de forma inteligente según las señales técnicas."
        elif 'off' in message_lower or 'desactivar' in message_lower or 'apagar' in message_lower:
            TRADING_DATA['auto_enabled'] = False
            return "IA automática DESACTIVADA. Control manual habilitado."
    elif 'cerrar' in message_lower or 'close' in message_lower:
        with PRICE_LOCK:
            closed = len(TRADING_DATA['trades'])
            TRADING_DATA['closed_trades'].extend(TRADING_DATA['trades'])
            TRADING_DATA['trades'] = []
            TRADING_DATA['trades_open'] = 0
        return f"Se cerraron {closed} operaciones abiertas."
    
    elif 'ayuda' in message_lower or 'help' in message_lower or 'comandos' in message_lower:
        return "Comandos disponibles: compra, venta, estado, analizar, auto on/off, cerrar, aprender. Soy tu asistente inteligente de trading."
    
    elif 'aprender' in message_lower or 'learning' in message_lower:
        learn_from_user_interaction(message, 'Consulta de aprendizaje', None)
        learning_pct = (AI_LEARNING_DB['learning_score'] * 100)
        response = (
            f"Mi progreso de aprendizaje: {learning_pct:.1f}%. "
            f"He analizado {len(AI_LEARNING_DB['trade_history'])} operaciones y {len(AI_LEARNING_DB['successful_patterns'])} patrones exitosos. "
            f"Mi memoria actual conserva tus preferencias y el contexto reciente para mejorar cada interacción."
        )
        memory.setdefault('entries', []).append({'text': message, 'response': response[:220]})
        memory['summary'] = response[:220]
        save_chat_memory(memory)
        return response
    
    else:
        response = (
            f"Comando no reconocido. Estoy aprendiendo de tu mensaje y del mercado {market['symbol']} ({market['trend']}), "
            f"y lo combinaré con mi memoria para responder mejor en la próxima interacción."
        )
        memory.setdefault('entries', []).append({'text': message, 'response': response[:220]})
        memory['summary'] = response[:220]
        save_chat_memory(memory)
        return response


# ====================================================================
# ENDPOINTS DEL BOT + IA + MT5 INTEGRADO
# ====================================================================

@app.route('/api/bot/status')
def api_bot_status():
    """Obtiene estado del sistema integrado Bot + IA + MT5"""
    
    if not BOT_TRADER or not INTEGRATION_AVAILABLE:
        return jsonify({'error': 'Sistema integrado no disponible'}), 503
    
    status = BOT_TRADER.get_status()
    return jsonify({
        'running': status['running'],
        'mt5_connected': status['mt5_connected'],
        'config': status['config'],
        'stats': status['stats'],
        'account': status['account'],
        'positions': status['positions'],
        'current_price': status['current_price'],
        'price_history': status['price_history'][-50:]
    })


@app.route('/api/bot/start', methods=['POST'])
def api_bot_start():
    """Inicia el trading automático integrado"""
    
    if not BOT_TRADER or not INTEGRATION_AVAILABLE:
        return jsonify({'error': 'Sistema integrado no disponible'}), 503
    
    global BOT_THREAD
    
    data = request.get_json() or {}
    duration = data.get('duration', None)  # Minutos
    
    if BOT_TRADER.running:
        return jsonify({'error': 'Bot ya está ejecutándose'}), 400
    
    # Iniciar en thread separado
    BOT_THREAD = threading.Thread(target=BOT_TRADER.start_trading, args=(duration,), daemon=True)
    BOT_THREAD.start()
    
    return jsonify({
        'success': True,
        'message': f'Bot iniciado{"" if not duration else f" por {duration} minutos"}',
        'mt5_connected': BOT_TRADER.mt5_manager.connected
    })


@app.route('/api/bot/stop', methods=['POST'])
def api_bot_stop():
    """Detiene el trading automático integrado"""
    
    if not BOT_TRADER:
        return jsonify({'error': 'Sistema integrado no disponible'}), 503
    
    BOT_TRADER.stop_trading()
    
    return jsonify({
        'success': True,
        'message': 'Bot detenido'
    })


@app.route('/api/bot/connect-mt5', methods=['POST'])
def api_bot_connect_mt5():
    """Conecta el bot a MT5"""
    
    if not BOT_TRADER:
        return jsonify({'error': 'Sistema integrado no disponible'}), 503
    
    data = request.get_json()
    login = int(data.get('login', 0))
    password = data.get('password', '')
    server = data.get('server', '')
    
    if not all([login, password, server]):
        return jsonify({'error': 'Credenciales incompletas'}), 400
    
    result = BOT_TRADER._connect_mt5(login, password, server)
    
    if result:
        account = BOT_TRADER.mt5_manager.get_account_info()
        return jsonify({
            'success': True,
            'message': f'Conectado a MT5: {login}',
            'account': account
        })
    else:
        return jsonify({
            'success': False,
            'error': 'No se pudo conectar a MT5'
        }), 400


@app.route('/api/bot/execute-manual', methods=['POST'])
def api_bot_execute_manual():
    """Ejecuta un trade manual a través del bot integrado"""
    
    if not BOT_TRADER:
        return jsonify({'error': 'Sistema integrado no disponible'}), 503
    
    data = request.get_json()
    action = data.get('action', '').upper()
    
    if action not in ['BUY', 'SELL']:
        return jsonify({'error': 'Acción inválida'}), 400
    
    symbol = data.get('symbol', 'EURUSD')
    volume = float(data.get('volume', BOT_TRADER.config['default_volume']))
    
    if BOT_TRADER.mt5_manager.connected:
        result = BOT_TRADER.mt5_manager.place_order(action, symbol, volume)
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    else:
        # Ejecutar en simulación
        current_price = BOT_TRADER.price_history[-1]
        trade = BOT_TRADER.trading_engine.open_trade(action, current_price, 0.85)
        return jsonify({
            'success': True,
            'trade': trade,
            'message': f'Trade simulado: {action} {volume} {symbol}'
        })


@app.route('/api/bot/positions')
def api_bot_positions():
    """Obtiene las posiciones abiertas"""
    
    if not BOT_TRADER:
        return jsonify({'error': 'Sistema integrado no disponible'}), 503
    
    positions = []
    
    if BOT_TRADER.mt5_manager.connected:
        positions = BOT_TRADER.mt5_manager.get_positions(BOT_TRADER.config['trading_symbol'])
    
    return jsonify({
        'positions': positions,
        'count': len(positions),
        'source': 'MT5' if BOT_TRADER.mt5_manager.connected else 'Simulación'
    })


@app.route('/api/bot/config', methods=['GET', 'POST'])
def api_bot_config():
    """Obtiene o actualiza la configuración del bot"""
    
    if not BOT_TRADER:
        return jsonify({'error': 'Sistema integrado no disponible'}), 503
    
    if request.method == 'POST':
        data = request.get_json()
        
        # Actualizar configuración
        for key, value in data.items():
            if key in BOT_TRADER.config:
                BOT_TRADER.config[key] = value
        
        return jsonify({
            'success': True,
            'config': BOT_TRADER.config
        })
    
    # GET
    return jsonify({'config': BOT_TRADER.config})


# ====================================================================
# TEMPLATES HTML
# ====================================================================

LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Trading + IA</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea, #764ba2);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .login-box {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            width: 100%;
            max-width: 400px;
        }
        .login-box h1 {
            color: #667eea;
            text-align: center;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            color: #333;
            font-weight: bold;
            margin-bottom: 8px;
        }
        input {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        input:focus { outline: none; border-color: #667eea; }
        button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
        }
        button:hover { opacity: 0.9; }
        .error {
            color: red;
            margin-bottom: 20px;
            text-align: center;
            font-weight: bold;
        }
        .creds {
            margin-top: 30px;
            padding-top: 30px;
            border-top: 1px solid #eee;
            font-size: 12px;
            color: #666;
        }
        .creds code {
            background: #f5f5f5;
            padding: 4px 8px;
            border-radius: 3px;
            font-family: monospace;
        }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>🤖 Trading + IA</h1>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST">
            <div class="form-group">
                <label>Usuario</label>
                <input type="text" name="username" required>
            </div>
            <div class="form-group">
                <label>Contraseña</label>
                <input type="password" name="password" required>
            </div>
            <button type="submit">Entrar</button>
        </form>
        <div class="creds">
            <strong>Credenciales de Demo:</strong><br>
            Admin: <code>admin</code> / <code>RyzA_jjITjuPQtV66Wwf0A</code><br>
            Trader: <code>trader</code> / <code>SecurePass123</code>
        </div>
    </div>
</body>
</html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Dashboard - Trading</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-chart-financial@0.1.0/dist/chartjs-chart-financial.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #16213e 100%);
            color: #e2e8f0;
            min-height: 100vh;
        }
        .navbar {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e2e8f0;
            padding: 20px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #d4af37;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
        }
        .navbar h1 {
            background: linear-gradient(135deg, #d4af37, #f0e68c);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-size: 28px;
            letter-spacing: 1px;
        }
        .navbar a {
            color: white;
            text-decoration: none;
            background: rgba(255,255,255,0.2);
            padding: 8px 15px;
            border-radius: 5px;
            cursor: pointer;
        }
        .container {
            max-width: 1400px;
            margin: 20px auto;
            padding: 20px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: linear-gradient(135deg, #1a2a4e 0%, #16213e 100%);
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 15px 40px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(212, 175, 55, 0.1);
            border: 1px solid #d4af37;
            position: relative;
            overflow: hidden;
        }
        .card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 1px;
            background: linear-gradient(90deg, transparent, #d4af37, transparent);
        }
        .card h3 {
            color: #d4af37;
            margin-bottom: 18px;
            font-size: 16px;
            letter-spacing: 1px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .stat {
            font-size: 36px;
            font-weight: 700;
            background: linear-gradient(135deg, #d4af37, #f0e68c);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin: 16px 0;
        }
        .btn {
            padding: 12px 28px;
            margin: 8px 6px 0 0;
            background: linear-gradient(135deg, #d4af37, #b8860b);
            color: #1a2a4e;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 600;
            letter-spacing: 0.5px;
            box-shadow: 0 6px 20px rgba(212, 175, 55, 0.3);
        }
        .btn:hover {
            background: linear-gradient(135deg, #f0e68c, #d4af37);
            box-shadow: 0 8px 30px rgba(212, 175, 55, 0.5);
            transform: translateY(-2px);
        }
        .btn-red {
            background: linear-gradient(135deg, #e74c3c, #c0392b);
            color: #fff;
            box-shadow: 0 6px 20px rgba(231, 76, 60, 0.3);
        }
        .btn-red:hover {
            background: linear-gradient(135deg, #ec7063, #e74c3c);
            box-shadow: 0 8px 30px rgba(231, 76, 60, 0.5);
        }
        .btn-green {
            background: linear-gradient(135deg, #27ae60, #229954);
            color: #fff;
            box-shadow: 0 6px 20px rgba(39, 174, 96, 0.3);
        }
        .btn-green:hover {
            background: linear-gradient(135deg, #2ecc71, #27ae60);
            box-shadow: 0 8px 30px rgba(39, 174, 96, 0.5);
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        th, td {
            padding: 14px 16px;
            text-align: left;
            border-bottom: 1px solid rgba(212, 175, 55, 0.2);
            color: #cbd5e1;
        }
        th {
            background: rgba(212, 175, 55, 0.1);
            font-weight: 700;
            color: #d4af37;
            text-transform: uppercase;
            font-size: 13px;
            letter-spacing: 0.5px;
        }
        tr:hover {
            background: rgba(212, 175, 55, 0.05);
        }
        .chart-container {
            position: relative;
            height: 420px;
            margin-top: 15px;
            border-radius: 18px;
            overflow: hidden;
            background: linear-gradient(180deg, rgba(15,23,42,0.95), rgba(15,23,42,0.75));
            box-shadow: inset 0 0 0 1px rgba(212,175,55,0.12), 0 18px 50px rgba(0,0,0,0.35);
        }
        .chart-container canvas {
            width: 100% !important;
            height: 100% !important;
            display: block;
        }
    </style>
</head>
<body>
    <div class="navbar">
        <h1>Sistema de Trading Inteligente</h1>
    </div>
    <div class="container">
        <h2 style="margin-bottom: 30px; color: #d4af37; font-size: 24px; letter-spacing: 1px;">Panel de Control de Trading en Vivo</h2>
        <div class="grid">
            <div class="card">
                <h3>Símbolo Actual</h3>
                <div class="stat" id="status-symbol">EURUSD</div>
            </div>
            <div class="card">
                <h3>Precio Actual</h3>
                <div class="stat" id="price">1.0850</div>
            </div>
            <div class="card">
                <h3>Predicción</h3>
                <div class="stat" id="pred-price">-</div>
            </div>
            <div class="card">
                <h3>Dirección</h3>
                <div class="stat" id="pred-direction">-</div>
            </div>
            <div class="card">
                <h3>Confianza</h3>
                <div class="stat" id="pred-confidence">-</div>
            </div>
            <div class="card">
                <h3>Aprendizaje IA</h3> 
                <div class="stat" id="ai-learning">0%</div>
            </div>
        </div>

        <div class="card">
            <h3>Controles de IA y Predicción</h3>
            <button class="btn" onclick="toggleAuto()">IA Automática</button>
            <button class="btn" onclick="togglePrediction()">Predicción Auto</button>
            <button class="btn" onclick="update()">Actualizar</button>
            <div style="margin-top: 20px; display: grid; gap: 8px;">
                <div><strong style="color: #d4af37;">Estado de IA:</strong> <span id="auto-status" style="color: #27ae60;">INACTIVA</span></div>
                <div><strong style="color: #d4af37;">Uso de Predicción:</strong> <span id="prediction-status" style="color: #d4af37;">ON</span></div>
                <div><strong style="color: #d4af37;">Entrada sugerida:</strong> <span id="pred-entry">-</span></div>
                <div><strong style="color: #d4af37;">Stop Loss:</strong> <span id="pred-sl">-</span></div>
                <div><strong style="color: #d4af37;">Take Profit:</strong> <span id="pred-tp">-</span></div>
            </div>
        </div>

        <div class="card">
            <h3>Conexión MetaTrader 5</h3>
            <button class="btn" onclick="connectMT5()">Conectar Cuenta MT5</button>
            <div style="margin-top: 20px;">
                <div style="margin: 10px 0;"><strong style="color: #d4af37;">Estado:</strong> <span id="mt5-status" style="color: #e74c3c;">Desconectado</span></div>
                <div style="margin: 10px 0;"><strong style="color: #d4af37;">Cuenta:</strong> <span id="mt5-login">-</span></div>
                <div style="margin: 10px 0;"><strong style="color: #d4af37;">Saldo MT5:</strong> <span id="mt5-balance">-</span></div>
                <div style="margin: 10px 0;"><strong style="color: #d4af37;">Patrimonio MT5:</strong> <span id="mt5-equity">-</span></div>
            </div>
        </div>

        <div class="card" style="display: grid; grid-template-columns: minmax(300px, 1fr) minmax(280px, 280px); gap: 20px; align-items: start;">
            <div>
                <h3>Gráfico de Precios</h3>
                <div class="chart-container">
                    <canvas id="chart"></canvas>
                </div>
            </div>
            <div style="display: flex; flex-direction: column; gap: 18px;">
                <div style="background: rgba(22, 33, 62, 0.95); border: 1px solid #d4af37; border-radius: 12px; padding: 18px;">
                    <h3 style="margin-bottom: 14px;">Cambiar Símbolo</h3>
                    <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                        <select id="symbol-selector" style="background: #16213e; border: 1px solid #d4af37; border-radius: 6px; color: #e2e8f0; padding: 12px; min-width: 140px;">
                            <option value="EURUSD">EURUSD</option>
                            <option value="XAUUSD">XAUUSD</option>
                        </select>
                        <button class="btn" onclick="changeSymbol()">Cambiar</button>
                    </div>
                    <div style="margin-top: 12px; color: #94a3b8; font-size: 13px;">El precio y el gráfico se actualizarán al cambiar el símbolo.</div>
                </div>
                <div style="background: rgba(22, 33, 62, 0.95); border: 1px solid #d4af37; border-radius: 12px; padding: 18px;">
                    <h3 style="margin-bottom: 14px;">Símbolo seleccionado</h3>
                    <div class="stat" id="selected-symbol" style="margin-top: 0;">EURUSD</div>
                </div>
                <div style="background: rgba(22, 33, 62, 0.95); border: 1px solid #d4af37; border-radius: 12px; padding: 18px;">
                    <h3 style="margin-bottom: 14px;">Alerta de Volatilidad</h3>
                    <div style="margin: 8px 0;"><strong style="color: #d4af37;">Estado:</strong> <span id="volatility-level">NORMAL</span></div>
                    <div style="margin: 8px 0;"><strong style="color: #d4af37;">Dirección:</strong> <span id="volatility-direction">LATERAL</span></div>
                    <div id="volatility-message" style="margin-top: 8px; font-size: 13px; color: #94a3b8;">Esperando datos...</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h3>Análisis Inteligente de IA</h3>
            <div style="margin: 12px 0;"><strong style="color: #d4af37;">Señal:</strong> <span id="ai-signal" style="color: #27ae60;">ESPERA</span></div>
            <div style="margin: 12px 0;"><strong style="color: #d4af37;">Confianza:</strong> <span id="ai-confidence" style="color: #f39c12;">0%</span></div>
            <div style="margin: 12px 0;"><strong style="color: #d4af37;">Patrón:</strong> <span id="ai-pattern">-</span></div>
            <div style="margin: 12px 0;"><strong style="color: #d4af37;">Tendencia Global:</strong> <span id="ai-global-trend">NEUTRAL</span></div>
            <div style="margin: 12px 0;"><strong style="color: #d4af37;">Volatilidad:</strong> <span id="ai-volatility">-</span></div>
            <div style="margin: 12px 0;"><strong style="color: #d4af37;">Inteligencia IA:</strong> <span id="ai-learning" style="color: #3498db;">Aprendiendo...</span></div>
        </div>

        <div class="card">
            <h3>Noticias Macro (NFP, CPI, PCE, FOMC/FED, ISM, ADP)</h3>
            <div id="macro-news-updated" style="font-size: 12px; color: #94a3b8; margin-bottom: 12px;">Actualizando...</div>
            <div id="macro-news-list" style="display: grid; gap: 10px;">
                <div style="color: #94a3b8;">Cargando eventos macro...</div>
            </div>
        </div>

        <div class="card">
            <h3>Predicciones y Niveles</h3>
            <div style="margin: 12px 0;"><strong style="color: #d4af37;">Predicción:</strong> <span id="pred-direction-detail">-</span></div>
            <div style="margin: 12px 0;"><strong style="color: #d4af37;">Precio Previsto:</strong> <span id="pred-price-detail">-</span></div>
            <div style="margin: 12px 0;"><strong style="color: #d4af37;">Confianza Predicción:</strong> <span id="pred-confidence-detail">-</span></div>
            <div style="margin: 12px 0;"><strong style="color: #d4af37;">Entry:</strong> <span id="pred-entry-detail">-</span>  <strong style="color: #d4af37; margin-left:12px;">SL:</strong> <span id="pred-sl-detail">-</span>  <strong style="color: #d4af37; margin-left:12px;">TP:</strong> <span id="pred-tp-detail">-</span></div>
            <div style="display:flex; gap:10px; align-items:center; margin-top: 12px; flex-wrap: wrap;">
                <button class="btn" onclick="generateOneShotPrediction()">Generar 1 Predicción Avanzada</button>
                <span id="pred-one-shot-status" style="font-size: 13px; color: #94a3b8;">Manual: usa este botón para análisis profundo.</span>
            </div>
            <div id="pred-one-shot-reasons" style="margin-top: 10px; color: #cbd5e1; font-size: 13px;"></div>
        </div>

        <div class="card">
            <h3>Operaciones Abiertas</h3>
            <table>
                <thead>
                    <tr><th>ID</th><th>Tipo</th><th>Entrada</th><th>Ganancia/Pérdida</th></tr>
                </thead>
                <tbody id="trades-list">
                    <tr><td colspan="4" style="text-align:center; padding: 20px;">Sin operaciones abiertas</td></tr>
                </tbody>
            </table>
        </div>

        <div class="card">
            <h3>Control de Posiciones MT5 (Dispositivo)</h3>
            <div style="margin-bottom: 10px; color: #94a3b8; font-size: 13px;">
                Solo se permiten cierres con ganancia minima de $1 por posicion.
            </div>
            <table>
                <thead>
                    <tr><th>Ticket</th><th>Símbolo</th><th>Tipo</th><th>Vol</th><th>Entrada</th><th>Profit</th><th>Acción</th></tr>
                </thead>
                <tbody id="mt5-positions-list">
                    <tr><td colspan="7" style="text-align:center; padding: 20px;">MT5 no conectado</td></tr>
                </tbody>
            </table>
        </div>

        <div class="card">
            <h3>Asistente de IA</h3>
            <div id="chat-box" style="height: 240px; overflow-y: auto; background: rgba(15, 23, 42, 0.5); border: 1px solid #d4af37; border-radius: 8px; padding: 12px; margin-bottom: 15px; color: #cbd5e1;"></div>
            <div style="display: flex; gap: 10px;">
                <input id="chat-input" type="text" placeholder="Escribe un comando o pregunta..." style="flex: 1; padding: 12px; background: #16213e; border: 1px solid #d4af37; border-radius: 6px; color: #e2e8f0; font-size: 14px;" />
                <button class="btn" onclick="sendChat()">Enviar</button>
            </div>
        </div>
    </div>

    <script>
        let chart = null;
        let lastAIUpdateTs = 0;
        let lastPredictionUpdateTs = 0;
        let lastMacroNewsTs = 0;
        let lastChatLoadTs = 0;
        let statusRequestInFlight = false;
        let oneShotOverrideUntil = 0;

        window.currentSymbol = 'EURUSD';
        window.chartSymbol = null;

        function setText(id, value) {
            const escapedId = (window.CSS && typeof window.CSS.escape === 'function')
                ? window.CSS.escape(id)
                : id;
            let nodes = [];
            try {
                nodes = document.querySelectorAll('#' + escapedId);
            } catch (err) {
                nodes = document.querySelectorAll('[id="' + String(id).replace(/"/g, '\\"') + '"]');
            }
            if (nodes && nodes.length) {
                nodes.forEach(el => {
                    el.textContent = value;
                });
                return;
            }

            const el = document.getElementById(id);
            if (el) {
                el.textContent = value;
            }
        }

        function formatPrice(value, symbol) {
            if (typeof value !== 'number') return '-';
            return (symbol === 'XAUUSD' ? value.toFixed(2) : value.toFixed(4));
        }

        function formatSymbolDecimals(value, symbol) {
            if (typeof value !== 'number') return '-';
            return value.toFixed(symbol === 'XAUUSD' ? 2 : 5);
        }

        function setPredictionDisplays(direction, predictedPriceText, confidenceText, entryText, slText, tpText) {
            setText('pred-direction', direction);
            setText('pred-direction-detail', direction);
            setText('pred-price', predictedPriceText);
            setText('pred-price-detail', predictedPriceText);
            setText('pred-confidence', confidenceText);
            setText('pred-confidence-detail', confidenceText);
            setText('pred-entry', entryText);
            setText('pred-entry-detail', entryText);
            setText('pred-sl', slText);
            setText('pred-sl-detail', slText);
            setText('pred-tp', tpText);
            setText('pred-tp-detail', tpText);
        }

        function update() {
            if (statusRequestInFlight) {
                return;
            }
            statusRequestInFlight = true;

            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 3200);

            fetch('/api/status', { signal: controller.signal })
                .then(r => r.json())
                .then(d => {
                    clearTimeout(timeoutId);
                    if (d.error) {
                        console.warn('Status API returned error:', d.error);
                    }
                    const currentSymbol = d.symbol || 'EURUSD';
                    if (chart && window.chartSymbol !== currentSymbol) {
                        try { if (chart) { chart.destroy(); } } catch (err) {}
                        chart = null;
                    }
                    window.chartSymbol = currentSymbol;
                    window.currentSymbol = currentSymbol;
                    setText('status-symbol', currentSymbol);
                    setText('selected-symbol', currentSymbol);
                    const selector = document.getElementById('symbol-selector');
                    if (selector) {
                        selector.value = currentSymbol;
                    }
                    if (typeof d.balance === 'number') {
                        setText('balance', '$' + d.balance.toFixed(2));
                    }
                    if (typeof d.equity === 'number') {
                        setText('equity', '$' + d.equity.toFixed(2));
                    }
                    if (typeof d.price === 'number') {
                        setText('price', formatPrice(d.price, currentSymbol));
                    }
                    setText('trades', d.trades_open || 0);
                    const autoStatus = document.getElementById('auto-status');
                    if (autoStatus) {
                        autoStatus.textContent = d.auto_enabled ? 'ON' : 'OFF';
                        autoStatus.style.color = d.auto_enabled ? '#27ae60' : '#e74c3c';
                    }
                    const predictionStatus = document.getElementById('prediction-status');
                    if (predictionStatus) {
                        predictionStatus.textContent = d.use_prediction ? 'ON' : 'OFF';
                        predictionStatus.style.color = d.use_prediction ? '#27ae60' : '#e74c3c';
                    }

                    if (d.mt5) {
                        const mt5Status = document.getElementById('mt5-status');
                        if (mt5Status) {
                            mt5Status.textContent = d.mt5.connected ? 'Conectado' : 'Desconectado';
                        }
                        setText('mt5-login', d.mt5.login || '-');
                        setText('mt5-balance', d.mt5.balance ? '$' + d.mt5.balance.toFixed(2) : '-');
                        setText('mt5-equity', d.mt5.equity ? '$' + d.mt5.equity.toFixed(2) : '-');
                        updateMT5Positions(!!d.mt5.connected, currentSymbol);
                    } else {
                        updateMT5Positions(false, currentSymbol);
                    }

                    if (d.volatility_alert) {
                        const v = d.volatility_alert;
                        const levelEl = document.getElementById('volatility-level');
                        const dirEl = document.getElementById('volatility-direction');
                        const msgEl = document.getElementById('volatility-message');
                        if (levelEl) levelEl.textContent = v.level || 'NORMAL';
                        if (dirEl) {
                            dirEl.textContent = v.direction || 'LATERAL';
                            if (v.color === 'blue') dirEl.style.color = '#3498db';
                            else if (v.color === 'red') dirEl.style.color = '#e74c3c';
                            else dirEl.style.color = '#f1c40f';
                        }
                        if (msgEl) msgEl.textContent = v.message || 'Mercado estable';
                    }

                    let html = '';
                    if (d.trades && d.trades.length > 0) {
                        d.trades.forEach(t => {
                            const entryValue = typeof t.entry === 'number' ? t.entry.toFixed(4) : t.entry;
                            const plValue = typeof t.pl === 'number' ? t.pl.toFixed(2) : '0.00';
                            html += '<tr><td>#' + t.id + '</td><td>' + t.action + '</td><td>' + entryValue + '</td><td>' + plValue + '</td></tr>';
                        });
                    } else {
                        html = '<tr><td colspan="4" style="text-align:center">-</td></tr>';
                    }
                    const tradesList = document.getElementById('trades-list');
                    if (tradesList) {
                        tradesList.innerHTML = html;
                    }

                    try {
                        const chartDataArr = Array.isArray(d.candles) && d.candles.length ? d.candles : (Array.isArray(d.prices) ? d.prices : []);
                        const raw = Array.isArray(chartDataArr) ? chartDataArr : [];
                        const useCandles = raw.length > 0 && typeof raw[0] === 'object' && raw[0].c !== undefined && raw[0].o !== undefined;
                        const dataPoints = raw.map((item, index) => {
                            if (useCandles) {
                                return { x: item.x || index, y: item.c };
                            }
                            return { x: item && item.x !== undefined ? item.x : index, y: typeof item === 'number' ? item : (item.c || item.y || 0) };
                        });
                        const labels = dataPoints.map(p => p.x);

                        // If chart exists, update its data in-place to avoid recreating and losing state/hover
                        if (chart) {
                            try {
                                chart.data.labels = labels;
                                chart.data.datasets[0].data = dataPoints;
                                if (chart.data.datasets[0].label !== currentSymbol) {
                                    chart.data.datasets[0].label = currentSymbol;
                                }
                                chart.update('none');
                            } catch (err) {
                                console.warn('Error actualizando datos del gráfico:', err);
                                chart = null;
                            }
                        } else {
                            // create chart for the first time
                            try {
                                drawChart(raw);
                            } catch (err) {
                                console.warn('Error dibujando gráfico por primera vez:', err);
                            }
                        }
                    } catch (err) {
                        console.warn('Error actualizando gráfico:', err);
                    }
                    const now = Date.now();
                    if ((now - lastChatLoadTs) > 2500) {
                        loadChat();
                        lastChatLoadTs = now;
                    }
                    if ((now - lastAIUpdateTs) > 3000) {
                        updateAIAnalysis();
                        lastAIUpdateTs = now;
                    }
                    if ((now - lastPredictionUpdateTs) > 4000) {
                        updatePrediction();
                        lastPredictionUpdateTs = now;
                    }
                    if ((now - lastMacroNewsTs) > 60000) {
                        updateMacroNews();
                        lastMacroNewsTs = now;
                    }
                })
                .catch(e => {
                    clearTimeout(timeoutId);
                    console.error('Error fetching dashboard status:', e);
                    updateMT5Positions(false, window.currentSymbol || 'EURUSD');
                })
                .finally(() => {
                    statusRequestInFlight = false;
                });
        }

        function renderMT5Positions(rows) {
            const container = document.getElementById('mt5-positions-list');
            if (!container) return;

            if (!rows || rows.length === 0) {
                container.innerHTML = '<tr><td colspan="7" style="text-align:center">Sin posiciones MT5 abiertas</td></tr>';
                return;
            }

            let html = '';
            rows.forEach(p => {
                const symbol = p.symbol || 'EURUSD';
                const decimals = symbol === 'XAUUSD' ? 2 : 4;
                const entry = typeof p.entry === 'number' ? p.entry.toFixed(decimals) : '-';
                const profit = typeof p.profit === 'number' ? p.profit.toFixed(2) : '0.00';
                const volume = typeof p.volume === 'number' ? p.volume.toFixed(2) : '-';
                const canClose = !!p.can_close;
                const profitColor = (Number(p.profit || 0) >= 1) ? '#27ae60' : '#e74c3c';
                const actionBtn = canClose
                    ? '<button class="btn" onclick="closeMT5Position(' + p.ticket + ')" style="padding: 6px 10px; font-size: 12px;">Cerrar</button>'
                    : '<span style="color:#f39c12; font-size:12px;">Esperando $1+</span>';

                html += '<tr>' +
                    '<td>#' + p.ticket + '</td>' +
                    '<td>' + symbol + '</td>' +
                    '<td>' + (p.action || '-') + '</td>' +
                    '<td>' + volume + '</td>' +
                    '<td>' + entry + '</td>' +
                    '<td style="color:' + profitColor + ';">$' + profit + '</td>' +
                    '<td>' + actionBtn + '</td>' +
                '</tr>';
            });

            container.innerHTML = html;
        }

        function updateMT5Positions(connected, symbol) {
            const container = document.getElementById('mt5-positions-list');
            if (!container) return;

            if (!connected) {
                container.innerHTML = '<tr><td colspan="7" style="text-align:center">MT5 no conectado</td></tr>';
                return;
            }

            fetch('/api/mt5/positions?symbol=' + encodeURIComponent(symbol || ''))
                .then(r => r.json())
                .then(d => {
                    if (!d.success) {
                        container.innerHTML = '<tr><td colspan="7" style="text-align:center">Error cargando posiciones MT5</td></tr>';
                        return;
                    }
                    renderMT5Positions(d.positions || []);
                })
                .catch(() => {
                    container.innerHTML = '<tr><td colspan="7" style="text-align:center">Error cargando posiciones MT5</td></tr>';
                });
        }

        function closeMT5Position(ticket) {
            fetch('/api/mt5/close-position', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ticket: ticket })
            })
                .then(r => r.json())
                .then(d => {
                    if (!d.success) {
                        alert('No se pudo cerrar ticket #' + ticket + ': ' + (d.error || 'Respuesta inválida'));
                    } else {
                        alert('Ticket #' + ticket + ' cerrado correctamente');
                    }
                    update();
                })
                .catch(e => {
                    alert('Error cerrando ticket #' + ticket + ': ' + e.message);
                    update();
                });
        }

        function drawChart(chartData) {
            const ctx = document.getElementById('chart');
            if (!ctx) {
                console.warn('Canvas de gráfico no encontrado');
                return;
            }
            const canvasContext = ctx.getContext('2d');
            const rawData = Array.isArray(chartData) ? chartData : [];
            const useCandles = rawData.length > 0 && typeof rawData[0] === 'object' && rawData[0].c !== undefined && rawData[0].o !== undefined;
            const dataPoints = rawData.map((item, index) => {
                if (useCandles) {
                    return { x: item.x || index, y: item.c };
                }
                return { x: item && item.x !== undefined ? item.x : index, y: typeof item === 'number' ? item : item.c || item.y || 0 };
            });

            const labels = dataPoints.map(p => p.x);

            const symbolLabel = window.chartSymbol || window.currentSymbol || 'EURUSD';
            const chartConfig = {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: symbolLabel,
                        data: dataPoints,
                        borderColor: '#facc15',
                        backgroundColor: 'rgba(250, 204, 21, 0.15)',
                        fill: true,
                        tension: 0.22,
                        pointRadius: 0,
                        pointHoverRadius: 5,
                        borderWidth: 2,
                        segment: {
                            borderColor: ctx => ctx.p1.parsed.y > ctx.p0.parsed.y ? '#22c55e' : '#ef4444'
                        }
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    layout: {
                        padding: { top: 14, right: 16, bottom: 10, left: 10 }
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            mode: 'nearest',
                            intersect: false,
                            backgroundColor: 'rgba(15, 23, 42, 0.96)',
                            titleColor: '#f8fafc',
                            bodyColor: '#e2e8f0',
                            borderColor: 'rgba(212, 175, 55, 0.3)',
                            borderWidth: 1,
                            callbacks: {
                                title: items => `${symbolLabel}`,
                                label: context => `${symbolLabel}: ` + Number(context.parsed.y).toFixed(symbolLabel === 'XAUUSD' ? 2 : 4)
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: false,
                            grid: {
                                color: 'rgba(148, 163, 184, 0.14)',
                                borderColor: 'rgba(148, 163, 184, 0.18)'
                            },
                            ticks: {
                                color: '#cbd5e1',
                                font: { size: 11 },
                                callback: value => Number(value).toFixed(symbolLabel === 'XAUUSD' ? 2 : 4)
                            }
                        },
                        x: {
                            display: true,
                            grid: { display: false },
                            ticks: {
                                color: '#94a3b8',
                                font: { size: 10 },
                                maxRotation: 0,
                                autoSkip: true
                            }
                        }
                    },
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    },
                    hover: {
                        mode: 'index',
                        intersect: false
                    }
                }
            };

            if (dataPoints.length === 0) {
                chart = new Chart(canvasContext, chartConfig);
                return;
            }

            chart = new Chart(canvasContext, chartConfig);
        }

        function buy() {
            fetch('/api/buy', { method: 'POST' })
                .then(r => r.json())
                .then(d => {
                    if (!d.success) {
                        alert('Error al ejecutar compra: ' + (d.error || 'Respuesta inválida'));
                    } else {
                        alert('Compra ejecutada a: ' + d.price.toFixed(4));
                    }
                    update();
                })
                .catch(e => {
                    alert('Error en compra: ' + e.message);
                    update();
                });
        }

        function sell() {
            fetch('/api/sell', { method: 'POST' })
                .then(r => r.json())
                .then(d => {
                    if (!d.success) {
                        alert('Error al ejecutar venta: ' + (d.error || 'Respuesta inválida'));
                    } else {
                        alert('Venta ejecutada a: ' + d.price.toFixed(4));
                    }
                    update();
                })
                .catch(e => {
                    alert('Error en venta: ' + e.message);
                    update();
                });
        }

        function closeAll() {
            fetch('/api/close-all', { method: 'POST' })
                .then(r => r.json())
                .then(d => {
                    if (!d.success) {
                        alert('Error al cerrar posiciones: ' + (d.error || 'Respuesta inválida'));
                    } else {
                        alert('Se cerraron ' + d.closed + ' operaciones');
                    }
                    update();
                })
                .catch(e => {
                    alert('Error cerrando posiciones: ' + e.message);
                    update();
                });
        }

        function toggleAuto() {
            fetch('/api/toggle-auto', { method: 'POST' })
                .then(r => r.json())
                .then(d => {
                    const estado = d.auto_enabled ? 'ACTIVA' : 'INACTIVA';
                    const color = d.auto_enabled ? '#27ae60' : '#e74c3c';
                    const autoStatus = document.getElementById('auto-status');
                    if (autoStatus) {
                        autoStatus.textContent = estado;
                        autoStatus.style.color = color;
                    }
                    alert('IA Automática: ' + estado);
                    update();
                });
        }

        function togglePrediction() {
            fetch('/api/toggle-prediction', { method: 'POST' })
                .then(r => r.json())
                .then(d => {
                    const estado = d.use_prediction ? 'ON' : 'OFF';
                    const color = d.use_prediction ? '#27ae60' : '#e74c3c';
                    const predictionStatus = document.getElementById('prediction-status');
                    if (predictionStatus) {
                        predictionStatus.textContent = estado;
                        predictionStatus.style.color = color;
                    }
                    alert('Uso de predicción automática: ' + estado);
                    update();
                });
        }

        function connectMT5() {
            fetch('/api/mt5/connect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            })
                .then(r => r.json())
                .then(d => {
                    if (d.success) {
                        alert('Conexión exitosa: ' + d.message);
                        const mt5info = d.mt5 || {};
                        const connected = mt5info.connected === true;
                        const mt5Status = document.getElementById('mt5-status');
                        if (mt5Status) {
                            mt5Status.textContent = connected ? 'Conectado' : 'Desconectado';
                            mt5Status.style.color = connected ? '#27ae60' : '#e74c3c';
                        }
                        setText('mt5-login', mt5info.login || '-');
                        setText('mt5-balance', mt5info.balance ? '$' + mt5info.balance.toFixed(2) : '-');
                        setText('mt5-equity', mt5info.equity ? '$' + mt5info.equity.toFixed(2) : '-');
                    } else {
                        alert('Error de conexión: ' + (d.error || 'No se pudo conectar a MT5'));
                    }
                    update();
                })
                .catch(e => {
                    alert('Error conectando a MT5: ' + e.message);
                });
        }

        function renderChat(messages) {
            const box = document.getElementById('chat-box');
            if (!box) return;
            box.innerHTML = '';
            messages.slice(-20).forEach(msg => {
                const sender = msg.sender || (msg.command ? 'IA' : 'Tú');
                const text = msg.text || msg.response || '';
                const el = document.createElement('div');
                el.style.marginBottom = '12px';
                el.style.padding = '10px';
                el.style.borderRadius = '6px';
                if (sender === 'IA' || sender === 'Sistema') {
                    el.style.background = 'rgba(212, 175, 55, 0.15)';
                    el.style.borderLeft = '3px solid #d4af37';
                    el.style.color = '#f0e68c';
                } else {
                    el.style.background = 'rgba(52, 152, 219, 0.15)';
                    el.style.borderLeft = '3px solid #3498db';
                    el.style.color = '#85c1e9';
                }
                el.innerHTML = `<strong style="color: ${sender === 'IA' || sender === 'Sistema' ? '#d4af37' : '#3498db'};">${sender === 'IA' || sender === 'Sistema' ? 'Sistema' : 'Tú'}:</strong> ${text}`;
                box.appendChild(el);
            });
            box.scrollTop = box.scrollHeight;
        }

        function loadChat() {
            fetch('/api/chat/history')
                .then(r => r.json())
                .then(d => {
                    if (!d.error && d.history) {
                        renderChat(d.history);
                    }
                })
                .catch(e => console.error('Chat load error:', e));
        }

        function sendChat() {
            const input = document.getElementById('chat-input');
            const message = input.value.trim();
            if (!message) return;
            fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            })
                .then(r => r.json())
                .then(d => {
                    input.value = '';
                    update();
                })
                .catch(e => console.error('Chat send error:', e));
        }

        function updateAIAnalysis() {
            fetch('/api/professional-analysis')
                .then(r => r.json())
                .then(d => {
                    if (d.error) return;
                    const signal = d.signal || 'ESPERA';
                    const color = signal === 'COMPRA' ? '#27ae60' : signal === 'VENTA' ? '#e74c3c' : '#f39c12';
                    const aiSignal = document.getElementById('ai-signal');
                    if (aiSignal) {
                        aiSignal.textContent = signal;
                        aiSignal.style.color = color;
                    }
                    const confidencePct = typeof d.confidence_percent === 'number' ? d.confidence_percent : ((d.confidence || 0) * 100);
                    setText('ai-confidence', confidencePct.toFixed(1) + '%');
                    setText('ai-pattern', d.pattern || '-');
                    setText('ai-global-trend', d.global_market_trend || 'NEUTRAL');
                    setText('ai-volatility', d.volatility || '-');
                    const learning = (d.learning_progress || 0).toFixed(1) + '%';
                    setText('ai-learning', 'Aprendida: ' + learning);
                })
                .catch(e => console.error('Error en análisis de IA:', e));
        }

        function changeSymbol() {
            const symbol = document.getElementById('symbol-selector').value;
            if (!symbol) return;
            fetch('/api/symbol', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbol, manual: true })
            })
                .then(r => r.json())
                .then(d => {
                    if (!d.success) {
                        alert('Error cambiando símbolo: ' + (d.error || 'Respuesta inválida'));
                        return;
                    }
                    window.currentSymbol = d.symbol;
                    oneShotOverrideUntil = 0;
                    window.chartSymbol = null;
                    try { if (chart) { chart.destroy(); } } catch (err) {}
                    chart = null;
                    setText('status-symbol', d.symbol);
                    setText('selected-symbol', d.symbol);
                    if (typeof d.price === 'number') {
                        setText('price', formatPrice(d.price, d.symbol));
                    }
                    const freshSeries = (Array.isArray(d.candles) && d.candles.length) ? d.candles : (Array.isArray(d.prices) ? d.prices : []);
                    if (freshSeries.length) {
                        drawChart(freshSeries);
                    }
                    window.chartSymbol = d.symbol;
                    window.currentSymbol = d.symbol;
                    update();
                })
                .catch(e => alert('Error cambiando símbolo: ' + e.message));
        }

        function updatePrediction() {
            if (Date.now() < oneShotOverrideUntil) {
                return;
            }

            fetch('/api/predict')
                .then(r => r.json())
                .then(d => {
                    if (!d.success) return;
                    const p = d.prediction;
                    setPredictionDisplays(
                        p.direction || '-',
                        p.predicted_price ? p.predicted_price.toFixed(4) : '-',
                        p.confidence ? (p.confidence * 100).toFixed(1) + '%' : '-',
                        document.getElementById('pred-entry')?.textContent || '-',
                        document.getElementById('pred-sl')?.textContent || '-',
                        document.getElementById('pred-tp')?.textContent || '-'
                    );
                })
                .catch(e => console.error('Error fetching predict:', e));

            fetch('/api/predict/levels')
                .then(r => r.json())
                .then(d => {
                    if (!d.success) return;
                    const l = d.levels;
                    const entryText = l.entry || '-';
                    const slText = l.stop_loss || '-';
                    const tpText = l.take_profit || '-';
                    setText('pred-entry', entryText);
                    setText('pred-entry-detail', entryText);
                    setText('pred-sl', slText);
                    setText('pred-sl-detail', slText);
                    setText('pred-tp', tpText);
                    setText('pred-tp-detail', tpText);
                })
                .catch(e => console.error('Error fetching predict levels:', e));

            fetch('/api/predict/signal')
                .then(r => r.json())
                .then(d => {
                    if (!d.success) return;
                    console.debug('Prediction signal:', d.prediction_signal || d.predictionSignal);
                })
                .catch(e => console.error('Error fetching predict signal:', e));
        }

        function formatEtaMinutes(minutes) {
            if (typeof minutes !== 'number') return '-';
            const days = Math.floor(minutes / 1440);
            const hours = Math.floor((minutes % 1440) / 60);
            const mins = minutes % 60;
            if (days > 0) return `${days}d ${hours}h`;
            if (hours > 0) return `${hours}h ${mins}m`;
            return `${mins}m`;
        }

        function impactColor(impact) {
            const value = String(impact || '').toUpperCase();
            if (value.includes('MUY')) return '#ef4444';
            if (value.includes('ALTO')) return '#f97316';
            if (value.includes('MEDIO')) return '#facc15';
            return '#94a3b8';
        }

        function updateMacroNews() {
            fetch('/api/news/macro')
                .then(r => r.json())
                .then(d => {
                    if (!d.success || !d.news) return;
                    setText('macro-news-updated', 'Actualizado: ' + (d.news.updated_at_utc || '-'));

                    const list = document.getElementById('macro-news-list');
                    if (!list) return;
                    const events = Array.isArray(d.news.events) ? d.news.events : [];

                    if (!events.length) {
                        list.innerHTML = '<div style="color:#94a3b8;">Sin eventos disponibles.</div>';
                        return;
                    }

                    list.innerHTML = events.map(ev => {
                        const impact = ev.impact || '-';
                        const impactClr = impactColor(impact);
                        const eta = formatEtaMinutes(ev.eta_minutes);
                        return `
                            <div style="border:1px solid rgba(212,175,55,0.25); border-radius:10px; padding:10px; background:rgba(15,23,42,0.45)">
                                <div style="display:flex; justify-content:space-between; gap:10px; flex-wrap:wrap;">
                                    <strong style="color:#f1f5f9;">${ev.code || '-'} - ${ev.label || '-'}</strong>
                                    <span style="color:${impactClr}; font-weight:700;">${impact}</span>
                                </div>
                                <div style="margin-top:6px; font-size:12px; color:#cbd5e1;">Próximo: ${ev.next_release_utc || '-'} | ETA: ${eta}</div>
                                <div style="margin-top:6px; font-size:12px; color:#94a3b8;">${ev.hint || ''}</div>
                            </div>
                        `;
                    }).join('');
                })
                .catch(e => console.error('Error fetching macro news:', e));
        }

        function generateOneShotPrediction() {
            const statusEl = document.getElementById('pred-one-shot-status');
            const reasonsEl = document.getElementById('pred-one-shot-reasons');
            if (statusEl) {
                statusEl.textContent = 'Analizando patrones globales...';
                statusEl.style.color = '#f1c40f';
            }
            if (reasonsEl) {
                reasonsEl.textContent = '';
            }

            fetch('/api/predict/one-shot', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            })
                .then(async r => {
                    const data = await r.json();
                    return { ok: r.ok, data };
                })
                .then(({ ok, data }) => {
                    if (!ok || !data.success) {
                        const msg = data && data.error ? data.error : 'No se pudo generar predicción avanzada.';
                        if (statusEl) {
                            statusEl.textContent = msg;
                            statusEl.style.color = '#e74c3c';
                        }
                        return;
                    }

                    const directionText = data.direction || '-';
                    const predictedPriceText = typeof data.predicted_price === 'number'
                        ? formatSymbolDecimals(data.predicted_price, window.currentSymbol || data.symbol || 'EURUSD')
                        : '-';
                    const confidenceText = typeof data.confidence_percent === 'number'
                        ? data.confidence_percent.toFixed(1) + '%'
                        : '-';
                    const entryText = formatSymbolDecimals(
                        typeof data.entry === 'number' ? data.entry : (data.levels && typeof data.levels.entry === 'number' ? data.levels.entry : null),
                        data.symbol || window.currentSymbol || 'EURUSD'
                    );
                    const slText = formatSymbolDecimals(
                        typeof data.stop_loss === 'number' ? data.stop_loss : (data.levels && typeof data.levels.stop_loss === 'number' ? data.levels.stop_loss : null),
                        data.symbol || window.currentSymbol || 'EURUSD'
                    );
                    const tpText = formatSymbolDecimals(
                        typeof data.take_profit === 'number' ? data.take_profit : (data.levels && typeof data.levels.take_profit === 'number' ? data.levels.take_profit : null),
                        data.symbol || window.currentSymbol || 'EURUSD'
                    );

                    setPredictionDisplays(directionText, predictedPriceText, confidenceText, entryText, slText, tpText);
                    oneShotOverrideUntil = Date.now() + 90000;

                    if (statusEl) {
                        if (data.target_met) {
                            statusEl.textContent = 'Predicción válida: confianza >= 70%. Acción sugerida: ' + (data.action || 'ESPERA');
                            statusEl.style.color = '#27ae60';
                        } else {
                            statusEl.textContent = 'Predicción sin umbral (<' + (data.target_confidence || 70) + '%). Recomendación: ESPERA.';
                            statusEl.style.color = '#e67e22';
                        }
                    }

                    if (reasonsEl) {
                        const reasons = Array.isArray(data.reasons) ? data.reasons : [];
                        reasonsEl.textContent = reasons.length ? ('Motivos: ' + reasons.join(' | ')) : '';
                    }
                })
                .catch(e => {
                    if (statusEl) {
                        statusEl.textContent = 'Error en predicción avanzada: ' + e.message;
                        statusEl.style.color = '#e74c3c';
                    }
                });
        }

        update();
        updateMacroNews();
        setInterval(update, 1500);
    </script>
</body>
</html>
"""

# ====================================================================
# MAIN
# ====================================================================

def run_flask_app():
    start_background_services()
    preferred_ports = [FLASK_PORT] + [p for p in [5000, 5001, 8000, 8080] if p != FLASK_PORT]
    for port in preferred_ports:
        try:
            print(f"Intentando iniciar servidor en http://0.0.0.0:{port}")
            app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
            return
        except OSError as e:
            print(f"Puerto {port} no disponible: {e}")
    raise SystemExit("No se pudo iniciar el servidor en ningún puerto disponible.")

def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'

if __name__ == '__main__':
    print("\n" + "="*70)
    print("  TRADING SYSTEM - INICIANDO")
    print("="*70 + "\n")
    local_ip = get_local_ip()
    print(f"Servidor accesible desde otros dispositivos en http://{local_ip}:{FLASK_PORT}")
    print(f"También disponible localmente en http://127.0.0.1:{FLASK_PORT}")
    print("La conexión a MT5 se realiza desde la UI con /api/mt5/connect")
    print("\n" + "="*70 + "\n")
    run_flask_app()
