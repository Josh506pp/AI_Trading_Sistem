#!/usr/bin/env python3
"""
Script de mejora automatizada para src/app.py
Aplica: selector de símbolos, IA mejorada, panel de predicción avanzada,
integración MT5 con detección de aliases y mejoras de UI.
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_PY = ROOT / "src" / "app.py"
BAK = ROOT / "src" / "app.py.bak2"

if not APP_PY.exists():
    print(f"No se encuentra {APP_PY}")
    sys.exit(1)

# Backup
shutil.copyfile(APP_PY, BAK)
print(f"Backup creado en {BAK}")

content = APP_PY.read_text(encoding="utf-8")

# ------------------------------------------------------------------
# 1. Imports de market_symbols
# ------------------------------------------------------------------
import_block = '''try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False

try:
    from .market_symbols import (
        list_symbols, get_symbol_config, normalize_symbol,
        get_simulation_params, format_price, POPULAR_SYMBOLS
    )
    SYMBOLS_AVAILABLE = True
except ImportError:
    try:
        from market_symbols import (
            list_symbols, get_symbol_config, normalize_symbol,
            get_simulation_params, format_price, POPULAR_SYMBOLS
        )
        SYMBOLS_AVAILABLE = True
    except ImportError:
        SYMBOLS_AVAILABLE = False
'''

old_import = '''try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False
'''

if old_import in content:
    content = content.replace(old_import, import_block)
    print("[OK] Imports de market_symbols añadidos")
else:
    print("[WARN] No se encontró bloque MT5 para reemplazar")

# ------------------------------------------------------------------
# 2. Reemplazar inicialización TRADING_DATA
# ------------------------------------------------------------------
old_trading_data = '''TRADING_DATA = {
    'price': 1.0850,
    'price_history': [1.0850 + i * 0.0001 + random.uniform(-0.0005, 0.0005) for i in range(50)],  # Tendencia gradual
    'balance': 10000.0,
    'equity': 10000.0,
    'trades_open': 0,
    'trades': [],
    'closed_trades': [],
    'auto_enabled': False,
    'use_prediction': True,
    'signal': {'action': 'HOLD', 'confidence': 0.0},
    'chat_history': [{'sender': 'IA', 'text': 'Hola! Bienvenido al sistema de trading. Soy tu asistente de IA.'}]
}'''

new_trading_data = '''SYMBOL_LIST = list(POPULAR_SYMBOLS.keys()) if SYMBOLS_AVAILABLE else ['EURUSD']
DEFAULT_SYMBOL = 'XAUUSD' if SYMBOLS_AVAILABLE and 'XAUUSD' in SYMBOL_LIST else (SYMBOL_LIST[0] if SYMBOL_LIST else 'EURUSD')
_sim_params = get_simulation_params(DEFAULT_SYMBOL) if SYMBOLS_AVAILABLE else {'default_price': 1.0850, 'volatility': 0.00008, 'decimals': 5}
_initial_price = float(_sim_params.get('default_price', 1.0850))
_initial_vol = float(_sim_params.get('volatility', 0.00008))
_initial_decimals = int(_sim_params.get('decimals', 5))

TRADING_DATA = {
    'symbol': DEFAULT_SYMBOL,
    'symbols': SYMBOL_LIST,
    'volume': 0.01,
    'price': round(_initial_price, _initial_decimals),
    'price_history': [round(_initial_price + i * (_initial_vol * 0.1) + random.uniform(-_initial_vol * 5, _initial_vol * 5), _initial_decimals) for i in range(50)],
    'balance': 10000.0,
    'equity': 10000.0,
    'trades_open': 0,
    'trades': [],
    'closed_trades': [],
    'auto_enabled': False,
    'use_prediction': True,
    'signal': {'action': 'HOLD', 'confidence': 0.0},
    'chat_history': [{'sender': 'IA', 'text': 'Hola! Bienvenido al sistema de trading. Soy tu asistente de IA.'}]
}


def get_symbol_format(symbol):
    """Devuelve decimales, pip_size, volatilidad, precio por defecto y volumen por defecto."""
    if SYMBOLS_AVAILABLE:
        cfg = get_symbol_config(symbol)
        if cfg:
            return cfg.decimals, cfg.pip_size, cfg.volatility, cfg.default_price, cfg.default_volume
    return 5, 0.0001, 0.00008, 1.0850, 0.01


def reset_price_history(symbol):
    """Reinicia el historial de precios para un símbolo."""
    decimals, pip_size, volatility, default_price, default_volume = get_symbol_format(symbol)
    TRADING_DATA['symbol'] = symbol
    TRADING_DATA['volume'] = default_volume
    TRADING_DATA['price'] = round(default_price, decimals)
    TRADING_DATA['price_history'] = [round(default_price + i * (volatility * 0.1) + random.uniform(-volatility * 5, volatility * 5), decimals) for i in range(50)]
    return decimals, volatility, default_price, default_volume'''

if old_trading_data in content:
    content = content.replace(old_trading_data, new_trading_data)
    print("[OK] TRADING_DATA actualizado con soporte de símbolos")
else:
    print("[WARN] No se encontró TRADING_DATA original")

# ------------------------------------------------------------------
# 3. Modificar update_prices: volatilidad por símbolo
# ------------------------------------------------------------------
old_update_body = '''                last = TRADING_DATA['price_history'][-1]
                # Movimientos realistas con volatilidad variable
                change = random.uniform(-0.00008, 0.00008)
                new_price = max(0.9, last + change)
                TRADING_DATA['price_history'].append(new_price)
                if len(TRADING_DATA['price_history']) > 200:
                    TRADING_DATA['price_history'].pop(0)
                TRADING_DATA['price'] = new_price'''

new_update_body = '''                symbol = TRADING_DATA.get('symbol', DEFAULT_SYMBOL)
                decimals, pip_size, volatility, default_price, _ = get_symbol_format(symbol)
                last = TRADING_DATA['price_history'][-1]
                # Movimientos realistas con volatilidad variable según símbolo
                change = random.uniform(-volatility, volatility)
                new_price = max(default_price * 0.5, last + change)
                new_price = round(new_price, decimals)
                TRADING_DATA['price_history'].append(new_price)
                if len(TRADING_DATA['price_history']) > 200:
                    TRADING_DATA['price_history'].pop(0)
                TRADING_DATA['price'] = new_price'''

if old_update_body in content:
    content = content.replace(old_update_body, new_update_body)
    print("[OK] update_prices adaptado por símbolo")
else:
    print("[WARN] No se encontró cuerpo de update_prices")

# ------------------------------------------------------------------
# 4. Reemplazar analyze_signal completa
# ------------------------------------------------------------------
old_analyze = '''def analyze_signal(prices):
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
    }'''

new_analyze = '''def _ema(prices, period):
    """Calcula EMA simple."""
    if len(prices) < period:
        return sum(prices) / len(prices) if prices else 0.0
    multiplier = 2.0 / (period + 1)
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = price * multiplier + ema * (1 - multiplier)
    return ema


def _stochastic(prices, k_period=14, d_period=3):
    """Calcula estocástico %K."""
    if len(prices) < k_period:
        return 50.0
    recent = prices[-k_period:]
    lowest = min(recent)
    highest = max(recent)
    current = prices[-1]
    if highest == lowest:
        return 50.0
    return ((current - lowest) / (highest - lowest)) * 100


def _atr(prices, period=14):
    """Calcula ATR simplificado."""
    if len(prices) < 2:
        return 0.001
    tr_list = [abs(prices[i] - prices[i - 1]) for i in range(1, len(prices))]
    return sum(tr_list[-period:]) / len(tr_list[-period:]) if tr_list else 0.001


def analyze_signal(prices, symbol=None):
    """Análisis inteligente con scoring ponderado multi-factor."""
    if len(prices) < 30:
        return {'action': 'ESPERA', 'confidence': 0.0, 'rsi': 50.0, 'trend': 'NEUTRAL',
                'macd': 0.0, 'bb': '0-0', 'ema_fast': 0.0, 'ema_slow': 0.0,
                'stochastic': 50.0, 'atr': 0.0, 'score': 0.0, 'pattern': {}}

    current = prices[-1]
    rsi = calculate_rsi(prices)
    macd_data = calculate_macd(prices)
    bb_data = calculate_bollinger_bands(prices)
    ema_fast = _ema(prices, 12)
    ema_slow = _ema(prices, 26)
    stochastic = _stochastic(prices)
    atr = _atr(prices)
    sma_long = sum(prices[-20:]) / 20
    trend = 'ALZA' if current > sma_long else 'BAJA' if current < sma_long else 'LATERAL'

    score = 0.0
    # RSI
    if rsi < 30:
        score += 30
    elif rsi < 40:
        score += 15
    elif rsi > 70:
        score -= 30
    elif rsi > 60:
        score -= 15
    # MACD
    if macd_data['histogram'] > 0:
        score += 20
    elif macd_data['histogram'] < 0:
        score -= 20
    # EMA cruzada
    if ema_fast > ema_slow:
        score += 15
    elif ema_fast < ema_slow:
        score -= 15
    # Stochastic
    if stochastic < 20:
        score += 15
    elif stochastic > 80:
        score -= 15
    # Bollinger
    if current < bb_data['lower']:
        score += 10
    elif current > bb_data['upper']:
        score -= 10
    # Momentum
    momentum = current - prices[-5]
    if momentum > atr * 1.5:
        score += 10
    elif momentum < -atr * 1.5:
        score -= 10

    # Aprendizaje de patrones
    learned_bonus = 0.0
    if AI_LEARNING_DB['successful_patterns']:
        for pattern in AI_LEARNING_DB['successful_patterns'][-10:]:
            if pattern.get('trend') == trend:
                learned_bonus += 5 * (pattern.get('success_rate', 0.5) or 0.5)
    score += max(-15, min(15, learned_bonus))

    if score > 30:
        action = 'COMPRA'
    elif score < -30:
        action = 'VENTA'
    else:
        action = 'ESPERA'
    confidence = min(0.98, abs(score) / 100.0)

    pattern_record = {
        'rsi': rsi, 'trend': trend, 'score': score, 'action': action,
        'confidence': confidence, 'atr': atr
    }

    return {
        'action': action,
        'confidence': confidence,
        'rsi': rsi,
        'trend': trend,
        'macd': macd_data['histogram'],
        'bb': f"{bb_data['lower']:.4f}-{bb_data['upper']:.4f}",
        'ema_fast': ema_fast,
        'ema_slow': ema_slow,
        'stochastic': stochastic,
        'atr': atr,
        'score': score,
        'pattern': pattern_record
    }'''

if old_analyze in content:
    content = content.replace(old_analyze, new_analyze)
    print("[OK] analyze_signal mejorado con scoring")
else:
    print("[WARN] No se encontró analyze_signal original")

# ------------------------------------------------------------------
# 5. Detectar símbolo MT5
# ------------------------------------------------------------------
detect_helper = '''

def detect_mt5_symbol(symbol):
    """Detecta el nombre exacto del símbolo en MT5 probando aliases."""
    if not MT5_AVAILABLE:
        return symbol
    if SYMBOLS_AVAILABLE:
        cfg = get_symbol_config(symbol)
        aliases = cfg.mt5_symbol_aliases if cfg else [symbol]
    else:
        aliases = [symbol]
    for alias in aliases:
        try:
            if mt5.symbol_select(alias, True):
                tick = mt5.symbol_info_tick(alias)
                if tick is not None:
                    return alias
        except Exception:
            continue
    return symbol

'''

# Insertar antes de get_candle_data
marker = "def get_candle_data(max_candles=40):"
if marker in content and "def detect_mt5_symbol" not in content:
    content = content.replace(marker, detect_helper + marker)
    print("[OK] detect_mt5_symbol añadido")
else:
    print("[WARN] No se pudo añadir detect_mt5_symbol")

# Modificar get_candle_data
old_candle = '''    if MT5_AVAILABLE and MT5_CONNECTED:
        try:
            symbol = TRADING_SYMBOL or 'EURUSD'
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, max_candles)'''
new_candle = '''    if MT5_AVAILABLE and MT5_CONNECTED:
        try:
            symbol = detect_mt5_symbol(TRADING_SYMBOL or TRADING_DATA.get('symbol', 'EURUSD'))
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, max_candles)'''
if old_candle in content:
    content = content.replace(old_candle, new_candle)
    print("[OK] get_candle_data usa detect_mt5_symbol")
else:
    print("[WARN] No se encontró get_candle_data para modificar")

# Modificar place_mt5_order
old_place = '''    symbol = TRADING_SYMBOL or 'EURUSD'
    volume = DEFAULT_VOLUME or 0.01
    if not mt5.symbol_select(symbol, True):'''
new_place = '''    symbol = detect_mt5_symbol(TRADING_SYMBOL or TRADING_DATA.get('symbol', 'EURUSD'))
    volume = TRADING_DATA.get('volume', DEFAULT_VOLUME or 0.01)
    if not mt5.symbol_select(symbol, True):'''
if old_place in content:
    content = content.replace(old_place, new_place)
    print("[OK] place_mt5_order usa detect_mt5_symbol y volumen UI")
else:
    print("[WARN] No se encontró place_mt5_order para modificar")

# Modificar close_all_mt5_positions
old_close = '''    symbol = TRADING_SYMBOL or 'EURUSD'
    positions = mt5.positions_get(symbol=symbol)'''
new_close = '''    symbol = detect_mt5_symbol(TRADING_SYMBOL or TRADING_DATA.get('symbol', 'EURUSD'))
    positions = mt5.positions_get(symbol=symbol)'''
if old_close in content:
    content = content.replace(old_close, new_close)
    print("[OK] close_all_mt5_positions usa detect_mt5_symbol")
else:
    print("[WARN] No se encontró close_all_mt5_positions para modificar")

# ------------------------------------------------------------------
# 6. api_status incluir symbol y volume
# ------------------------------------------------------------------
old_status = '''            'prices': TRADING_DATA['price_history'][-30:],
            'candles': get_candle_data(40),'''
new_status = '''            'symbol': TRADING_DATA.get('symbol', DEFAULT_SYMBOL),
            'volume': TRADING_DATA.get('volume', 0.01),
            'prices': TRADING_DATA['price_history'][-30:],
            'candles': get_candle_data(40),'''
if old_status in content:
    content = content.replace(old_status, new_status)
    print("[OK] api_status incluye symbol y volume")
else:
    print("[WARN] No se encontró api_status para modificar")

# ------------------------------------------------------------------
# 7. save_mt5_config_file incluir símbolo y volumen
# ------------------------------------------------------------------
old_save = '''def save_mt5_config_file(login, password, server, path=None):
    """Guarda las credenciales MT5 en el archivo mt5_config.py para uso persistente."""
    global MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, MT5_PATH, MT5_CREDENTIALS'''
new_save = '''def save_mt5_config_file(login, password, server, path=None, symbol=None, volume=None):
    """Guarda las credenciales MT5 en el archivo mt5_config.py para uso persistente."""
    global MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, MT5_PATH, MT5_CREDENTIALS, TRADING_SYMBOL, DEFAULT_VOLUME'''
if old_save in content:
    content = content.replace(old_save, new_save)
    print("[OK] save_mt5_config_file acepta symbol y volume")
else:
    print("[WARN] No se encontró save_mt5_config_file")

# Añadir actualización de TRADING_SYMBOL y DEFAULT_VOLUME dentro de save
old_save_update = '''        MT5_LOGIN = str(login).strip()
        MT5_PASSWORD = str(password)
        MT5_SERVER = str(server).strip()
        MT5_PATH = str(path).strip() if path else MT5_PATH'''
new_save_update = '''        MT5_LOGIN = str(login).strip()
        MT5_PASSWORD = str(password)
        MT5_SERVER = str(server).strip()
        MT5_PATH = str(path).strip() if path else MT5_PATH
        if symbol:
            TRADING_SYMBOL = normalize_symbol(symbol) if SYMBOLS_AVAILABLE else symbol.upper()
        if volume is not None:
            try:
                DEFAULT_VOLUME = float(volume)
            except Exception:
                pass'''
if old_save_update in content:
    content = content.replace(old_save_update, new_save_update)
    print("[OK] save_mt5_config_file actualiza TRADING_SYMBOL/DEFAULT_VOLUME")
else:
    print("[WARN] No se encontró cuerpo de save_mt5_config_file")

# Guardar símbolo/volumen en el archivo
old_content_str = '''        content = (
            "#!/usr/bin/env python3\\n"
            '"""MetaTrader5 Configuration File (auto-generated)"""\\n\\n"
            "# Auto-generated MT5 config\\n"
            f"MT5_LOGIN = {login_repr}\\n"
            f"MT5_PASSWORD = {password_repr}\\n"
            f"MT5_SERVER = {server_repr}\\n"
            f"MT5_PATH = {path_repr}\\n\\n"
            "# Defaults (preserved from original template)\\n"
            "TRADING_SYMBOL = \\"EURUSD\\"\\n"
            "DEFAULT_VOLUME = 0.01\\n"'''
new_content_str = '''        sym_repr = '"' + (normalize_symbol(symbol) if SYMBOLS_AVAILABLE and symbol else (symbol or TRADING_SYMBOL or 'EURUSD')).upper() + '"'
        vol_repr = str(DEFAULT_VOLUME)
        content = (
            "#!/usr/bin/env python3\\n"
            '"""MetaTrader5 Configuration File (auto-generated)"""\\n\\n"
            "# Auto-generated MT5 config\\n"
            f"MT5_LOGIN = {login_repr}\\n"
            f"MT5_PASSWORD = {password_repr}\\n"
            f"MT5_SERVER = {server_repr}\\n"
            f"MT5_PATH = {path_repr}\\n"
            f"TRADING_SYMBOL = {sym_repr}\\n"
            f"DEFAULT_VOLUME = {vol_repr}\\n\\n"
            "# Defaults\\n"'''
if old_content_str in content:
    content = content.replace(old_content_str, new_content_str)
    print("[OK] Contenido de mt5_config.py guarda símbolo/volumen")
else:
    print("[WARN] No se encontró string de contenido de mt5_config")

# ------------------------------------------------------------------
# 8. Añadir endpoints /api/symbols, /api/symbol, /api/advanced-prediction
# ------------------------------------------------------------------
endpoint_block = '''

@app.route('/api/symbols')
def api_symbols():
    """Lista los símbolos disponibles."""
    if SYMBOLS_AVAILABLE:
        return jsonify({'success': True, 'symbols': list_symbols(), 'current': TRADING_DATA.get('symbol', DEFAULT_SYMBOL)})
    return jsonify({'success': True, 'symbols': [{'name': 'EURUSD', 'display_name': 'Euro / Dólar', 'category': 'FOREX', 'default_price': 1.0850, 'default_volume': 0.01, 'decimals': 5, 'description': '', 'session_hours': ''}], 'current': 'EURUSD'})


@app.route('/api/symbol', methods=['POST'])
def api_set_symbol():
    """Cambia el símbolo activo."""
    global TRADING_SYMBOL, DEFAULT_VOLUME
    data = request.get_json(silent=True) or {}
    symbol = data.get('symbol', DEFAULT_SYMBOL)
    volume = data.get('volume')
    if SYMBOLS_AVAILABLE:
        symbol = normalize_symbol(symbol)
        cfg = get_symbol_config(symbol)
        if not cfg:
            return jsonify({'success': False, 'error': f'Símbolo {symbol} no soportado'}), 400
    symbol = symbol.upper()
    TRADING_SYMBOL = symbol
    reset_price_history(symbol)
    if volume is not None:
        try:
            vol = float(volume)
            if vol > 0:
                TRADING_DATA['volume'] = vol
                DEFAULT_VOLUME = vol
        except Exception:
            pass
    msg = f'Símbolo cambiado a {symbol}, volumen {TRADING_DATA["volume"]}'
    TRADING_DATA['chat_history'].append({'timestamp': datetime.now().isoformat(), 'sender': 'IA', 'text': msg})
    return jsonify({'success': True, 'symbol': symbol, 'volume': TRADING_DATA['volume'], 'price': TRADING_DATA['price']})


@app.route('/api/advanced-prediction')
def api_advanced_prediction():
    """Panel de predicción avanzada con todos los indicadores."""
    with PRICE_LOCK:
        prices = TRADING_DATA['price_history']
        symbol = TRADING_DATA.get('symbol', DEFAULT_SYMBOL)
        analysis = analyze_signal(prices, symbol)
        pred = {'predicted_price': prices[-1], 'expected_high': prices[-1], 'expected_low': prices[-1], 'confidence': 0.0, 'direction': 'NEUTRAL', 'volatility': 0.0}
        levels = {'support': 0, 'resistance': 0, 'pivot': 0, 'entry': prices[-1], 'stop_loss': prices[-1], 'take_profit': prices[-1]}
        if PREDICTION_AVAILABLE and prediction_engine:
            try:
                pred = prediction_engine.predict_price_range(prices, periods=5)
                levels = prediction_engine.get_trading_levels(prices)
            except Exception as e:
                print(f"Error predicción avanzada: {e}")
        else:
            if len(prices) >= 10:
                recent = prices[-50:]
                high = max(recent)
                low = min(recent)
                pivot = (high + low + prices[-1]) / 3
                atr = analysis.get('atr', 0.001) or 0.001
                levels = {
                    'support': (2 * pivot) - high,
                    'resistance': (2 * pivot) - low,
                    'pivot': pivot,
                    'entry': prices[-1],
                    'stop_loss': prices[-1] - atr * 2,
                    'take_profit': prices[-1] + atr * 2
                }
                pred = {
                    'predicted_price': prices[-1] + (prices[-1] - prices[-5]) if len(prices) >= 5 else prices[-1],
                    'expected_high': prices[-1] + atr * 3,
                    'expected_low': prices[-1] - atr * 3,
                    'confidence': analysis.get('confidence', 0),
                    'direction': 'ALCISTA' if analysis['action'] == 'COMPRA' else ('BAJISTA' if analysis['action'] == 'VENTA' else 'NEUTRAL'),
                    'volatility': atr
                }
        return jsonify({
            'success': True,
            'symbol': symbol,
            'signal': analysis['action'],
            'score': analysis.get('score', 0),
            'confidence': analysis['confidence'],
            'indicators': {
                'rsi': round(analysis['rsi'], 2),
                'macd': round(analysis['macd'], 6),
                'ema_fast': round(analysis['ema_fast'], 6),
                'ema_slow': round(analysis['ema_slow'], 6),
                'stochastic': round(analysis['stochastic'], 2),
                'atr': round(analysis['atr'], 6),
                'trend': analysis['trend'],
                'bb': analysis['bb']
            },
            'levels': {k: round(v, 6) if isinstance(v, float) else v for k, v in levels.items()},
            'prediction': {k: round(v, 6) if isinstance(v, float) else v for k, v in pred.items()},
            'timestamp': datetime.now().isoformat()
        })

'''

# Insertar antes de @app.route('/api/mt5/connect'
marker2 = "@app.route('/api/mt5/connect', methods=['POST'])"
if marker2 in content and "@app.route('/api/symbols')" not in content:
    content = content.replace(marker2, endpoint_block + marker2)
    print("[OK] Endpoints /api/symbols, /api/symbol, /api/advanced-prediction añadidos")
else:
    print("[WARN] No se pudieron añadir endpoints de símbolos")

# ------------------------------------------------------------------
# 9. Modificar UI DASHBOARD_HTML
# ------------------------------------------------------------------
# Añadir selector de símbolo y volumen en Controles de Operaciones
old_controls = '''        <div class="card">
            <h3>Controles de Operaciones</h3>
            <button class="btn btn-green" onclick="buy()">COMPRAR</button>
            <button class="btn btn-red" onclick="sell()">VENDER</button>
            <button class="btn btn-red" onclick="closeAll()">Cerrar Todo</button>
            <button class="btn" onclick="toggleAuto()">IA Automática</button>
            <button class="btn" onclick="togglePrediction()">Predicción Auto</button>'''

new_controls = '''        <div class="card">
            <h3>Controles de Operaciones</h3>
            <div style="margin-bottom: 15px; display: flex; gap: 12px; flex-wrap: wrap; align-items: center;">
                <label style="color:#d4af37; font-weight:600;">Símbolo:</label>
                <select id="symbol-select" onchange="changeSymbol(this.value)" style="padding: 8px 12px; background:#16213e; border:1px solid #d4af37; color:#e2e8f0; border-radius:6px;">
                    <option value="XAUUSD">XAUUSD (Oro)</option>
                    <option value="EURUSD">EURUSD</option>
                    <option value="GBPUSD">GBPUSD</option>
                    <option value="USDJPY">USDJPY</option>
                    <option value="US30">US30</option>
                    <option value="NAS100">NAS100</option>
                    <option value="BTCUSD">BTCUSD</option>
                    <option value="USDCHF">USDCHF</option>
                    <option value="AUDUSD">AUDUSD</option>
                    <option value="USOIL">USOIL</option>
                </select>
                <label style="color:#d4af37; font-weight:600;">Volumen:</label>
                <input id="volume-input" type="number" step="0.01" value="0.01" style="width:80px; padding:8px; background:#16213e; border:1px solid #d4af37; color:#e2e8f0; border-radius:6px;">
                <button class="btn" onclick="applyVolume()" style="padding:8px 16px;">Aplicar</button>
            </div>
            <button class="btn btn-green" onclick="buy()">COMPRAR</button>
            <button class="btn btn-red" onclick="sell()">VENDER</button>
            <button class="btn btn-red" onclick="closeAll()">Cerrar Todo</button>
            <button class="btn" onclick="toggleAuto()">IA Automática</button>
            <button class="btn" onclick="togglePrediction()">Predicción Auto</button>'''

if old_controls in content:
    content = content.replace(old_controls, new_controls)
    print("[OK] Selector de símbolo y volumen añadido")
else:
    print("[WARN] No se encontró Controles de Operaciones")

# Añadir panel de predicción avanzada antes de Operaciones Abiertas
old_pred_panel = '''        <div class="card">
            <h3>Predicciones y Niveles</h3>
            <div style="margin: 12px 0;"><strong style="color: #d4af37;">Predicción:</strong> <span id="pred-direction">-</span></div>
            <div style="margin: 12px 0;"><strong style="color: #d4af37;">Precio Previsto:</strong> <span id="pred-price">-</span></div>
            <div style="margin: 12px 0;"><strong style="color: #d4af37;">Confianza Predicción:</strong> <span id="pred-confidence">-</span></div>
            <div style="margin: 12px 0;"><strong style="color: #d4af37;">Entry:</strong> <span id="pred-entry">-</span>  <strong style="color: #d4af37; margin-left:12px;">SL:</strong> <span id="pred-sl">-</span>  <strong style="color: #d4af37; margin-left:12px;">TP:</strong> <span id="pred-tp">-</span></div>
        </div>

        <div class="card">
            <h3>Operaciones Abiertas</h3>'''

new_pred_panel = '''        <div class="card">
            <h3>Predicciones y Niveles</h3>
            <div style="margin: 12px 0;"><strong style="color: #d4af37;">Predicción:</strong> <span id="pred-direction">-</span></div>
            <div style="margin: 12px 0;"><strong style="color: #d4af37;">Precio Previsto:</strong> <span id="pred-price">-</span></div>
            <div style="margin: 12px 0;"><strong style="color: #d4af37;">Confianza Predicción:</strong> <span id="pred-confidence">-</span></div>
            <div style="margin: 12px 0;"><strong style="color: #d4af37;">Entry:</strong> <span id="pred-entry">-</span>  <strong style="color: #d4af37; margin-left:12px;">SL:</strong> <span id="pred-sl">-</span>  <strong style="color: #d4af37; margin-left:12px;">TP:</strong> <span id="pred-tp">-</span></div>
        </div>

        <div class="card">
            <h3>Predicción Avanzada de IA</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;">
                <div><strong style="color: #d4af37;">Señal Combinada:</strong> <span id="adv-signal">-</span></div>
                <div><strong style="color: #d4af37;">Score:</strong> <span id="adv-score">-</span></div>
                <div><strong style="color: #d4af37;">Confianza:</strong> <span id="adv-confidence">-</span></div>
                <div><strong style="color: #d4af37;">Tendencia:</strong> <span id="adv-trend">-</span></div>
                <div><strong style="color: #d4af37;">RSI:</strong> <span id="adv-rsi">-</span></div>
                <div><strong style="color: #d4af37;">MACD:</strong> <span id="adv-macd">-</span></div>
                <div><strong style="color: #d4af37;">EMA 12/26:</strong> <span id="adv-ema">-</span></div>
                <div><strong style="color: #d4af37;">Estocástico:</strong> <span id="adv-stoch">-</span></div>
                <div><strong style="color: #d4af37;">ATR:</strong> <span id="adv-atr">-</span></div>
                <div><strong style="color: #d4af37;">Soporte:</strong> <span id="adv-support">-</span></div>
                <div><strong style="color: #d4af37;">Resistencia:</strong> <span id="adv-resistance">-</span></div>
                <div><strong style="color: #d4af37;">Rango Esperado:</strong> <span id="adv-range">-</span></div>
                <div><strong style="color: #d4af37;">Próximo Precio:</strong> <span id="adv-next">-</span></div>
            </div>
        </div>

        <div class="card">
            <h3>Operaciones Abiertas</h3>'''

if old_pred_panel in content:
    content = content.replace(old_pred_panel, new_pred_panel)
    print("[OK] Panel de predicción avanzada añadido")
else:
    print("[WARN] No se encontró panel de predicciones")

# ------------------------------------------------------------------
# 10. Funciones JavaScript
# ------------------------------------------------------------------
# Actualizar update() para llamar loadSymbols y updateAdvancedPrediction
old_update_call = '''                    loadChat();
                    updateAIAnalysis();
                    updatePrediction();
                })'''
new_update_call = '''                    loadChat();
                    loadSymbols();
                    updateAIAnalysis();
                    updatePrediction();
                    updateAdvancedPrediction();
                })'''
if old_update_call in content:
    content = content.replace(old_update_call, new_update_call)
    print("[OK] update() llama a funciones nuevas")
else:
    print("[WARN] No se encontró llamada en update()")

# Añadir funciones JS al final antes de update();
old_script_end = '''        update();
        setInterval(update, 1000);
    </script>
</body>
</html>
"""'''

new_script_end = '''        function loadSymbols() {
            fetch('/api/symbols')
                .then(r => r.json())
                .then(d => {
                    if (!d.success) return;
                    const sel = document.getElementById('symbol-select');
                    if (sel && d.current && sel.value !== d.current) {
                        sel.value = d.current;
                    }
                })
                .catch(e => console.error('Error cargando símbolos:', e));
        }

        function changeSymbol(symbol) {
            const volume = parseFloat(document.getElementById('volume-input').value) || 0.01;
            fetch('/api/symbol', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbol, volume })
            })
                .then(r => r.json())
                .then(d => {
                    if (d.success) {
                        alert('Símbolo cambiado a ' + d.symbol + ' (volumen ' + d.volume + ')');
                        update();
                    } else {
                        alert('Error: ' + (d.error || ''));
                    }
                })
                .catch(e => alert('Error cambiando símbolo: ' + e.message));
        }

        function applyVolume() {
            const symbol = document.getElementById('symbol-select').value;
            changeSymbol(symbol);
        }

        function updateAdvancedPrediction() {
            fetch('/api/advanced-prediction')
                .then(r => r.json())
                .then(d => {
                    if (!d.success) return;
                    const sigEl = document.getElementById('adv-signal');
                    sigEl.textContent = d.signal || '-';
                    sigEl.style.color = d.signal === 'COMPRA' ? '#27ae60' : d.signal === 'VENTA' ? '#e74c3c' : '#f39c12';
                    document.getElementById('adv-score').textContent = (d.score || 0).toFixed(1);
                    document.getElementById('adv-confidence').textContent = ((d.confidence || 0) * 100).toFixed(1) + '%';
                    const ind = d.indicators || {};
                    document.getElementById('adv-trend').textContent = ind.trend || '-';
                    document.getElementById('adv-rsi').textContent = ind.rsi !== undefined ? ind.rsi.toFixed(2) : '-';
                    document.getElementById('adv-macd').textContent = ind.macd !== undefined ? ind.macd.toFixed(6) : '-';
                    document.getElementById('adv-ema').textContent = (ind.ema_fast !== undefined ? ind.ema_fast.toFixed(5) : '-') + ' / ' + (ind.ema_slow !== undefined ? ind.ema_slow.toFixed(5) : '-');
                    document.getElementById('adv-stoch').textContent = ind.stochastic !== undefined ? ind.stochastic.toFixed(2) : '-';
                    document.getElementById('adv-atr').textContent = ind.atr !== undefined ? ind.atr.toFixed(6) : '-';
                    const lvl = d.levels || {};
                    document.getElementById('adv-support').textContent = lvl.support !== undefined ? lvl.support.toFixed(5) : '-';
                    document.getElementById('adv-resistance').textContent = lvl.resistance !== undefined ? lvl.resistance.toFixed(5) : '-';
                    const pred = d.prediction || {};
                    document.getElementById('adv-next').textContent = pred.predicted_price !== undefined ? pred.predicted_price.toFixed(5) : '-';
                    const low = pred.expected_low !== undefined ? pred.expected_low.toFixed(5) : '-';
                    const high = pred.expected_high !== undefined ? pred.expected_high.toFixed(5) : '-';
                    document.getElementById('adv-range').textContent = low + ' - ' + high;
                })
                .catch(e => console.error('Error predicción avanzada:', e));
        }

        update();
        setInterval(update, 1000);
    </script>
</body>
</html>
"""'''

if old_script_end in content:
    content = content.replace(old_script_end, new_script_end)
    print("[OK] Funciones JavaScript añadidas")
else:
    print("[WARN] No se encontró final del script")

# ------------------------------------------------------------------
# Guardar y validar
# ------------------------------------------------------------------
APP_PY.write_text(content, encoding="utf-8")
print(f"[OK] Archivo escrito en {APP_PY}")

result = subprocess.run(
    [r"F:\Python311\python.exe", "-m", "py_compile", str(APP_PY)],
    capture_output=True, text=True
)

if result.returncode != 0:
    print("[ERROR] py_compile falló:")
    print(result.stdout)
    print(result.stderr)
    print("Restaurando backup...")
    shutil.copyfile(BAK, APP_PY)
    sys.exit(1)

print("[OK] Validación de sintaxis exitosa. Mejoras aplicadas.")
