#!/usr/bin/env python3
"""
TRADING SYSTEM - APLICACIÓN WEB SIMPLE Y FUNCIONAL
Versión limpia sin dependencias complicadas
"""

import os
import sys
import subprocess
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
req_file = os.path.join(ROOT, 'requirements.txt')
if '--no-install' not in sys.argv and os.path.exists(req_file):
    try:
        print('Instalando dependencias desde requirements.txt...')
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', req_file])
    except Exception as e:
        print('Advertencia: no se pudo instalar dependencias automáticamente:', e)
        print('Ejecuta manualmente: python -m pip install -r requirements.txt')

from flask import Flask, render_template_string, request, redirect, jsonify
import random
import threading
import socket
import webbrowser
from datetime import datetime

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False

try:
    from professional_trading_system import AIAnalyzer as ProAIAnalyzer
    PROFESSIONAL_AVAILABLE = True
except ImportError:
    ProAIAnalyzer = None
    PROFESSIONAL_AVAILABLE = False

try:
    from mt5_integration import BotAITrader
    INTEGRATION_AVAILABLE = True
except ImportError:
    BotAITrader = None
    INTEGRATION_AVAILABLE = False

# Configuración MT5 inline (se puede editar aquí directamente)
MT5_LOGIN = None
MT5_PASSWORD = None
MT5_SERVER = None
MT5_PATH = None
TRADING_SYMBOL = 'EURUSD'
DEFAULT_VOLUME = 0.01
USE_REAL_ACCOUNT = False


MT5_CREDENTIALS = {}
if all([MT5_LOGIN, MT5_PASSWORD, MT5_SERVER]):
    MT5_CREDENTIALS = {
        'login': MT5_LOGIN,
        'password': MT5_PASSWORD,
        'server': MT5_SERVER,
        'path': MT5_PATH
    }

app = Flask(__name__)
app.secret_key = 'trading-system-secret-2026'

# ====================================================================
# DATOS GLOBALES
# ====================================================================

TRADING_DATA = {
    'price': 1.0850,
    'price_history': [1.0850 + i * 0.0001 + random.uniform(-0.0005, 0.0005) for i in range(50)],  # Tendencia gradual
    'balance': 10000.0,
    'equity': 10000.0,
    'trades_open': 0,
    'trades': [],
    'closed_trades': [],
    'auto_enabled': False,
    'signal': {'action': 'HOLD', 'confidence': 0.0},
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
    'learning_score': 0.0,
    'confidence_threshold': 0.65
}

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
    
    # Aprendizaje: Aprender de patrones históricos exitosos
    learned_bonus = 0.0
    if AI_LEARNING_DB['successful_patterns']:
        # Buscar patrones similares en el histórico
        for pattern in AI_LEARNING_DB['successful_patterns'][-10:]:
            if pattern['trend'] == trend and pattern['momentum'] == momentum:
                learned_bonus += 0.15 * (pattern['success_rate'] or 0.5)
    
    # Señal de trading inteligente
    confidence = 0.0
    action = 'ESPERA'
    
    if rsi < 35 and trend == 'BAJA' and macd_data['histogram'] < 0:
        confidence = min(0.95, 0.4 + (35 - rsi) / 70 + learned_bonus)
        action = 'COMPRA'
    elif rsi > 65 and trend == 'ALZA' and macd_data['histogram'] > 0:
        confidence = min(0.95, 0.4 + (rsi - 65) / 35 + learned_bonus)
        action = 'VENTA'
    elif (current > bb_data['upper']) and rsi > 60:
        confidence = min(0.85, 0.3 + (rsi - 60) / 40)
        action = 'VENTA'
    elif (current < bb_data['lower']) and rsi < 40:
        confidence = min(0.85, 0.3 + (40 - rsi) / 40)
        action = 'COMPRA'
    
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

# ====================================================================
# ACTUALIZACIÓN DE PRECIOS
# ====================================================================

