import unittest
from unittest.mock import patch

import pandas as pd

from src.market_data import MarketDataProvider, calculate_liquidity_metrics


class TestMarketDataProvider(unittest.TestCase):
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
            quote = MarketDataProvider().get_latest_quote('XAUUSD')

        self.assertEqual(quote, {
            'price': 3898.9,
            'timestamp': timestamp.isoformat(),
            'history': [3898.9],
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
            quote = MarketDataProvider().get_latest_quote('XAUUSD')

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
