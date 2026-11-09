#!/usr/bin/env python3
"""
TRADING SYSTEM - PLATAFORMA DE TRADING CON IA
Versión 2.0: Datos reales, usuarios, planes
"""

from flask import Flask, render_template_string, request, redirect, jsonify, session
import os
import sys
import time
import random
import threading
import socket
import webbrowser
import secrets
import math
import copy
import logging
import smtplib
import ssl
import hashlib
from email.message import EmailMessage
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import urlparse
from sqlalchemy.exc import IntegrityError

# Asegurar que el directorio src esté en el path para imports absolutos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

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

try:
    from .market_data import market_data, calculate_liquidity_metrics
    MARKET_DATA_AVAILABLE = True
except ImportError:
    try:
        from market_data import market_data, calculate_liquidity_metrics
        MARKET_DATA_AVAILABLE = True
    except ImportError:
        market_data = None
        calculate_liquidity_metrics = None
        MARKET_DATA_AVAILABLE = False

try:
    from .professional_trading_system import AIAnalyzer as ProAIAnalyzer
    PROFESSIONAL_AVAILABLE = True
except ImportError:
    ProAIAnalyzer = None
    PROFESSIONAL_AVAILABLE = False

try:
    from .prediction_system import prediction_engine
    PREDICTION_AVAILABLE = True
except ImportError:
    prediction_engine = None
    PREDICTION_AVAILABLE = False

try:
    from .technical_indicators import (
        calculate_bollinger_bands,
        calculate_macd,
        calculate_rsi,
    )
    from .trading_signals import build_prediction_signal as build_prediction_signal_uncached
    from .trading_signals import build_experimental_demo_signal
except ImportError:
    from technical_indicators import (
        calculate_bollinger_bands,
        calculate_macd,
        calculate_rsi,
    )
    from trading_signals import (
        build_experimental_demo_signal,
        build_prediction_signal as build_prediction_signal_uncached,
    )

try:
    from .demo_trading import (
        DEMO_MAX_LOSS_USD,
        DEMO_MAX_TARGET_PROFIT_USD,
        DEMO_MIN_TARGET_PROFIT_USD,
        DEMO_EARLY_CLOSE_PROFIT_USD,
        DEMO_MONITOR_MAX_SECONDS,
        DEMO_MAGIC,
        SUPPORTED_TEST_SYMBOLS,
        DemoTradeRejected,
        monitor_demo_position,
        prepare_demo_order,
        send_demo_order,
    )
except ImportError:
    from demo_trading import (
        DEMO_MAX_LOSS_USD,
        DEMO_MAX_TARGET_PROFIT_USD,
        DEMO_MIN_TARGET_PROFIT_USD,
        DEMO_EARLY_CLOSE_PROFIT_USD,
        DEMO_MONITOR_MAX_SECONDS,
        DEMO_MAGIC,
        SUPPORTED_TEST_SYMBOLS,
        DemoTradeRejected,
        monitor_demo_position,
        prepare_demo_order,
        send_demo_order,
    )

try:
    from . import paypal_payments
    from .paypal_payments import PayPalConfigurationError, PayPalProviderError
except ImportError:
    import paypal_payments
    from paypal_payments import PayPalConfigurationError, PayPalProviderError

logger = logging.getLogger(__name__)

try:
    from .models import (
        db, User, LoginSession, BillingHistory, PasswordResetToken,
        PaymentTransaction, PaymentWebhookEvent, init_db
    )
    DB_AVAILABLE = True
except ImportError:
    try:
        from models import (
            db, User, LoginSession, BillingHistory, PasswordResetToken,
            PaymentTransaction, PaymentWebhookEvent, init_db
        )
        DB_AVAILABLE = True
    except ImportError:
        db = None
        DB_AVAILABLE = False

try:
    from .security import (
        SecurityValidator, rate_limit, setup_cors, 
        log_security_event, CryptographyHelper
    )
    SECURITY_AVAILABLE = True
except ImportError:
    try:
        from security import (
            SecurityValidator, rate_limit, setup_cors,
            log_security_event, CryptographyHelper
        )
        SECURITY_AVAILABLE = True
    except ImportError:
        SECURITY_AVAILABLE = False
        SecurityValidator = None
        rate_limit = lambda x: lambda f: f  # dummy decorator


# Configuración global
TRADING_SYMBOL = os.environ.get('TRADING_SYMBOL', 'EURUSD')
DEFAULT_VOLUME = float(os.environ.get('DEFAULT_VOLUME', 0.01))

def resolve_flask_secret_key(environment):
    configured_secret = environment.get('FLASK_SECRET_KEY')
    if not configured_secret:
        if environment.get('FLASK_ENV', '').lower() == 'production':
            raise RuntimeError('FLASK_SECRET_KEY must be configured in production.')
        return secrets.token_urlsafe(48)
    if len(configured_secret) < 32 and environment.get('FLASK_ENV', '').lower() == 'production':
        raise RuntimeError('FLASK_SECRET_KEY must contain at least 32 characters in production.')
    return configured_secret


def resolve_database_path(environment, default_path):
    return os.path.abspath(environment.get('DATABASE_PATH') or default_path)


app = Flask(__name__)
app.secret_key = resolve_flask_secret_key(os.environ)

# Configuración de base de datos
default_db_path = os.path.join(os.path.dirname(__file__), '..', 'trading_platform.db')
db_path = resolve_database_path(os.environ, default_db_path)
os.makedirs(os.path.dirname(db_path), exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path.replace(os.sep, '/')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024

if DB_AVAILABLE:
    db.init_app(app)
    with app.app_context():
        try:
            init_db(app)
        except Exception as e:
            print(f"Error inicializando BD: {e}")

app.config.update({
    'SESSION_COOKIE_HTTPONLY': True,
    'SESSION_COOKIE_SAMESITE': 'Lax',
    'SESSION_COOKIE_SECURE': os.environ.get('FLASK_ENV') == 'production'
})

# Configurar CORS y seguridad
if SECURITY_AVAILABLE:
    setup_cors(app)

# ====================================================================
# DATOS GLOBALES
# ====================================================================

SYMBOL_LIST = list(POPULAR_SYMBOLS.keys()) if SYMBOLS_AVAILABLE else ['EURUSD']
DEFAULT_SYMBOL = 'XAUUSD' if SYMBOLS_AVAILABLE else 'EURUSD'
_sim_params = get_simulation_params(DEFAULT_SYMBOL) if SYMBOLS_AVAILABLE else {'default_price': 1.0850, 'volatility': 0.00008, 'decimals': 5}
_initial_price = float(_sim_params.get('default_price', 1.0850))
_initial_vol = float(_sim_params.get('volatility', 0.00008))
_initial_decimals = int(_sim_params.get('decimals', 5))
_initial_price_history = [
    round(_initial_price + i * (_initial_vol * 0.1) + random.uniform(-_initial_vol * 5, _initial_vol * 5), _initial_decimals)
    for i in range(49)
]
_initial_price_history.append(round(_initial_price, _initial_decimals))

TRADING_DATA = {
    'symbol': DEFAULT_SYMBOL,
    'symbols': SYMBOL_LIST,
    'volume': 0.01,
    'price': round(_initial_price, _initial_decimals),
    'price_history': _initial_price_history,
    'price_updated_at': None,
    'price_source': None,
    'recent_ticks': [],
    'market_candles': [],
    'liquidity': {'available': False, 'flow_bias': 'SIN DATOS'},
    'balance': 10000.0,
    'equity': 10000.0,
    'trades_open': 0,
    'trades': [],
    'closed_trades': [],
    'auto_enabled': False,
    'use_prediction': True,
    'signal': {'action': 'HOLD', 'confidence': 0.0},
    'alerts': [],
    'news': []
}
CHAT_HISTORY_BY_USER = {}
DEMO_CHAT_TRADE_JOBS = {}
_demo_chat_trade_jobs_lock = threading.Lock()


def _update_demo_chat_trade_job(job_id, status, message, **fields):
    with _demo_chat_trade_jobs_lock:
        job = DEMO_CHAT_TRADE_JOBS.get(job_id)
        if not job:
            return
        job.update(fields)
        job['status'] = status
        job['message'] = message
        job['updated_at'] = datetime.utcnow().isoformat() + 'Z'
        user_id = job['user_id']

    if status not in ('queued', 'running'):
        with PRICE_LOCK:
            get_chat_history(user_id).append({
                'sender': 'IA',
                'text': message,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })


def get_demo_chat_trade_job(job_id, user_id):
    with _demo_chat_trade_jobs_lock:
        job = DEMO_CHAT_TRADE_JOBS.get(job_id)
        if not job or job['user_id'] != user_id:
            return None
        return {
            key: value for key, value in job.items()
            if key != 'user_id'
        }


def start_demo_chat_trade_job(user_id, symbol):
    if symbol not in SUPPORTED_TEST_SYMBOLS:
        raise ValueError('El símbolo debe ser EURUSD o XAUUSD.')

    job_id = secrets.token_urlsafe(16)
    with _demo_chat_trade_jobs_lock:
        if any(
            job['status'] in ('queued', 'running')
            for job in DEMO_CHAT_TRADE_JOBS.values()
        ):
            raise RuntimeError('Ya hay una operación demo automática en curso.')
        DEMO_CHAT_TRADE_JOBS[job_id] = {
            'job_id': job_id,
            'user_id': user_id,
            'symbol': symbol,
            'status': 'queued',
            'message': 'Solicitud recibida; comprobando cuenta demo y señal.',
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'updated_at': datetime.utcnow().isoformat() + 'Z'
        }
        worker = threading.Thread(
            target=_run_demo_chat_trade_job,
            args=(job_id, user_id, symbol),
            name=f'demo-trade-{job_id[:8]}',
            daemon=True
        )
        try:
            worker.start()
        except Exception:
            DEMO_CHAT_TRADE_JOBS.pop(job_id, None)
            raise
    return job_id


def _run_demo_chat_trade_job(job_id, user_id, symbol):
    order_ticket = None
    try:
        with app.app_context():
            try:
                user = db.session.get(User, user_id) if DB_AVAILABLE else None
                if (
                    user is None or user.subscription_plan != 'PREMIUM' or
                    not user.has_active_subscription() or
                    not has_verified_paid_subscription(user)
                ):
                    raise DemoTradeRejected(
                        'El comando de operación demo requiere una suscripción PREMIUM activa.'
                    )
            finally:
                if DB_AVAILABLE:
                    db.session.remove()

        provider = market_data if MARKET_DATA_AVAILABLE else None
        mt5 = getattr(provider, 'mt5', None) if provider else None
        if mt5 is None or not provider._ensure_mt5():
            raise DemoTradeRejected('No hay una sesión conectada de MetaTrader 5.')

        terminal = mt5.terminal_info()
        account = mt5.account_info()
        if (
            terminal is None or account is None or
            account.trade_mode != getattr(mt5, 'ACCOUNT_TRADE_MODE_DEMO', 0) or
            not getattr(terminal, 'connected', False) or
            not getattr(terminal, 'trade_allowed', False) or
            getattr(terminal, 'tradeapi_disabled', True) or
            not getattr(account, 'trade_allowed', False) or
            getattr(account, 'currency', None) != 'USD'
        ):
            raise DemoTradeRejected(
                'Se requiere una cuenta MT5 demo USD conectada con Algo Trading habilitado.'
            )

        positions = mt5.positions_get()
        pending_orders = mt5.orders_get()
        if positions is None or pending_orders is None:
            raise DemoTradeRejected(
                f'No se pudo comprobar la exposición actual de MT5: {mt5.last_error()}'
            )
        if positions or pending_orders:
            raise DemoTradeRejected(
                'No se inicia otra operación mientras la cuenta tenga posiciones u órdenes abiertas.'
            )

        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 200)
        if rates is None or len(rates) < 60:
            raise DemoTradeRejected(f'MT5 no entregó suficientes velas M1 para {symbol}.')
        prices = [float(rate['close']) for rate in rates]
        signal = build_experimental_demo_signal(
            prices, periods=PREDICTION_HORIZON_MINUTES, engine=prediction_engine
        )
        plan = prepare_demo_order(
            mt5,
            symbol,
            signal,
            int(rates[-1]['time']),
            max_loss_usd=DEMO_MAX_LOSS_USD,
            allow_unconfirmed_direction=True,
            target_profit_range=(
                DEMO_MIN_TARGET_PROFIT_USD,
                DEMO_MAX_TARGET_PROFIT_USD
            )
        )

        positions = mt5.positions_get()
        pending_orders = mt5.orders_get()
        if positions is None or pending_orders is None:
            raise DemoTradeRejected(
                f'No se pudo revalidar la exposición antes de enviar: {mt5.last_error()}'
            )
        if positions or pending_orders:
            raise DemoTradeRejected(
                'Se detectó una posición u orden abierta antes del envío; no se operó.'
            )

        _update_demo_chat_trade_job(
            job_id,
            'running',
            f'Señal {signal["signal"]} validada para demo. Enviando una sola orden; '
            f'TP estimado ${plan.estimated_target_usd:.2f}, '
            f'riesgo estimado al SL ${plan.estimated_stop_loss_usd:.2f}.',
            direction=signal['signal'],
            volume=plan.volume,
            target_goal_usd=plan.target_goal_usd,
            estimated_target_usd=plan.estimated_target_usd,
            estimated_stop_loss_usd=plan.estimated_stop_loss_usd,
            estimated_risk_reward=plan.estimated_risk_reward
        )
        result = send_demo_order(mt5, symbol, plan)
        order_ticket = int(getattr(result, 'order', 0))
        if not order_ticket:
            matches = [
                position for position in (mt5.positions_get(symbol=symbol) or ())
                if int(getattr(position, 'magic', 0)) == DEMO_MAGIC
            ]
            if len(matches) == 1:
                order_ticket = int(matches[0].ticket)
        if not order_ticket:
            raise DemoTradeRejected(
                'MT5 aceptó la orden, pero no se pudo identificar la posición para monitorearla; '
                'verifica el TP/SL desde el terminal.'
            )

        _update_demo_chat_trade_job(
            job_id,
            'running',
            f'Orden demo {order_ticket} abierta; esperando TP/SL o giro confirmado.',
            order_id=order_ticket
        )
        monitor_result = monitor_demo_position(
            mt5,
            symbol,
            order_ticket,
            prediction_engine,
            min_profit_usd=DEMO_EARLY_CLOSE_PROFIT_USD,
            max_wait_seconds=DEMO_MONITOR_MAX_SECONDS
        )

        if monitor_result['status'] == 'still_open_with_server_sl_tp':
            _update_demo_chat_trade_job(
                job_id,
                'timed_out_open',
                'Terminó la ventana de monitoreo. La posición sigue abierta con TP/SL en MT5; '
                'no se abrió otra operación.',
                order_id=order_ticket,
                outcome=monitor_result
            )
            return

        deals = mt5.history_deals_get(position=order_ticket)
        net_profit = None
        if deals is not None:
            net_profit = round(sum(
                float(deal.profit) + float(deal.commission) +
                float(deal.swap) + float(getattr(deal, 'fee', 0.0))
                for deal in deals
            ), 2)
        result_text = (
            f'Operación demo {order_ticket} cerrada ({monitor_result["status"]}).'
        )
        if net_profit is not None:
            result_text += f' PnL neto registrado: ${net_profit:.2f}.'
        _update_demo_chat_trade_job(
            job_id,
            'completed',
            result_text,
            order_id=order_ticket,
            outcome=monitor_result,
            net_profit_usd=net_profit
        )
    except DemoTradeRejected as exc:
        _update_demo_chat_trade_job(
            job_id,
            'rejected',
            f'No se abrió una operación demo: {exc}',
            error=str(exc),
            order_id=order_ticket
        )
    except Exception as exc:
        logger.exception('Error en operación demo solicitada desde el chat.')
        message = f'Error durante la operación demo: {type(exc).__name__}.'
        if order_ticket:
            message += ' Verifica en MT5 que la posición conserve su TP y SL.'
        _update_demo_chat_trade_job(
            job_id,
            'error',
            message,
            error=type(exc).__name__,
            order_id=order_ticket
        )


def get_chat_history(user_id):
    return CHAT_HISTORY_BY_USER.setdefault(
        user_id,
        [{'sender': 'IA', 'text': 'Hola! Bienvenido al sistema de trading. Soy tu asistente de IA.'}]
    )

# Configuración de alertas de volatilidad
ALERT_CONFIG = {
    'price_spike_pct': 0.15,       # % mínimo de movimiento brusco en ventana corta
    'volatility_window': 10,       # puntos del historial para medir spike
    'atr_spike_multiplier': 2.5,   # ATR actual > media ATR * multiplicador
    'max_alerts': 50,              # máximo de alertas guardadas
    'cooldown_seconds': 30         # tiempo mínimo entre alertas similares
}

_LAST_ALERT_TIME = {}

NEWS_TEMPLATES = {
    'XAUUSD': [
        {'title': 'El oro se dispara ante la caída del dólar y la aversión al riesgo', 'impact': 'alto', 'source': 'Market Pulse'},
        {'title': 'Reservas de oro de los bancos centrales alcanzan máximos históricos', 'impact': 'medio', 'source': 'FX Insights'},
        {'title': 'Tensiones geopolíticas impulsan la demanda de activos refugio', 'impact': 'alto', 'source': 'Global Macro'},
        {'title': 'Datos de inflación de EE.UU. generan volatilidad en metales preciosos', 'impact': 'alto', 'source': 'Economic Calendar'},
    ],
    'EURUSD': [
        {'title': 'El BCE deja entrever posibles recortes de tipos en próximas reuniones', 'impact': 'alto', 'source': 'Euro FX'},
        {'title': 'Dólar se debilita tras decepcionantes datos de empleo en EE.UU.', 'impact': 'alto', 'source': 'Market Pulse'},
        {'title': 'Zona euro publica cifras de manufactura mejor de lo esperado', 'impact': 'medio', 'source': 'Economic Calendar'},
        {'title': 'Paridad euro/dólar en foco por diferencial de tipos', 'impact': 'medio', 'source': 'FX Insights'},
    ],
    'GBPUSD': [
        {'title': 'El Banco de Inglaterra mantiene tipos en máximos de ciclo', 'impact': 'alto', 'source': 'Sterling Watch'},
        {'title': 'Libra recupera terreno tras datos de crecimiento del Reino Unido', 'impact': 'medio', 'source': 'Market Pulse'},
        {'title': 'Incertidumbre política en UK presiona a la libra esterlina', 'impact': 'medio', 'source': 'Global Macro'},
    ],
    'USDJPY': [
        {'title': 'El Banco de Japón insinúa salida de política ultrafloja', 'impact': 'alto', 'source': 'Yen Desk'},
        {'title': 'Diferencial de tipos USD/JPY se estrecha rápidamente', 'impact': 'alto', 'source': 'FX Insights'},
        {'title': 'Intervención verbal del Ministerio de Finanzas de Japón', 'impact': 'medio', 'source': 'Market Pulse'},
    ],
    'US30': [
        {'title': 'Wall Street abre con fuerte volatilidad tras datos macro', 'impact': 'alto', 'source': 'Equities Desk'},
        {'title': 'Resultados corporativos del Dow Jones superan expectativas', 'impact': 'medio', 'source': 'Market Pulse'},
        {'title': 'Temor recesivo arrastra al Dow Jones en sesión asiática', 'impact': 'alto', 'source': 'Global Macro'},
    ],
    'NAS100': [
        {'title': 'Tecnológicas del Nasdaq impulsan el índice tras reportes trimestrales', 'impact': 'alto', 'source': 'Tech Trader'},
        {'title': 'Rendimientos del Tesoro afectan a valores de crecimiento del Nasdaq', 'impact': 'medio', 'source': 'Market Pulse'},
        {'title': 'Nuevo récord histórico para el Nasdaq 100', 'impact': 'medio', 'source': 'Global Macro'},
    ],
    'BTCUSD': [
        {'title': 'Bitcoin rompe resistencia clave con volumen récord', 'impact': 'alto', 'source': 'Crypto Desk'},
        {'title': 'Entradas masivas en ETFs de Bitcoin impulsan al alza', 'impact': 'alto', 'source': 'CoinWatch'},
        {'title': 'Reguladores estadounidenses aclaran normativa para criptoactivos', 'impact': 'medio', 'source': 'Crypto News'},
    ],
    'USDCHF': [
        {'title': 'El franco suizo se fortalece como refugio ante la incertidumbre', 'impact': 'medio', 'source': 'FX Insights'},
        {'title': 'SNB interviene para moderar la apreciación del franco', 'impact': 'alto', 'source': 'Market Pulse'},
    ],
    'AUDUSD': [
        {'title': 'Australia publica datos de empleo sólidos; el dólar australiano repunta', 'impact': 'medio', 'source': 'Aussie FX'},
        {'title': 'Precios de materias primas impulsan al dólar australiano', 'impact': 'medio', 'source': 'Global Macro'},
    ],
    'USOIL': [
        {'title': 'El petróleo WTI sube ante recortes de producción de la OPEP+', 'impact': 'alto', 'source': 'Energy Desk'},
        {'title': 'Reservas de crudo de EE.UU. caen más de lo previsto', 'impact': 'medio', 'source': 'Market Pulse'},
        {'title': 'Tensiones en el Golfo Pérsico elevan el precio del crudo', 'impact': 'alto', 'source': 'Global Macro'},
    ]
}

GENERIC_NEWS = [
    {'title': 'Los mercados globales operan con nerviosismo antes de datos clave', 'impact': 'medio', 'source': 'Market Pulse'},
    {'title': 'Índices asiáticos cierran mixtos; Europa a la espera de apertura', 'impact': 'bajo', 'source': 'Global Macro'},
    {'title': 'El dólar index mantiene rango estrecho en sesión europea', 'impact': 'bajo', 'source': 'FX Insights'},
    {'title': 'Los operadores ajustan posiciones antes del fin de semana', 'impact': 'bajo', 'source': 'Trading Desk'},
]