def update_prices():
    """Actualiza precios en tiempo real con análisis inteligente"""
    while True:
        try:
            with PRICE_LOCK:
                last = TRADING_DATA['price_history'][-1]
                # Movimientos realistas con volatilidad variable
                change = random.uniform(-0.00008, 0.00008)
                new_price = max(0.9, last + change)
                TRADING_DATA['price_history'].append(new_price)
                if len(TRADING_DATA['price_history']) > 200:
                    TRADING_DATA['price_history'].pop(0)
                TRADING_DATA['price'] = new_price
                
                # Sistema automático de trading inteligente
                if TRADING_DATA['auto_enabled'] and len(TRADING_DATA['price_history']) >= 50:
                    # Análisis inteligente con múltiples indicadores
                    analysis = analyze_signal(TRADING_DATA['price_history'])
                    TRADING_DATA['signal'] = {'action': analysis['action'], 'confidence': analysis['confidence']}
                    
                    # Registrar análisis para aprendizaje
                    AI_LEARNING_DB['learning_score'] += analysis['confidence'] * 0.01
                    if analysis['action'] != 'ESPERA':
                        AI_LEARNING_DB['successful_patterns'].append(analysis['pattern'])
                    
                    # Ejecutar operación solo con confianza suficiente
                    if analysis['action'] != 'ESPERA' and analysis['confidence'] > AI_LEARNING_DB['confidence_threshold']:
                        # Execute trade automatically via MT5 when available
                        trade_info = None
                        if MT5_AVAILABLE and MT5_CONNECTED:
                            result = place_mt5_order(analysis['action'])
                            if result.get('success'):
                                trade_info = {
                                    'id': len(TRADING_DATA['trades']) + len(TRADING_DATA['closed_trades']) + 1,
                                    'action': analysis['action'],
                                    'entry': result['price'],
                                    'size': result['volume'],
                                    'pl': 0,
                                    'confidence': analysis['confidence'],
                                    'ticket': result['ticket'],
                                    'source': 'MT5'
                                }
                        if trade_info is None:
                            trade_info = {
                                'id': len(TRADING_DATA['trades']) + len(TRADING_DATA['closed_trades']) + 1,
                                'action': analysis['action'],
                                'entry': TRADING_DATA['price'],
                                'size': 0.1,
                                'pl': 0,
                                'confidence': analysis['confidence'],
                                'source': 'SIM'
                            }
                        TRADING_DATA['trades'].append(trade_info)
                        TRADING_DATA['trades_open'] = len(TRADING_DATA['trades'])
                        AI_LEARNING_DB['trade_history'].append(trade_info)
                        
                        # Registrar en histórico
                        TRADING_DATA['chat_history'].append({
                            'timestamp': datetime.now().isoformat(),
                            'sender': 'IA',
                            'text': f'Operación automática: {analysis["action"]} a {trade_info["entry"]:.4f} (Confianza: {analysis["confidence"]:.1%}). RSI: {analysis["rsi"]:.1f}, Tendencia: {analysis["trend"]}'
                        })
            
            time.sleep(1)
        except Exception as e:
            print(f"Error actualizando precios: {e}")
            pass


