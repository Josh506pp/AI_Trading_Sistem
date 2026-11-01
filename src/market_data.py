#!/usr/bin/env python3
"""
Real Market Data Service using yfinance
Provides live OHLCV data for multiple assets
"""

import yfinance as yf
from datetime import datetime, timedelta
import logging

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
        try:
            ticker = self.get_yf_ticker(symbol)
            data = yf.download(ticker, period='1d', interval='1m', progress=False)
            if data.empty:
                logger.warning(f"No data for {symbol}")
                return None
            val = data['Close'].values.flatten()[-1]
            return float(val)
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
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