def _get_symbol_news(symbol):
    """Devuelve noticias relevantes para el símbolo activo."""
    symbol = normalize_symbol(symbol) if SYMBOLS_AVAILABLE else symbol.upper()
    templates = NEWS_TEMPLATES.get(symbol, GENERIC_NEWS)
    now = datetime.now()
    news = []
    for i, item in enumerate(templates[:6]):
        news.append({
            'title': item['title'],
            'impact': item['impact'],
            'source': item['source'],
            'time': (now.replace(minute=max(0, now.minute - i * 12))).strftime('%H:%M'),
            'symbol': symbol
        })
    # Mezclar noticias genéricas para dar sensación de feed en vivo
    for i, item in enumerate(random.sample(GENERIC_NEWS, min(2, len(GENERIC_NEWS)))):
        news.append({
            'title': item['title'],
            'impact': item['impact'],
            'source': item['source'],
            'time': (now.replace(minute=max(0, now.minute - (i + 5) * 15))).strftime('%H:%M'),
            'symbol': 'GLOBAL'
        })
    random.shuffle(news)
    return news[:8]


def _calculate_volatility_metrics(prices, decimals=5):
    """Calcula métricas de volatilidad: spike, ATR relativo, rango."""
    if len(prices) < ALERT_CONFIG['volatility_window'] + 5:
        return {'spike_pct': 0.0, 'atr': 0.0, 'atr_ratio': 1.0, 'range_pct': 0.0}
    current = prices[-1]
    window_start = prices[-ALERT_CONFIG['volatility_window']]
    spike_pct = abs(current - window_start) / window_start * 100 if window_start != 0 else 0.0

    tr_list = [abs(prices[i] - prices[i - 1]) for i in range(1, len(prices))]
    atr_current = sum(tr_list[-ALERT_CONFIG['volatility_window']:]) / ALERT_CONFIG['volatility_window']
    atr_mean = sum(tr_list[-50:]) / min(50, len(tr_list)) if tr_list else atr_current
    atr_ratio = (atr_current / atr_mean) if atr_mean > 0 else 1.0

    recent = prices[-50:]
    range_pct = (max(recent) - min(recent)) / current * 100 if current != 0 else 0.0
    return {
        'spike_pct': round(spike_pct, 4),
        'atr': round(atr_current, decimals),
        'atr_ratio': round(atr_ratio, 3),
        'range_pct': round(range_pct, 4)
    }


def _can_trigger(alert_type):
    """Controla cooldown entre alertas del mismo tipo."""
    global _LAST_ALERT_TIME
    now = time.time()
    last = _LAST_ALERT_TIME.get(alert_type, 0)
    if now - last < ALERT_CONFIG['cooldown_seconds']:
        return False
    _LAST_ALERT_TIME[alert_type] = now
    return True


def _add_alert(level, alert_type, title, message):
    """Añade una alerta al historial manteniendo límite máximo."""
    alert = {
        'id': int(time.time() * 1000),
        'timestamp': datetime.now().isoformat(),
        'level': level,  # critica, alta, media, baja
        'type': alert_type,  # volatilidad, noticia, breakout, oportunidad
        'title': title,
        'message': message,
        'symbol': TRADING_DATA.get('symbol', DEFAULT_SYMBOL)
    }
    TRADING_DATA['alerts'].insert(0, alert)
    if len(TRADING_DATA['alerts']) > ALERT_CONFIG['max_alerts']:
        TRADING_DATA['alerts'].pop()
    return alert


def check_market_alerts():
    """Evalúa condiciones de mercado y genera alertas/noticias.
    NOTA: debe llamarse dentro de un bloque con PRICE_LOCK ya adquirido."""
    symbol = TRADING_DATA.get('symbol', DEFAULT_SYMBOL)
    decimals, pip_size, volatility, default_price, _ = get_symbol_format(symbol)
    prices = TRADING_DATA['price_history']
    if len(prices) < 20:
        return

    metrics = _calculate_volatility_metrics(prices, decimals)
    current = prices[-1]

    # Alerta de movimiento brusco
    if metrics['spike_pct'] >= ALERT_CONFIG['price_spike_pct'] and _can_trigger('spike'):
        direction = 'ALCISTA' if current > prices[-ALERT_CONFIG['volatility_window']] else 'BAJISTA'
        _add_alert(
            'alta' if metrics['spike_pct'] >= 0.35 else 'media',
            'volatilidad',
            f'Movimiento brusco {direction} en {symbol}',
            f'El precio se movió {metrics["spike_pct"]:.3f}% en los últimos {ALERT_CONFIG["volatility_window"]} ticks. ATR: {metrics["atr"]}'
        )

    # Alerta de ATR elevado
    if metrics['atr_ratio'] >= ALERT_CONFIG['atr_spike_multiplier'] and _can_trigger('atr'):
        _add_alert(
            'alta',
            'volatilidad',
            f'Volatilidad extrema detectada en {symbol}',
            f'El ATR actual es {metrics["atr_ratio"]:.1f}x superior a la media reciente. Rango 50 ticks: {metrics["range_pct"]:.3f}%'
        )

    # Alerta de oportunidad tras rango acumulado amplio
    if metrics['range_pct'] >= 1.2 and metrics['spike_pct'] >= 0.10 and _can_trigger('range_opportunity'):
        direction = 'COMPRA' if prices[-1] > sum(prices[-10:]) / 10 else 'VENTA'
        _add_alert(
            'media',
            'oportunidad',
            f'Posible oportunidad de {direction} en {symbol}',
            f'Rango ampliado del {metrics["range_pct"]:.3f}% con momentum. Evalúa entrada en {direction}.'
        )

    # Actualizar feed de noticias periódicamente
    if not TRADING_DATA['news'] or random.random() < 0.05:
        TRADING_DATA['news'] = _get_symbol_news(symbol)


def get_recent_alerts(limit=20):
    """Devuelve las alertas más recientes."""
    return TRADING_DATA['alerts'][:limit]


def get_symbol_format(symbol):
    """Devuelve decimales, pip_size, volatilidad, precio por defecto y volumen por defecto."""
    if SYMBOLS_AVAILABLE:
        cfg = get_symbol_config(symbol)
        if cfg:
            return cfg.decimals, cfg.pip_size, cfg.volatility, cfg.default_price, cfg.default_volume
    return 5, 0.0001, 0.00008, 1.0850, 0.01


def reset_price_history(symbol):
    """Reinicia el historial de precios para un símbolo con datos reales de mercado."""
    decimals, pip_size, volatility, default_price, default_volume = get_symbol_format(symbol)
    intraday = []
    if MARKET_DATA_AVAILABLE and market_data:
        try:
            intraday = market_data.get_intraday_prices(symbol, count=50)
        except Exception as e:
            print(f"Error fetching real prices for reset: {e}")

    with PRICE_LOCK:
        TRADING_DATA['symbol'] = symbol
        TRADING_DATA['volume'] = default_volume
        if intraday:
            TRADING_DATA['price_history'] = intraday
            TRADING_DATA['price'] = intraday[-1]
        else:
            TRADING_DATA['price'] = round(default_price, decimals)
            TRADING_DATA['price_history'] = [TRADING_DATA['price']] * 50
        TRADING_DATA['price_updated_at'] = None
        TRADING_DATA['price_source'] = None
        TRADING_DATA['recent_ticks'] = []
        TRADING_DATA['market_candles'] = []
        TRADING_DATA['liquidity'] = {'available': False, 'flow_bias': 'SIN DATOS'}
        invalidate_prediction_cache(symbol)
        return decimals, volatility, TRADING_DATA['price'], default_volume

PRICE_LOCK = threading.Lock()

# Modo simulación: todas las operaciones se ejecutan localmente
SIMULATION_MODE = True

# IA Profesional Mejorada
if PROFESSIONAL_AVAILABLE:
    PRO_AI_ANALYZER = ProAIAnalyzer()
else:
    PRO_AI_ANALYZER = None




# ====================================================================
# SISTEMA INTELIGENTE DE ANÁLISIS Y APRENDIZAJE DE IA
# ====================================================================

def _ema(prices, period):
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
    }


PREDICTION_COOLDOWN_SECONDS = 15
FREE_ANALYSIS_COOLDOWN_SECONDS = 900
PAID_ANALYSIS_COOLDOWN_SECONDS = 300
PREDICTION_HORIZON_MINUTES = 10
PREMIUM_ANALYSIS_COOLDOWN_SECONDS = 300
ADVANCED_PREDICTION_COOLDOWN_SECONDS = {'PRO': 300, 'PREMIUM': 120}
_prediction_cache = {}
_prediction_cache_lock = threading.Lock()
_advanced_prediction_cache = {}
_advanced_prediction_cache_lock = threading.Lock()
_user_prediction_cache = {}
_user_prediction_cache_lock = threading.Lock()
_basic_analysis_cache = {}
_basic_analysis_cache_lock = threading.Lock()
_professional_analysis_cache = {}
_professional_analysis_cache_lock = threading.Lock()


def get_cached_analysis(user_id, symbol, prices, plan='FREE'):
    """Cachea el análisis básico usando la cuota de refresco del plan."""
    cache_key = (user_id, symbol, plan)
    cooldown = (
        FREE_ANALYSIS_COOLDOWN_SECONDS
        if plan == 'FREE'
        else PAID_ANALYSIS_COOLDOWN_SECONDS
    )
    now = time.monotonic()
    with _basic_analysis_cache_lock:
        cached = _basic_analysis_cache.get(cache_key)
        if cached and now - cached['created_at'] < cooldown:
            result = copy.deepcopy(cached['result'])
            result['analysis_cache'] = {
                'status': 'cached',
                'cooldown_seconds': cooldown,
                'remaining_seconds': max(
                    0, math.ceil(cooldown - (now - cached['created_at']))
                ),
                'calculated_at': cached['calculated_at']
            }
            return result

        analysis = analyze_signal(prices, symbol)
        calculated_at = datetime.utcnow().isoformat() + 'Z'
        response = {
            'success': True,
            'available': True,
            'symbol': symbol,
            'signal': analysis['action'],
            'confidence': analysis['confidence'],
            'confidence_percent': round(analysis['confidence'] * 100, 1),
            'pattern': analysis['trend'],
            'volatility': (
                'ALTA' if analysis['atr'] / max(abs(prices[-1]), 1e-12) >= 0.001
                else 'BAJA'
            ) if prices else 'SIN DATOS',
            'indicators': {
                'rsi': round(analysis['rsi'], 2),
                'trend': analysis['trend'],
                'momentum': 'FUERTE' if abs(prices[-1] - prices[-5]) > 0.002 else 'DÉBIL',
                'bb_range': analysis['bb'],
                'macd_histogram': round(analysis['macd'], 6)
            },
            'analysis_cache': {
                'status': 'calculated',
                'cooldown_seconds': cooldown,
                'remaining_seconds': cooldown,
                'calculated_at': calculated_at
            }
        }
        _basic_analysis_cache[cache_key] = {
            'created_at': now,
            'calculated_at': calculated_at,
            'result': copy.deepcopy(response)
        }
        return response


def get_cached_professional_analysis(user_id, symbol, calculate):
    """Cachea el análisis PREMIUM por usuario durante el cooldown de cinco minutos."""
    cache_key = (user_id, symbol)
    now = time.monotonic()
    cooldown = PREMIUM_ANALYSIS_COOLDOWN_SECONDS
    with _professional_analysis_cache_lock:
        cached = _professional_analysis_cache.get(cache_key)
        if cached and now - cached['created_at'] < cooldown:
            response = copy.deepcopy(cached['response'])
            response['analysis_cache'] = {
                'status': 'cached',
                'cooldown_seconds': cooldown,
                'remaining_seconds': max(
                    0, math.ceil(cooldown - (now - cached['created_at']))
                ),
                'calculated_at': cached['calculated_at']
            }
            return response

        response = calculate()
        calculated_at = datetime.utcnow().isoformat() + 'Z'
        response['analysis_cache'] = {
            'status': 'calculated',
            'cooldown_seconds': cooldown,
            'remaining_seconds': cooldown,
            'calculated_at': calculated_at
        }
        _professional_analysis_cache[cache_key] = {
            'created_at': now,
            'calculated_at': calculated_at,
            'response': copy.deepcopy(response)
        }
        return response


def get_cached_user_prediction(user, symbol, prices, periods=PREDICTION_HORIZON_MINUTES):
    cooldown = PREDICTION_COOLDOWN_SECONDS
    cache_key = (user.id, symbol, periods)
    now = time.monotonic()
    with _user_prediction_cache_lock:
        cached = _user_prediction_cache.get(cache_key)
        if cached and now - cached['created_at'] < cooldown:
            result = copy.deepcopy(cached['result'])
            result['cache_status'] = 'cached'
            result['cooldown_seconds'] = max(
                0, math.ceil(cooldown - (now - cached['created_at']))
            )
            return result

        result = build_prediction_signal(prices, symbol, periods)
        result['cooldown_seconds'] = cooldown
        _user_prediction_cache[cache_key] = {
            'created_at': time.monotonic(),
            'result': copy.deepcopy(result)
        }
        return result


def get_cached_advanced_prediction(plan, symbol, calculate, user_id=None):
    """Cachea el análisis avanzado según el cooldown propio de cada plan."""
    plan = plan if plan in ADVANCED_PREDICTION_COOLDOWN_SECONDS else 'PRO'
    cooldown = ADVANCED_PREDICTION_COOLDOWN_SECONDS[plan]
    cache_key = (user_id, plan, symbol)
    now = time.monotonic()

    with _advanced_prediction_cache_lock:
        cached = _advanced_prediction_cache.get(cache_key)
        if cached and now - cached['created_at'] < cooldown:
            result = copy.deepcopy(cached['result'])
            result['prediction_cache'] = {
                'status': 'cached',
                'cooldown_seconds': cooldown,
                'remaining_seconds': max(
                    0, math.ceil(cooldown - (now - cached['created_at']))
                ),
                'calculated_at': cached['calculated_at']
            }
            return result

        result = calculate()
        calculated_at = datetime.utcnow().isoformat() + 'Z'
        result['prediction_cache'] = {
            'status': 'calculated',
            'cooldown_seconds': cooldown,
            'remaining_seconds': cooldown,
            'calculated_at': calculated_at
        }
        _advanced_prediction_cache[cache_key] = {
            'created_at': now,
            'calculated_at': calculated_at,
            'result': copy.deepcopy(result)
        }
        return result


def build_prediction_signal(prices, symbol=None, periods=PREDICTION_HORIZON_MINUTES):
    """Reutiliza el análisis por símbolo durante el cooldown para evitar recálculos concurrentes."""
    cache_symbol = symbol or TRADING_DATA.get('symbol', DEFAULT_SYMBOL)
    now = time.monotonic()
    with _prediction_cache_lock:
        cache_key = (cache_symbol, periods)
        cached = _prediction_cache.get(cache_key)
        if cached and now - cached['created_at'] < PREDICTION_COOLDOWN_SECONDS:
            result = copy.deepcopy(cached['result'])
            result['cache_status'] = 'cached'
            result['cooldown_seconds'] = max(
                0, math.ceil(PREDICTION_COOLDOWN_SECONDS - (now - cached['created_at']))
            )
            return result

        result = _build_prediction_signal_uncached(prices, periods)
        result['cache_status'] = 'calculated'
        result['cooldown_seconds'] = PREDICTION_COOLDOWN_SECONDS
        result['calculated_at'] = datetime.utcnow().isoformat() + 'Z'
        _prediction_cache[cache_key] = {
            'created_at': time.monotonic(),
            'result': copy.deepcopy(result)
        }
        return result


def invalidate_prediction_cache(symbol):
    with _prediction_cache_lock:
        for cache_key in [key for key in _prediction_cache if key[0] == symbol]:
            _prediction_cache.pop(cache_key, None)
    with _advanced_prediction_cache_lock:
        for cache_key in [key for key in _advanced_prediction_cache if key[2] == symbol]:
            _advanced_prediction_cache.pop(cache_key, None)
    with _user_prediction_cache_lock:
        for cache_key in [key for key in _user_prediction_cache if key[1] == symbol]:
            _user_prediction_cache.pop(cache_key, None)
    with _basic_analysis_cache_lock:
        for cache_key in [key for key in _basic_analysis_cache if key[1] == symbol]:
            _basic_analysis_cache.pop(cache_key, None)
    with _professional_analysis_cache_lock:
        for cache_key in [key for key in _professional_analysis_cache if key[1] == symbol]:
            _professional_analysis_cache.pop(cache_key, None)


def _build_prediction_signal_uncached(prices, periods):
    """Genera una recomendación conservadora con niveles de riesgo verificables."""
    engine = prediction_engine if PREDICTION_AVAILABLE else None
    return build_prediction_signal_uncached(prices, periods, engine)

# ====================================================================
# ACTUALIZACIÓN DE PRECIOS
# ====================================================================

def update_market_price_once():
    """Actualiza tick, velas y serie de predicción desde una sola instantánea."""
    with PRICE_LOCK:
        symbol = TRADING_DATA.get('symbol', DEFAULT_SYMBOL)

    updated = False
    if MARKET_DATA_AVAILABLE and market_data:
        quote = market_data.get_latest_quote(symbol)
        with PRICE_LOCK:
            if symbol == TRADING_DATA.get('symbol') and quote:
                try:
                    latest_price = float(quote['price'])
                    if latest_price > 0 and math.isfinite(latest_price):
                        clean_history = []
                        for item in (quote.get('history') or [])[-1000:]:
                            try:
                                value = float(item)
                            except (TypeError, ValueError):
                                continue
                            if value > 0 and math.isfinite(value):
                                clean_history.append(value)
                        if clean_history:
                            clean_history[-1] = latest_price
                            TRADING_DATA['price_history'] = clean_history
                        elif TRADING_DATA['price_history']:
                            TRADING_DATA['price_history'][-1] = latest_price

                        market_candles = [
                            dict(candle) for candle in quote.get('candles', [])
                        ]
                        if market_candles:
                            latest_candle = market_candles[-1]
                            latest_candle['close'] = latest_price
                            latest_candle['high'] = max(
                                float(latest_candle['high']), latest_price
                            )
                            latest_candle['low'] = min(
                                float(latest_candle['low']), latest_price
                            )
                            TRADING_DATA['market_candles'] = market_candles
                            if calculate_liquidity_metrics:
                                TRADING_DATA['liquidity'] = calculate_liquidity_metrics(
                                    market_candles, symbol
                                )

                        TRADING_DATA['price'] = latest_price
                        TRADING_DATA['price_source'] = quote.get('source', 'Proveedor externo')
                        TRADING_DATA['price_updated_at'] = quote['timestamp']
                        tick = {
                            'timestamp': quote['timestamp'],
                            'price': latest_price,
                            'bid': quote.get('bid'),
                            'ask': quote.get('ask'),
                            'source': TRADING_DATA['price_source']
                        }
                        ticks = TRADING_DATA['recent_ticks']
                        if not ticks or (
                            ticks[-1]['timestamp'] != tick['timestamp'] or
                            ticks[-1]['price'] != tick['price']
                        ):
                            ticks.append(tick)
                            del ticks[:-2000]
                        updated = True
                except (KeyError, TypeError, ValueError):
                    print(f'Precio de mercado inválido para {symbol}: {quote}')

    with PRICE_LOCK:
        try:
            check_market_alerts()
        except Exception as e:
            print(f'Error en alertas: {e}')
    return updated


def update_prices():
    """Mantiene el feed de MT5 casi en tiempo real y Yahoo como respaldo."""
    while True:
        try:
            update_market_price_once()
            with PRICE_LOCK:
                poll_interval = 1 if TRADING_DATA.get('price_source') == 'MetaTrader 5' else 5
            time.sleep(poll_interval)
        except Exception as e:
            print(f"Error en update_prices: {e}")
            time.sleep(5)

price_thread = None
_price_thread_lock = threading.Lock()

def start_background_services():
    global price_thread
    with _price_thread_lock:
        if price_thread is None or not price_thread.is_alive():
            price_thread = threading.Thread(target=update_prices, daemon=True)
            price_thread.start()


@app.before_request
def ensure_market_data_service():
    if not app.config.get('TESTING', False):
        start_background_services()

# ====================================================================
# AUTENTICACIÓN Y AUTORIZACIÓN
# ====================================================================

def get_current_user():
    """Obtener usuario actual de la sesión con verificación de expiración de plan"""
    if not DB_AVAILABLE or 'user_id' not in session or 'session_token' not in session:
        session.clear()
        return None
    try:
        login_session = LoginSession.query.filter_by(
            user_id=session['user_id'],
            session_token=session['session_token'],
            is_active=True
        ).first()
        if not login_session:
            session.clear()
            return None
        if not login_session.is_valid():
            login_session.is_active = False
            db.session.commit()
            session.clear()
            return None

        user = db.session.get(User, session['user_id'])
        if not user or not user.is_active:
            login_session.is_active = False
            db.session.commit()
            session.clear()
            return None
        if user and user.subscription_plan in ('PRO', 'PREMIUM') and user.subscription_expires:
            if datetime.utcnow() > user.subscription_expires:
                user.subscription_plan = 'FREE'
                user.subscription_status = 'expired'
                db.session.commit()
        return user
    except Exception:
        logger.exception('Could not validate the current login session.')
        db.session.rollback()
        session.clear()
        return None


def has_verified_paid_subscription(user):
    if not user or user.subscription_plan == 'FREE':
        return bool(user)
    if not DB_AVAILABLE:
        return False
    return PaymentTransaction.query.filter_by(
        user_id=user.id,
        provider='paypal',
        plan=user.subscription_plan,
        status='active'
    ).first() is not None