def initialize_mt5(login=None, password=None, server=None, path=None):
    """Inicializa y conecta MetaTrader5 con credenciales dadas o con las guardadas."""
    global MT5_CONNECTED, MT5_ACCOUNT_INFO, MT5_CREDENTIALS
    if not MT5_AVAILABLE:
        return {'success': False, 'error': 'MetaTrader5 package not instalado'}

    if login and password and server:
        MT5_CREDENTIALS = {
            'login': login,
            'password': password,
            'server': server,
            'path': path or MT5_PATH
        }

    if not MT5_CREDENTIALS.get('login') or not MT5_CREDENTIALS.get('password') or not MT5_CREDENTIALS.get('server'):
        return {'success': False, 'error': 'MT5 credentials no configuradas. Envía login, password y server.'}

    if MT5_CONNECTED:
        # Si ya está conectado y las credenciales no cambiaron, no re-inicializamos
        return {'success': True, 'message': 'MT5 ya está conectado'}

    try:
        if MT5_CREDENTIALS.get('path'):
            if not mt5.initialize(path=MT5_CREDENTIALS['path']):
                return {'success': False, 'error': f'Error inicializando MT5 con path {MT5_CREDENTIALS["path"]}'}
        else:
            if not mt5.initialize():
                return {'success': False, 'error': 'Error inicializando MT5'}

        if not mt5.login(login=int(MT5_CREDENTIALS['login']), password=MT5_CREDENTIALS['password'], server=MT5_CREDENTIALS['server']):
            mt5.shutdown()
            return {'success': False, 'error': 'Login MT5 fallido. Verifica credenciales y servidor'}

        account_info = mt5.account_info()
        if account_info is None:
            mt5.shutdown()
            return {'success': False, 'error': 'No se pudo obtener info de cuenta MT5'}

        MT5_CONNECTED = True
        MT5_ACCOUNT_INFO = account_info
        return {'success': True, 'message': f'Conectado a MT5 cuenta {account_info.login}'}
    except Exception as e:
        try:
            mt5.shutdown()
        except Exception:
            pass
        return {'success': False, 'error': f'Error MT5: {str(e)}'}


def get_candle_data(max_candles=40):
    """Devuelve datos de velas para el gráfico."""
    if MT5_AVAILABLE and MT5_CONNECTED:
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


def mt5_status():
    """Devuelve estado y datos de la cuenta MT5"""
    global MT5_CONNECTED, MT5_ACCOUNT_INFO
    if not MT5_AVAILABLE:
        return {'connected': False, 'error': 'MetaTrader5 package no instalado'}

    if not MT5_CONNECTED:
        return {'connected': False, 'error': 'No conectado a MT5'}

    account = MT5_ACCOUNT_INFO
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
        MT5_CONNECTED = False
        return {'connected': False, 'error': f'Error al obtener info MT5: {str(e)}'}


def place_mt5_order(action):
    """Envía orden a MT5"""
    if not MT5_AVAILABLE:
        return {'success': False, 'error': 'MetaTrader5 no disponible'}

    if not MT5_CONNECTED:
        result = initialize_mt5()
        if not result.get('success'):
            return {'success': False, 'error': result.get('error', 'No conectado a MT5')}

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
        return {'success': False, 'error': 'Orden MT5 no enviada'}

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return {'success': False, 'error': f'Orden MT5 fallida: {result.retcode} - {result.comment}'}

    return {'success': True, 'ticket': int(result.order), 'price': float(price), 'volume': float(volume)}


def close_all_mt5_positions():
    """Cierra todas las posiciones abiertas en MT5 para el símbolo configurado"""
    if not MT5_AVAILABLE or not MT5_CONNECTED:
        return {'success': False, 'error': 'MT5 no conectado'}

    symbol = TRADING_SYMBOL or 'EURUSD'
    positions = mt5.positions_get(symbol=symbol)
    if positions is None or len(positions) == 0:
        return {'success': True, 'closed': 0}

    closed = 0
    for pos in positions:
        order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).bid if order_type == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(symbol).ask
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
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            closed += 1

    return {'success': True, 'closed': closed}


# Iniciar thread de precios
price_thread = threading.Thread(target=update_prices, daemon=True)
price_thread.start()

# ====================================================================
# RUTAS
# ====================================================================

@app.route('/')
def index():
    """Dashboard principal"""
    return render_template_string(DASHBOARD_HTML)


@app.route('/dashboard')
def dashboard():
    """Ruta alternativa para el panel de control"""
    return render_template_string(DASHBOARD_HTML)


