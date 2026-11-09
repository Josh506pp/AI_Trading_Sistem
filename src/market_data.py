#!/usr/bin/env python3
"""Read-only MT5 quotes with Yahoo Finance fallback for supported market symbols."""

import yfinance as yf
from datetime import datetime, timedelta
import logging
import math
import threading
import time
from datetime import timezone

try:
    from .market_symbols import get_symbol_config
except ImportError:
    from market_symbols import get_symbol_config

try:
    import MetaTrader5
except (ImportError, OSError):
    MetaTrader5 = None

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


def calculate_volume_profile(candles, bin_count=32):
    """Estima volumen por nivel de precio a partir de velas OHLCV."""
    valid = []
    for candle in candles:
        try:
            row = {
                key: float(candle[key])
                for key in ('high', 'low', 'volume')
            }
        except (KeyError, TypeError, ValueError):
            continue
        if (
            all(math.isfinite(value) for value in row.values()) and
            row['low'] > 0 and row['high'] >= row['low'] and row['volume'] > 0
        ):
            valid.append(row)

    if not valid:
        return {
            'available': False,
            'source': 'ohlcv_estimate',
            'levels': [],
            'note': 'No hay volumen OHLCV utilizable para estimar el perfil.'
        }

    bin_count = max(4, min(int(bin_count), 80))
    minimum = min(row['low'] for row in valid)
    maximum = max(row['high'] for row in valid)
    if maximum <= minimum:
        padding = max(abs(minimum) * 0.000001, 0.00000001)
        minimum -= padding
        maximum += padding

    bin_width = (maximum - minimum) / bin_count
    volumes = [0.0] * bin_count
    for row in valid:
        candle_low = max(minimum, row['low'])
        candle_high = min(maximum, row['high'])
        if candle_high <= candle_low:
            index = min(
                bin_count - 1,
                max(0, int((candle_low - minimum) / bin_width))
            )
            volumes[index] += row['volume']
            continue

        first = max(0, int((candle_low - minimum) / bin_width))
        last = min(bin_count - 1, int((candle_high - minimum) / bin_width))
        overlaps = []
        for index in range(first, last + 1):
            level_low = minimum + index * bin_width
            level_high = level_low + bin_width
            overlaps.append(max(0.0, min(candle_high, level_high) - max(candle_low, level_low)))
        overlap_total = sum(overlaps)
        if overlap_total <= 0:
            volumes[first] += row['volume']
            continue
        for index, overlap in zip(range(first, last + 1), overlaps):
            volumes[index] += row['volume'] * overlap / overlap_total

    levels = [
        {
            'low': round(minimum + index * bin_width, 10),
            'high': round(minimum + (index + 1) * bin_width, 10),
            'volume': round(volume, 4)
        }
        for index, volume in enumerate(volumes)
        if volume > 0
    ]
    return {
        'available': bool(levels),
        'source': 'ohlcv_estimate',
        'levels': levels,
        'max_volume': round(max(volumes), 4) if levels else 0,
        'note': (
            'Estimación distribuida desde el rango OHLCV; no representa órdenes '
            'en espera ni profundidad real del libro.'
        )
    }