def login_required(f):
    """Decorador para rutas que requieren autenticación"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'success': False, 'error': 'Autenticación requerida'}), 401
        request.user = user
        return f(*args, **kwargs)
    return decorated_function

def check_subscription(required_plan='FREE'):
    """Decorador para verificar que el usuario autenticado tiene el plan necesario"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({'success': False, 'error': 'Autenticación requerida'}), 401
            
            if required_plan == 'PRO':
                if (
                    user.subscription_plan not in ('PRO', 'PREMIUM') or
                    not user.has_active_subscription() or
                    not has_verified_paid_subscription(user)
                ):
                    return jsonify({
                        'success': False, 
                        'error': 'Esta función requiere un plan PRO ($9.99/mes) o PREMIUM ($19.99/mes)',
                        'upgrade_required': True
                    }), 403
            elif required_plan == 'PREMIUM':
                if (
                    user.subscription_plan != 'PREMIUM' or
                    not user.has_active_subscription() or
                    not has_verified_paid_subscription(user)
                ):
                    return jsonify({
                        'success': False, 
                        'error': 'Esta función requiere un plan PREMIUM ($19.99/mes)',
                        'upgrade_required': True
                    }), 403
            
            request.user = user
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ====================================================================
# RUTAS DE AUTENTICACIÓN
# ====================================================================

