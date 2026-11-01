import importlib
import unittest
from unittest.mock import patch


app_module = importlib.import_module('src.app')


class TestDashboardChart(unittest.TestCase):
    def test_status_returns_chart_data_without_reentering_price_lock(self):
        with patch.object(app_module, 'MARKET_DATA_AVAILABLE', False):
            response = app_module.app.test_client().get('/api/status')

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload['prices'])
        self.assertTrue(payload['candles'])
        self.assertIn('c', payload['candles'][0])


if __name__ == '__main__':
    unittest.main()