@app.route('/api/status')
def api_status():
    """Obtener estado del trading"""
    with PRICE_LOCK:
        mt5_state = mt5_status() if MT5_AVAILABLE else {'connected': False, 'error': 'MetaTrader5 package no instalado'}
        return jsonify({
            'price': TRADING_DATA['price'],
            'balance': TRADING_DATA['balance'],
            'equity': TRADING_DATA['equity'],
            'trades_open': TRADING_DATA['trades_open'],
            'trades': TRADING_DATA['trades'],
            'auto_enabled': TRADING_DATA['auto_enabled'],
            'signal': TRADING_DATA['signal'],
            'prices': TRADING_DATA['price_history'][-30:],
            'candles': get_candle_data(40),
            'closed_count': len(TRADING_DATA['closed_trades']),
            'chat_history': TRADING_DATA['chat_history'][-20:],
            'mt5': mt5_state
        })


@app.route('/api/mt5/connect', methods=['POST'])
def api_mt5_connect():
    """Conecta MT5 usando credenciales enviadas por la web o mt5_config.py"""
    data = request.get_json(silent=True) or {}
    login = data.get('login')
    password = data.get('password')
    server = data.get('server')
    path = data.get('path')

    result = initialize_mt5(login=login, password=password, server=server, path=path)
    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 400


@app.route('/api/mt5/status')
def api_mt5_status():
    return jsonify(mt5_status())


@app.route('/api/professional-analysis')
def api_professional_analysis():
    """Análisis profesional inteligente con indicadores técnicos avanzados y aprendizaje"""
    with PRICE_LOCK:
        prices = TRADING_DATA['price_history']
        
        if len(prices) < 20:
            return jsonify({
                'available': False,
                'reason': 'Insuficientes datos históricos (se necesitan 20+ precios)',
                'learning_progress': 0.0
            })
        
        # Análisis inteligente
        analysis = analyze_signal(prices)
        
        # Calcular indicadores avanzados
        rsi = analysis['rsi']
        learning_pct = min(100.0, AI_LEARNING_DB['learning_score'] * 10)
        
        return jsonify({
            'available': True,
            'current_price': TRADING_DATA['price'],
            'signal': analysis['action'],
            'confidence': analysis['confidence'],
            'learning_progress': learning_pct,
            'indicators': {
                'rsi': round(rsi, 2),
                'trend': analysis['trend'],
                'momentum': 'FUERTE' if abs(prices[-1] - prices[-5]) > 0.002 else 'DÉBIL',
                'bb_range': analysis['bb'],
                'macd_histogram': round(analysis['macd'], 6)
            },
            'pattern': analysis['trend'],
            'successful_trades': len([t for t in AI_LEARNING_DB['trade_history'] if t.get('pl', 0) > 0]),
            'total_trades': len(AI_LEARNING_DB['trade_history']),
            'timestamp': datetime.now().isoformat()
        })