@app.route('/api/auth/register', methods=['POST'])
@rate_limit(10)  # 10 registros por minuto máximo
def api_register():
    """Registrar nuevo usuario"""
    if not DB_AVAILABLE:
        return jsonify({'success': False, 'error': 'Sistema de usuarios no disponible'}), 503
    
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'success': False, 'error': 'Datos de registro no válidos'}), 400
    email = data.get('email', '')
    username = data.get('username', '')
    password = data.get('password', '')
    full_name = data.get('full_name', '')
    if not all(isinstance(value, str) for value in (email, username, password, full_name)):
        return jsonify({'success': False, 'error': 'Datos de registro no válidos'}), 400
    email = email.strip().lower()
    username = username.strip()
    full_name = SecurityValidator.sanitize_string(full_name.strip(), 255)
    
    # Validaciones
    if not email or not username or not password:
        return jsonify({'success': False, 'error': 'Email, usuario y contraseña requeridos'}), 400

    if not SecurityValidator.validate_email(email):
        return jsonify({'success': False, 'error': 'Email no válido'}), 400

    if not SecurityValidator.validate_username(username):
        return jsonify({'success': False, 'error': 'Usuario no válido'}), 400

    if len(password) < 8:
        return jsonify({'success': False, 'error': 'Contraseña debe tener al menos 8 caracteres'}), 400
    
    # Verificar si existe
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'error': 'El email ya está registrado'}), 400
    
    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'error': 'El usuario ya está en uso'}), 400
    
    try:
        # Crear usuario
        user = User(
            email=email,
            username=username,
            full_name=full_name,
            subscription_plan='FREE',
            subscription_status='active'
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Crear sesión automática
        token = secrets.token_urlsafe(32)
        login_sess = LoginSession(
            user_id=user.id,
            session_token=token,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db.session.add(login_sess)
        db.session.commit()
        
        session['user_id'] = user.id
        session['session_token'] = token
        
        return jsonify({
            'success': True,
            'message': 'Usuario registrado exitosamente',
            'user': user.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auth/login', methods=['POST'])
@rate_limit(20)  # 20 intentos por minuto máximo
def api_login():
    """Login de usuario"""
    if not DB_AVAILABLE:
        return jsonify({'success': False, 'error': 'Sistema de usuarios no disponible'}), 503
    
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'success': False, 'error': 'Datos de acceso no válidos'}), 400
    email_or_user = data.get('email') or data.get('username', '')
    password = data.get('password', '')
    if not isinstance(email_or_user, str) or not isinstance(password, str):
        return jsonify({'success': False, 'error': 'Datos de acceso no válidos'}), 400
    email_or_user = email_or_user.strip()
    
    if not email_or_user or not password:
        return jsonify({'success': False, 'error': 'Email/usuario y contraseña requeridos'}), 400
    
    # Buscar usuario
    user = User.query.filter(
        (User.email == email_or_user.lower()) | (User.username == email_or_user)
    ).first()
    
    if not user or not user.check_password(password):
        return jsonify({'success': False, 'error': 'Email/usuario o contraseña incorrectos'}), 401
    
    if not user.is_active:
        return jsonify({'success': False, 'error': 'Usuario desactivado'}), 403
    
    try:
        # Crear sesión
        token = secrets.token_urlsafe(32)
        login_sess = LoginSession(
            user_id=user.id,
            session_token=token,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        
        user.last_login = datetime.utcnow()
        db.session.add(login_sess)
        db.session.commit()
        
        session['user_id'] = user.id
        session['session_token'] = token
        
        return jsonify({
            'success': True,
            'message': 'Login exitoso',
            'user': user.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auth/logout', methods=['POST'])
@login_required
def api_logout():
    """Logout de usuario"""
    try:
        if 'session_token' in session:
            login_sess = LoginSession.query.filter_by(
                session_token=session['session_token']
            ).first()
            if login_sess:
                login_sess.is_active = False
                db.session.commit()
        
        session.clear()
        return jsonify({'success': True, 'message': 'Logout exitoso'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auth/me')
@login_required
def api_get_current_user():
    """Obtener datos del usuario actual"""
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    user_data = user.to_dict(include_sensitive=True)
    if user.subscription_plan != 'FREE' and not has_verified_paid_subscription(user):
        user_data['subscription_plan'] = 'FREE'
        user_data['subscription_status'] = 'payment_required'
    return jsonify({
        'success': True,
        'user': user_data
    })


@app.route('/api/user/profile', methods=['PUT', 'POST'])
@login_required
def api_update_profile():
    """Actualizar perfil del usuario autenticado"""
    user = get_current_user()
    data = request.get_json() or {}
    
    full_name = data.get('full_name')
    avatar_url = data.get('avatar_url')
    
    if full_name is not None:
        user.full_name = str(full_name).strip()
    if avatar_url is not None:
        user.avatar_url = str(avatar_url).strip()
        
    try:
        user.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Perfil actualizado correctamente',
            'user': user.to_dict(include_sensitive=True)
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/user/password', methods=['PUT', 'POST'])
@login_required
def api_change_password():
    """Cambiar contraseña del usuario autenticado"""
    user = get_current_user()
    data = request.get_json() or {}
    
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    
    if not current_password or not new_password:
        return jsonify({'success': False, 'error': 'Se requiere contraseña actual y nueva'}), 400
        
    if not user.check_password(current_password):
        return jsonify({'success': False, 'error': 'La contraseña actual es incorrecta'}), 401
        
    if not SecurityValidator.validate_password(new_password):
        return jsonify({'success': False, 'error': 'La nueva contraseña debe tener al menos 8 caracteres'}), 400
        
    try:
        user.set_password(new_password)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Contraseña cambiada exitosamente'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


class PasswordResetDeliveryError(RuntimeError):
    """Raised when account recovery email delivery is not configured or fails."""


def _password_reset_email_settings():
    host = os.environ.get('SMTP_HOST', '').strip()
    sender = os.environ.get('SMTP_FROM', '').strip()
    if not host or not sender:
        raise PasswordResetDeliveryError(
            'Configura SMTP_HOST y SMTP_FROM para habilitar recuperación de contraseña.'
        )
    try:
        port = int(os.environ.get('SMTP_PORT', '587'))
    except ValueError as exc:
        raise PasswordResetDeliveryError('SMTP_PORT debe ser un puerto válido.') from exc
    username = os.environ.get('SMTP_USERNAME', '').strip()
    password = os.environ.get('SMTP_PASSWORD', '')
    if bool(username) != bool(password):
        raise PasswordResetDeliveryError(
            'SMTP_USERNAME y SMTP_PASSWORD deben configurarse juntos.'
        )
    use_ssl = os.environ.get('SMTP_USE_SSL', '').lower() == 'true'
    use_starttls = os.environ.get('SMTP_STARTTLS', 'true').lower() == 'true'
    if use_ssl and use_starttls:
        raise PasswordResetDeliveryError(
            'Usa SMTP_USE_SSL o SMTP_STARTTLS, no ambos.'
        )
    return {
        'host': host,
        'port': port,
        'sender': sender,
        'username': username,
        'password': password,
        'use_ssl': use_ssl,
        'use_starttls': use_starttls
    }


def _send_password_reset_email(email, token):
    settings = _password_reset_email_settings()
    message = EmailMessage()
    message['Subject'] = 'Restablece tu contraseña'
    message['From'] = settings['sender']
    message['To'] = email
    message.set_content(
        'Recibimos una solicitud para restablecer la contraseña de tu cuenta.\n\n'
        f'Tu código de recuperación es: {token}\n\n'
        'El código vence en una hora y solo puede utilizarse una vez. '
        'Si no solicitaste este cambio, ignora este correo.'
    )

    if settings['use_ssl']:
        smtp_client = smtplib.SMTP_SSL(
            settings['host'],
            settings['port'],
            timeout=15,
            context=ssl.create_default_context()
        )
    else:
        smtp_client = smtplib.SMTP(
            settings['host'],
            settings['port'],
            timeout=15
        )

    with smtp_client as smtp:
        if settings['use_starttls']:
            smtp.starttls(context=ssl.create_default_context())
        if settings['username']:
            smtp.login(settings['username'], settings['password'])
        smtp.send_message(message)


def _password_reset_token_digest(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


@app.route('/api/auth/forgot-password', methods=['POST'])
@rate_limit(5)
def api_forgot_password():
    """Solicitar recuperación de contraseña"""
    if not DB_AVAILABLE:
        return jsonify({'success': False, 'error': 'Sistema no disponible'}), 503
        
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict) or not isinstance(data.get('email'), str):
        return jsonify({'success': False, 'error': 'Solicitud no válida'}), 400
    email = data['email'].strip().lower()
    
    if not email:
        return jsonify({'success': False, 'error': 'Email requerido'}), 400

    try:
        _password_reset_email_settings()
    except PasswordResetDeliveryError:
        return jsonify({
            'success': False,
            'error': 'La recuperación por correo no está configurada.'
        }), 503
        
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({
            'success': True,
            'message': 'Si el email está registrado, recibirás instrucciones de recuperación.'
        }), 202
        
    try:
        token_str = secrets.token_urlsafe(32)
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=_password_reset_token_digest(token_str),
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db.session.add(reset_token)
        db.session.commit()
        try:
            _send_password_reset_email(email, token_str)
        except (PasswordResetDeliveryError, smtplib.SMTPException, OSError):
            reset_token.is_used = True
            db.session.commit()
            logger.exception('Password reset email delivery failed.')
            return jsonify({
                'success': False,
                'message': (
                    'Si el email está registrado, recibirás instrucciones de recuperación.'
                )
            }), 202

        return jsonify({
            'success': True,
            'message': 'Si el email está registrado, recibirás instrucciones de recuperación.'
        }), 202
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auth/reset-password', methods=['POST'])
@rate_limit(5)
def api_reset_password():
    """Restablecer contraseña usando token de recuperación"""
    if not DB_AVAILABLE:
        return jsonify({'success': False, 'error': 'Sistema no disponible'}), 503
        
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'success': False, 'error': 'Solicitud no válida'}), 400
    token_str = data.get('token', '')
    new_password = data.get('new_password', '')
    if not isinstance(token_str, str) or not isinstance(new_password, str):
        return jsonify({'success': False, 'error': 'Token y contraseña deben ser texto'}), 400
    token_str = token_str.strip()
    
    if not token_str or not new_password:
        return jsonify({'success': False, 'error': 'Token y nueva contraseña requeridos'}), 400
        
    if not SecurityValidator.validate_password(new_password):
        return jsonify({'success': False, 'error': 'La contraseña debe tener al menos 8 caracteres'}), 400
        
    try:
        reset_token = PasswordResetToken.query.filter_by(
            token=_password_reset_token_digest(token_str)
        ).first()
        if not reset_token or not reset_token.is_valid():
            return jsonify({'success': False, 'error': 'Token inválido o expirado'}), 400
            
        user = reset_token.user
        user.set_password(new_password)
        reset_tokens = PasswordResetToken.query.filter_by(
            user_id=user.id,
            is_used=False
        ).all()
        for token in reset_tokens:
            token.is_used = True
        LoginSession.query.filter_by(user_id=user.id, is_active=True).update(
            {'is_active': False}
        )
        db.session.commit()
        session.clear()
        
        return jsonify({
            'success': True,
            'message': 'Contraseña restablecida exitosamente'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# ====================================================================
# RUTAS DE SUSCRIPCIÓN
# ====================================================================

@app.route('/api/subscription/plans')
def api_get_plans():
    """Obtener planes disponibles"""
    plans = {
        'FREE': {
            'name': 'Gratis',
            'price': 0,
            'currency': 'USD',
            'billing_period': 'forever',
            'features': [
                'Acceso básico a trading',
                'Máximo 5 operaciones por día',
                'Gráficos simples',
                'Análisis técnico básico',
                'Sin datos históricos avanzados'
            ]
        },
        'PRO': {
            'name': 'Pro',
            'price': 9.99,
            'currency': 'USD',
            'billing_period': 'monthly',
            'features': [
                'Trading ilimitado',
                'Gráficos avanzados',
                'Análisis técnico completo',
                'Datos históricos 1 año',
                'Alertas de precios',
                'Soporte prioritario'
            ]
        },
        'PREMIUM': {
            'name': 'Premium',
            'price': 19.99,
            'currency': 'USD',
            'billing_period': 'monthly',
            'features': [
                'Todo de PRO',
                'IA predictiva avanzada',
                'Datos históricos 5 años',
    
                'API access',
                'Soporte 24/7',
                'Análisis personalizado'
            ]
        }
    }
    return jsonify({
        'success': True,
        'plans': plans,
        'payment_provider': 'PayPal',
        'payment_available': paypal_payments.is_configured()
    })


def _paypal_subscription_matches_transaction(transaction, provider_subscription):
    expected_custom_id = (
        f'trading-platform:user:{transaction.user_id}:plan:{transaction.plan}'
    )
    if (
        provider_subscription.get('id') != transaction.provider_reference or
        provider_subscription.get('status') != 'ACTIVE' or
        provider_subscription.get('plan_id') != paypal_payments.plan_id(transaction.plan) or
        provider_subscription.get('custom_id') != expected_custom_id
    ):
        return False

    last_payment = (
        provider_subscription.get('billing_info', {})
        .get('last_payment', {})
    )
    amount = last_payment.get('amount') or {}
    try:
        paid_amount = Decimal(str(amount.get('value')))
        expected_amount = Decimal(str(transaction.amount))
    except (InvalidOperation, TypeError, ValueError):
        return False
    if (
        amount.get('currency_code') != transaction.currency or
        paid_amount.quantize(Decimal('0.01')) != expected_amount.quantize(Decimal('0.01'))
    ):
        return False

    plan_details = paypal_payments.get_plan_details(
        paypal_payments.plan_id(transaction.plan)
    )
    if plan_details.get('id') != provider_subscription.get('plan_id'):
        return False
    regular_cycles = [
        cycle for cycle in plan_details.get('billing_cycles', [])
        if cycle.get('tenure_type') == 'REGULAR'
    ]
    for cycle in regular_cycles:
        frequency = cycle.get('frequency') or {}
        fixed_price = (cycle.get('pricing_scheme') or {}).get('fixed_price') or {}
        try:
            configured_amount = Decimal(str(fixed_price.get('value')))
            interval_count = int(frequency.get('interval_count', 0))
        except (InvalidOperation, TypeError, ValueError):
            continue
        if (
            frequency.get('interval_unit') == 'MONTH' and
            interval_count == 1 and
            fixed_price.get('currency_code') == transaction.currency and
            configured_amount.quantize(Decimal('0.01')) ==
            expected_amount.quantize(Decimal('0.01'))
        ):
            return True
    return False


def _paypal_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')).replace(
            tzinfo=None
        )
    except (TypeError, ValueError):
        return None


def _activate_paypal_transaction(transaction, provider_subscription):
    if not _paypal_subscription_matches_transaction(
        transaction, provider_subscription
    ):
        return False
    if transaction.status == 'active':
        return True

    user = db.session.get(User, transaction.user_id)
    if not user or not user.is_active:
        return False
    now = datetime.utcnow()
    user.subscription_plan = transaction.plan
    user.subscription_status = 'active'
    billing_info = provider_subscription.get('billing_info', {})
    user.subscription_expires = (
        _paypal_datetime(billing_info.get('next_billing_time')) or
        now + timedelta(days=30)
    )
    transaction.status = 'active'
    last_payment = billing_info.get('last_payment') or {}
    payment_reference = last_payment.get('id') or transaction.provider_reference
    payment_description = f'PayPal payment {payment_reference}'
    transaction.last_payment_at = _paypal_datetime(last_payment.get('time')) or now
    if not BillingHistory.query.filter_by(
        user_id=user.id,
        description=payment_description
    ).first():
        db.session.add(BillingHistory(
            user_id=user.id,
            plan=transaction.plan,
            amount=transaction.amount,
            currency=transaction.currency,
            status='succeeded',
            description=payment_description
        ))
    return True


def _paypal_public_approval_url(provider_subscription):
    for link in provider_subscription.get('links', []):
        if link.get('rel') != 'approve':
            continue
        href = link.get('href', '')
        parsed = urlparse(href)
        if (
            parsed.scheme == 'https' and parsed.hostname and
            (parsed.hostname == 'paypal.com' or parsed.hostname.endswith('.paypal.com'))
        ):
            return href
    return None


@app.route('/api/subscription/current')
@login_required
def api_get_subscription():
    """Obtener suscripción actual del usuario"""
    user = get_current_user()
    verified = has_verified_paid_subscription(user)
    effective_plan = user.subscription_plan if verified else 'FREE'
    
    return jsonify({
        'success': True,
        'subscription': {
            'plan': effective_plan,
            'status': user.subscription_status if verified else 'payment_required',
            'expires_at': user.subscription_expires.isoformat() if user.subscription_expires else None,
            'is_active': user.has_active_subscription() and verified
        }
    })


@app.route('/api/subscription/checkout', methods=['POST'])
@login_required
@rate_limit(5)
def api_subscription_checkout():
    if not DB_AVAILABLE:
        return jsonify({'success': False, 'error': 'Sistema no disponible'}), 503

    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict) or data.get('plan') not in ('PRO', 'PREMIUM'):
        return jsonify({'success': False, 'error': 'Plan de pago no válido'}), 400
    user = request.user
    plan = data['plan']
    if user.subscription_plan == plan and user.has_active_subscription() and \
            has_verified_paid_subscription(user):
        return jsonify({'success': False, 'error': f'Ya tienes el plan {plan} activo'}), 409
    active_provider_subscription = PaymentTransaction.query.filter_by(
        user_id=user.id,
        provider='paypal',
        status='active'
    ).first()
    if active_provider_subscription:
        return jsonify({
            'success': False,
            'error': 'Cancela tu suscripción PayPal actual antes de iniciar otro plan.'
        }), 409
    pending = PaymentTransaction.query.filter_by(
        user_id=user.id,
        provider='paypal',
        status='pending'
    ).order_by(PaymentTransaction.created_at.desc()).first()
    if pending and pending.created_at < datetime.utcnow() - timedelta(minutes=30):
        pending.status = 'expired'
        db.session.commit()
        pending = None
    if pending:
        return jsonify({
            'success': False,
            'error': 'Ya existe un checkout pendiente. Termínalo o espera 30 minutos para que expire.'
        }), 409

    try:
        provider_subscription = paypal_payments.create_subscription(
            plan,
            user.id,
            request_id=secrets.token_urlsafe(24)
        )
    except PayPalConfigurationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 503
    except PayPalProviderError as exc:
        logger.warning('PayPal checkout creation failed: %s', exc)
        return jsonify({
            'success': False,
            'error': 'PayPal sandbox no pudo iniciar el checkout.'
        }), 502

    subscription_id = provider_subscription.get('id')
    approval_url = _paypal_public_approval_url(provider_subscription)
    if not subscription_id or not approval_url:
        logger.error('PayPal returned a subscription without a valid approval link.')
        return jsonify({
            'success': False,
            'error': 'PayPal no devolvió un enlace de aprobación válido.'
        }), 502

    try:
        transaction = PaymentTransaction(
            user_id=user.id,
            provider='paypal',
            provider_reference=subscription_id,
            plan=plan,
            amount=paypal_payments.plan_amount(plan),
            currency='USD',
            status='pending'
        )
        db.session.add(transaction)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.exception('Could not persist PayPal checkout reference.')
        return jsonify({
            'success': False,
            'error': 'No se pudo guardar el intento de pago.'
        }), 500

    return jsonify({
        'success': True,
        'provider': 'PayPal',
        'status': 'pending',
        'approval_url': approval_url
    }), 201


@app.route('/billing/paypal/return')
def paypal_subscription_return():
    user = get_current_user()
    if not user:
        return redirect('/login')
    subscription_id = request.args.get('subscription_id', '').strip()
    if not subscription_id:
        return redirect('/dashboard?payment=missing')

    transaction = PaymentTransaction.query.filter_by(
        user_id=user.id,
        provider='paypal',
        provider_reference=subscription_id
    ).first()
    if not transaction:
        return redirect('/dashboard?payment=not-found')
    if transaction.status == 'active':
        return redirect('/dashboard?payment=success')

    try:
        provider_subscription = paypal_payments.get_subscription(subscription_id)
        if not _activate_paypal_transaction(transaction, provider_subscription):
            db.session.commit()
            return redirect('/dashboard?payment=pending')
        db.session.commit()
    except PayPalConfigurationError:
        db.session.rollback()
        logger.exception('PayPal return validation is not configured.')
        return redirect('/dashboard?payment=unavailable')
    except PayPalProviderError as exc:
        db.session.rollback()
        logger.warning('PayPal return validation failed: %s', exc)
        return redirect('/dashboard?payment=verification-failed')
    except Exception:
        db.session.rollback()
        logger.exception('Could not apply the verified PayPal subscription.')
        return redirect('/dashboard?payment=verification-failed')
    return redirect('/dashboard?payment=success')


@app.route('/billing/paypal/cancel')
def paypal_subscription_cancel():
    user = get_current_user()
    if not user:
        return redirect('/login')
    subscription_id = request.args.get('subscription_id', '').strip()
    if subscription_id:
        pending = PaymentTransaction.query.filter_by(
            user_id=user.id,
            provider='paypal',
            provider_reference=subscription_id,
            status='pending'
        ).first()
        if pending:
            pending.status = 'cancelled'
            db.session.commit()
    return redirect('/dashboard?payment=cancelled')


@app.route('/api/payments/paypal/webhook', methods=['POST'])
def api_paypal_webhook():
    event = request.get_json(silent=True)
    if not isinstance(event, dict) or not isinstance(event.get('id'), str):
        return jsonify({'success': False, 'error': 'Evento PayPal no válido'}), 400
    try:
        if not paypal_payments.verify_webhook(request.headers, event):
            return jsonify({'success': False, 'error': 'Firma PayPal no válida'}), 400
    except PayPalConfigurationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 503
    except PayPalProviderError as exc:
        logger.warning('PayPal webhook verification failed: %s', exc)
        return jsonify({'success': False, 'error': 'No se pudo verificar el evento PayPal'}), 502

    if PaymentWebhookEvent.query.filter_by(
        provider='paypal',
        event_id=event['id']
    ).first():
        return jsonify({'success': True, 'duplicate': True}), 200

    try:
        db.session.add(PaymentWebhookEvent(
            provider='paypal',
            event_id=event['id'],
            event_type=str(event.get('event_type', 'unknown'))[:128]
        ))
        db.session.flush()

        event_type = event.get('event_type')
        resource = event.get('resource') or {}
        subscription_id = (
            resource.get('id')
            if event_type and event_type.startswith('BILLING.SUBSCRIPTION.')
            else resource.get('billing_agreement_id') or resource.get('subscription_id')
        )
        transaction = None
        if isinstance(subscription_id, str) and subscription_id:
            transaction = PaymentTransaction.query.filter_by(
                provider='paypal',
                provider_reference=subscription_id
            ).first()

        if transaction and event_type in (
            'BILLING.SUBSCRIPTION.ACTIVATED',
            'PAYMENT.SALE.COMPLETED'
        ):
            provider_subscription = paypal_payments.get_subscription(subscription_id)
            _activate_paypal_transaction(transaction, provider_subscription)
            if (
                event_type == 'PAYMENT.SALE.COMPLETED' and
                transaction.status == 'active'
            ):
                amount_info = resource.get('amount') or {}
                try:
                    sale_amount = Decimal(str(amount_info.get('total')))
                    expected_amount = Decimal(str(transaction.amount))
                except (InvalidOperation, TypeError, ValueError):
                    raise PayPalProviderError('El monto del evento PayPal no es válido.')
                if (
                    amount_info.get('currency') != transaction.currency or
                    sale_amount.quantize(Decimal('0.01')) !=
                    expected_amount.quantize(Decimal('0.01'))
                ):
                    raise PayPalProviderError('El monto del evento no coincide con el plan.')

                sale_reference = resource.get('id', event['id'])
                description = f'PayPal payment {sale_reference}'
                user = db.session.get(User, transaction.user_id)
                event_time = (
                    _paypal_datetime(event.get('create_time')) or
                    datetime.utcnow()
                )
                is_new_billing_cycle = (
                    transaction.last_payment_at is None or
                    event_time > transaction.last_payment_at + timedelta(days=1)
                )
                if is_new_billing_cycle:
                    if user and transaction.last_payment_at:
                        next_billing = _paypal_datetime(
                            provider_subscription.get('billing_info', {}).get(
                                'next_billing_time'
                            )
                        )
                        user.subscription_expires = next_billing or max(
                            user.subscription_expires or event_time,
                            event_time
                        ) + timedelta(days=30)
                    if user and not BillingHistory.query.filter_by(
                        user_id=transaction.user_id,
                        description=description
                    ).first():
                        db.session.add(BillingHistory(
                            user_id=transaction.user_id,
                            plan=transaction.plan,
                            amount=float(sale_amount),
                            currency=transaction.currency,
                            status='succeeded',
                            description=description
                        ))
                    transaction.last_payment_at = event_time

        elif transaction and event_type in (
            'BILLING.SUBSCRIPTION.CANCELLED',
            'BILLING.SUBSCRIPTION.EXPIRED',
            'BILLING.SUBSCRIPTION.SUSPENDED'
        ):
            provider_subscription = paypal_payments.get_subscription(subscription_id)
            provider_status = provider_subscription.get('status')
            if provider_status in ('CANCELLED', 'EXPIRED', 'SUSPENDED'):
                transaction.status = provider_status.lower()
                user = db.session.get(User, transaction.user_id)
                other_active = PaymentTransaction.query.filter(
                    PaymentTransaction.user_id == transaction.user_id,
                    PaymentTransaction.provider == 'paypal',
                    PaymentTransaction.status == 'active',
                    PaymentTransaction.id != transaction.id
                ).first()
                if user and not other_active and user.subscription_plan == transaction.plan:
                    user.subscription_plan = 'FREE'
                    user.subscription_status = 'canceled'
                    user.subscription_expires = None

        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        if PaymentWebhookEvent.query.filter_by(
            provider='paypal',
            event_id=event['id']
        ).first():
            return jsonify({'success': True, 'duplicate': True}), 200
        logger.exception('Could not store the PayPal webhook event.')
        return jsonify({'success': False, 'error': 'Evento PayPal no procesado'}), 500
    except PayPalProviderError as exc:
        db.session.rollback()
        logger.warning('PayPal webhook event processing failed: %s', exc)
        return jsonify({'success': False, 'error': 'Evento PayPal no procesado'}), 502
    except Exception:
        db.session.rollback()
        logger.exception('Unexpected PayPal webhook processing error.')
        return jsonify({'success': False, 'error': 'Evento PayPal no procesado'}), 500

    return jsonify({'success': True}), 200


@app.route('/api/subscription/upgrade', methods=['POST'])
@login_required
def api_upgrade_subscription():
    """Prevent client requests from granting paid access without provider payment."""
    return jsonify({
        'success': False,
        'error': 'El upgrade directo está deshabilitado. Inicia el pago con PayPal checkout.'
    }), 410


@app.route('/api/subscription/cancel', methods=['POST'])
@login_required
def api_cancel_subscription():
    """Cancel the authenticated user's PayPal recurring subscription."""
    if not DB_AVAILABLE:
        return jsonify({'success': False, 'error': 'Sistema no disponible'}), 503

    user = request.user
    if user.subscription_plan == 'FREE':
        return jsonify({'success': False, 'error': 'No hay suscripción activa para cancelar'}), 400

    transaction = PaymentTransaction.query.filter_by(
        user_id=user.id,
        provider='paypal',
        plan=user.subscription_plan,
        status='active'
    ).order_by(PaymentTransaction.created_at.desc()).first()
    if not transaction:
        return jsonify({
            'success': False,
            'error': 'No encontramos una suscripción PayPal verificada para cancelar. Contacta soporte.'
        }), 409

    try:
        paypal_payments.cancel_subscription(
            transaction.provider_reference,
            'Cancellation requested by subscriber'
        )
        transaction.status = 'cancelled'
        user.cancel_subscription()
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'La suscripción recurrente de PayPal fue cancelada.',
            'subscription': {'plan': user.subscription_plan, 'status': user.subscription_status}
        })
    except PayPalConfigurationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 503
    except PayPalProviderError as exc:
        db.session.rollback()
        logger.warning('PayPal subscription cancellation failed: %s', exc)
        return jsonify({
            'success': False,
            'error': 'PayPal no pudo cancelar la suscripción. Inténtalo más tarde.'
        }), 502
    except Exception:
        db.session.rollback()
        logger.exception('Could not persist PayPal subscription cancellation.')
        return jsonify({'success': False, 'error': 'No se pudo registrar la cancelación.'}), 500


@app.route('/api/subscription/renew', methods=['POST'])
@login_required
def api_renew_subscription():
    """Renewal is handled automatically by the verified PayPal subscription."""
    return jsonify({
        'success': False,
        'error': 'La renovación se procesa automáticamente por PayPal; no se puede simular.'
    }), 410


@app.route('/api/billing/history')
@login_required
def api_billing_history():
    """Obtener historial de pagos"""
    if not DB_AVAILABLE:
        return jsonify({'success': False, 'error': 'Sistema no disponible'}), 503
    
    user = get_current_user()
    
    billing_records = BillingHistory.query.filter_by(user_id=user.id).order_by(
        BillingHistory.charged_at.desc()
    ).limit(20).all()
    
    return jsonify({
        'success': True,
        'billing_history': [record.to_dict() for record in billing_records]
    })

# ====================================================================
# RUTAS DE PÁGINAS Y NAVEGACIÓN
# ====================================================================

@app.route('/')
def index():
    """Ruta raíz: redirige según autenticación"""
    user = get_current_user()
    if user:
        return redirect('/dashboard')
    return redirect('/login')


@app.route('/dashboard')
def dashboard():
    """Panel de control principal"""
    user = get_current_user()
    if not user:
        return redirect('/login')
    return render_template_string(DASHBOARD_HTML)


@app.route('/login', methods=['GET', 'POST'])
def view_login():
    """Vista de inicio de sesión"""
    if not DB_AVAILABLE:
        return render_template_string(
            LOGIN_HTML,
            error='Autenticación no disponible: revisa SQLAlchemy y la base de datos.'
        ), 503

    if request.method == 'POST':
        email_or_user = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = User.query.filter(
            (User.email == email_or_user.lower()) | (User.username == email_or_user)
        ).first() if DB_AVAILABLE else None
        
        if user and user.is_active and user.check_password(password):
            token = secrets.token_urlsafe(32)
            login_sess = LoginSession(
                user_id=user.id,
                session_token=token,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', ''),
                expires_at=datetime.utcnow() + timedelta(days=30)
            )
            user.last_login = datetime.utcnow()
            db.session.add(login_sess)
            db.session.commit()
            
            session['user_id'] = user.id
            session['session_token'] = token
            return redirect('/dashboard')
        
        return render_template_string(LOGIN_HTML, error='Usuario/Email o contraseña incorrectos')
    
    user = get_current_user()
    if user:
        return redirect('/dashboard')
    return render_template_string(LOGIN_HTML)


@app.route('/register', methods=['GET', 'POST'])
def view_register():
    """Vista de registro de usuario"""
    if not DB_AVAILABLE:
        return render_template_string(
            REGISTER_HTML,
            error='Registro no disponible: revisa la base de datos.'
        ), 503

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        
        if not email or not username or not password:
            return render_template_string(REGISTER_HTML, error='Campos requeridos incompletos')

        if not SecurityValidator.validate_email(email):
            return render_template_string(REGISTER_HTML, error='Email no válido')
        if not SecurityValidator.validate_username(username):
            return render_template_string(REGISTER_HTML, error='Usuario no válido')
        if len(password) < 8:
            return render_template_string(REGISTER_HTML, error='La contraseña debe tener al menos 8 caracteres')
        full_name = SecurityValidator.sanitize_string(full_name, 255)
            
        if User.query.filter_by(email=email).first():
            return render_template_string(REGISTER_HTML, error='El email ya está registrado')
            
        if User.query.filter_by(username=username).first():
            return render_template_string(REGISTER_HTML, error='El usuario ya está en uso')
            
        try:
            user = User(
                email=email,
                username=username,
                full_name=full_name,
                subscription_plan='FREE',
                subscription_status='active'
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            token = secrets.token_urlsafe(32)
            login_sess = LoginSession(
                user_id=user.id,
                session_token=token,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', ''),
                expires_at=datetime.utcnow() + timedelta(days=30)
            )
            db.session.add(login_sess)
            db.session.commit()
            
            session['user_id'] = user.id
            session['session_token'] = token
            return redirect('/dashboard')
        except Exception as e:
            db.session.rollback()
            return render_template_string(REGISTER_HTML, error=f'Error creando cuenta: {e}')
            
    user = get_current_user()
    if user:
        return redirect('/dashboard')
    return render_template_string(REGISTER_HTML)


@app.route('/api/status')
def api_status():
    """Obtener estado del sistema de mercado y predicciones"""
    with PRICE_LOCK:
        symbol = TRADING_DATA.get('symbol', DEFAULT_SYMBOL)
        decimals, _, _, _, _ = get_symbol_format(symbol)
        current_price = float(TRADING_DATA['price'])
        chart_candles = [
            dict(candle) for candle in TRADING_DATA.get('market_candles', [])[-120:]
            if all(key in candle for key in ('open', 'high', 'low', 'close'))
        ]
        if chart_candles:
            latest_candle = chart_candles[-1]
            latest_candle['close'] = current_price
            latest_candle['high'] = max(float(latest_candle['high']), current_price)
            latest_candle['low'] = min(float(latest_candle['low']), current_price)
            chart_prices = [float(candle['close']) for candle in chart_candles]
        else:
            chart_prices = [
                float(price) for price in TRADING_DATA['price_history'][-40:]
            ]
            if not chart_prices or chart_prices[-1] != current_price:
                chart_prices.append(current_price)
        status = {
            'price': current_price,
            'price_updated_at': TRADING_DATA.get('price_updated_at'),
            'price_source': TRADING_DATA.get('price_source'),
            'chart_timeframe': '1m' if chart_candles else None,
            'recent_tick_count': len(TRADING_DATA['recent_ticks']),
            'liquidity': copy.deepcopy(TRADING_DATA.get('liquidity', {'available': False})),
            'decimals': decimals,
            'signal': TRADING_DATA['signal'],
            'symbol': symbol,
            'prices': TRADING_DATA['price_history'][-30:],
            'chart_prices': chart_prices,
            'chart_candles': chart_candles
        }

    status['candles'] = [
        {'c': price, 'x': i + 1}
        for i, price in enumerate(chart_prices)
    ]
    return jsonify(status)




@app.route('/api/symbols')
def api_symbols():
    """Lista los símbolos disponibles."""
    if SYMBOLS_AVAILABLE:
        return jsonify({'success': True, 'symbols': list_symbols(), 'current': TRADING_DATA.get('symbol', DEFAULT_SYMBOL)})
    return jsonify({'success': True, 'symbols': [{'name': 'EURUSD', 'display_name': 'Euro / Dólar', 'category': 'FOREX', 'default_price': 1.0850, 'default_volume': 0.01, 'decimals': 5, 'description': '', 'session_hours': ''}], 'current': 'EURUSD'})


@app.route('/api/symbol', methods=['POST'])
@login_required
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
    reset_price_history(symbol)
    with PRICE_LOCK:
        TRADING_SYMBOL = symbol
        if volume is not None:
            try:
                vol = float(volume)
                if vol > 0:
                    TRADING_DATA['volume'] = vol
                    DEFAULT_VOLUME = vol
            except Exception:
                pass
        return jsonify({'success': True, 'symbol': symbol, 'volume': TRADING_DATA['volume'], 'price': TRADING_DATA['price']})


@app.route('/api/news-alerts')
@login_required
@check_subscription('PRO')
def api_news_alerts():
    """Devuelve noticias y alertas de volatilidad recientes."""
    with PRICE_LOCK:
        symbol = TRADING_DATA.get('symbol', DEFAULT_SYMBOL)
        prices = TRADING_DATA['price_history']
        metrics = _calculate_volatility_metrics(prices, get_symbol_format(symbol)[0]) if len(prices) >= 20 else {
            'spike_pct': 0.0, 'atr': 0.0, 'atr_ratio': 1.0, 'range_pct': 0.0
        }
        # Asegurar que siempre haya noticias
        if not TRADING_DATA['news']:
            TRADING_DATA['news'] = _get_symbol_news(symbol)
        return jsonify({
            'success': True,
            'symbol': symbol,
            'volatility': metrics,
            'alerts': get_recent_alerts(15),
            'news': TRADING_DATA['news'][:10]
        })


@app.route('/api/advanced-prediction')
@login_required
@check_subscription('PRO')
def api_advanced_prediction():
    """Predicción avanzada a 10 minutos con cooldown por plan."""
    with PRICE_LOCK:
        prices = list(TRADING_DATA['price_history'])
        symbol = TRADING_DATA.get('symbol', DEFAULT_SYMBOL)

    def calculate_advanced_prediction():
        analysis = analyze_signal(prices, symbol)
        trade = build_prediction_signal(
            prices, symbol, periods=PREDICTION_HORIZON_MINUTES
        )
        return {
            'success': True,
            'symbol': symbol,
            'signal': trade['signal'],
            'score': trade['strength'],
            'confidence': trade['confidence'],
            'trade_allowed': trade['trade_allowed'],
            'risk_reward': trade['risk_reward'],
            'reasons': trade['reasons'],
            'risk_note': trade['risk_note'],
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
            'levels': {
                key: round(value, 6) if isinstance(value, float) else value
                for key, value in trade['levels'].items()
            },
            'prediction': {
                key: round(value, 6) if isinstance(value, float) else value
                for key, value in trade['prediction_range'].items()
            },
            'timestamp': datetime.now().isoformat()
        }

    plan = request.user.subscription_plan
    result = get_cached_advanced_prediction(
        plan, symbol, calculate_advanced_prediction, request.user.id
    )
    return jsonify(result)


@app.route('/api/professional-analysis')
@login_required
@check_subscription('PREMIUM')
def api_professional_analysis():
    """Análisis profesional con cooldown server-side de cinco minutos."""
    user_id = request.user.id
    with PRICE_LOCK:
        prices = list(TRADING_DATA['price_history'])
        symbol = TRADING_DATA.get('symbol', DEFAULT_SYMBOL)
        current_price = TRADING_DATA['price']

    def calculate_professional_analysis():
        if len(prices) < 20:
            return {
                'available': False,
                'reason': 'Insuficientes datos históricos (se necesitan 20+ precios)',
                'market_learning': {
                    'source': 'rolling_walk_forward_market_history',
                    'available': False,
                    'samples': 0
                },
                'symbol': symbol
            }

        analysis = analyze_signal(prices, symbol)
        trade = build_prediction_signal(prices, symbol)
        prediction = trade['prediction']
        return {
            'available': True,
            'symbol': symbol,
            'current_price': current_price,
            'signal': trade['signal'],
            'confidence': trade['confidence'],
            'confidence_percent': round(trade['confidence'] * 100, 1),
            'trade_allowed': trade['trade_allowed'],
            'risk_reward': trade['risk_reward'],
            'signal_reasons': trade['reasons'],
            'market_learning': {
                'source': 'rolling_walk_forward_market_history',
                'available': prediction.get('walk_forward_samples', 0) > 0,
                'baseline_accuracy': prediction.get('walk_forward_accuracy'),
                'adaptive_accuracy': prediction.get('adaptive_walk_forward_accuracy'),
                'adaptive_samples': prediction.get('adaptive_walk_forward_samples', 0),
                'model_performance': prediction.get('model_performance', {}),
                'model_weights': prediction.get('model_weights', {})
            },
            'indicators': {
                'rsi': round(analysis['rsi'], 2),
                'trend': analysis['trend'],
                'momentum': 'FUERTE' if abs(prices[-1] - prices[-5]) > 0.002 else 'DÉBIL',
                'bb_range': analysis['bb'],
                'macd_histogram': round(analysis['macd'], 6)
            },
            'volatility': 'ALTA' if analysis['atr'] > 0 else 'SIN DATOS',
            'pattern': analysis['trend'],
            'timestamp': datetime.now().isoformat()
        }

    return jsonify(get_cached_professional_analysis(
        user_id, symbol, calculate_professional_analysis
    ))


@app.route('/api/analysis')
@login_required
def api_basic_analysis():
    """FREE: análisis técnico básico cada 15 min; planes pagos: cada 5 min."""
    with PRICE_LOCK:
        prices = list(TRADING_DATA['price_history'])
        symbol = TRADING_DATA.get('symbol', DEFAULT_SYMBOL)
    return jsonify(get_cached_analysis(
        request.user.id, symbol, prices, request.user.subscription_plan
    ))


@app.route('/api/predict')
@login_required
@check_subscription('PRO')
def api_predict():
    """Predicción de precio futuro y dirección usando PredictionEngine."""
    with PRICE_LOCK:
        prices = TRADING_DATA['price_history']
        try:
            symbol = TRADING_DATA.get('symbol', DEFAULT_SYMBOL)
            trade = get_cached_user_prediction(request.user, symbol, list(prices))
            pred = trade['prediction']
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

        return jsonify({
            'success': True,
            'prediction': pred,
            'recommendation': trade['signal'],
            'trade': trade,
            'levels': trade['levels'],
            'prediction_cache': {
                'status': trade['cache_status'],
                'cooldown_seconds': trade['cooldown_seconds'],
                'calculated_at': trade['calculated_at']
            }
        })


@app.route('/api/predict/levels')
@login_required
@check_subscription('PRO')
def api_predict_levels():
    """Devuelve niveles clave (soportes/resistencias, entry, SL, TP)."""
    with PRICE_LOCK:
        prices = TRADING_DATA['price_history']
        try:
            trade = get_cached_user_prediction(
                request.user,
                TRADING_DATA.get('symbol', DEFAULT_SYMBOL),
                list(prices)
            )
            levels = trade['levels']
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

        return jsonify({
            'success': True,
            'levels': levels,
            'prediction_cache': {
                'status': trade['cache_status'],
                'cooldown_seconds': trade['cooldown_seconds']
            }
        })


@app.route('/api/predict/signal')
@login_required
@check_subscription('PRO')
def api_predict_signal():
    """Combina predicción y indicadores para una señal operativa recomendada."""
    with PRICE_LOCK:
        prices = TRADING_DATA['price_history']
        try:
            signal = get_cached_user_prediction(
                request.user,
                TRADING_DATA.get('symbol', DEFAULT_SYMBOL),
                list(prices)
            )
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

        return jsonify({
            'success': True,
            'prediction_signal': signal,
            'prediction_cache': {
                'status': signal['cache_status'],
                'cooldown_seconds': signal['cooldown_seconds']
            }
        })


@app.route('/api/chat', methods=['POST'])
@login_required
@check_subscription('PRO')
def api_chat():
    """Procesar mensajes del chat"""
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict) or not isinstance(data.get('message'), str):
        return jsonify({'success': False, 'error': 'Mensaje no válido'}), 400
    original_message = data['message'].strip()
    if not original_message or len(original_message) > 2000:
        return jsonify({
            'success': False,
            'error': 'El mensaje debe tener entre 1 y 2000 caracteres'
        }), 400
    message = original_message.lower()
    
    response = process_chat_message(message)
    
    with PRICE_LOCK:
        history = get_chat_history(request.user.id)
        history.append({'sender': 'Yo', 'text': original_message})
        history.append({'sender': 'IA', 'text': response})
    
    return jsonify({'success': True, 'response': response})


@app.route('/api/chat/command', methods=['POST'])
@login_required
@check_subscription('PRO')
@rate_limit(3)
def api_chat_command():
    """Procesar comando de chat"""
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict) or not isinstance(data.get('command'), str):
        return jsonify({'error': 'Missing command'}), 400
    
    command = data['command'].strip()
    if not command or len(command) > 2000:
        return jsonify({'error': 'Command must be between 1 and 2000 characters'}), 400

    command_parts = command.split()
    if command_parts and command_parts[0].lower() == '/trade':
        if (
            request.user.subscription_plan != 'PREMIUM' or
            not request.user.has_active_subscription() or
            not has_verified_paid_subscription(request.user)
        ):
            return jsonify({
                'success': False,
                'error': 'El trade automático demo requiere un plan PREMIUM activo.',
                'upgrade_required': True
            }), 403
        if (
            len(command_parts) != 4 or
            command_parts[1].lower().replace('á', 'a') not in ('auto', 'automatico') or
            command_parts[2].lower() != 'demo'
        ):
            return jsonify({
                'success': False,
                'error': 'Uso: /trade auto demo XAUUSD (o EURUSD).'
            }), 400
        symbol = command_parts[3].upper()
        if symbol not in SUPPORTED_TEST_SYMBOLS:
            return jsonify({
                'success': False,
                'error': 'El comando demo solo admite EURUSD o XAUUSD.'
            }), 400
        try:
            job_id = start_demo_chat_trade_job(request.user.id, symbol)
        except RuntimeError as exc:
            return jsonify({'success': False, 'error': str(exc)}), 409
        except ValueError as exc:
            return jsonify({'success': False, 'error': str(exc)}), 400

        response = (
            f'Solicitud aceptada para {symbol}. Solo se intentará una operación '
            'en cuenta demo, con TP estimado USD 5-15 y pérdida estimada máxima USD 5. '
            'No se garantiza ganancia; puedes consultar el estado desde el chat.'
        )
        with PRICE_LOCK:
            history = get_chat_history(request.user.id)
            history.append({'sender': 'Tú', 'text': command})
            history.append({'sender': 'IA', 'text': response})
        return jsonify({
            'success': True,
            'response': response,
            'job_id': job_id,
            'status': 'queued'
        }), 202
    
    # Procesar comando
    response = process_chat_message(command.lower())
    
    # Agregar al historial
    with PRICE_LOCK:
        get_chat_history(request.user.id).append({
            'timestamp': datetime.now().isoformat(),
            'command': command,
            'response': response
        })
    
    return jsonify({'response': response})


@app.route('/api/chat/demo-trade/<job_id>')
@login_required
@check_subscription('PREMIUM')
def api_chat_demo_trade_status(job_id):
    job = get_demo_chat_trade_job(job_id, request.user.id)
    if not job:
        return jsonify({'success': False, 'error': 'Operación no encontrada.'}), 404
    return jsonify({'success': True, 'job': job})


@app.route('/api/chat/history')
@login_required
@check_subscription('PRO')
def api_chat_history():
    """Obtener historial de chat"""
    with PRICE_LOCK:
        return jsonify({
            'history': list(get_chat_history(request.user.id))
        })


def process_chat_message(message):
    """Procesa mensajes del chat con IA de análisis de mercado"""
    if not message:
        return "Por favor escribe una consulta sobre el mercado o una predicción."
    
    message_lower = message.lower()
    
    if 'estado' in message_lower or 'status' in message_lower or 'precio' in message_lower:
        with PRICE_LOCK:
            return f"Estado del Mercado - Símbolo: {TRADING_DATA.get('symbol', 'EURUSD')}, Precio Actual: {TRADING_DATA['price']:.4f}."
    
    elif 'analizar' in message_lower or 'analyze' in message_lower or 'señal' in message_lower or 'prediccion' in message_lower:
        with PRICE_LOCK:
            signal = TRADING_DATA.get('signal', {'action': 'ANALIZANDO', 'confidence': 0.75})
            return f"Análisis de Mercado: Señal {signal.get('action', 'ESPERA')} con confianza {signal.get('confidence', 0.75):.1%}. Revisa el panel de Predicción Avanzada."
    
    elif 'ayuda' in message_lower or 'help' in message_lower:
        return (
            "Soy tu Asistente de IA de Trading. Puedes usar /status o preguntar por "
            "precio y análisis. PREMIUM puede solicitar una operación demo con "
            "/trade auto demo XAUUSD o /trade auto demo EURUSD."
        )
    
    else:
        with PRICE_LOCK:
            return f"He analizado tu consulta '{message}'. El símbolo actual es {TRADING_DATA.get('symbol', 'EURUSD')} a un precio de {TRADING_DATA['price']:.4f}."


# ====================================================================



# ====================================================================
# TEMPLATES HTML
# ====================================================================

LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Iniciar Sesión - Asistente de Trading</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg: #050505;
            --surface: #0a0a0a;
            --gold: #FFD700;
            --gold-dim: #B8860B;
            --purple: #8B5CF6;
            --text: #F5F5F5;
            --text-dim: #A0A0A0;
            --border: rgba(255, 215, 0, 0.2);
        }
        body {
            font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .login-box {
            background: var(--surface);
            padding: 40px;
            border-radius: 16px;
            border: 1px solid var(--border);
            box-shadow: 0 10px 40px rgba(0,0,0,0.8);
            width: 100%;
            max-width: 420px;
        }
        .login-box h1 {
            background: linear-gradient(90deg, var(--gold), #fff7cc, var(--gold));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            font-size: 24px;
            margin-bottom: 24px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .form-group { margin-bottom: 18px; }
        label { display: block; color: var(--gold); font-size: 13px; font-weight: 600; margin-bottom: 6px; }
        input {
            width: 100%;
            padding: 12px;
            background: #0d0d0d;
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text);
            font-size: 14px;
        }
        input:focus { outline: none; border-color: var(--gold); }
        button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(90deg, var(--gold), var(--gold-dim));
            color: #000;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s ease;
            margin-top: 8px;
        }
        button:hover { opacity: 0.9; transform: translateY(-1px); }
        .error { color: #FF2D2D; background: rgba(255,45,45,0.1); border: 1px solid rgba(255,45,45,0.3); padding: 10px; border-radius: 8px; margin-bottom: 18px; text-align: center; font-size: 13px; }
        .links { margin-top: 20px; text-align: center; font-size: 13px; color: var(--text-dim); }
        .links a { color: var(--gold); text-decoration: none; font-weight: 600; }
        .links a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>Asistente de Trading</h1>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST">
            <div class="form-group">
                <label>Usuario o Email</label>
                <input type="text" name="username" placeholder="usuario o correo@ejemplo.com" required>
            </div>
            <div class="form-group">
                <label>Contraseña</label>
                <input type="password" name="password" placeholder="••••••••" required>
            </div>
            <button type="submit">Iniciar Sesión</button>
        </form>
        <div class="links">
            <p>¿No tienes cuenta? <a href="/register">Regístrate gratis</a></p>
            <p style="margin-top:8px;"><a href="#" onclick="showForgotModal()">¿Olvidaste tu contraseña?</a></p>
        </div>
    </div>

    <!-- Modal Recuperación -->
    <div id="forgot-modal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); justify-content:center; align-items:center; z-index:999;">
        <div style="background:var(--surface); padding:30px; border-radius:14px; border:1px solid var(--gold); max-width:400px; width:90%;">
            <h3 style="color:var(--gold); margin-bottom:15px;">Recuperar Contraseña</h3>
            <div id="forgot-step-1">
                <p style="font-size:13px; color:var(--text-dim); margin-bottom:12px;">Introduce tu correo electrónico y te enviaremos un código de recuperación si la cuenta existe.</p>
                <input id="forgot-email" type="email" placeholder="correo@ejemplo.com" style="width:100%; padding:10px; background:#0d0d0d; border:1px solid var(--border); color:#fff; border-radius:6px; margin-bottom:12px;">
                <button onclick="requestForgotToken()" style="width:100%;">Solicitar Token</button>
            </div>
            <div id="forgot-step-2" style="display:none; margin-top:15px;">
                <p style="font-size:12px; color:var(--gold); margin-bottom:10px;" id="forgot-msg"></p>
                <input id="reset-token-input" type="text" placeholder="Token de recuperación" style="width:100%; padding:10px; background:#0d0d0d; border:1px solid var(--border); color:#fff; border-radius:6px; margin-bottom:10px;">
                <input id="reset-new-pass" type="password" placeholder="Nueva Contraseña (mínimo 8 caracteres)" minlength="8" style="width:100%; padding:10px; background:#0d0d0d; border:1px solid var(--border); color:#fff; border-radius:6px; margin-bottom:12px;">
                <button onclick="submitResetPassword()" style="width:100%;">Restablecer Contraseña</button>
            </div>
            <button onclick="closeForgotModal()" style="background:transparent; color:var(--text-dim); border:1px solid var(--text-dim); margin-top:12px; width:100%;">Cancelar</button>
        </div>
    </div>

    <script>
        function showForgotModal() { document.getElementById('forgot-modal').style.display = 'flex'; }
        function closeForgotModal() { document.getElementById('forgot-modal').style.display = 'none'; }
        function requestForgotToken() {
            const email = document.getElementById('forgot-email').value.trim();
            if (!email) return alert('Por favor ingresa tu email');
            fetch('/api/auth/forgot-password', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ email })
            }).then(r => r.json()).then(d => {
                if (d.success) {
                    document.getElementById('forgot-step-1').style.display = 'none';
                    document.getElementById('forgot-step-2').style.display = 'block';
                    document.getElementById('forgot-msg').textContent = d.message;
                } else {
                    alert(d.error || 'Error al solicitar token');
                }
            });
        }
        function submitResetPassword() {
            const token = document.getElementById('reset-token-input').value.trim();
            const new_password = document.getElementById('reset-new-pass').value.trim();
            if (!token || !new_password) return alert('Completa todos los campos');
            fetch('/api/auth/reset-password', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ token, new_password })
            }).then(r => r.json()).then(d => {
                if (d.success) {
                    alert('Contraseña actualizada correctamente. Ahora puedes iniciar sesión.');
                    closeForgotModal();
                } else {
                    alert(d.error || 'Error al restablecer contraseña');
                }
            });
        }
    </script>
