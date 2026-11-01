#!/usr/bin/env python3
"""
Real Market Data Service using yfinance
Provides live OHLCV data for multiple assets
"""

import yfinance as yf
from datetime import datetime, timedelta
import logging
import math

logger = logging.getLogger(__name__)

# Symbol mapping: Our symbols -> Yahoo Finance tickers
SYMBOL_MAPPING = {
    'EURUSD': 'EURUSD=X',
    'GBPUSD': 'GBPUSD=X',
    'USDJPY': 'USDJPY=X',
    'USDCHF': 'USDCHF=X',
    'AUDUSD': 'AUDUSD=X',
    'XAUUSD': 'GC=F',      # Gold Futures
    'USOIL': 'CL=F',       # WTI Oil Futures
    'BTCUSD': 'BTC-USD',   # Bitcoin
    'ETHUSD': 'ETH-USD',   # Ethereum
    'US30': '^DJI',        # Dow Jones
    'NAS100': '^IXIC',     # NASDAQ
    'SPX500': '^GSPC',     # S&P 500
}


def calculate_liquidity_metrics(candles, symbol):
    """Calcula métricas aproximadas de volumen y presión a partir de velas OHLCV."""
    valid = []
    for candle in candles:
        try:
            row = {
                key: float(candle[key])
                for key in ('open', 'high', 'low', 'close', 'volume')
            }
        except (KeyError, TypeError, ValueError):
            continue
        if (
            all(math.isfinite(value) for value in row.values()) and
            row['low'] > 0 and row['volume'] > 0 and
            row['high'] >= row['low']
        ):
            valid.append(row)

    if not valid:
        return {
            'available': False,
            'flow_bias': 'SIN DATOS',
            'flow_note': 'El proveedor no entregó volumen utilizable para este instrumento.'
        }

    recent = valid[-30:]
    volumes = [row['volume'] for row in recent]
    signed_flows = []
    for row in recent:
        candle_range = row['high'] - row['low']
        close_location = (
            ((2 * row['close']) - row['high'] - row['low']) / candle_range
            if candle_range > 0 else 0.0
        )
        signed_flows.append(max(-1.0, min(1.0, close_location)) * row['volume'])

    total_volume = sum(volumes)
    net_flow = sum(signed_flows)
    buy_pressure = (50 + (net_flow / total_volume * 50)) if total_volume else 50.0
    buy_pressure = max(0.0, min(100.0, buy_pressure))
    if buy_pressure >= 55:
        flow_bias = 'PRESIÓN COMPRADORA'
    elif buy_pressure <= 45:
        flow_bias = 'PRESIÓN VENDEDORA'
    else:
        flow_bias = 'FLUJO MIXTO'

    current_average = sum(volumes[-10:]) / min(len(volumes), 10)
    baseline = volumes[:-10]
    baseline_average = sum(baseline) / len(baseline) if baseline else 0.0
    relative_volume = current_average / baseline_average if baseline_average else None

    min_price = min(row['low'] for row in recent)
    max_price = max(row['high'] for row in recent)
    zone_count = 8
    zone_width = (max_price - min_price) / zone_count if max_price > min_price else 0.0
    zones = [0.0] * zone_count
    for row in recent:
        typical_price = (row['high'] + row['low'] + row['close']) / 3
        zone_index = min(
            zone_count - 1,
            int((typical_price - min_price) / zone_width) if zone_width else 0
        )
        zones[zone_index] += row['volume']
    busiest_zone = max(range(zone_count), key=zones.__getitem__)
    zone_low = min_price + busiest_zone * zone_width
    zone_high = max_price if busiest_zone == zone_count - 1 else zone_low + zone_width

    upper_symbol = symbol.upper()
    if upper_symbol in {'BTCUSD', 'ETHUSD'}:
        volume_unit = 'volumen reportado (unidad del proveedor)'
    elif upper_symbol in {'XAUUSD', 'USOIL'}:
        volume_unit = 'contratos reportados'
    else:
        volume_unit = 'volumen reportado (proxy del proveedor)'

    return {
        'available': True,
        'window_candles': len(recent),
        'window_minutes': len(recent),
        'volume_unit': volume_unit,
        'volume_total': round(total_volume, 4),
        'average_volume': round(sum(volumes) / len(volumes), 4),
        'relative_volume': round(relative_volume, 2) if relative_volume is not None else None,
        'buy_pressure_pct': round(buy_pressure, 1),
        'sell_pressure_pct': round(100.0 - buy_pressure, 1),
        'net_flow_volume': round(net_flow, 4),
        'flow_bias': flow_bias,
        'active_price_zone': {
            'low': round(zone_low, 6),
            'high': round(zone_high, 6),
            'volume': round(zones[busiest_zone], 4)
        },
        'flow_note': 'Presión inferida de OHLCV; no identifica posiciones institucionales ni el agresor real.'
    }


