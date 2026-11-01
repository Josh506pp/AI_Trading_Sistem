import importlib
import unittest
from unittest.mock import patch


app_module = importlib.import_module('src.app')
app_module.app.config['TESTING'] = True


class TestDashboardChart(unittest.TestCase):
    def test_status_returns_chart_data_without_reentering_price_lock(self):
        with patch.object(app_module, 'MARKET_DATA_AVAILABLE', False):
            response = app_module.app.test_client().get('/api/status')

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload['prices'])
        self.assertTrue(payload['candles'])
        self.assertIn('c', payload['candles'][0])

    def test_chart_quote_and_series_use_the_same_active_symbol_snapshot(self):
        with app_module.PRICE_LOCK:
            previous_symbol = app_module.TRADING_DATA['symbol']
            previous_price = app_module.TRADING_DATA['price']
            previous_history = app_module.TRADING_DATA['price_history']
            app_module.TRADING_DATA['symbol'] = 'USDJPY'
            app_module.TRADING_DATA['price'] = 149.123
            app_module.TRADING_DATA['price_history'] = [149.0, 149.05, 149.123]

        try:
            with patch.object(app_module.market_data, 'get_historical_data') as historical_data:
                response = app_module.app.test_client().get('/api/status')

            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertEqual(payload['symbol'], 'USDJPY')
            self.assertEqual(payload['price'], 149.123)
            self.assertEqual(payload['chart_prices'][-1], payload['price'])
            self.assertEqual(payload['candles'][-1]['c'], payload['price'])
            historical_data.assert_not_called()
        finally:
            with app_module.PRICE_LOCK:
                app_module.TRADING_DATA['symbol'] = previous_symbol
                app_module.TRADING_DATA['price'] = previous_price
                app_module.TRADING_DATA['price_history'] = previous_history

    def test_dashboard_displays_the_active_instrument_quote(self):
        from src.app import DASHBOARD_HTML

        self.assertIn('id="chart-current-quote"', DASHBOARD_HTML)
        self.assertIn('id="chart-update-time"', DASHBOARD_HTML)
        self.assertIn("currentSymbol + ': ' + formatPrice(d.price, currentDecimals)", DASHBOARD_HTML)
        self.assertIn("d.chart_prices", DASHBOARD_HTML)

    def test_market_tick_updates_the_quote_and_chart_history(self):
        with app_module.PRICE_LOCK:
            previous_symbol = app_module.TRADING_DATA['symbol']
            previous_price = app_module.TRADING_DATA['price']
            previous_history = app_module.TRADING_DATA['price_history']
            previous_timestamp = app_module.TRADING_DATA.get('price_updated_at')
            app_module.TRADING_DATA['symbol'] = 'USDJPY'
            app_module.TRADING_DATA['price'] = 149.123
            app_module.TRADING_DATA['price_history'] = [149.0, 149.123]

        try:
            with patch.object(app_module, 'MARKET_DATA_AVAILABLE', True), \
                    patch.object(app_module.market_data, 'get_latest_quote', return_value={
                        'price': 149.127,
                        'timestamp': '2026-10-30T16:59:00-04:00',
                        'history': [149.0, 149.123]
                    }), \
                    patch.object(app_module.market_data, 'get_intraday_prices', return_value=[]):
                updated = app_module.update_market_price_once()

            self.assertTrue(updated)
            self.assertEqual(app_module.TRADING_DATA['price'], 149.127)
            self.assertEqual(app_module.TRADING_DATA['price_history'][-1], 149.127)
            self.assertEqual(app_module.TRADING_DATA['price_updated_at'], '2026-10-30T16:59:00-04:00')
        finally:
            with app_module.PRICE_LOCK:
                app_module.TRADING_DATA['symbol'] = previous_symbol
                app_module.TRADING_DATA['price'] = previous_price
                app_module.TRADING_DATA['price_history'] = previous_history
                app_module.TRADING_DATA['price_updated_at'] = previous_timestamp

    def test_market_tick_publishes_liquidity_for_the_active_symbol(self):
        candle = {
            'time': '2026-10-30T16:59:00-04:00',
            'open': 149.0,
            'high': 150.0,
            'low': 148.0,
            'close': 149.8,
            'volume': 120.0
        }
        with app_module.PRICE_LOCK:
            previous_symbol = app_module.TRADING_DATA['symbol']
            previous_price = app_module.TRADING_DATA['price']
            previous_history = app_module.TRADING_DATA['price_history']
            previous_candles = app_module.TRADING_DATA['market_candles']
            previous_liquidity = app_module.TRADING_DATA['liquidity']
            previous_timestamp = app_module.TRADING_DATA.get('price_updated_at')
            app_module.TRADING_DATA['symbol'] = 'USDJPY'
            app_module.TRADING_DATA['price_history'] = [149.0]

        try:
            quote = {
                'price': 149.8,
                'timestamp': candle['time'],
                'history': [149.0, 149.8],
                'candles': [candle] * 12
            }
            with patch.object(app_module, 'MARKET_DATA_AVAILABLE', True), \
                    patch.object(app_module.market_data, 'get_latest_quote', return_value=quote):
                app_module.update_market_price_once()

            response = app_module.app.test_client().get('/api/status')
            liquidity = response.get_json()['liquidity']
            self.assertTrue(liquidity['available'])
            self.assertEqual(liquidity['window_candles'], 12)
            self.assertEqual(liquidity['flow_bias'], 'PRESIÓN COMPRADORA')
        finally:
            with app_module.PRICE_LOCK:
                app_module.TRADING_DATA['symbol'] = previous_symbol
                app_module.TRADING_DATA['price'] = previous_price
                app_module.TRADING_DATA['price_history'] = previous_history
                app_module.TRADING_DATA['market_candles'] = previous_candles
                app_module.TRADING_DATA['liquidity'] = previous_liquidity
                app_module.TRADING_DATA['price_updated_at'] = previous_timestamp

    def test_changing_symbol_updates_the_chart_to_that_symbols_latest_quote(self):
        with app_module.PRICE_LOCK:
            previous_symbol = app_module.TRADING_DATA['symbol']
            previous_price = app_module.TRADING_DATA['price']
            previous_history = app_module.TRADING_DATA['price_history']
            previous_trading_symbol = app_module.TRADING_SYMBOL

        try:
            with patch.object(app_module.market_data, 'get_intraday_prices', return_value=[1.084, 1.0852]):
                client = app_module.app.test_client()
                change_response = client.post('/api/symbol', json={'symbol': 'EURUSD'})
                status_response = client.get('/api/status')

            self.assertEqual(change_response.status_code, 200)
            payload = status_response.get_json()
            self.assertEqual(payload['symbol'], 'EURUSD')
            self.assertEqual(payload['price'], 1.0852)
            self.assertEqual(payload['chart_prices'][-1], 1.0852)
            self.assertEqual(payload['candles'][-1]['c'], 1.0852)
        finally:
            with app_module.PRICE_LOCK:
                app_module.TRADING_DATA['symbol'] = previous_symbol
                app_module.TRADING_DATA['price'] = previous_price
                app_module.TRADING_DATA['price_history'] = previous_history
                app_module.TRADING_SYMBOL = previous_trading_symbol


if __name__ == '__main__':
    unittest.main()