class MarketDataProvider:
    """Proveedor de datos reales del mercado"""
    
    def __init__(self, mt5_client=None, mt5_retry_seconds=30):
        self.cache = {}
        self.last_update = {}
        self.cache_duration = 60  # segundos
        self.mt5 = None if mt5_client is False else (
            mt5_client if mt5_client is not None else MetaTrader5
        )
        self.mt5_retry_seconds = mt5_retry_seconds
        self._mt5_initialized = False
        self._mt5_last_attempt = 0.0
        self._mt5_lock = threading.Lock()
        self._market_book_lock = threading.Lock()
        self._market_book_subscriptions = set()
        self._market_book_retry_after = {}

    def _ensure_mt5(self):
        if self.mt5 is None:
            return False

        with self._mt5_lock:
            if self._mt5_initialized:
                try:
                    terminal = self.mt5.terminal_info()
                    if (
                        self.mt5.account_info() is not None and
                        terminal is not None and
                        getattr(terminal, 'connected', False)
                    ):
                        return True
                except Exception:
                    pass
                self._mt5_initialized = False

            now = time.monotonic()
            if now - self._mt5_last_attempt < self.mt5_retry_seconds:
                return False
            self._mt5_last_attempt = now

            try:
                if not self.mt5.initialize():
                    logger.info("MetaTrader 5 no está disponible; se usará la fuente de respaldo.")
                    return False
                terminal = self.mt5.terminal_info()
                if (
                    self.mt5.account_info() is None or terminal is None or
                    not getattr(terminal, 'connected', False)
                ):
                    logger.info("MetaTrader 5 no tiene una sesión de bróker conectada.")
                    self.mt5.shutdown()
                    return False
                self._mt5_initialized = True
                return True
            except Exception as exc:
                logger.info("No se pudo conectar con MetaTrader 5: %s", exc)
                return False

    def _resolve_mt5_symbol(self, symbol):
        candidates = [symbol.upper()]
        config = get_symbol_config(symbol)
        if config:
            candidates.extend(alias for alias in config.symbol_aliases if alias not in candidates)

        for candidate in candidates:
            info = self.mt5.symbol_info(candidate)
            if info is not None:
                if not getattr(info, 'visible', True) and not self.mt5.symbol_select(candidate, True):
                    continue
                return candidate

        symbols_get = getattr(self.mt5, 'symbols_get', None)
        if symbols_get:
            for candidate in candidates:
                matches = symbols_get(group=f'{candidate}*') or ()
                for info in matches:
                    name = getattr(info, 'name', '')
                    if name.upper().startswith(candidate.upper()):
                        if not getattr(info, 'visible', True) and not self.mt5.symbol_select(name, True):
                            continue
                        return name
        return None

    def _mt5_candles(self, symbol, interval='1m', count=200):
        if not self._ensure_mt5():
            return []

        timeframes = {
            '1m': 'TIMEFRAME_M1',
            '5m': 'TIMEFRAME_M5',
            '15m': 'TIMEFRAME_M15',
            '1h': 'TIMEFRAME_H1'
        }
        timeframe_name = timeframes.get(interval)
        if not timeframe_name or not hasattr(self.mt5, timeframe_name):
            return []

        mt5_symbol = self._resolve_mt5_symbol(symbol)
        if not mt5_symbol:
            return []
        rates = self.mt5.copy_rates_from_pos(
            mt5_symbol, getattr(self.mt5, timeframe_name), 0, count
        )
        if rates is None:
            return []

        candles = []
        for rate in rates:
            try:
                real_volume = float(rate['real_volume'])
                tick_volume = float(rate['tick_volume'])
                volume = real_volume if real_volume > 0 else tick_volume
                timestamp = int(rate['time'])
                candle = {
                    'time': timestamp,
                    'open': float(rate['open']),
                    'high': float(rate['high']),
                    'low': float(rate['low']),
                    'close': float(rate['close']),
                    'volume': volume
                }
            except (KeyError, TypeError, ValueError, OverflowError):
                continue
            if (
                all(math.isfinite(candle[key]) for key in ('open', 'high', 'low', 'close', 'volume')) and
                candle['close'] > 0 and candle['volume'] >= 0
            ):
                candles.append(candle)
        return candles

    def get_market_depth(self, symbol, max_levels=20):
        """Lee el libro DOM de MT5 cuando el bróker ofrece profundidad."""
        unavailable = {
            'available': False,
            'source': 'mt5_dom',
            'bids': [],
            'asks': [],
            'note': 'La profundidad real de MT5 no está disponible para este símbolo.'
        }
        if not self._ensure_mt5():
            unavailable['note'] = 'No hay una sesión conectada de MetaTrader 5.'
            return unavailable

        book_add = getattr(self.mt5, 'market_book_add', None)
        book_get = getattr(self.mt5, 'market_book_get', None)
        if not callable(book_add) or not callable(book_get):
            unavailable['note'] = 'Esta instalación de MT5 no ofrece lectura de DOM.'
            return unavailable

        mt5_symbol = self._resolve_mt5_symbol(symbol)
        if not mt5_symbol:
            unavailable['note'] = 'El símbolo no está disponible en MetaTrader 5.'
            return unavailable

        with self._market_book_lock:
            now = time.monotonic()
            retry_after = self._market_book_retry_after.get(mt5_symbol, 0.0)
            if mt5_symbol not in self._market_book_subscriptions and now < retry_after:
                return unavailable
            if mt5_symbol not in self._market_book_subscriptions:
                try:
                    if not book_add(mt5_symbol):
                        self._market_book_retry_after[mt5_symbol] = now + 30
                        logger.info(
                            'MetaTrader 5 no publica profundidad DOM para %s.',
                            mt5_symbol
                        )
                        return unavailable
                except Exception as exc:
                    self._market_book_retry_after[mt5_symbol] = now + 30
                    logger.warning(
                        'No se pudo suscribir al DOM de %s: %s',
                        mt5_symbol,
                        exc
                    )
                    return unavailable
                self._market_book_subscriptions.add(mt5_symbol)

            try:
                entries = book_get(mt5_symbol)
            except Exception as exc:
                logger.warning('No se pudo leer el DOM de %s: %s', mt5_symbol, exc)
                return unavailable

        if not entries:
            return unavailable

        sell_type = getattr(self.mt5, 'BOOK_TYPE_SELL', 1)
        buy_type = getattr(self.mt5, 'BOOK_TYPE_BUY', 2)
        bids = {}
        asks = {}
        for entry in entries:
            try:
                order_type = int(entry.type)
                price = float(entry.price)
                volume_value = getattr(entry, 'volume_dbl', None)
                if volume_value is None:
                    volume_value = getattr(entry, 'volume', 0)
                volume = float(volume_value)
            except (AttributeError, TypeError, ValueError, OverflowError):
                continue
            if not math.isfinite(price) or price <= 0 or not math.isfinite(volume) or volume <= 0:
                continue
            side = bids if order_type == buy_type else asks if order_type == sell_type else None
            if side is not None:
                side[price] = side.get(price, 0.0) + volume

        if not bids and not asks:
            return unavailable

        max_levels = max(1, min(int(max_levels), 50))
        return {
            'available': True,
            'source': 'mt5_dom',
            'symbol': mt5_symbol,
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'bids': [
                {'price': price, 'volume': round(volume, 4)}
                for price, volume in sorted(bids.items(), reverse=True)[:max_levels]
            ],
            'asks': [
                {'price': price, 'volume': round(volume, 4)}
                for price, volume in sorted(asks.items())[:max_levels]
            ],
            'note': 'Profundidad publicada por el bróker a través de MT5.'
        }

    def _get_mt5_quote(self, symbol):
        if not self._ensure_mt5():
            return None

        mt5_symbol = self._resolve_mt5_symbol(symbol)
        if not mt5_symbol:
            logger.info("El símbolo %s no está disponible en MetaTrader 5.", symbol)
            return None
        tick = self.mt5.symbol_info_tick(mt5_symbol)
        if tick is None:
            return None

        bid = float(getattr(tick, 'bid', 0.0) or 0.0)
        ask = float(getattr(tick, 'ask', 0.0) or 0.0)
        last = float(getattr(tick, 'last', 0.0) or 0.0)
        symbol_info = self.mt5.symbol_info(mt5_symbol)
        chart_mode_last = getattr(self.mt5, 'SYMBOL_CHART_MODE_LAST', 1)
        if (
            symbol_info is not None and
            getattr(symbol_info, 'chart_mode', None) == chart_mode_last and
            last > 0
        ):
            price = last
        else:
            price = bid if bid > 0 else last if last > 0 else ask
        if not math.isfinite(price) or price <= 0:
            return None

        time_msc = int(getattr(tick, 'time_msc', 0) or 0)
        tick_time = (
            datetime.fromtimestamp(time_msc / 1000, tz=timezone.utc).isoformat()
            if time_msc else
            datetime.fromtimestamp(int(tick.time), tz=timezone.utc).isoformat()
        )
        candles = self._mt5_candles(symbol, '1m', 1000)
        history = [candle['close'] for candle in candles]
        if not history or history[-1] != price:
            history.append(price)

        return {
            'price': price,
            'timestamp': tick_time,
            'history': history[-1000:],
            'candles': candles[-120:],
            'source': 'MetaTrader 5',
            'bid': bid if bid > 0 else None,
            'ask': ask if ask > 0 else None,
            'spread': ask - bid if bid > 0 and ask > 0 else None,
            'mt5_symbol': mt5_symbol
        }
    
    def get_yf_ticker(self, symbol):
        """Obtener ticker de Yahoo Finance para el símbolo"""
        return SYMBOL_MAPPING.get(symbol.upper(), symbol.upper())
    
    def get_latest_price(self, symbol):
        """Obtener el último precio de mercado"""
        quote = self.get_latest_quote(symbol)
        return quote['price'] if quote else None

    def get_latest_quote(self, symbol):
        """Prioriza el tick de MT5 conectado; usa Yahoo Finance como respaldo."""
        try:
            mt5_quote = self._get_mt5_quote(symbol)
        except Exception as exc:
            logger.warning("No se pudo leer %s desde MT5; se usará Yahoo Finance: %s", symbol, exc)
            mt5_quote = None
        if mt5_quote:
            return mt5_quote

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
                'history': [candle['close'] for candle in valid_candles[-1000:]],
                'candles': valid_candles[-120:],
                'source': 'Yahoo Finance'
            }
        except Exception as e:
            logger.error(f"Error getting latest quote for {symbol}: {e}")
            return None
    
    def get_historical_data(self, symbol, period='1mo', interval='1h'):
        """Obtener historia de MT5 cuando esté conectado; Yahoo queda como respaldo."""
        try:
            # Cache check
            cache_key = f"{symbol}_{period}_{interval}"
            if cache_key in self.cache:
                if datetime.now() - self.last_update.get(cache_key, datetime.min) < timedelta(seconds=self.cache_duration):
                    return self.cache[cache_key]
            
            mt5_count = self._history_count(period, interval)
            try:
                mt5_candles = self._mt5_candles(symbol, interval, mt5_count)
            except Exception as exc:
                logger.warning("No se pudo leer historia de MT5 para %s: %s", symbol, exc)
                mt5_candles = []
            if mt5_candles:
                self.cache[cache_key] = mt5_candles
                self.last_update[cache_key] = datetime.now()
                return mt5_candles

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

    @staticmethod
    def _history_count(period, interval):
        period_days = int(period[:-1]) * (365 if period.endswith('y') else 30 if period.endswith('mo') else 7 if period.endswith('d') else 1)
        bars_per_day = {'1m': 1440, '5m': 288, '15m': 96, '1h': 24}.get(interval, 24)
        return min(10000, max(1, period_days * bars_per_day))
    
    def get_intraday_prices(self, symbol, count=50):
        """Obtener últimos N precios intradiarios para actualización continua"""
        try:
            mt5_candles = self._mt5_candles(symbol, '1m', count)
        except Exception as exc:
            logger.warning("No se pudo leer historia intradía de MT5 para %s: %s", symbol, exc)
            mt5_candles = []
        if mt5_candles:
            return [candle['close'] for candle in mt5_candles[-count:]]

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
