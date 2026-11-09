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
        self.assertIn('liquidity_map', payload)

    def test_status_prefers_mt5_dom_and_falls_back_to_estimated_volume_profile(self):
        candles = [
            {
                'time': 1730000000 + index * 60,
                'open': 1.1000,
                'high': 1.1020,
                'low': 1.0990,
                'close': 1.1010,
                'volume': 100.0 + index
            }
            for index in range(12)
        ]
        with app_module.PRICE_LOCK:
            previous = {
                key: app_module.TRADING_DATA.get(key)
                for key in ('symbol', 'price', 'price_history', 'market_candles', 'market_depth')
            }
            app_module.TRADING_DATA.update({
                'symbol': 'EURUSD',
                'price': 1.1010,
                'price_history': [1.1000, 1.1010],
                'market_candles': candles,
                'market_depth': {
                    'available': True,
                    'bids': [{'price': 1.1009, 'volume': 5.0}],
                    'asks': [{'price': 1.1011, 'volume': 4.0}]
                }
            })

        try:
            client = app_module.app.test_client()
            dom_map = client.get('/api/status').get_json()['liquidity_map']
            self.assertEqual(dom_map['mode'], 'dom')
            self.assertEqual(dom_map['source'], 'mt5_dom')
            self.assertEqual(dom_map['bids'][0]['volume'], 5.0)

            with app_module.PRICE_LOCK:
                app_module.TRADING_DATA['market_depth'] = {'available': False}
            profile_map = client.get('/api/status').get_json()['liquidity_map']
            self.assertEqual(profile_map['mode'], 'volume_profile')
            self.assertEqual(profile_map['source'], 'ohlcv_estimate')
            self.assertTrue(profile_map['levels'])
            self.assertIn('no representa órdenes en espera', profile_map['note'])
        finally:
            with app_module.PRICE_LOCK:
                app_module.TRADING_DATA.update(previous)

    def test_status_uses_mt5_ohlc_candles_and_keeps_last_close_in_sync(self):
        candle_history = [
            {'time': 1793656800, 'open': 3945.87, 'high': 3945.87,
             'low': 3943.88, 'close': 3944.65, 'volume': 10.0},
            {'time': 1793656860, 'open': 3944.65, 'high': 3950.0,
             'low': 3944.0, 'close': 3948.99, 'volume': 20.0}
        ]
        with app_module.PRICE_LOCK:
            previous = {
                key: app_module.TRADING_DATA.get(key)
                for key in (
                    'symbol', 'price', 'price_history', 'market_candles',
                    'price_source', 'price_updated_at'
                )
            }
            app_module.TRADING_DATA.update({
                'symbol': 'XAUUSD',
                'price': 3949.33,
                'price_history': [3944.65, 3948.99, 3949.33],
                'market_candles': candle_history,
                'price_source': 'MetaTrader 5',
                'price_updated_at': '2026-11-02T22:04:13+00:00'
            })

        try:
            response = app_module.app.test_client().get('/api/status')
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()

            self.assertEqual(payload['chart_timeframe'], '1m')
            self.assertEqual(len(payload['chart_candles']), 2)
            self.assertEqual(payload['chart_candles'][0]['time'], 1793656800)
            self.assertEqual(payload['chart_candles'][-1]['close'], payload['price'])
            self.assertEqual(payload['chart_candles'][-1]['high'], 3950.0)
            self.assertEqual(payload['chart_prices'], [3944.65, 3949.33])
        finally:
            with app_module.PRICE_LOCK:
                app_module.TRADING_DATA.update(previous)

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
            self.assertIn('price_source', payload)
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
        self.assertIn('d.price_source', DASHBOARD_HTML)
        self.assertIn("currentSymbol + ': ' + formatPrice(d.price, currentDecimals)", DASHBOARD_HTML)
        self.assertIn("d.chart_prices", DASHBOARD_HTML)
        self.assertIn("d.chart_candles", DASHBOARD_HTML)
        self.assertIn('function drawCandlestickChart(candles, liquidityMap)', DASHBOARD_HTML)
        self.assertIn('function normalizeCandleData(chartData)', DASHBOARD_HTML)
        self.assertIn('function drawLiquidityMapPanel(', DASHBOARD_HTML)
        self.assertIn('function updateLiquidityMapUI(liquidityMap)', DASHBOARD_HTML)
        self.assertIn('id="liquidity-map-status"', DASHBOARD_HTML)

    def test_market_tick_updates_the_quote_and_chart_history(self):
        with app_module.PRICE_LOCK:
            previous_symbol = app_module.TRADING_DATA['symbol']
            previous_price = app_module.TRADING_DATA['price']
            previous_history = app_module.TRADING_DATA['price_history']
            previous_timestamp = app_module.TRADING_DATA.get('price_updated_at')
            previous_source = app_module.TRADING_DATA.get('price_source')
            previous_ticks = app_module.TRADING_DATA['recent_ticks']
            previous_depth = app_module.TRADING_DATA['market_depth']
            app_module.TRADING_DATA['symbol'] = 'USDJPY'
            app_module.TRADING_DATA['price'] = 149.123
            app_module.TRADING_DATA['price_history'] = [149.0, 149.123]

        try:
            with patch.object(app_module, 'MARKET_DATA_AVAILABLE', True), \
                    patch.object(app_module.market_data, 'get_latest_quote', return_value={
                        'price': 149.127,
                        'timestamp': '2026-10-30T16:59:00-04:00',
                        'history': [149.0, 149.123],
                        'source': 'MetaTrader 5'
                    }), \
                    patch.object(app_module.market_data, 'get_market_depth', return_value={
                        'available': True,
                        'source': 'mt5_dom',
                        'bids': [],
                        'asks': []
                    }), \
                    patch.object(app_module.market_data, 'get_intraday_prices', return_value=[]):
                updated = app_module.update_market_price_once()

            self.assertTrue(updated)
            self.assertEqual(app_module.TRADING_DATA['price'], 149.127)
            self.assertEqual(app_module.TRADING_DATA['price_history'][-1], 149.127)
            self.assertEqual(app_module.TRADING_DATA['price_updated_at'], '2026-10-30T16:59:00-04:00')
            self.assertEqual(app_module.TRADING_DATA['price_source'], 'MetaTrader 5')
        finally:
            with app_module.PRICE_LOCK:
                app_module.TRADING_DATA['symbol'] = previous_symbol
                app_module.TRADING_DATA['price'] = previous_price
                app_module.TRADING_DATA['price_history'] = previous_history
                app_module.TRADING_DATA['price_updated_at'] = previous_timestamp
                app_module.TRADING_DATA['price_source'] = previous_source
                app_module.TRADING_DATA['recent_ticks'] = previous_ticks
                app_module.TRADING_DATA['market_depth'] = previous_depth

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
            previous_depth = app_module.TRADING_DATA['market_depth']
            previous_timestamp = app_module.TRADING_DATA.get('price_updated_at')
            previous_source = app_module.TRADING_DATA.get('price_source')
            previous_ticks = app_module.TRADING_DATA['recent_ticks']
            app_module.TRADING_DATA['symbol'] = 'USDJPY'
            app_module.TRADING_DATA['price_history'] = [149.0]

        try:
            quote = {
                'price': 149.8,
                'timestamp': candle['time'],
                'history': [149.0, 149.8],
                'candles': [candle] * 12,
                'source': 'MetaTrader 5'
            }
            with patch.object(app_module, 'MARKET_DATA_AVAILABLE', True), \
                    patch.object(app_module.market_data, 'get_latest_quote', return_value=quote), \
                    patch.object(app_module.market_data, 'get_market_depth', return_value={
                        'available': True,
                        'source': 'mt5_dom',
                        'bids': [{'price': 149.7, 'volume': 3.0}],
                        'asks': [{'price': 149.9, 'volume': 2.0}]
                    }):
                app_module.update_market_price_once()

            response = app_module.app.test_client().get('/api/status')
            liquidity = response.get_json()['liquidity']
            depth = response.get_json()['liquidity_map']
            self.assertTrue(liquidity['available'])
            self.assertEqual(liquidity['window_candles'], 12)
            self.assertEqual(liquidity['flow_bias'], 'PRESIÓN COMPRADORA')
            self.assertEqual(depth['mode'], 'dom')
            self.assertEqual(depth['bids'][0]['price'], 149.7)
        finally:
            with app_module.PRICE_LOCK:
                app_module.TRADING_DATA['symbol'] = previous_symbol
                app_module.TRADING_DATA['price'] = previous_price
                app_module.TRADING_DATA['price_history'] = previous_history
                app_module.TRADING_DATA['market_candles'] = previous_candles
                app_module.TRADING_DATA['liquidity'] = previous_liquidity
                app_module.TRADING_DATA['market_depth'] = previous_depth
                app_module.TRADING_DATA['price_updated_at'] = previous_timestamp
                app_module.TRADING_DATA['price_source'] = previous_source
                app_module.TRADING_DATA['recent_ticks'] = previous_ticks

    def test_incoming_ticks_refresh_the_current_bar_without_mixing_ticks_into_bar_history(self):
        with app_module.PRICE_LOCK:
            previous_symbol = app_module.TRADING_DATA['symbol']
            previous_price = app_module.TRADING_DATA['price']
            previous_history = app_module.TRADING_DATA['price_history']
            previous_ticks = app_module.TRADING_DATA['recent_ticks']
            previous_timestamp = app_module.TRADING_DATA.get('price_updated_at')
            previous_source = app_module.TRADING_DATA.get('price_source')
            previous_candles = app_module.TRADING_DATA['market_candles']
            previous_liquidity = app_module.TRADING_DATA['liquidity']
            previous_depth = app_module.TRADING_DATA['market_depth']
            app_module.TRADING_DATA['symbol'] = 'EURUSD'
            app_module.TRADING_DATA['recent_ticks'] = []

        base_candle = {
            'time': 1730000000,
            'open': 1.1,
            'high': 1.101,
            'low': 1.099,
            'close': 1.1,
            'volume': 10.0
        }
        quotes = [
            {
                'price': 1.1005, 'timestamp': '2026-10-30T16:59:01+00:00',
                'history': [1.099, 1.1], 'candles': [dict(base_candle)],
                'source': 'MetaTrader 5', 'bid': 1.1004, 'ask': 1.1006
            },
            {
                'price': 1.1007, 'timestamp': '2026-10-30T16:59:02+00:00',
                'history': [1.099, 1.1], 'candles': [dict(base_candle)],
                'source': 'MetaTrader 5', 'bid': 1.1006, 'ask': 1.1008
            }
        ]
        try:
            with patch.object(app_module, 'MARKET_DATA_AVAILABLE', True), \
                    patch.object(app_module.market_data, 'get_latest_quote', side_effect=quotes), \
                    patch.object(app_module.market_data, 'get_market_depth', return_value={
                        'available': True,
                        'source': 'mt5_dom',
                        'bids': [{'price': 1.1006, 'volume': 1.0}],
                        'asks': []
                    }):
                app_module.update_market_price_once()
                app_module.update_market_price_once()

            self.assertEqual(len(app_module.TRADING_DATA['price_history']), 2)
            self.assertEqual(app_module.TRADING_DATA['price_history'][-1], 1.1007)
            self.assertEqual(len(app_module.TRADING_DATA['recent_ticks']), 2)
            self.assertEqual(app_module.TRADING_DATA['market_candles'][-1]['close'], 1.1007)
            self.assertEqual(app_module.TRADING_DATA['market_candles'][-1]['high'], 1.101)
        finally:
            with app_module.PRICE_LOCK:
                app_module.TRADING_DATA['symbol'] = previous_symbol
                app_module.TRADING_DATA['price'] = previous_price
                app_module.TRADING_DATA['price_history'] = previous_history
                app_module.TRADING_DATA['recent_ticks'] = previous_ticks
                app_module.TRADING_DATA['price_updated_at'] = previous_timestamp
                app_module.TRADING_DATA['price_source'] = previous_source
                app_module.TRADING_DATA['market_candles'] = previous_candles
                app_module.TRADING_DATA['liquidity'] = previous_liquidity
                app_module.TRADING_DATA['market_depth'] = previous_depth

    def test_changing_symbol_updates_the_chart_to_that_symbols_latest_quote(self):
        with app_module.PRICE_LOCK:
            previous_symbol = app_module.TRADING_DATA['symbol']
            previous_price = app_module.TRADING_DATA['price']
            previous_history = app_module.TRADING_DATA['price_history']
            previous_trading_symbol = app_module.TRADING_SYMBOL

        try:
            unauthorized = app_module.app.test_client().post(
                '/api/symbol', json={'symbol': 'EURUSD'}
            )
            self.assertEqual(unauthorized.status_code, 401)
            with patch.object(app_module, 'get_current_user', return_value=object()), \
                    patch.object(app_module.market_data, 'get_intraday_prices', return_value=[1.084, 1.0852]):
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
