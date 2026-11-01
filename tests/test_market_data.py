import unittest
from unittest.mock import patch

import pandas as pd

from src.market_data import MarketDataProvider


class TestMarketDataProvider(unittest.TestCase):
    def test_latest_quote_uses_recent_intraday_data_and_returns_source_timestamp(self):
        timestamp = pd.Timestamp('2026-10-30 16:59:00', tz='America/New_York')
        data = pd.DataFrame({'Close': [3898.9]}, index=[timestamp])

        with patch('src.market_data.yf.download', return_value=data) as download:
            quote = MarketDataProvider().get_latest_quote('XAUUSD')

        self.assertEqual(quote, {
            'price': 3898.9,
            'timestamp': timestamp.isoformat(),
            'history': [3898.9]
        })
        self.assertEqual(download.call_args.kwargs['period'], '7d')
        self.assertEqual(download.call_args.kwargs['interval'], '1m')

    def test_latest_quote_returns_none_when_market_has_no_recent_data(self):
        with patch('src.market_data.yf.download', return_value=pd.DataFrame()):
            quote = MarketDataProvider().get_latest_quote('XAUUSD')

        self.assertIsNone(quote)


if __name__ == '__main__':
    unittest.main()