</body>
</html>
"""

REGISTER_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Registro - Asistente de Trading</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg: #050505;
            --surface: #0a0a0a;
            --gold: #FFD700;
            --gold-dim: #B8860B;
            --text: #F5F5F5;
            --text-dim: #A0A0A0;
            --border: rgba(255, 215, 0, 0.2);
        }
        body {
            font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .register-box {
            background: var(--surface);
            padding: 40px;
            border-radius: 16px;
            border: 1px solid var(--border);
            box-shadow: 0 10px 40px rgba(0,0,0,0.8);
            width: 100%;
            max-width: 440px;
        }
        .register-box h1 {
            background: linear-gradient(90deg, var(--gold), #fff7cc, var(--gold));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            font-size: 24px;
            margin-bottom: 24px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .form-group { margin-bottom: 16px; }
        label { display: block; color: var(--gold); font-size: 13px; font-weight: 600; margin-bottom: 6px; }
        input {
            width: 100%;
            padding: 12px;
            background: #0d0d0d;
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text);
            font-size: 14px;
        }
        input:focus { outline: none; border-color: var(--gold); }
        button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(90deg, var(--gold), var(--gold-dim));
            color: #000;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 700;
            cursor: pointer;
            margin-top: 10px;
        }
        button:hover { opacity: 0.9; }
        .error { color: #FF2D2D; background: rgba(255,45,45,0.1); border: 1px solid rgba(255,45,45,0.3); padding: 10px; border-radius: 8px; margin-bottom: 18px; text-align: center; font-size: 13px; }
        .links { margin-top: 20px; text-align: center; font-size: 13px; color: var(--text-dim); }
        .links a { color: var(--gold); text-decoration: none; font-weight: 600; }
    </style>
</head>
<body>
    <div class="register-box">
        <h1>Crear Cuenta</h1>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST">
            <div class="form-group">
                <label>Nombre Completo</label>
                <input type="text" name="full_name" placeholder="Tu Nombre">
            </div>
            <div class="form-group">
                <label>Usuario *</label>
                <input type="text" name="username" placeholder="usuario123" required>
            </div>
            <div class="form-group">
                <label>Correo Electrónico *</label>
                <input type="email" name="email" placeholder="correo@ejemplo.com" required>
            </div>
            <div class="form-group">
                <label>Contraseña *</label>
                <input type="password" name="password" placeholder="Mínimo 8 caracteres" required minlength="8">
            </div>
            <button type="submit">Registrarme</button>
        </form>
        <div class="links">
            <p>¿Ya tienes cuenta? <a href="/login">Inicia sesión aquí</a></p>
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
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg: #050505;
            --surface: #0a0a0a;
            --surface-2: #111111;
            --gold: #FFD700;
            --gold-dim: #B8860B;
            --red: #FF2D2D;
            --green: #00E676;
            --purple: #8B5CF6;
            --text: #F5F5F5;
            --text-dim: #A0A0A0;
            --border: rgba(255, 215, 0, 0.15);
        }
        body {
            font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
        }
        .navbar {
            background: linear-gradient(90deg, #000000 0%, #1a0a1a 50%, #000000 100%);
            color: var(--text);
            padding: 22px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
            box-shadow: 0 0 30px rgba(139, 92, 246, 0.15);
        }
        .navbar h1 {
            background: linear-gradient(90deg, var(--gold), #fff7cc, var(--gold));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-size: 26px;
            letter-spacing: 2px;
            font-weight: 700;
            text-transform: uppercase;
        }
        .navbar a {
            color: var(--text);
            text-decoration: none;
            background: rgba(139, 92, 246, 0.12);
            padding: 8px 18px;
            border-radius: 6px;
            border: 1px solid rgba(139, 92, 246, 0.3);
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .navbar a:hover {
            background: rgba(139, 92, 246, 0.25);
            box-shadow: 0 0 12px rgba(139, 92, 246, 0.3);
        }
        .container {
            max-width: 1400px;
            margin: 24px auto;
            padding: 20px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 18px;
            margin-bottom: 22px;
        }
        .card {
            background: var(--surface);
            padding: 22px;
            border-radius: 14px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border);
            position: relative;
            overflow: hidden;
        }
        .card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, transparent, var(--gold), var(--purple), transparent);
        }
        .card h3 {
            color: var(--gold);
            margin-bottom: 16px;
            font-size: 13px;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            font-weight: 600;
            letter-spacing: 1px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .stat {
            font-size: 34px;
            font-weight: 700;
            font-family: 'SF Mono', 'Roboto Mono', Consolas, monospace;
            color: var(--text);
            margin: 14px 0;
            text-shadow: 0 0 18px rgba(255, 215, 0, 0.25);
        }
        .btn {
            padding: 11px 24px;
            margin: 8px 6px 0 0;
            background: transparent;
            color: var(--gold);
            border: 1px solid var(--gold);
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.25s ease;
            font-weight: 600;
            letter-spacing: 0.5px;
            box-shadow: 0 0 0 rgba(255, 215, 0, 0);
        }
        .btn:hover {
            background: rgba(255, 215, 0, 0.12);
            box-shadow: 0 0 18px rgba(255, 215, 0, 0.25);
            transform: translateY(-1px);
        }
        .btn-red {
            color: var(--red);
            border-color: var(--red);
            box-shadow: 0 0 0 rgba(255, 45, 45, 0);
        }
        .btn-red:hover {
            background: rgba(255, 45, 45, 0.12);
            box-shadow: 0 0 18px rgba(255, 45, 45, 0.25);
        }
        .btn-green {
            color: var(--green);
            border-color: var(--green);
            box-shadow: 0 0 0 rgba(0, 230, 118, 0);
        }
        .btn-green:hover {
            background: rgba(0, 230, 118, 0.12);
            box-shadow: 0 0 18px rgba(0, 230, 118, 0.25);
        }
        .btn-purple {
            color: var(--purple);
            border-color: var(--purple);
        }
        .btn-purple:hover {
            background: rgba(139, 92, 246, 0.12);
            box-shadow: 0 0 18px rgba(139, 92, 246, 0.25);
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        th, td {
            padding: 13px 15px;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
            color: var(--text-dim);
        }
        th {
            background: rgba(255, 215, 0, 0.06);
            font-weight: 700;
            color: var(--gold);
            text-transform: uppercase;
            font-size: 12px;
            letter-spacing: 0.8px;
        }
        tr:hover {
            background: rgba(139, 92, 246, 0.05);
        }
        .chart-container {
            position: relative;
            height: 420px;
            margin-top: 15px;
            border-radius: 14px;
            overflow: hidden;
            background: var(--surface-2);
            box-shadow: inset 0 0 0 1px rgba(255,215,0,0.08), 0 12px 40px rgba(0,0,0,0.5);
        }
        .chart-tooltip {
            position: absolute;
            display: none;
            z-index: 2;
            padding: 8px 10px;
            border: 1px solid rgba(212,175,55,0.55);
            border-radius: 6px;
            background: rgba(10,10,10,0.96);
            color: #F5F5F5;
            font: 12px 'SF Mono', Consolas, monospace;
            pointer-events: none;
            white-space: nowrap;
        }
        .alert-list {
            max-height: 320px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin-top: 12px;
        }
        .alert-item {
            padding: 12px 14px;
            border-radius: 10px;
            border-left: 4px solid var(--gold);
            background: var(--surface-2);
            font-size: 13px;
            transition: transform 0.15s ease;
        }
        .alert-item:hover { transform: translateX(4px); }
        .alert-item.critica { border-left-color: var(--red); box-shadow: 0 0 14px rgba(255, 45, 45, 0.15); }
        .alert-item.alta { border-left-color: #FF6B35; }
        .alert-item.media { border-left-color: var(--gold); }
        .alert-item.baja { border-left-color: var(--green); }
        .alert-item .alert-title {
            font-weight: 700;
            margin-bottom: 4px;
            color: var(--text);
        }
        .alert-item .alert-meta {
            color: var(--text-dim);
            font-size: 11px;
            margin-bottom: 6px;
        }
        .alert-item .alert-msg {
            color: var(--text-dim);
            line-height: 1.4;
        }
        .alert-badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-right: 6px;
        }
        .badge-volatilidad { background: rgba(255, 45, 45, 0.15); color: var(--red); border: 1px solid rgba(255, 45, 45, 0.3); }
        .badge-oportunidad { background: rgba(0, 230, 118, 0.12); color: var(--green); border: 1px solid rgba(0, 230, 118, 0.3); }
        .badge-noticia { background: rgba(139, 92, 246, 0.12); color: var(--purple); border: 1px solid rgba(139, 92, 246, 0.3); }
        .badge-breakout { background: rgba(255, 215, 0, 0.12); color: var(--gold); border: 1px solid rgba(255, 215, 0, 0.3); }
        .news-list {
            max-height: 340px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin-top: 12px;
        }
        .news-item {
            padding: 12px 14px;
            border-radius: 10px;
            background: var(--surface-2);
            border: 1px solid rgba(255,255,255,0.04);
            font-size: 13px;
        }
        .news-item .news-title { color: var(--text); margin-bottom: 5px; line-height: 1.4; }
        .news-item .news-meta { color: var(--text-dim); font-size: 11px; }
        .news-impact { font-weight: 700; text-transform: uppercase; font-size: 10px; margin-left: 8px; }
        .impact-alto { color: var(--red); }
        .impact-medio { color: var(--gold); }
        .impact-bajo { color: var(--green); }
        .volatility-bar {
            height: 6px;
            border-radius: 3px;
            background: rgba(255,255,255,0.06);
            overflow: hidden;
            margin-top: 8px;
        }
        .volatility-fill {
            height: 100%;
            border-radius: 3px;
            background: linear-gradient(90deg, var(--green), var(--gold), var(--red));
            transition: width 0.5s ease;
        }
        .pulse-dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--red);
            margin-right: 6px;
            box-shadow: 0 0 0 0 rgba(255, 45, 45, 0.7);
            animation: pulse-alert 1.5s infinite;
        }
        @keyframes pulse-alert {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 45, 45, 0.7); }
            70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(255, 45, 45, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 45, 45, 0); }
        }
        .chart-container canvas {
            width: 100% !important;
            height: 100% !important;
            display: block;
            cursor: crosshair;
        }
    </style>
</head>
<body>
    <div class="navbar">
        <h1>Asistente de Trading Inteligente</h1>
        <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
            <span id="nav-user-name" style="font-size: 13px; color: var(--text); font-weight: 600;">Usuario: Invitado</span>
            <span id="nav-plan-badge" style="font-size: 11px; padding: 4px 10px; border-radius: 12px; background: rgba(212,175,55,0.15); color: var(--gold); border: 1px solid var(--gold); font-weight: 700;">Plan: FREE</span>
            <button class="btn btn-purple" onclick="openPlansModal()" style="font-size:12px; padding:6px 14px; margin:0;">Planes ($0 - $19.99)</button>
            <button class="btn" onclick="openProfileModal()" style="font-size:12px; padding:6px 14px; margin:0;">Perfil</button>
            <button class="btn btn-red" onclick="logout()" style="font-size:12px; padding:6px 14px; margin:0;">Salir</button>
        </div>
    </div>
    <div class="container">
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                <h3>Gráfico de Precios</h3>
                <div style="display: flex; gap: 10px; align-items: center;">
                        <span id="chart-current-quote" style="color:var(--gold); font:12px 'SF Mono',Consolas,monospace; white-space:nowrap;">XAUUSD: -</span>
                        <span id="chart-update-time" style="color:var(--text-dim); font-size:11px; white-space:nowrap;">Conectando fuente...</span>
                        <label style="color:var(--gold); font-weight:600; font-size:12px; text-transform:uppercase; letter-spacing:0.5px;">Divisa:</label>
                    <select id="symbol-select" onchange="changeSymbol(this.value)" style="padding: 6px 12px; background:#0d0d0d; border:1px solid var(--gold); color:var(--text); border-radius:6px; font-family:'SF Mono',Consolas,monospace; font-size:12px;">
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
                </div>
            </div>
            <div class="chart-container">
                <canvas id="chart"></canvas>
                <div id="chart-tooltip" class="chart-tooltip"></div>
            </div>
        </div>

        <div class="card">
            <h3>Liquidez y flujo estimado</h3>
            <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; margin-top:12px;">
                <div><strong style="color:var(--gold);">Sesgo de flujo:</strong> <span id="liquidity-bias">Sin datos</span></div>
                <div><strong style="color:var(--gold);">Presión compra/venta:</strong> <span id="liquidity-pressure">-</span></div>
                <div><strong style="color:var(--gold);">Volumen relativo:</strong> <span id="liquidity-relative-volume">-</span></div>
                <div><strong style="color:var(--gold);">Zona con más volumen:</strong> <span id="liquidity-zone">-</span></div>
                <div><strong style="color:var(--gold);">Volumen analizado:</strong> <span id="liquidity-total">-</span></div>
            </div>
            <small id="liquidity-note" style="display:block; color:var(--text-dim); margin-top:12px;">
                Presión inferida de velas y volumen del proveedor; no representa órdenes institucionales ni garantiza flujo real.
            </small>
        </div>

        <div class="card">
            <h3>Análisis Inteligente de IA</h3>
            <div style="margin: 12px 0;"><strong style="color: var(--gold);">Señal:</strong> <span id="ai-signal" style="color: var(--green);">ESPERA</span></div>
            <div style="margin: 12px 0;"><strong style="color: var(--gold);">Confianza:</strong> <span id="ai-confidence" style="color: var(--gold);">0%</span></div>
            <div style="margin: 12px 0;"><strong style="color: var(--gold);">Patrón:</strong> <span id="ai-pattern">-</span></div>
            <div style="margin: 12px 0;"><strong style="color: var(--gold);">Volatilidad:</strong> <span id="ai-volatility">-</span></div>
            <div style="margin: 12px 0;"><strong style="color: var(--gold);">Inteligencia IA:</strong> <span id="ai-learning" style="color: var(--purple);">Aprendiendo...</span></div>
        </div>

        <div class="card">
            <h3>Predicciones y Niveles</h3>
            <div id="predictions-plan-locked" style="display:none; color:var(--text-dim);">
                Las predicciones están disponibles desde el plan PRO.
                <button class="btn btn-purple" onclick="openPlansModal()" style="margin-left:8px;">Ver planes</button>
            </div>
            <div id="predictions-content">
            <div style="margin: 12px 0;"><strong style="color: var(--gold);">Predicción (10 min):</strong> <span id="pred-direction">-</span></div>
            <div style="margin: 12px 0;"><strong style="color: var(--gold);">Precio Previsto:</strong> <span id="pred-price">-</span></div>
            <div style="margin: 12px 0;"><strong style="color: var(--gold);">Consenso de modelos:</strong> <span id="pred-confidence">-</span></div>
            <div style="margin: 12px 0;"><strong style="color: var(--gold);">Backtest direccional:</strong> <span id="pred-backtest">-</span> <small id="pred-cooldown" style="color:var(--text-dim);"></small></div>
            <div style="margin: 12px 0;"><strong style="color: var(--gold);">Validación adaptativa:</strong> <span id="pred-adaptive-backtest">-</span></div>
            <div style="margin: 12px 0;"><strong style="color: var(--gold);">Aprendizaje por modelo:</strong> <span id="pred-model-learning" style="color:var(--text-dim);">-</span></div>
            <small style="color:var(--text-dim);">El acierto es una prueba histórica reciente, no una probabilidad ni garantía de resultados futuros.</small>
            <div style="margin: 12px 0;"><strong style="color: var(--gold);">Operación sugerida:</strong> <span id="pred-signal">ESPERA</span> <strong style="color: var(--gold); margin-left:12px;">Riesgo/beneficio:</strong> <span id="pred-risk-reward">-</span></div>
            <div style="margin: 12px 0;"><strong style="color: var(--gold);">Entry:</strong> <span id="pred-entry">-</span>  <strong style="color: var(--gold); margin-left:12px;">SL:</strong> <span id="pred-sl">-</span>  <strong style="color: var(--gold); margin-left:12px;">TP:</strong> <span id="pred-tp">-</span></div>
            <div style="margin: 12px 0;"><strong style="color: var(--gold);">Filtro:</strong> <span id="pred-reasons">Calculando...</span></div>
            <small style="color:var(--text-dim);">Filtro mínimo 2:1. Las estimaciones no incluyen costos ni garantizan ganancias.</small>
            </div>
        </div>



        <div class="card">
            <h3>Predicción Avanzada de IA</h3>
            <div id="advanced-plan-locked" style="display:none; color:var(--text-dim); margin-bottom:12px;">
                La predicción avanzada requiere plan PRO o PREMIUM.
                <button class="btn btn-purple" onclick="openPlansModal()" style="margin-left:8px;">Ver planes</button>
            </div>
            <div style="margin-bottom: 16px;">
                <button class="btn btn-purple" id="adv-btn" onclick="loadAdvancedPrediction()">Calcular Predicción Avanzada</button>
                <span id="adv-loading" style="display:none; margin-left:12px; color:var(--purple); font-size:13px;">Calculando...</span>
                <span id="adv-timestamp" style="margin-left:12px; color:var(--text-dim); font-size:12px;"></span>
                <span id="adv-cooldown" style="margin-left:12px; color:var(--text-dim); font-size:12px;"></span>
            </div>
            <div id="adv-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; opacity:0.6;">
                <div><strong style="color: var(--gold);">Señal Combinada:</strong> <span id="adv-signal">-</span></div>
                <div><strong style="color: var(--gold);">Score:</strong> <span id="adv-score">-</span></div>
                <div><strong style="color: var(--gold);">Confianza:</strong> <span id="adv-confidence">-</span></div>
                <div><strong style="color: var(--gold);">Tendencia:</strong> <span id="adv-trend">-</span></div>
                <div><strong style="color: var(--gold);">RSI:</strong> <span id="adv-rsi">-</span></div>
                <div><strong style="color: var(--gold);">MACD:</strong> <span id="adv-macd">-</span></div>
                <div><strong style="color: var(--gold);">EMA 12/26:</strong> <span id="adv-ema">-</span></div>
                <div><strong style="color: var(--gold);">Estocástico:</strong> <span id="adv-stoch">-</span></div>
                <div><strong style="color: var(--gold);">ATR:</strong> <span id="adv-atr">-</span></div>
                <div><strong style="color: var(--gold);">Soporte:</strong> <span id="adv-support">-</span></div>
                <div><strong style="color: var(--gold);">Resistencia:</strong> <span id="adv-resistance">-</span></div>
                <div><strong style="color: var(--gold);">Rango Esperado:</strong> <span id="adv-range">-</span></div>
                <div><strong style="color: var(--gold);">Próximo Precio:</strong> <span id="adv-next">-</span></div>
            </div>
        </div>

        <div class="card">
            <h3>Noticias y Alertas de Volatilidad</h3>
            <div id="news-plan-locked" style="display:none; color:var(--text-dim);">
                Alertas de volatilidad y noticias están disponibles desde el plan PRO.
                <button class="btn btn-purple" onclick="openPlansModal()" style="margin-left:8px;">Ver planes</button>
            </div>
            <div id="news-content">
            <div style="display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 12px;">
                <button class="btn btn-purple" id="news-btn" onclick="loadNewsAlerts()">Actualizar Noticias/Alertas</button>
                <span id="news-loading" style="display:none; color:var(--purple); font-size:13px; align-self:center;">Cargando...</span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 18px;">
                <div>
                    <h4 style="color:var(--gold); font-size:13px; text-transform:uppercase; letter-spacing:1px; margin-bottom:10px;">Alertas en Vivo</h4>
                    <div id="alert-list" class="alert-list">
                        <div class="alert-item media">
                            <div class="alert-title">Sistema de alertas activo</div>
                            <div class="alert-meta">Ahora</div>
                            <div class="alert-msg">Se monitorean movimientos bruscos, ATR elevado y oportunidades de entrada.</div>
                        </div>
                    </div>
                    </div>
                </div>
                <div>
                    <h4 style="color:var(--gold); font-size:13px; text-transform:uppercase; letter-spacing:1px; margin-bottom:10px;">Noticias del Mercado</h4>
                    <div id="news-list" class="news-list">
                        <div class="news-item">
                            <div class="news-title">Cargando noticias...</div>
                        </div>
                    </div>
                </div>
            </div>
            <div style="margin-top: 16px; padding: 14px; border-radius: 10px; background: var(--surface-2); border: 1px solid rgba(255,255,255,0.04);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <span style="font-size:13px; color:var(--text-dim);">Índice de Volatilidad Actual</span>
                    <span id="vol-index" style="font-weight:700; color:var(--gold);">0%</span>
                </div>
                <div class="volatility-bar"><div id="vol-fill" class="volatility-fill" style="width:0%"></div></div>
                <div style="display: flex; gap: 16px; margin-top: 10px; font-size: 12px; color: var(--text-dim);">
                    <span>Spike: <b id="vol-spike" style="color:var(--text);">0%</b></span>
                    <span>ATR ratio: <b id="vol-atr" style="color:var(--text);">1.0x</b></span>
                    <span>Rango: <b id="vol-range" style="color:var(--text);">0%</b></span>
                </div>
            </div>
        </div>



        <div class="card" id="chat-card">
            <h3>Asistente de IA</h3>
            <div id="chat-plan-locked" style="display:none; color:var(--text-dim);">
                El chat con la IA está disponible desde el plan PRO.
                <button class="btn btn-purple" onclick="openPlansModal()" style="margin-left:8px;">Ver planes</button>
            </div>
            <div id="chat-content">
                <div id="chat-box" style="height: 240px; overflow-y: auto; background: var(--surface-2); border: 1px solid var(--border); border-radius: 10px; padding: 12px; margin-bottom: 15px; color: var(--text-dim);"></div>
                <div style="display: flex; gap: 10px;">
                    <input id="chat-input" type="text" placeholder="Escribe un comando o pregunta..." style="flex: 1; padding: 12px; background: #0d0d0d; border: 1px solid var(--gold); border-radius: 8px; color: var(--text); font-size: 14px;" />
                    <button class="btn" onclick="sendChat()">Enviar</button>
                </div>
                <div id="demo-trade-command" style="display:none; margin-top:10px; font-size:12px; color:var(--text-dim);">
                    PREMIUM · Demo MT5: <code>/trade auto demo XAUUSD</code> o <code>/trade auto demo EURUSD</code>.
                    Una operación por solicitud; riesgo estimado máximo USD 5.
                </div>
                <div id="chat-demo-trade-status" role="status" aria-live="polite" style="margin-top:8px; font-size:12px; color:var(--gold);"></div>
            </div>
        </div>
    </div>

    <!-- Modal Planes -->
    <div id="plans-modal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); justify-content:center; align-items:center; z-index:999; overflow-y:auto; padding:20px;">
        <div style="background:var(--surface); padding:30px; border-radius:16px; border:1px solid var(--gold); max-width:900px; width:100%;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                <h2 style="color:var(--gold);">Planes de Suscripción</h2>
                <button onclick="closePlansModal()" class="btn btn-red" style="padding:4px 10px; margin:0;">✕ Cerrar</button>
            </div>
            
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap:20px; margin-bottom:24px;">
                <!-- FREE -->
                <div style="background:var(--surface-2); padding:20px; border-radius:12px; border:1px solid rgba(255,255,255,0.1); text-align:center;">
                    <h3 style="color:var(--text); margin-bottom:10px;">FREE</h3>
                    <div style="font-size:28px; font-weight:700; color:var(--gold); margin-bottom:15px;">$0 <span style="font-size:13px; color:var(--text-dim);">/mes</span></div>
                    <ul style="text-align:left; font-size:13px; color:var(--text-dim); margin-bottom:20px; list-style:none; line-height:1.8;">
                        <li>✓ Precios en tiempo real</li>
                        <li>✓ Gráficos y datos reales</li>
                        <li>✓ Análisis técnico básico cada 15 minutos</li>
                        <li>✗ Chat con IA</li>
                        <li>✗ Predicciones</li>
                        <li>✗ Predicción Avanzada (PRO)</li>
                        <li>✗ Análisis Profesional (PREMIUM)</li>
                    </ul>
                    <button onclick="changePlan('FREE')" class="btn" style="width:100%; margin:0;">Usar FREE</button>
                </div>
                <!-- PRO -->
                <div style="background:var(--surface-2); padding:20px; border-radius:12px; border:1px solid var(--purple); text-align:center;">
                    <h3 style="color:var(--purple); margin-bottom:10px;">PRO</h3>
                    <div style="font-size:28px; font-weight:700; color:var(--gold); margin-bottom:15px;">$9.99 <span style="font-size:13px; color:var(--text-dim);">/mes</span></div>
                    <ul style="text-align:left; font-size:13px; color:var(--text-dim); margin-bottom:20px; list-style:none; line-height:1.8;">
                        <li>✓ Todo de FREE</li>
                        <li>✓ Análisis cada 5 minutos</li>
                        <li>✓ Predicción Avanzada (cooldown 5 min)</li>
                        <li>✓ Chat con IA</li>
                        <li>✓ Alertas de Volatilidad</li>
                        <li>✓ Indicadores RSI, MACD, BB</li>
                        <li>✗ Análisis Profesional</li>
                    </ul>
                    <button onclick="changePlan('PRO')" class="btn btn-purple" style="width:100%; margin:0;">Continuar con PayPal</button>
                </div>
                <!-- PREMIUM -->
                <div style="background:var(--surface-2); padding:20px; border-radius:12px; border:1px solid var(--gold); text-align:center;">
                    <h3 style="color:var(--gold); margin-bottom:10px;">PREMIUM</h3>
                    <div style="font-size:28px; font-weight:700; color:var(--gold); margin-bottom:15px;">$19.99 <span style="font-size:13px; color:var(--text-dim);">/mes</span></div>
                    <ul style="text-align:left; font-size:13px; color:var(--text-dim); margin-bottom:20px; list-style:none; line-height:1.8;">
                        <li>✓ Todo de PRO</li>
                        <li>✓ Análisis Profesional IA (cooldown 5 min)</li>
                        <li>✓ Chat con IA</li>
                        <li>✓ Acceso Prioritario</li>
                        <li>✓ Soporte 24/7</li>
                    </ul>
                    <button onclick="changePlan('PREMIUM')" class="btn" style="width:100%; margin:0; background:var(--gold); color:#000;">Continuar con PayPal</button>
                </div>
            </div>

            <div style="display:flex; gap:12px; margin-bottom:20px;">
                <button onclick="renewPlan()" class="btn btn-green" style="flex:1;">Renovar Plan (+30 Días)</button>
                <button onclick="cancelPlan()" class="btn btn-red" style="flex:1;">Cancelar Suscripción</button>
            </div>

            <h4 style="color:var(--gold); margin-bottom:10px;">Historial de Pagos</h4>
            <div style="max-height:180px; overflow-y:auto; background:var(--bg); border-radius:8px; padding:10px;">
                <table style="width:100%; font-size:12px;">
                    <thead><tr><th>Plan</th><th>Monto</th><th>Estado</th><th>Fecha</th><th>Descripción</th></tr></thead>
                    <tbody id="billing-history-body"><tr><td colspan="5" style="text-align:center;">Cargando...</td></tr></tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Modal Perfil -->
    <div id="profile-modal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); justify-content:center; align-items:center; z-index:999;">
        <div style="background:var(--surface); padding:30px; border-radius:16px; border:1px solid var(--gold); max-width:450px; width:90%;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
                <h3 style="color:var(--gold);">Perfil y Configuración</h3>
                <button onclick="closeProfileModal()" class="btn btn-red" style="padding:4px 10px; margin:0;">✕</button>
            </div>
            <div style="margin-bottom:20px;">
                <h4 style="color:var(--text); font-size:13px; margin-bottom:8px;">Datos de Usuario</h4>
                <div style="margin-bottom:10px;">
                    <label style="font-size:12px; color:var(--text-dim);">Nombre Completo:</label>
                    <input id="profile-fullname" type="text" style="width:100%; padding:8px; background:#0d0d0d; border:1px solid var(--border); color:#fff; border-radius:6px;">
                </div>
                <button onclick="saveProfile()" class="btn" style="width:100%; margin:0;">Guardar Perfil</button>
            </div>
            <div style="border-top:1px solid rgba(255,255,255,0.1); padding-top:15px;">
                <h4 style="color:var(--text); font-size:13px; margin-bottom:8px;">Cambiar Contraseña</h4>
                <div style="margin-bottom:10px;">
                    <input id="pass-current" type="password" placeholder="Contraseña Actual" style="width:100%; padding:8px; background:#0d0d0d; border:1px solid var(--border); color:#fff; border-radius:6px; margin-bottom:8px;">
                    <input id="pass-new" type="password" placeholder="Nueva Contraseña (mín 8 car.)" minlength="8" style="width:100%; padding:8px; background:#0d0d0d; border:1px solid var(--border); color:#fff; border-radius:6px;">
                </div>
                <button onclick="changePassword()" class="btn btn-purple" style="width:100%; margin:0;">Actualizar Contraseña</button>
            </div>
        </div>
    </div>

    <script>
        let chart = null;
        let chartHoverData = null;
        let currentSymbol = 'EURUSD';
        let currentDecimals = 4;
        let currentSubscriptionPlan = 'FREE';
        let demoTradePollingJobId = null;
        const PREDICTION_COOLDOWN_MS = 15000;
        const BASIC_ANALYSIS_COOLDOWN_MS = 300000;
        const FREE_ANALYSIS_COOLDOWN_MS = 900000;
        const PREDICTION_HORIZON_MINUTES = 10;
        let lastPredictionRequestAt = 0;
        let predictionRequestInFlight = false;
        let lastAIRequestAt = 0;
        let advancedCooldownInterval = null;
        const SYMBOL_DECIMALS = {
            'XAUUSD': 2, 'EURUSD': 5, 'GBPUSD': 5, 'USDJPY': 3,
            'US30': 1, 'NAS100': 1, 'BTCUSD': 2, 'USDCHF': 5,
            'AUDUSD': 5, 'USOIL': 2
        };

        function getSymbolDecimals(symbol) {
            return SYMBOL_DECIMALS[symbol] || 5;
        }

        function formatPrice(value, decimals) {
            if (typeof value !== 'number') return value || '-';
            return value.toFixed(decimals);
        }

        function update() {
            fetch('/api/status')
                .then(r => r.json())
                .then(d => {
                    if (d.error) {
                        console.warn('Status API returned error:', d.error);
                    }
                    
                    currentSymbol = d.symbol || currentSymbol;
                    currentDecimals = typeof d.decimals === 'number' ? d.decimals : getSymbolDecimals(currentSymbol);

                    const quoteElement = document.getElementById('chart-current-quote');
                    if (quoteElement && typeof d.price === 'number') {
                        quoteElement.textContent = currentSymbol + ': ' + formatPrice(d.price, currentDecimals);
                    }
                    const updateTimeElement = document.getElementById('chart-update-time');
                    if (updateTimeElement) {
                        const isMt5Source = d.price_source === 'MetaTrader 5';
                        const sourceLabel = isMt5Source ?
                            'MetaTrader 5 · velas ' + (d.chart_timeframe || '1m') :
                            (d.price_source || 'Fuente sin confirmar');
                        if (d.price_updated_at) {
                            const quoteTime = new Date(d.price_updated_at);
                            const stale = Date.now() - quoteTime.getTime() > 180000;
                            const timeLabel = quoteTime.toLocaleTimeString(
                                undefined,
                                isMt5Source ? { timeZone: 'UTC' } : undefined
                            );
                            updateTimeElement.textContent = sourceLabel + ' · ' +
                                (stale ? 'último tick ' : 'tick ') +
                                timeLabel + (isMt5Source ? ' UTC/MT5' : '') +
                                (stale ? ' · dato atrasado' : '');
                        } else {
                            updateTimeElement.textContent = sourceLabel + ' · Sin cotización';
                        }
                    }
                    const chartDataArr = Array.isArray(d.chart_candles) && d.chart_candles.length > 0 ?
                        d.chart_candles : (Array.isArray(d.chart_prices) && d.chart_prices.length > 0 ?
                            d.chart_prices : (Array.isArray(d.candles) && d.candles.length > 0 ?
                                d.candles : (Array.isArray(d.prices) ? d.prices : [])));
                    drawChart(chartDataArr);
                    updateLiquidityUI(d.liquidity || {});
                    
                    // Actualizar otros elementos
                    if (currentSubscriptionPlan === 'PRO' || currentSubscriptionPlan === 'PREMIUM') {
                        loadChat();
                    }
                    
                    try {
                        loadSymbols();
                    } catch (e) { console.error('Error en loadSymbols:', e); }
                    
                    try {
                        updateAIAnalysis();
                    } catch (e) { console.error('Error en updateAIAnalysis:', e); }
                    
                    try {
                        updatePrediction();
                    } catch (e) { console.error('Error en updatePrediction:', e); }
                    
                })
                .catch(e => {
                    console.error('Error fetching dashboard status:', e);
                });
        }

        function normalizeChartData(chartData) {
            if (!Array.isArray(chartData)) return [];
            return chartData.map((item) => {
                const rawValue = typeof item === 'number' ? item :
                    (item && item.c !== undefined ? item.c :
                        (item && item.y !== undefined ? item.y : item && item.close));
                const value = Number(rawValue);
                return Number.isFinite(value) && value > 0 ? value : null;
            }).filter(value => value !== null);
        }

        function normalizeCandleData(chartData) {
            if (!Array.isArray(chartData)) return [];
            return chartData.map(item => {
                if (!item || typeof item !== 'object' ||
                    item.open === undefined || item.high === undefined ||
                    item.low === undefined || item.close === undefined) {
                    return null;
                }
                const candle = {
                    time: item.time,
                    open: Number(item.open),
                    high: Number(item.high),
                    low: Number(item.low),
                    close: Number(item.close)
                };
                if (
                    ![candle.open, candle.high, candle.low, candle.close].every(
                        value => Number.isFinite(value) && value > 0
                    ) ||
                    candle.high < Math.max(candle.open, candle.close) ||
                    candle.low > Math.min(candle.open, candle.close)
                ) return null;
                return candle;
            }).filter(candle => candle !== null);
        }

        function formatCandleTime(value) {
            const numeric = Number(value);
            const date = Number.isFinite(numeric) ?
                new Date(numeric < 100000000000 ? numeric * 1000 : numeric) :
                new Date(value);
            return Number.isFinite(date.getTime()) ?
                date.toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                    timeZone: 'UTC'
                }) : '';
        }

        function drawCandlestickChart(candles) {
            const canvas = document.getElementById('chart');
            if (!canvas || !canvas.parentElement) return;
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
                chart = null;
            }
            if (!canvas.dataset.hoverBound) {
                canvas.addEventListener('mousemove', showChartTooltip);
                canvas.addEventListener('mouseleave', hideChartTooltip);
                canvas.dataset.hoverBound = 'true';
            }

            const bounds = canvas.parentElement.getBoundingClientRect();
            const width = Math.max(bounds.width, 320);
            const height = Math.max(bounds.height, 260);
            const pixelRatio = window.devicePixelRatio || 1;
            canvas.width = Math.round(width * pixelRatio);
            canvas.height = Math.round(height * pixelRatio);
            const context = canvas.getContext('2d');
            if (!context) return;
            context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
            context.clearRect(0, 0, width, height);

            if (!candles.length) {
                chartHoverData = null;
                hideChartTooltip();
                context.fillStyle = '#A0A0A0';
                context.font = '14px sans-serif';
                context.textAlign = 'center';
                context.fillText('Esperando datos de mercado...', width / 2, height / 2);
                return;
            }

            const padding = { top: 24, right: 78, bottom: 34, left: 16 };
            const plotWidth = width - padding.left - padding.right;
            const plotHeight = height - padding.top - padding.bottom;
            const low = Math.min(...candles.map(candle => candle.low));
            const high = Math.max(...candles.map(candle => candle.high));
            const range = high - low || Math.max(Math.abs(high) * 0.001, 0.000001);
            const minimum = low - range * 0.08;
            const maximum = high + range * 0.08;
            const yAt = value => padding.top + (maximum - value) * plotHeight / (maximum - minimum);
            const xAt = index => padding.left + (index + 0.5) * plotWidth / candles.length;
            const candleWidth = Math.max(2, Math.min(12, plotWidth / candles.length * 0.68));
            chartHoverData = {
                values: candles,
                left: padding.left,
                right: padding.left + plotWidth,
                top: padding.top,
                bottom: padding.top + plotHeight,
                plotWidth
            };

            context.font = '10px monospace';
            context.textAlign = 'right';
            context.textBaseline = 'middle';
            for (let line = 0; line <= 4; line++) {
                const y = padding.top + line * plotHeight / 4;
                const value = maximum - line * (maximum - minimum) / 4;
                context.strokeStyle = 'rgba(255,255,255,0.08)';
                context.beginPath();
                context.moveTo(padding.left, y);
                context.lineTo(width - padding.right, y);
                context.stroke();
                context.fillStyle = '#A0A0A0';
                context.fillText(formatPrice(value, currentDecimals), width - 8, y);
            }

            candles.forEach((candle, index) => {
                const x = xAt(index);
                const rising = candle.close >= candle.open;
                const color = rising ? '#26A69A' : '#EF5350';
                context.strokeStyle = color;
                context.fillStyle = color;
                context.lineWidth = 1;
                context.beginPath();
                context.moveTo(x, yAt(candle.high));
                context.lineTo(x, yAt(candle.low));
                context.stroke();

                const openY = yAt(candle.open);
                const closeY = yAt(candle.close);
                const bodyTop = Math.min(openY, closeY);
                const bodyHeight = Math.max(1, Math.abs(closeY - openY));
                context.fillRect(x - candleWidth / 2, bodyTop, candleWidth, bodyHeight);
            });

            const lastCandle = candles[candles.length - 1];
            const currentY = yAt(lastCandle.close);
            context.strokeStyle = 'rgba(212,175,55,0.75)';
            context.setLineDash([4, 3]);
            context.beginPath();
            context.moveTo(padding.left, currentY);
            context.lineTo(width - padding.right, currentY);
            context.stroke();
            context.setLineDash([]);

            const labelCount = Math.min(5, candles.length);
            context.fillStyle = '#A0A0A0';
            context.font = '10px monospace';
            context.textBaseline = 'top';
            for (let label = 0; label < labelCount; label++) {
                const index = Math.round(label * (candles.length - 1) / Math.max(1, labelCount - 1));
                const x = xAt(index);
                context.textAlign = label === 0 ? 'left' :
                    label === labelCount - 1 ? 'right' : 'center';
                context.fillText(formatCandleTime(candles[index].time), x, height - padding.bottom + 8);
            }
        }

        function drawFallbackChart(dataPoints) {
            const canvas = document.getElementById('chart');
            if (!canvas || !canvas.parentElement) return;
            if (!canvas.dataset.hoverBound) {
                canvas.addEventListener('mousemove', showChartTooltip);
                canvas.addEventListener('mouseleave', hideChartTooltip);
                canvas.dataset.hoverBound = 'true';
            }
            const bounds = canvas.parentElement.getBoundingClientRect();
            const width = Math.max(bounds.width, 320);
            const height = Math.max(bounds.height, 260);
            const pixelRatio = window.devicePixelRatio || 1;
            canvas.width = Math.round(width * pixelRatio);
            canvas.height = Math.round(height * pixelRatio);
            const context = canvas.getContext('2d');
            if (!context) return;
            context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
            context.clearRect(0, 0, width, height);

            if (!dataPoints.length) {
                chartHoverData = null;
                hideChartTooltip();
                context.fillStyle = '#A0A0A0';
                context.font = '14px sans-serif';
                context.textAlign = 'center';
                context.fillText('Esperando datos de mercado...', width / 2, height / 2);
                return;
            }

            const padding = { top: 24, right: 76, bottom: 30, left: 16 };
            const plotWidth = width - padding.left - padding.right;
            const plotHeight = height - padding.top - padding.bottom;
            chartHoverData = {
                values: dataPoints.slice(),
                left: padding.left,
                right: padding.left + plotWidth,
                top: padding.top,
                bottom: padding.top + plotHeight,
                plotWidth
            };
            const low = Math.min(...dataPoints);
            const high = Math.max(...dataPoints);
            const range = high - low || Math.max(Math.abs(high) * 0.001, 0.000001);
            const minimum = low - range * 0.08;
            const maximum = high + range * 0.08;
            const xAt = index => padding.left + (dataPoints.length < 2 ? plotWidth / 2 : index * plotWidth / (dataPoints.length - 1));
            const yAt = value => padding.top + (maximum - value) * plotHeight / (maximum - minimum);
            const isOverallUp = dataPoints[dataPoints.length - 1] >= dataPoints[0];
            const lineColor = isOverallUp ? '#D4AF37' : '#8B5CF6';

            context.font = '10px monospace';
            context.textAlign = 'right';
            context.textBaseline = 'middle';
            for (let line = 0; line <= 4; line++) {
                const y = padding.top + line * plotHeight / 4;
                const value = maximum - line * (maximum - minimum) / 4;
                context.strokeStyle = 'rgba(255,255,255,0.08)';
                context.beginPath();
                context.moveTo(padding.left, y);
                context.lineTo(width - padding.right, y);
                context.stroke();
                context.fillStyle = '#A0A0A0';
                context.fillText(formatPrice(value, currentDecimals), width - 8, y);
            }

            const gradient = context.createLinearGradient(0, padding.top, 0, height - padding.bottom);
            gradient.addColorStop(0, isOverallUp ? 'rgba(212,175,55,0.28)' : 'rgba(139,92,246,0.28)');
            gradient.addColorStop(1, 'rgba(0,0,0,0)');
            context.beginPath();
            dataPoints.forEach((value, index) => {
                const x = xAt(index);
                const y = yAt(value);
                if (index === 0) context.moveTo(x, y);
                else context.lineTo(x, y);
            });
            context.lineTo(xAt(dataPoints.length - 1), height - padding.bottom);
            context.lineTo(xAt(0), height - padding.bottom);
            context.closePath();
            context.fillStyle = gradient;
            context.fill();

            context.beginPath();
            dataPoints.forEach((value, index) => {
                const x = xAt(index);
                const y = yAt(value);
                if (index === 0) context.moveTo(x, y);
                else context.lineTo(x, y);
            });
            context.strokeStyle = lineColor;
            context.lineWidth = 2.5;
            context.stroke();
            context.fillStyle = '#A0A0A0';
            context.font = '10px monospace';
            context.textAlign = 'left';
            context.textBaseline = 'bottom';
            context.fillText('1', padding.left, height - 6);
            context.textAlign = 'right';
            context.fillText(String(dataPoints.length), width - padding.right, height - 6);
        }

        function showChartTooltip(event) {
            const canvas = event.currentTarget;
            const tooltip = document.getElementById('chart-tooltip');
            if (!chartHoverData || !tooltip || chartHoverData.values.length === 0) return;

            const rect = canvas.getBoundingClientRect();
            const x = event.clientX - rect.left;
            const y = event.clientY - rect.top;
            if (x < chartHoverData.left || x > chartHoverData.right ||
                y < chartHoverData.top || y > chartHoverData.bottom) {
                hideChartTooltip();
                return;
            }

            const relativeX = (x - chartHoverData.left) / chartHoverData.plotWidth;
            const index = Math.round(relativeX * (chartHoverData.values.length - 1));
            const item = chartHoverData.values[index];
            if (item && typeof item === 'object' && item.open !== undefined) {
                tooltip.textContent = currentSymbol + ' · ' +
                    formatCandleTime(item.time) + ' UTC · O ' +
                    formatPrice(item.open, currentDecimals) + ' H ' +
                    formatPrice(item.high, currentDecimals) + ' L ' +
                    formatPrice(item.low, currentDecimals) + ' C ' +
                    formatPrice(item.close, currentDecimals);
            } else {
                tooltip.textContent = currentSymbol + ': ' +
                    formatPrice(item, currentDecimals);
            }
            tooltip.style.display = 'block';

            const containerRect = canvas.parentElement.getBoundingClientRect();
            const left = event.clientX - containerRect.left + 12;
            const top = event.clientY - containerRect.top - tooltip.offsetHeight - 8;
            tooltip.style.left = Math.max(8, Math.min(left, containerRect.width - tooltip.offsetWidth - 8)) + 'px';
            tooltip.style.top = Math.max(8, Math.min(top, containerRect.height - tooltip.offsetHeight - 8)) + 'px';
        }

        function hideChartTooltip() {
            const tooltip = document.getElementById('chart-tooltip');
            if (tooltip) tooltip.style.display = 'none';
        }

        function drawChart(chartData) {
            const candles = normalizeCandleData(chartData);
            if (candles.length) {
                drawCandlestickChart(candles);
                return;
            }
            const dataPoints = normalizeChartData(chartData);
            if (!dataPoints.length) {
                if (chart) {
                    chart.destroy();
                    chart = null;
                }
                drawFallbackChart([]);
                return;
            }
            if (typeof Chart === 'undefined') {
                drawFallbackChart(dataPoints);
                return;
            }

            const canvas = document.getElementById('chart');
            if (!canvas) {
                console.error('Canvas de gráfico no encontrado');
                return;
            }

            try {
                const canvasContext = canvas.getContext('2d');
                if (!canvasContext) return;

                const labels = dataPoints.map((_, i) => (i + 1).toString());
                const upColor = '#D4AF37';      // Dorado - para subidas
                const downColor = '#8B5CF6';    // Morado - para bajadas
                
                const firstVal = dataPoints[0] || 0;
                const lastVal = dataPoints[dataPoints.length - 1] || 0;
                const isOverallUp = lastVal >= firstVal;
                const mainColor = isOverallUp ? upColor : downColor;

                // Si el gráfico ya existe, actualizamos los datos sin destruirlo constantemente
                if (chart && typeof chart.update === 'function' && chart.ctx) {
                    try {
                        chart.data.labels = labels;
                        chart.data.datasets[0].label = currentSymbol + ' (' + formatPrice(lastVal, currentDecimals) + ')';
                        chart.data.datasets[0].data = dataPoints;
                        chart.data.datasets[0].borderColor = mainColor;
                        if (chart.options && chart.options.plugins && chart.options.plugins.legend) {
                            chart.options.plugins.legend.labels.color = mainColor;
                        }
                        chart.update('none');
                        return;
                    } catch (e) {
                        console.warn('Error actualizando gráfico, recreando:', e);
                        try { chart.destroy(); } catch (err) {}
                        chart = null;
                    }
                }

                const chartConfig = {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: currentSymbol + ' (' + formatPrice(lastVal, currentDecimals) + ')',
                            data: dataPoints,
                            borderColor: mainColor,
                            backgroundColor: (context) => {
                                try {
                                    const chartObj = context.chart;
                                    const canvasCtx = chartObj.ctx;
                                    const gradient = canvasCtx.createLinearGradient(0, 0, 0, 380);
                                    if (isOverallUp) {
                                        gradient.addColorStop(0, 'rgba(212, 175, 55, 0.30)');
                                        gradient.addColorStop(1, 'rgba(212, 175, 55, 0.00)');
                                    } else {
                                        gradient.addColorStop(0, 'rgba(139, 92, 246, 0.30)');
                                        gradient.addColorStop(1, 'rgba(139, 92, 246, 0.00)');
                                    }
                                    return gradient;
                                } catch (e) {
                                    return isOverallUp ? 'rgba(212, 175, 55, 0.15)' : 'rgba(139, 92, 246, 0.15)';
                                }
                            },
                            fill: true,
                            tension: 0.3,
                            pointRadius: 3,
                            pointHoverRadius: 7,
                            pointBackgroundColor: (ctx) => {
                                try {
                                    if (ctx && ctx.dataIndex > 0 && ctx.chart && ctx.chart.data && ctx.chart.data.datasets && ctx.chart.data.datasets[0]) {
                                        const datasetData = ctx.chart.data.datasets[0].data;
                                        if (datasetData && ctx.dataIndex < datasetData.length) {
                                            const current = datasetData[ctx.dataIndex];
                                            const prev = datasetData[ctx.dataIndex - 1];
                                            return (current >= prev) ? upColor : downColor;
                                        }
                                    }
                                } catch(e) {}
                                return mainColor;
                            },
                            pointBorderColor: '#FFFFFF',
                            pointBorderWidth: 1.5,
                            borderWidth: 2.5,
                            segment: {
                                borderColor: (ctx) => {
                                    try {
                                        if (ctx && ctx.p0 && ctx.p1 && ctx.p0.parsed && ctx.p1.parsed) {
                                            return ctx.p1.parsed.y >= ctx.p0.parsed.y ? upColor : downColor;
                                        }
                                    } catch(e) {}
                                    return mainColor;
                                }
                            }
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        animation: false,
                        layout: {
                            padding: { top: 15, right: 15, bottom: 10, left: 10 }
                        },
                        plugins: {
                            legend: {
                                display: true,
                                labels: { 
                                    color: mainColor, 
                                    font: { family: 'SF Mono, monospace', size: 12, weight: 'bold' },
                                    padding: 15
                                }
                            },
                            tooltip: {
                                mode: 'index',
                                intersect: false,
                                backgroundColor: 'rgba(10, 10, 10, 0.95)',
                                titleColor: '#D4AF37',
                                bodyColor: '#F5F5F5',
                                borderColor: 'rgba(212, 175, 55, 0.4)',
                                borderWidth: 1,
                                padding: 12,
                                callbacks: {
                                    label: (context) => {
                                        const value = Number(context.parsed.y);
                                        return '  ' + currentSymbol + ': ' + formatPrice(value, currentDecimals);
                                    }
                                }
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: false,
                                grid: {
                                    color: 'rgba(255, 255, 255, 0.05)'
                                },
                                ticks: {
                                    color: '#A0A0A0',
                                    font: { family: 'SF Mono, monospace', size: 10 },
                                    callback: (val) => formatPrice(val, currentDecimals)
                                }
                            },
                            x: {
                                display: true,
                                grid: { display: false },
                                ticks: {
                                    color: '#A0A0A0',
                                    font: { family: 'SF Mono, monospace', size: 9 },
                                    maxTicksLimit: 8
                                }
                            }
                        }
                    }
                };
                
                chart = new Chart(canvasContext, chartConfig);
            } catch (e) {
                console.error('Error al dibujar gráfico:', e);
            }
        }

        function loadCurrentUser() {
            return fetch('/api/auth/me')
                .then(r => {
                    if (r.status === 401) {
                        window.location.href = '/login';
                        return null;
                    }
                    return r.json();
                })
                .then(d => {
                    if (!d || !d.success) return;
                    const u = d.user;
                    const previousPlan = currentSubscriptionPlan;
                    currentSubscriptionPlan = u.subscription_plan || 'FREE';
                    if (previousPlan !== currentSubscriptionPlan) {
                        lastPredictionRequestAt = 0;
                        lastAIRequestAt = 0;
                    }
                    document.getElementById('nav-user-name').textContent = 'Usuario: ' + (u.full_name || u.username);
                    document.getElementById('nav-plan-badge').textContent = 'Plan: ' + currentSubscriptionPlan;
                    applyPlanFeatureAccess();
                    if (document.getElementById('profile-fullname')) {
                        document.getElementById('profile-fullname').value = u.full_name || '';
                    }
                    return u;
                })
                .catch(e => console.error('Error cargando usuario:', e));
        }

        function applyPlanFeatureAccess() {
            const canUseChat = currentSubscriptionPlan === 'PRO' || currentSubscriptionPlan === 'PREMIUM';
            const chatContent = document.getElementById('chat-content');
            const chatLocked = document.getElementById('chat-plan-locked');
            const demoTradeCommand = document.getElementById('demo-trade-command');
            const predictionsContent = document.getElementById('predictions-content');
            const predictionsLocked = document.getElementById('predictions-plan-locked');
            const newsContent = document.getElementById('news-content');
            const newsLocked = document.getElementById('news-plan-locked');
            const advancedButton = document.getElementById('adv-btn');
            const advancedLocked = document.getElementById('advanced-plan-locked');
            const advancedGrid = document.getElementById('adv-grid');
            if (predictionsContent) predictionsContent.style.display = canUseChat ? '' : 'none';
            if (predictionsLocked) predictionsLocked.style.display = canUseChat ? 'none' : 'block';
            if (newsContent) newsContent.style.display = canUseChat ? '' : 'none';
            if (newsLocked) newsLocked.style.display = canUseChat ? 'none' : 'block';
            if (chatContent) chatContent.style.display = canUseChat ? '' : 'none';
            if (chatLocked) chatLocked.style.display = canUseChat ? 'none' : 'block';
            if (demoTradeCommand) {
                demoTradeCommand.style.display =
                    currentSubscriptionPlan === 'PREMIUM' ? 'block' : 'none';
            }
            if (advancedButton) advancedButton.style.display = canUseChat ? '' : 'none';
            if (advancedLocked) advancedLocked.style.display = canUseChat ? 'none' : 'block';
            if (advancedGrid) advancedGrid.style.display = canUseChat ? 'grid' : 'none';
        }

        function openPlansModal() {
            document.getElementById('plans-modal').style.display = 'flex';
            loadBillingHistory();
        }

        function closePlansModal() {
            document.getElementById('plans-modal').style.display = 'none';
        }

        function openProfileModal() {
            document.getElementById('profile-modal').style.display = 'flex';
        }

        function closeProfileModal() {
            document.getElementById('profile-modal').style.display = 'none';
        }

        function logout() {
            fetch('/api/auth/logout', { method: 'POST' })
                .then(() => window.location.href = '/login');
        }

        function changePlan(plan) {
            if (plan === 'FREE') {
                return cancelPlan();
            }
            fetch('/api/subscription/checkout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ plan })
            })
                .then(async r => {
                    const data = await r.json();
                    if (!r.ok || !data.success) {
                        throw new Error(data.error || 'No se pudo iniciar el checkout.');
                    }
                    return data;
                })
                .then(d => {
                    if (!d.approval_url) throw new Error('PayPal no devolvió el enlace de aprobación.');
                    window.location.assign(d.approval_url);
                })
                .catch(e => alert(e.message));
        }

        function cancelPlan() {
            if (!confirm('¿Seguro que deseas cancelar tu suscripción y volver al plan FREE?')) return;
            fetch('/api/subscription/cancel', { method: 'POST' })
                .then(r => r.json())
                .then(d => {
                    if (d.success) {
                        alert(d.message);
                        loadCurrentUser().then(() => update());
                        loadBillingHistory();
                    } else {
                        alert(d.error || 'Error cancelando suscripción');
                    }
                });
        }

        function renewPlan() {
            fetch('/api/subscription/renew', { method: 'POST' })
                .then(r => r.json())
                .then(d => {
                    if (d.success) {
                        alert(d.message);
                        loadCurrentUser().then(() => update());
                        loadBillingHistory();
                    } else {
                        alert(d.error || 'Error renovando suscripción');
                    }
                });
        }

        function loadBillingHistory() {
            fetch('/api/billing/history')
                .then(r => r.json())
                .then(d => {
                    const tbody = document.getElementById('billing-history-body');
                    if (!d.success || !d.billing_history || d.billing_history.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">Sin registros de pago</td></tr>';
                        return;
                    }
                    tbody.innerHTML = d.billing_history.map(b => {
                        const date = b.charged_at ? new Date(b.charged_at).toLocaleDateString() : '-';
                        return `<tr>
                            <td><b>${b.plan}</b></td>
                            <td>$${b.amount}</td>
                            <td><span style="color:var(--green);">${b.status}</span></td>
                            <td>${date}</td>
                            <td>${b.description || '-'}</td>
                        </tr>`;
                    }).join('');
                });
        }

        function saveProfile() {
            const full_name = document.getElementById('profile-fullname').value.trim();
            fetch('/api/user/profile', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ full_name })
            })
                .then(r => r.json())
                .then(d => {
                    if (d.success) {
                        alert('Perfil actualizado correctamente');
                        loadCurrentUser();
                        closeProfileModal();
                    } else {
                        alert(d.error || 'Error actualizando perfil');
                    }
                });
        }

        function changePassword() {
            const current_password = document.getElementById('pass-current').value;
            const new_password = document.getElementById('pass-new').value;
            if (!current_password || !new_password) return alert('Completa ambas contraseñas');
            fetch('/api/user/password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ current_password, new_password })
            })
                .then(r => r.json())
                .then(d => {
                    if (d.success) {
                        alert('Contraseña actualizada correctamente');
                        document.getElementById('pass-current').value = '';
                        document.getElementById('pass-new').value = '';
                        closeProfileModal();
                    } else {
                        alert(d.error || 'Error cambiando contraseña');
                    }
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
                    el.style.background = 'rgba(255, 215, 0, 0.10)';
                    el.style.borderLeft = '3px solid var(--gold)';
                    el.style.color = 'var(--text)';
                } else {
                    el.style.background = 'rgba(139, 92, 246, 0.10)';
                    el.style.borderLeft = '3px solid var(--purple)';
                    el.style.color = 'var(--text)';
                }
                const title = document.createElement('strong');
                title.style.color = sender === 'IA' || sender === 'Sistema' ? 'var(--gold)' : 'var(--purple)';
                title.textContent = (sender === 'IA' || sender === 'Sistema' ? 'Sistema' : 'Tú') + ': ';
                el.appendChild(title);
                el.appendChild(document.createTextNode(text));
                box.appendChild(el);
            });
            box.scrollTop = box.scrollHeight;
        }

        function loadChat() {
            if (currentSubscriptionPlan === 'FREE') return;
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
            if (currentSubscriptionPlan === 'FREE') return;
            const input = document.getElementById('chat-input');
            const message = input.value.trim();
            if (!message) return;
            const isCommand = message.startsWith('/');
            fetch(isCommand ? '/api/chat/command' : '/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(isCommand ? { command: message } : { message })
            })
                .then(async r => {
                    const data = await r.json();
                    if (!r.ok || data.success === false) {
                        throw new Error(data.error || 'No se pudo procesar el mensaje.');
                    }
                    return data;
                })
                .then(d => {
                    input.value = '';
                    update();
                    if (d.job_id) pollDemoTradeJob(d.job_id);
                })
                .catch(e => {
                    const status = document.getElementById('chat-demo-trade-status');
                    if (status) status.textContent = e.message;
                });
        }

        function pollDemoTradeJob(jobId) {
            if (demoTradePollingJobId === jobId) return;
            demoTradePollingJobId = jobId;
            const poll = () => {
                fetch('/api/chat/demo-trade/' + encodeURIComponent(jobId))
                    .then(async r => {
                        const data = await r.json();
                        if (!r.ok || !data.success) {
                            throw new Error(data.error || 'No se pudo consultar la operación demo.');
                        }
                        return data.job;
                    })
                    .then(job => {
                        const status = document.getElementById('chat-demo-trade-status');
                        if (status) status.textContent = job.message || job.status;
                        if (job.status === 'queued' || job.status === 'running') {
                            window.setTimeout(poll, 3000);
                        } else {
                            demoTradePollingJobId = null;
                            loadChat();
                        }
                    })
                    .catch(e => {
                        demoTradePollingJobId = null;
                        const status = document.getElementById('chat-demo-trade-status');
                        if (status) status.textContent = e.message;
                    });
            };
            poll();
        }

        function updateAIAnalysis() {
            const analysisCooldownMs = currentSubscriptionPlan === 'FREE' ?
                FREE_ANALYSIS_COOLDOWN_MS : BASIC_ANALYSIS_COOLDOWN_MS;
            if (Date.now() - lastAIRequestAt < analysisCooldownMs) return;
            lastAIRequestAt = Date.now();
            const analysisEndpoint = currentSubscriptionPlan === 'PREMIUM' ?
                '/api/professional-analysis' : '/api/analysis';
            fetch(analysisEndpoint)
                .then(r => r.json())
                .then(d => {
                    if (d.success === false || d.available === false) return;
                    const signal = d.signal || 'ESPERA';
                    const color = signal === 'COMPRA' ? 'var(--green)' : signal === 'VENTA' ? 'var(--red)' : 'var(--gold)';
                    document.getElementById('ai-signal').textContent = signal;
                    document.getElementById('ai-signal').style.color = color;
                    const confidencePct = typeof d.confidence_percent === 'number' ? d.confidence_percent : ((d.confidence || 0) * 100);
                    document.getElementById('ai-confidence').textContent = confidencePct.toFixed(1) + '%';
                    const analysisCooldownSeconds = d.analysis_cache?.cooldown_seconds ||
                        (currentSubscriptionPlan === 'FREE' ? 900 : 300);
                    document.getElementById('ai-pattern').textContent = (d.pattern || '-') +
                        ' · Actualizado cada ' + Math.round(analysisCooldownSeconds / 60) + ' min';
                    document.getElementById('ai-volatility').textContent = d.volatility || '-';
                    document.getElementById('ai-learning').textContent =
                        'Cooldown: ' + Math.ceil(analysisCooldownSeconds / 60) + ' min';
                })
                .catch(e => console.error('Error en análisis de IA:', e));
        }

        function updatePrediction() {
            if (currentSubscriptionPlan === 'FREE') return;
            const predictionCooldownMs = PREDICTION_COOLDOWN_MS;
            if (
                predictionRequestInFlight ||
                Date.now() - lastPredictionRequestAt < predictionCooldownMs
            ) return;
            predictionRequestInFlight = true;
            lastPredictionRequestAt = Date.now();
            fetch('/api/predict')
                .then(r => r.json())
                .then(d => {
                    if (!d.success) return;
                    const p = d.prediction || {};
                    const trade = d.trade || {};
                    const levels = d.levels || {};
                    document.getElementById('pred-direction').textContent = p.direction || '-';
                    document.getElementById('pred-price').textContent = typeof p.predicted_price === 'number' ?
                        formatPrice(p.predicted_price, currentDecimals) : '-';
                    document.getElementById('pred-confidence').textContent = typeof p.confidence === 'number' ?
                        (p.confidence * 100).toFixed(1) + '%' : '-';
                    document.getElementById('pred-backtest').textContent =
                        typeof p.walk_forward_accuracy === 'number' ?
                            (p.walk_forward_accuracy * 100).toFixed(1) + '% (' +
                                (p.walk_forward_samples || 0) + ' pruebas)' : 'Muestra insuficiente';
                    document.getElementById('pred-adaptive-backtest').textContent =
                        typeof p.adaptive_walk_forward_accuracy === 'number' ?
                            (p.adaptive_walk_forward_accuracy * 100).toFixed(1) + '% (' +
                                (p.adaptive_walk_forward_samples || 0) + ' pruebas sin fuga)' :
                            'Muestra insuficiente';
                    const modelLabels = {
                        ema: 'EMA',
                        linear: 'Regresión',
                        momentum: 'Momentum',
                        volatility: 'Volatilidad'
                    };
                    const modelPerformance = p.model_performance || {};
                    const modelWeights = p.model_weights || {};
                    document.getElementById('pred-model-learning').textContent =
                        Object.keys(modelLabels).map(name => {
                            const metrics = modelPerformance[name] || {};
                            const accuracy = typeof metrics.accuracy === 'number' ?
                                (metrics.accuracy * 100).toFixed(0) + '%' : 's/d';
                            const weight = typeof modelWeights[name] === 'number' ?
                                (modelWeights[name] * 100).toFixed(0) + '%' : '-';
                            return modelLabels[name] + ' ' + accuracy + ' (' +
                                (metrics.samples || 0) + ') peso ' + weight;
                        }).join(' · ');
                    document.getElementById('pred-cooldown').textContent =
                        ' · Actualizado ' + new Date(d.prediction_cache.calculated_at).toLocaleTimeString() +
                        ' · cooldown ' + d.prediction_cache.cooldown_seconds + ' s';
                    const signal = trade.signal || d.recommendation || 'ESPERA';
                    const signalElement = document.getElementById('pred-signal');
                    signalElement.textContent = signal;
                    signalElement.style.color = signal === 'COMPRA' ? 'var(--green)' :
                        signal === 'VENTA' ? 'var(--red)' : 'var(--gold)';
                    document.getElementById('pred-risk-reward').textContent = trade.trade_allowed ?
                        Number(trade.risk_reward).toFixed(2) + ':1' : '-';
                    document.getElementById('pred-reasons').textContent =
                        Array.isArray(trade.reasons) ? trade.reasons.join(' · ') : '-';
                    document.getElementById('pred-entry').textContent = levels.entry ?
                        formatPrice(levels.entry, currentDecimals) : '-';
                    document.getElementById('pred-sl').textContent = levels.stop_loss ?
                        formatPrice(levels.stop_loss, currentDecimals) : '-';
                    document.getElementById('pred-tp').textContent = levels.take_profit ?
                        formatPrice(levels.take_profit, currentDecimals) : '-';
                })
                .catch(e => console.error('Error fetching predict:', e))
                .finally(() => { predictionRequestInFlight = false; });
        }

        function updateLiquidityUI(liquidity) {
            const bias = document.getElementById('liquidity-bias');
            const note = document.getElementById('liquidity-note');
            if (!liquidity.available) {
                bias.textContent = 'Sin datos de volumen';
                document.getElementById('liquidity-pressure').textContent = '-';
                document.getElementById('liquidity-relative-volume').textContent = '-';
                document.getElementById('liquidity-zone').textContent = '-';
                document.getElementById('liquidity-total').textContent = '-';
                if (note && liquidity.flow_note) note.textContent = liquidity.flow_note;
                return;
            }

            bias.textContent = liquidity.flow_bias || 'Flujo mixto';
            bias.style.color = liquidity.flow_bias === 'PRESIÓN COMPRADORA' ? 'var(--green)' :
                liquidity.flow_bias === 'PRESIÓN VENDEDORA' ? 'var(--red)' : 'var(--gold)';
            document.getElementById('liquidity-pressure').textContent =
                Number(liquidity.buy_pressure_pct).toFixed(1) + '% compra / ' +
                Number(liquidity.sell_pressure_pct).toFixed(1) + '% venta';
            document.getElementById('liquidity-relative-volume').textContent =
                typeof liquidity.relative_volume === 'number' ?
                    liquidity.relative_volume.toFixed(2) + '× promedio' : 'Sin referencia';
            const zone = liquidity.active_price_zone;
            document.getElementById('liquidity-zone').textContent = zone ?
                formatPrice(zone.low, currentDecimals) + ' - ' + formatPrice(zone.high, currentDecimals) : '-';
            const volumeFormat = new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 });
            document.getElementById('liquidity-total').textContent =
                volumeFormat.format(liquidity.volume_total) + ' ' + liquidity.volume_unit;
            if (note && liquidity.flow_note) note.textContent = liquidity.flow_note;
        }

        function loadSymbols() {
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
            const volElem = document.getElementById('volume-input');
            const volume = volElem ? (parseFloat(volElem.value) || 0.01) : 0.01;
            fetch('/api/symbol', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbol, volume })
            })
                .then(r => r.json())
                .then(d => {
                    if (d.success) {
                        currentSymbol = d.symbol;
                        lastPredictionRequestAt = 0;
                        lastAIRequestAt = 0;
                        if (chart) {
                            try { chart.destroy(); } catch(e) {}
                            chart = null;
                        }
                        update();
                    } else {
                        alert('Error: ' + (d.error || ''));
                    }
                })
                .catch(e => console.error('Error cambiando símbolo:', e));
        }

        function applyVolume() {
            const symbol = document.getElementById('symbol-select').value;
            changeSymbol(symbol);
        }

        function updateAdvancedPredictionUI(d) {
            if (!d.success) return;
            const sigEl = document.getElementById('adv-signal');
            sigEl.textContent = d.signal || '-';
            sigEl.style.color = d.signal === 'COMPRA' ? 'var(--green)' : d.signal === 'VENTA' ? 'var(--red)' : 'var(--gold)';
            document.getElementById('adv-score').textContent = (d.score || 0).toFixed(1);
            document.getElementById('adv-confidence').textContent = ((d.confidence || 0) * 100).toFixed(1) + '%';
            const ind = d.indicators || {};
            document.getElementById('adv-trend').textContent = ind.trend || '-';
            document.getElementById('adv-rsi').textContent = ind.rsi !== undefined ? ind.rsi.toFixed(2) : '-';
            document.getElementById('adv-macd').textContent = ind.macd !== undefined ? ind.macd.toFixed(6) : '-';
            document.getElementById('adv-ema').textContent = (ind.ema_fast !== undefined ? formatPrice(ind.ema_fast, currentDecimals) : '-') + ' / ' + (ind.ema_slow !== undefined ? formatPrice(ind.ema_slow, currentDecimals) : '-');
            document.getElementById('adv-stoch').textContent = ind.stochastic !== undefined ? ind.stochastic.toFixed(2) : '-';
            document.getElementById('adv-atr').textContent = ind.atr !== undefined ? ind.atr.toFixed(6) : '-';
            const lvl = d.levels || {};
            document.getElementById('adv-support').textContent = lvl.support !== undefined ? formatPrice(lvl.support, currentDecimals) : '-';
            document.getElementById('adv-resistance').textContent = lvl.resistance !== undefined ? formatPrice(lvl.resistance, currentDecimals) : '-';
            const pred = d.prediction || {};
            document.getElementById('adv-next').textContent = pred.predicted_price !== undefined ? formatPrice(pred.predicted_price, currentDecimals) : '-';
            const low = pred.expected_low !== undefined ? formatPrice(pred.expected_low, currentDecimals) : '-';
            const high = pred.expected_high !== undefined ? formatPrice(pred.expected_high, currentDecimals) : '-';
            document.getElementById('adv-range').textContent = low + ' - ' + high;
            const cache = d.prediction_cache || {};
            document.getElementById('adv-timestamp').textContent = cache.calculated_at ?
                'Actualizado ' + new Date(cache.calculated_at).toLocaleTimeString() +
                    ' · horizonte máx. ' + (pred.horizon_minutes || PREDICTION_HORIZON_MINUTES) + ' min' :
                (d.timestamp ? new Date(d.timestamp).toLocaleTimeString() : '');
            document.getElementById('adv-grid').style.opacity = '1';
        }

        function startAdvancedCooldown(seconds) {
            const btn = document.getElementById('adv-btn');
            const status = document.getElementById('adv-cooldown');
            if (advancedCooldownInterval) clearInterval(advancedCooldownInterval);
            let remaining = Math.max(0, Math.ceil(Number(seconds) || 0));
            if (!remaining) {
                btn.disabled = false;
                status.textContent = '';
                advancedCooldownInterval = null;
                return;
            }

            btn.disabled = true;
            const updateCountdown = () => {
                const minutes = Math.floor(remaining / 60);
                const secondsLeft = remaining % 60;
                status.textContent = 'Nueva predicción en ' +
                    String(minutes).padStart(2, '0') + ':' +
                    String(secondsLeft).padStart(2, '0');
                remaining -= 1;
                if (remaining < 0) {
                    clearInterval(advancedCooldownInterval);
                    advancedCooldownInterval = null;
                    btn.disabled = false;
                    btn.textContent = 'Calcular Predicción Avanzada';
                    status.textContent = 'Disponible';
                }
            };
            updateCountdown();
            advancedCooldownInterval = setInterval(updateCountdown, 1000);
        }

        function loadAdvancedPrediction() {
            const btn = document.getElementById('adv-btn');
            const loading = document.getElementById('adv-loading');
            if (btn.disabled) return;
            btn.disabled = true;
            loading.style.display = 'inline';
            fetch('/api/advanced-prediction')
                .then(r => {
                    if (r.status === 403) {
                        return r.json().then(d => {
                            alert(d.error || 'Esta función requiere plan PRO o PREMIUM');
                            openPlansModal();
                            throw new Error('Upgrade required');
                        });
                    }
                    return r.json();
                })
                .then(d => {
                    updateAdvancedPredictionUI(d);
                    if (d.success && d.prediction_cache) {
                        startAdvancedCooldown(d.prediction_cache.remaining_seconds);
                    }
                })
                .catch(e => {
                    if (e.message !== 'Upgrade required') {
                        console.error('Error predicción avanzada:', e);
                    }
                })
                .finally(() => {
                    if (!advancedCooldownInterval) btn.disabled = false;
                    loading.style.display = 'none';
                });
        }

        function renderAlerts(alerts) {
            const container = document.getElementById('alert-list');
            if (!alerts || alerts.length === 0) {
                container.innerHTML = '<div class="alert-item baja"><div class="alert-title">Sin alertas recientes</div><div class="alert-msg">El mercado opera dentro de parámetros normales.</div></div>';
                return;
            }
            container.innerHTML = alerts.map(a => {
                const time = a.timestamp ? new Date(a.timestamp).toLocaleTimeString() : 'Ahora';
                const badgeClass = a.type === 'volatilidad' ? 'badge-volatilidad' : a.type === 'oportunidad' ? 'badge-oportunidad' : a.type === 'noticia' ? 'badge-noticia' : 'badge-breakout';
                return `<div class="alert-item ${a.level}">
                    <div class="alert-meta"><span class="alert-badge ${badgeClass}">${a.type}</span>${time} · ${a.symbol}</div>
                    <div class="alert-title">${a.title}</div>
                    <div class="alert-msg">${a.message}</div>
                </div>`;
            }).join('');
        }

        function renderNews(news) {
            const container = document.getElementById('news-list');
            if (!news || news.length === 0) {
                container.innerHTML = '<div class="news-item"><div class="news-title">No hay noticias disponibles</div></div>';
                return;
            }
            container.innerHTML = news.map(n => {
                const impactClass = n.impact === 'alto' ? 'impact-alto' : n.impact === 'medio' ? 'impact-medio' : 'impact-bajo';
                return `<div class="news-item">
                    <div class="news-title">${n.title}</div>
                    <div class="news-meta">${n.time} · ${n.source} · ${n.symbol || 'GLOBAL'}<span class="news-impact ${impactClass}">${n.impact}</span></div>
                </div>`;
            }).join('');
        }

        function updateVolatilityMetrics(metrics) {
            const spike = metrics.spike_pct || 0;
            const atrRatio = metrics.atr_ratio || 1;
            const rangePct = metrics.range_pct || 0;
            const index = Math.min(100, Math.round((spike * 8 + (atrRatio - 1) * 25 + rangePct * 5)));
            document.getElementById('vol-index').textContent = index + '%';
            document.getElementById('vol-index').style.color = index >= 70 ? 'var(--red)' : index >= 40 ? 'var(--gold)' : 'var(--green)';
            document.getElementById('vol-fill').style.width = index + '%';
            document.getElementById('vol-spike').textContent = spike.toFixed(3) + '%';
            document.getElementById('vol-atr').textContent = atrRatio.toFixed(2) + 'x';
            document.getElementById('vol-range').textContent = rangePct.toFixed(3) + '%';
        }

        function loadNewsAlerts(forceLoading = true) {
            if (currentSubscriptionPlan === 'FREE') return;
            const btn = document.getElementById('news-btn');
            const loading = document.getElementById('news-loading');
            if (forceLoading && btn) btn.disabled = true;
            if (loading) loading.style.display = 'inline';
            fetch('/api/news-alerts')
                .then(r => r.json())
                .then(d => {
                    if (!d.success) return;
                    renderAlerts(d.alerts);
                    renderNews(d.news);
                    updateVolatilityMetrics(d.volatility || {});
                })
                .catch(e => console.error('Error cargando noticias/alertas:', e))
                .finally(() => {
                    if (btn) btn.disabled = false;
                    if (loading) loading.style.display = 'none';
                });
        }

        loadCurrentUser().then(() => {
            update();
            setInterval(update, 5000);
            setInterval(() => {
                if (currentSubscriptionPlan === 'PRO' || currentSubscriptionPlan === 'PREMIUM') {
                    loadNewsAlerts(false);
                }
            }, 5000);
        });
    </script>
</body>
</html>
"""

# ====================================================================
# MAIN
# ====================================================================

def run_flask_app():
    start_background_services()
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
    print("  ASISTENTE DE TRADING INTELIGENTE - INICIANDO")
    print("="*70 + "\n")
    
    print("Servidor iniciando en http://0.0.0.0:5000")
    print("\n" + "="*70 + "\n")
    
    try:
        webbrowser.open('http://127.0.0.1:5000')
    except:
        pass
    
    run_flask_app()
 