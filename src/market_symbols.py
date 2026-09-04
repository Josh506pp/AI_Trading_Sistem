#!/usr/bin/env python3
"""
MARKET SYMBOLS CONFIGURATION
Configuración centralizada de símbolos de trading populares.
Soporta Forex, índices, commodities y criptomonedas.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class SymbolConfig:
    """Configuración de un símbolo de trading."""
    name: str
    display_name: str
    category: str  # FOREX, COMMODITY, INDEX, CRYPTO
    default_price: float
    pip_size: float
    pip_value: float
    default_volume: float
    max_volume: float
    min_volume: float
    volatility: float  # factor de volatilidad para simulación
    decimals: int
    spread: float  # spread típico en puntos/pips
    session_hours: str
    description: str
    mt5_symbol_aliases: List[str]  # alias comunes en brokers


# Símbolos populares soportados
POPULAR_SYMBOLS: Dict[str, SymbolConfig] = {
    'XAUUSD': SymbolConfig(
        name='XAUUSD',
        display_name='Oro / Dólar',
        category='COMMODITY',
        default_price=2650.50,
        pip_size=0.01,
        pip_value=0.01,
        default_volume=0.01,
        max_volume=10.0,
        min_volume=0.01,
        volatility=0.35,
        decimals=2,
        spread=0.05,
        session_hours='23h (cierre viernes 22h UTC)',
        description='Oro spot contra dólar estadounidense',
        mt5_symbol_aliases=['XAUUSD', 'GOLD', 'XAUUSDm', 'XAUUSDb', 'XAUUSDc']
    ),
    'EURUSD': SymbolConfig(
        name='EURUSD',
        display_name='Euro / Dólar',
        category='FOREX',
        default_price=1.0850,
        pip_size=0.0001,
        pip_value=0.0001,
        default_volume=0.01,
        max_volume=50.0,
        min_volume=0.01,
        volatility=0.00008,
        decimals=5,
        spread=0.00003,
        session_hours='24h (Lun 00:00 - Vie 22:00 UTC)',
        description='Par de divisas Euro contra Dólar',
        mt5_symbol_aliases=['EURUSD', 'EURUSDm', 'EURUSDb', 'EURUSDc']
    ),
    'GBPUSD': SymbolConfig(
        name='GBPUSD',
        display_name='Libra / Dólar',
        category='FOREX',
        default_price=1.2750,
        pip_size=0.0001,
        pip_value=0.0001,
        default_volume=0.01,
        max_volume=50.0,
        min_volume=0.01,
        volatility=0.00012,
        decimals=5,
        spread=0.00004,
        session_hours='24h (Lun 00:00 - Vie 22:00 UTC)',
        description='Libra esterlina contra Dólar',
        mt5_symbol_aliases=['GBPUSD', 'GBPUSDm', 'GBPUSDb', 'GBPUSDc']
    ),
    'USDJPY': SymbolConfig(
        name='USDJPY',
        display_name='Dólar / Yen',
        category='FOREX',
        default_price=147.50,
        pip_size=0.01,
        pip_value=0.01,
        default_volume=0.01,
        max_volume=50.0,
        min_volume=0.01,
        volatility=0.008,
        decimals=3,
        spread=0.005,
        session_hours='24h (Lun 00:00 - Vie 22:00 UTC)',
        description='Dólar estadounidense contra Yen japonés',
        mt5_symbol_aliases=['USDJPY', 'USDJPYm', 'USDJPYb', 'USDJPYc']
    ),
    'US30': SymbolConfig(
        name='US30',
        display_name='Dow Jones 30',
        category='INDEX',
        default_price=41500.0,
        pip_size=1.0,
        pip_value=1.0,
        default_volume=0.01,
        max_volume=5.0,
        min_volume=0.01,
        volatility=12.0,
        decimals=1,
        spread=2.0,
        session_hours='Mon-Fri 13:30 - 20:00 UTC',
        description='Índice Dow Jones Industrial Average',
        mt5_symbol_aliases=['US30', 'US30Cash', 'DJ30', 'WallStreet', 'US30m']
    ),
    'NAS100': SymbolConfig(
        name='NAS100',
        display_name='Nasdaq 100',
        category='INDEX',
        default_price=18500.0,
        pip_size=1.0,
        pip_value=1.0,
        default_volume=0.01,
        max_volume=5.0,
        min_volume=0.01,
        volatility=18.0,
        decimals=1,
        spread=3.0,
        session_hours='Mon-Fri 13:30 - 20:00 UTC',
        description='Índice Nasdaq 100',
        mt5_symbol_aliases=['NAS100', 'NAS100Cash', 'USTEC', 'Nasdaq', 'NAS100m']
    ),
    'BTCUSD': SymbolConfig(
        name='BTCUSD',
        display_name='Bitcoin / Dólar',
        category='CRYPTO',
        default_price=67500.0,
        pip_size=0.01,
        pip_value=0.01,
        default_volume=0.01,
        max_volume=2.0,
        min_volume=0.01,
        volatility=85.0,
        decimals=2,
        spread=12.0,
        session_hours='24/7',
        description='Bitcoin contra Dólar estadounidense',
        mt5_symbol_aliases=['BTCUSD', 'BTCUSDT', 'BTCUSDm', 'Bitcoin']
    ),
    'USDCHF': SymbolConfig(
        name='USDCHF',
        display_name='Dólar / Franco Suizo',
        category='FOREX',
        default_price=0.9050,
        pip_size=0.0001,
        pip_value=0.0001,
        default_volume=0.01,
        max_volume=50.0,
        min_volume=0.01,
        volatility=0.00009,
        decimals=5,
        spread=0.00004,
        session_hours='24h (Lun 00:00 - Vie 22:00 UTC)',
        description='Dólar contra Franco suizo',
        mt5_symbol_aliases=['USDCHF', 'USDCHFm', 'USDCHFb']
    ),
    'AUDUSD': SymbolConfig(
        name='AUDUSD',
        display_name='Dólar Australiano / Dólar',
        category='FOREX',
        default_price=0.6720,
        pip_size=0.0001,
        pip_value=0.0001,
        default_volume=0.01,
        max_volume=50.0,
        min_volume=0.01,
        volatility=0.0001,
        decimals=5,
        spread=0.00003,
        session_hours='24h (Lun 00:00 - Vie 22:00 UTC)',
        description='Dólar australiano contra Dólar',
        mt5_symbol_aliases=['AUDUSD', 'AUDUSDm', 'AUDUSDb']
    ),
    'USOIL': SymbolConfig(
        name='USOIL',
        display_name='Petróleo Crudo WTI',
        category='COMMODITY',
        default_price=72.50,
        pip_size=0.01,
        pip_value=0.01,
        default_volume=0.01,
        max_volume=10.0,
        min_volume=0.01,
        volatility=0.12,
        decimals=2,
        spread=0.04,
        session_hours='Mon-Thu 00:00-22:00, Fri 00:00-20:30 UTC',
        description='Petróleo crudo WTI',
        mt5_symbol_aliases=['USOIL', 'WTI', 'XTIUSD', 'OIL', 'XTIUSDb']
    ),
}


def get_symbol_config(symbol: str) -> Optional[SymbolConfig]:
    """Obtiene la configuración de un símbolo por su nombre o alias."""
    symbol_upper = symbol.upper().strip() if symbol else ''
    if symbol_upper in POPULAR_SYMBOLS:
        return POPULAR_SYMBOLS[symbol_upper]
    # Buscar por alias
    for cfg in POPULAR_SYMBOLS.values():
        if symbol_upper in [a.upper() for a in cfg.mt5_symbol_aliases]:
            return cfg
    return None


def normalize_symbol(symbol: str) -> str:
    """Normaliza un símbolo a su nombre canónico."""
    cfg = get_symbol_config(symbol)
    return cfg.name if cfg else symbol.upper().strip()


def get_default_symbol() -> str:
    """Devuelve el símbolo por defecto (XAUUSD)."""
    return 'XAUUSD'


def list_symbols() -> List[Dict]:
    """Lista todos los símbolos disponibles como diccionarios."""
    return [
        {
            'name': cfg.name,
            'display_name': cfg.display_name,
            'category': cfg.category,
            'default_price': cfg.default_price,
            'default_volume': cfg.default_volume,
            'decimals': cfg.decimals,
            'description': cfg.description,
            'session_hours': cfg.session_hours,
        }
        for cfg in POPULAR_SYMBOLS.values()
    ]


def get_price_format(symbol: str) -> Dict:
    """Devuelve formato de precio para un símbolo."""
    cfg = get_symbol_config(symbol)
    if not cfg:
        return {'decimals': 5, 'pip_size': 0.0001}
    return {'decimals': cfg.decimals, 'pip_size': cfg.pip_size}


def format_price(symbol: str, price: float) -> str:
    """Formatea un precio según el símbolo."""
    cfg = get_symbol_config(symbol)
    decimals = cfg.decimals if cfg else 5
    return f"{price:.{decimals}f}"


def get_simulation_params(symbol: str) -> Dict:
    """Parámetros para simular movimientos de precio realistas."""
    cfg = get_symbol_config(symbol)
    if not cfg:
        return {'volatility': 0.00008, 'decimals': 5, 'default_price': 1.0850}
    return {
        'volatility': cfg.volatility,
        'decimals': cfg.decimals,
        'default_price': cfg.default_price,
        'spread': cfg.spread,
        'pip_size': cfg.pip_size,
    }