@app.route('/api/buy', methods=['POST'])
def api_buy():
    """Ejecutar compra"""
    with PRICE_LOCK:
        if MT5_AVAILABLE and MT5_CONNECTED:
            result = place_mt5_order('BUY')
            if result.get('success'):
                trade = {
                    'id': len(TRADING_DATA['trades']) + 1,
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

        trade = {
            'id': len(TRADING_DATA['trades']) + 1,
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
        if MT5_AVAILABLE and MT5_CONNECTED:
            result = place_mt5_order('SELL')
            if result.get('success'):
                trade = {
                    'id': len(TRADING_DATA['trades']) + 1,
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

        trade = {
            'id': len(TRADING_DATA['trades']) + 1,
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
        if MT5_AVAILABLE and MT5_CONNECTED:
            result = close_all_mt5_positions()
            if result.get('success'):
                closed = result.get('closed', 0)
            else:
                return jsonify({'success': False, 'error': result.get('error')}), 400
        else:
            closed = len(TRADING_DATA['trades'])

        TRADING_DATA['closed_trades'].extend(TRADING_DATA['trades'])
        TRADING_DATA['trades'] = []
        TRADING_DATA['trades_open'] = 0
        return jsonify({'success': True, 'closed': closed})


@app.route('/api/toggle-auto', methods=['POST'])
def api_toggle_auto():
    """Alternar modo IA automática"""
    with PRICE_LOCK:
        TRADING_DATA['auto_enabled'] = not TRADING_DATA['auto_enabled']
        return jsonify({'success': True, 'auto_enabled': TRADING_DATA['auto_enabled']})


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


def process_chat_message(message):
    """Procesa mensajes del chat con IA inteligente"""
    if not message:
        return "Por favor escribe un comando o pregunta."
    
    message_lower = message.lower()
    
    if 'compra' in message_lower or 'buy' in message_lower or 'comprar' in message_lower:
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
        return f"Operación de compra ejecutada a: {TRADING_DATA['price']:.4f}. Identificador #{trade['id']}."
    
    elif 'venta' in message_lower or 'sell' in message_lower or 'vender' in message_lower:
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
        return f"Operación de venta ejecutada a: {TRADING_DATA['price']:.4f}. Identificador #{trade['id']}."
    
    elif 'estado' in message_lower or 'status' in message_lower:
        with PRICE_LOCK:
            ia_status = 'ACTIVA' if TRADING_DATA['auto_enabled'] else 'INACTIVA'
            return f"Estado actual - Precio: {TRADING_DATA['price']:.4f}, Saldo: ${TRADING_DATA['balance']:.2f}, Operaciones abiertas: {TRADING_DATA['trades_open']}, IA: {ia_status}"
    
    elif 'analizar' in message_lower or 'analyze' in message_lower or 'señal' in message_lower:
        signal = TRADING_DATA['signal']
        return f"Señal actual: {signal['action']} (Confianza: {signal['confidence']:.1%}). Continúa observando los indicadores técnicos."
    
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
        learning_pct = (AI_LEARNING_DB['learning_score'] * 100)
        return f"Mi progreso de aprendizaje: {learning_pct:.1f}%. He analizado {len(AI_LEARNING_DB['trade_history'])} operaciones y {len(AI_LEARNING_DB['successful_patterns'])} patrones exitosos."
    
    else:
        return "Comando no reconocido. Escribe 'ayuda' para ver comandos disponibles. Continuaré aprendiendo de cada operación."


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
            height: 300px;
            margin-top: 15px;
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
                <h3>Saldo</h3>
                <div class="stat" id="balance">$10,000.00</div>
            </div>
            <div class="card">
                <h3>Patrimonio</h3>
                <div class="stat" id="equity">$10,000.00</div>
            </div>
            <div class="card">
                <h3>Precio Actual</h3>
                <div class="stat" id="price">1.0850</div>
            </div>
            <div class="card">
                <h3>Operaciones Abiertas</h3>
                <div class="stat" id="trades">0</div>
            </div>
        </div>

        <div class="card">
            <h3>Controles de Operaciones</h3>
            <button class="btn btn-green" onclick="buy()">COMPRAR</button>
            <button class="btn btn-red" onclick="sell()">VENDER</button>
            <button class="btn btn-red" onclick="closeAll()">Cerrar Todo</button>
            <button class="btn" onclick="toggleAuto()">IA Automática</button>
            <div style="margin-top: 20px;">
                <strong style="color: #d4af37;">Estado de IA:</strong> <span id="auto-status" style="color: #27ae60;">INACTIVA</span>
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

        <div class="card">
            <h3>Gráfico de Precios</h3>
            <div class="chart-container">
                <canvas id="chart"></canvas>
            </div>
        </div>

        <div class="card">
            <h3>Análisis Inteligente de IA</h3>
            <div style="margin: 12px 0;"><strong style="color: #d4af37;">Señal:</strong> <span id="ai-signal" style="color: #27ae60;">ESPERA</span></div>
            <div style="margin: 12px 0;"><strong style="color: #d4af37;">Confianza:</strong> <span id="ai-confidence" style="color: #f39c12;">0%</span></div>
            <div style="margin: 12px 0;"><strong style="color: #d4af37;">Patrón:</strong> <span id="ai-pattern">-</span></div>
            <div style="margin: 12px 0;"><strong style="color: #d4af37;">Volatilidad:</strong> <span id="ai-volatility">-</span></div>
            <div style="margin: 12px 0;"><strong style="color: #d4af37;">Inteligencia IA:</strong> <span id="ai-learning" style="color: #3498db;">Aprendiendo...</span></div>
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

        function update() {
            fetch('/api/status')
                .then(r => r.json())
                .then(d => {
                    if (d.error) return;
                    
                    document.getElementById('balance').textContent = '$' + d.balance.toFixed(2);
                    document.getElementById('equity').textContent = '$' + d.equity.toFixed(2);
                    document.getElementById('price').textContent = d.price.toFixed(4);
                    document.getElementById('trades').textContent = d.trades_open;
                    document.getElementById('auto-status').textContent = d.auto_enabled ? 'ON' : 'OFF';

                    if (d.mt5) {
                        document.getElementById('mt5-status').textContent = d.mt5.connected ? 'Conectado' : 'Desconectado';
                        document.getElementById('mt5-login').textContent = d.mt5.login || '-';
                        document.getElementById('mt5-balance').textContent = d.mt5.balance ? '$' + d.mt5.balance.toFixed(2) : '-';
                        document.getElementById('mt5-equity').textContent = d.mt5.equity ? '$' + d.mt5.equity.toFixed(2) : '-';
                    }
                    
                    let html = '';
                    if (d.trades && d.trades.length > 0) {
                        d.trades.forEach(t => {
                            html += '<tr><td>#' + t.id + '</td><td>' + t.action + '</td><td>' + t.entry.toFixed(4) + '</td><td>' + (t.pl || 0).toFixed(2) + '</td></tr>';
                        });
                    } else {
                        html = '<tr><td colspan="4" style="text-align:center">-</td></tr>';
                    }
                    document.getElementById('trades-list').innerHTML = html;
                    
                    if (chart) chart.destroy();
                    drawChart(d.candles || []);
                    loadChat();
                    updateAIAnalysis();
                })
                .catch(e => console.error('Error:', e));
        }

        function drawChart(candles) {
            const ctx = document.getElementById('chart').getContext('2d');
            const useCandles = Array.isArray(candles) && candles.length > 0;
            const chartConfig = {
                type: useCandles ? 'candlestick' : 'line',
                data: {
                    labels: useCandles ? candles.map(c => c.x) : candles.map((_, i) => i),
                    datasets: [{
                        label: 'EURUSD',
                        data: useCandles ? candles : candles,
                        borderColor: '#60a5fa',
                        color: '#60a5fa',
                        upColor: '#22c55e',
                        downColor: '#ef4444',
                        borderWidth: 1,
                        backgroundColor: useCandles ? undefined : 'rgba(96, 165, 250, 0.18)',
                        fill: !useCandles,
                        tension: 0.2,
                        pointRadius: useCandles ? 0 : 0,
                        pointHoverRadius: 3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            mode: 'nearest',
                            intersect: false,
                            backgroundColor: 'rgba(15, 23, 42, 0.95)',
                            titleColor: '#f8fafc',
                            bodyColor: '#e2e8f0'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: false,
                            grid: {
                                color: 'rgba(148, 163, 184, 0.12)',
                                borderColor: 'rgba(148, 163, 184, 0.2)'
                            },
                            ticks: {
                                color: '#cbd5e1',
                                font: { size: 11 }
                            }
                        },
                        x: {
                            display: true,
                            grid: { display: false },
                            ticks: { color: '#94a3b8', font: { size: 10 } }
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
            chart = new Chart(ctx, chartConfig);
        }

        function buy() {
            fetch('/api/buy', { method: 'POST' })
                .then(r => r.json())
                .then(d => {
                    alert('Compra ejecutada a: ' + d.price.toFixed(4));
                    update();
                });
        }

        function sell() {
            fetch('/api/sell', { method: 'POST' })
                .then(r => r.json())
                .then(d => {
                    alert('Venta ejecutada a: ' + d.price.toFixed(4));
                    update();
                });
        }

        function closeAll() {
            fetch('/api/close-all', { method: 'POST' })
                .then(r => r.json())
                .then(d => {
                    alert('Se cerraron ' + d.closed + ' operaciones');
                    update();
                });
        }

        function toggleAuto() {
            fetch('/api/toggle-auto', { method: 'POST' })
                .then(r => r.json())
                .then(d => {
                    const estado = d.auto_enabled ? 'ACTIVA' : 'INACTIVA';
                    const color = d.auto_enabled ? '#27ae60' : '#e74c3c';
                    document.getElementById('auto-status').textContent = estado;
                    document.getElementById('auto-status').style.color = color;
                    alert('IA Automática: ' + estado);
                    update();
                });
        }

        function connectMT5() {
            const login = prompt('Ingrese el número de cuenta MT5:');
            if (!login) return;
            const password = prompt('Ingrese la contraseña MT5:');
            if (!password) return;
            const server = prompt('Ingrese el servidor MT5 (ej: ICMarketsDemoEU-05):');
            if (!server) return;

            fetch('/api/mt5/connect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ login, password, server })
            })
                .then(r => r.json())
                .then(d => {
                    if (d.success) {
                        alert('Conexión exitosa: ' + d.message);
                        document.getElementById('mt5-status').textContent = 'Conectado';
                        document.getElementById('mt5-status').style.color = '#27ae60';
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
                const el = document.createElement('div');
                el.style.marginBottom = '12px';
                el.style.padding = '10px';
                el.style.borderRadius = '6px';
                if (msg.sender === 'IA') {
                    el.style.background = 'rgba(212, 175, 55, 0.15)';
                    el.style.borderLeft = '3px solid #d4af37';
                    el.style.color = '#f0e68c';
                } else {
                    el.style.background = 'rgba(52, 152, 219, 0.15)';
                    el.style.borderLeft = '3px solid #3498db';
                    el.style.color = '#85c1e9';
                }
                el.innerHTML = `<strong style="color: ${msg.sender === 'IA' ? '#d4af37' : '#3498db'};">${msg.sender === 'IA' ? 'Sistema' : 'Tú'}:</strong> ${msg.text}`;
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
                    document.getElementById('ai-signal').textContent = signal;
                    document.getElementById('ai-signal').style.color = color;
                    document.getElementById('ai-confidence').textContent = (d.confidence || 0).toFixed(1) + '%';
                    document.getElementById('ai-pattern').textContent = d.pattern || '-';
                    document.getElementById('ai-volatility').textContent = d.volatility || '-';
                    const learning = (d.learning_progress || 0).toFixed(1) + '%';
                    document.getElementById('ai-learning').textContent = 'Aprendida: ' + learning;
                })
                .catch(e => console.error('Error en análisis de IA:', e));
        }

        update();
        setInterval(update, 1000);
    </script>
</body>
</html>
"""

# ====================================================================
# MAIN
# ====================================================================

def run_flask_app():
    preferred_ports = [5000, 5001, 8000, 8080]
    for port in preferred_ports:
        try:
            print(f"Intentando iniciar servidor en http://0.0.0.0:{port}")
            app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
            return
        except OSError as e:
            print(f"Puerto {port} no disponible: {e}")
    raise SystemExit("No se pudo iniciar el servidor en ningún puerto disponible.")

if __name__ == '__main__':
    print("\n" + "="*70)
    print("  TRADING SYSTEM - INICIANDO")
    print("="*70 + "\n")
    
    print("Servidor iniciando en http://0.0.0.0:5000")
    print("La conexión a MT5 se realiza desde la UI con /api/mt5/connect")
    print("\n" + "="*70 + "\n")
    
    try:
        webbrowser.open('http://127.0.0.1:5000')
    except:
        pass
    
    run_flask_app()