class MarketDataProvider:
    """Proveedor de datos reales del mercado"""
    
    def __init__(self):
        self.cache = {}
        self.last_update = {}
        self.cache_duration = 60  # segundos
    
    def get_yf_ticker(self, symbol):
        """Obtener ticker de Yahoo Finance para el símbolo"""
        return SYMBOL_MAPPING.get(symbol.upper(), symbol.upper())
    
    def get_latest_price(self, symbol):
        """Obtener el último precio de mercado"""
        quote = self.get_latest_quote(symbol)
        return quote['price'] if quote else None

    def get_latest_quote(self, symbol):
        """Obtener precio y hora del último tick disponible del proveedor."""
        try:
            ticker = self.get_yf_ticker(symbol)
            data = yf.download(ticker, period='7d', interval='1m', progress=False)
            if data.empty:
                logger.warning(f"No data for {symbol}")
                return None
            def column_values(name, default=0.0):
                if name not in data:
                    return [default] * len(data)
                return data[name].values.flatten().tolist()

            columns = {
                name: column_values(name, 0.0)
                for name in ('Open', 'High', 'Low', 'Close', 'Volume')
            }
            valid_candles = []
            for index, timestamp in enumerate(data.index):
                try:
                    volume = float(columns['Volume'][index])
                    candle = {
                        'time': timestamp.isoformat(),
                        'open': float(columns['Open'][index]),
                        'high': float(columns['High'][index]),
                        'low': float(columns['Low'][index]),
                        'close': float(columns['Close'][index]),
                        'volume': volume if math.isfinite(volume) and volume >= 0 else 0.0
                    }
                except (TypeError, ValueError, IndexError):
                    continue
                if (
                    all(math.isfinite(candle[key]) for key in ('open', 'high', 'low', 'close', 'volume')) and
                    candle['close'] > 0 and candle['volume'] >= 0
                ):
                    valid_candles.append(candle)

            if not valid_candles:
                logger.warning(f"No valid recent prices for {symbol}")
                return None
            latest = valid_candles[-1]
            return {
                'price': latest['close'],
                'timestamp': latest['time'],
                'history': [candle['close'] for candle in valid_candles[-200:]],
                'candles': valid_candles[-120:]
            }
        except Exception as e:
            logger.error(f"Error getting latest quote for {symbol}: {e}")
            return None
    
    def get_historical_data(self, symbol, period='1mo', interval='1h'):
        """Obtener datos históricos para gráficos"""
        try:
            # Cache check
            cache_key = f"{symbol}_{period}_{interval}"
            if cache_key in self.cache:
                if datetime.now() - self.last_update.get(cache_key, datetime.min) < timedelta(seconds=self.cache_duration):
                    return self.cache[cache_key]
            
            ticker = self.get_yf_ticker(symbol)
            data = yf.download(ticker, period=period, interval=interval, progress=False)
            
            if data.empty:
                logger.warning(f"No historical data for {symbol}")
                return []
            
            # Format como lista de candles
            candles = []
            for idx, row in data.iterrows():
                candles.append({
                    'time': int(idx.timestamp()),
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': float(row['Volume']) if 'Volume' in row else 0
                })
            
            self.cache[cache_key] = candles
            self.last_update[cache_key] = datetime.now()
            return candles
        
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return []
    
    def get_intraday_prices(self, symbol, count=50):
        """Obtener últimos N precios intradiarios para actualización continua"""
        try:
            ticker = self.get_yf_ticker(symbol)
            data = yf.download(ticker, period='7d', interval='1m', progress=False)
            
            if data.empty:
                return []
            
            close_prices = data['Close']
            if hasattr(close_prices, 'values'):
                vals = close_prices.values.flatten()
            else:
                vals = list(close_prices)
                
            clean_prices = []
            for item in vals[-count:]:
                try:
                    if item is not None:
                        val = float(item)
                        if val == val: # check for NaN
                            clean_prices.append(val)
                except (ValueError, TypeError):
                    continue
            return clean_prices
        
        except Exception as e:
            logger.error(f"Error getting intraday prices for {symbol}: {e}")
            return []
    
    def validate_symbol(self, symbol):
        """Validar que el símbolo esté soportado"""
        return symbol.upper() in SYMBOL_MAPPING
    
    def get_supported_symbols(self):
        """Obtener lista de símbolos soportados"""
        return list(SYMBOL_MAPPING.keys())


# Instancia global
market_data = MarketDataProvider()
