import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.market_data import MarketDataProvider, calculate_liquidity_metrics


class FakeMetaTrader5:
    TIMEFRAME_M1 = 1

    def __init__(self, connected=True):
        self.connected = connected

    def initialize(self):
        return self.connected

    def account_info(self):
        return SimpleNamespace() if self.connected else None

    def terminal_info(self):
        return SimpleNamespace(connected=self.connected)

    def symbol_info(self, symbol):
        return SimpleNamespace(visible=True) if symbol == 'EURUSD' else None

    def symbol_select(self, symbol, selected):
        return True

    def symbol_info_tick(self, symbol):
        return SimpleNamespace(
            bid=1.1000,
            ask=1.1002,
            last=0.0,
            time=1730000000,
            time_msc=1730000000123
        )

    def copy_rates_from_pos(self, symbol, timeframe, start, count):
        dtype = [
            ('time', 'i8'), ('open', 'f8'), ('high', 'f8'), ('low', 'f8'),
            ('close', 'f8'), ('tick_volume', 'i8'), ('spread', 'i4'),
            ('real_volume', 'i8')
        ]
        return np.array([
            (1730000000, 1.0998, 1.1001, 1.0997, 1.1000, 12, 2, 0)
        ], dtype=dtype)


class TestMarketDataProvider(unittest.TestCase):
    def test_latest_quote_prefers_connected_mt5_tick_without_yahoo_request(self):
        provider = MarketDataProvider(mt5_client=FakeMetaTrader5())
        with patch('src.market_data.yf.download') as download:
            quote = provider.get_latest_quote('EURUSD')

        self.assertEqual(quote['source'], 'MetaTrader 5')
        self.assertEqual(quote['mt5_symbol'], 'EURUSD')
        self.assertAlmostEqual(quote['price'], 1.1001)
        self.assertAlmostEqual(quote['spread'], 0.0002)
        self.assertEqual(quote['candles'][0]['volume'], 12.0)
        self.assertEqual(
            quote['timestamp'],
            datetime.fromtimestamp(1730000000.123, tz=timezone.utc).isoformat()
        )
        download.assert_not_called()

    def test_latest_quote_falls_back_to_yahoo_without_connected_mt5(self):
        timestamp = pd.Timestamp('2026-10-30 16:59:00', tz='America/New_York')
        data = pd.DataFrame({
            'Open': [1.1], 'High': [1.2], 'Low': [1.0],
            'Close': [1.15], 'Volume': [50]
        }, index=[timestamp])
        provider = MarketDataProvider(mt5_client=FakeMetaTrader5(connected=False))

        with patch('src.market_data.yf.download', return_value=data):
            quote = provider.get_latest_quote('EURUSD')

        self.assertEqual(quote['source'], 'Yahoo Finance')
        self.assertEqual(quote['price'], 1.15)

    def test_latest_quote_uses_recent_intraday_data_and_returns_source_timestamp(self):
        timestamp = pd.Timestamp('2026-10-30 16:59:00', tz='America/New_York')
        data = pd.DataFrame({
            'Open': [3898.0],
            'High': [3900.0],
            'Low': [3897.0],
            'Close': [3898.9],
            'Volume': [120.0]
        }, index=[timestamp])

        with patch('src.market_data.yf.download', return_value=data) as download:
            quote = MarketDataProvider(mt5_client=False).get_latest_quote('XAUUSD')

        self.assertEqual(quote, {
            'price': 3898.9,
            'timestamp': timestamp.isoformat(),
            'history': [3898.9],
            'source': 'Yahoo Finance',
            'candles': [{
                'time': timestamp.isoformat(),
                'open': 3898.0,
                'high': 3900.0,
                'low': 3897.0,
                'close': 3898.9,
                'volume': 120.0
            }]
        })
        self.assertEqual(download.call_args.kwargs['period'], '7d')
        self.assertEqual(download.call_args.kwargs['interval'], '1m')

    def test_latest_quote_returns_none_when_market_has_no_recent_data(self):
        with patch('src.market_data.yf.download', return_value=pd.DataFrame()):
            quote = MarketDataProvider(mt5_client=False).get_latest_quote('XAUUSD')

        self.assertIsNone(quote)

    def test_liquidity_metrics_estimate_flow_and_high_volume_price_zone(self):
        candles = []
        for index in range(12):
            volume = 200.0 if index >= 10 else 100.0
            candles.append({
                'open': 100.0 + index,
                'high': 102.0 + index,
                'low': 99.0 + index,
                'close': 101.5 + index,
                'volume': volume
            })

        metrics = calculate_liquidity_metrics(candles, 'EURUSD')

        self.assertTrue(metrics['available'])
        self.assertEqual(metrics['flow_bias'], 'PRESIÓN COMPRADORA')
        self.assertGreater(metrics['buy_pressure_pct'], metrics['sell_pressure_pct'])
        self.assertEqual(metrics['relative_volume'], 1.2)
        self.assertGreater(metrics['active_price_zone']['volume'], 0)
        self.assertIn('no identifica posiciones institucionales', metrics['flow_note'])

    def test_liquidity_metrics_do_not_invent_missing_volume(self):
        metrics = calculate_liquidity_metrics([], 'XAUUSD')

        self.assertFalse(metrics['available'])
        self.assertEqual(metrics['flow_bias'], 'SIN DATOS')

    def test_liquidity_metrics_classify_down_closes_as_sell_pressure(self):
        candles = [{
            'open': 101.5,
            'high': 102.0,
            'low': 99.0,
            'close': 99.5,
            'volume': 100.0
        } for _ in range(12)]

        metrics = calculate_liquidity_metrics(candles, 'BTCUSD')

        self.assertEqual(metrics['flow_bias'], 'PRESIÓN VENDEDORA')
        self.assertGreater(metrics['sell_pressure_pct'], metrics['buy_pressure_pct'])
        self.assertEqual(metrics['volume_unit'], 'volumen reportado (unidad del proveedor)')


if __name__ == '__main__':
    unittest.main()
