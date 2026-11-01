import math
import unittest
from unittest.mock import patch

from src.app import app, calculate_bollinger_bands, calculate_macd, calculate_rsi
from src.prediction_system import PredictionEngine


class TestPredictionQuality(unittest.TestCase):
    def setUp(self):
        self.engine = PredictionEngine()

    def test_trade_requires_confirmed_direction_and_at_least_two_to_one_reward(self):
        prices = [100 + index * 0.08 + math.sin(index * 0.7) * 0.4 for index in range(120)]
        bands = calculate_bollinger_bands(prices)
        signal = self.engine.get_prediction_signal(
            prices,
            calculate_rsi(prices),
            calculate_macd(prices)['histogram'],
            bands['upper'],
            bands['lower']
        )

        self.assertTrue(signal['trade_allowed'])
        self.assertEqual(signal['signal'], 'COMPRA')
        self.assertGreaterEqual(signal['risk_reward'], 2.0)
        self.assertLess(signal['stop_loss'], signal['entry'])
        self.assertGreater(signal['take_profit'], signal['entry'])
        app.json.dumps(signal)

    def test_flat_prices_never_generate_a_trade(self):
        signal = self.engine.get_prediction_signal([100.0] * 60, 50.0, 0.0, 101.0, 99.0)

        self.assertFalse(signal['trade_allowed'])
        self.assertEqual(signal['signal'], 'ESPERA')
        self.assertIsNone(signal['stop_loss'])
        self.assertIsNone(signal['take_profit'])

    def test_forecast_below_two_to_one_is_rejected(self):
        prices = [100 + index * 0.08 + math.sin(index * 0.7) * 0.4 for index in range(120)]
        current = prices[-1]
        prediction = {
            'current_price': current,
            'predicted_price': current + 0.1,
            'price_change': 0.1,
            'change_percent': 0.1,
            'direction': 'ALCISTA',
            'confidence': 0.9,
            'model_agreement': 1.0,
            'confidence_basis': 'model_agreement_not_probability'
        }
        bands = calculate_bollinger_bands(prices)
        with patch.object(self.engine, 'predict_next_price', return_value=prediction):
            signal = self.engine.get_prediction_signal(
                prices,
                calculate_rsi(prices),
                calculate_macd(prices)['histogram'],
                bands['upper'],
                bands['lower']
            )

        self.assertFalse(signal['trade_allowed'])
        self.assertEqual(signal['signal'], 'ESPERA')
        self.assertLess(signal['risk_reward'], 2.0)

    def test_confirmed_downtrend_generates_short_setup(self):
        prices = [120 - index * 0.08 + math.sin(index) * 0.2 for index in range(120)]
        bands = calculate_bollinger_bands(prices)
        signal = self.engine.get_prediction_signal(
            prices,
            calculate_rsi(prices),
            calculate_macd(prices)['histogram'],
            bands['upper'],
            bands['lower']
        )

        self.assertTrue(signal['trade_allowed'])
        self.assertEqual(signal['signal'], 'VENTA')
        self.assertGreaterEqual(signal['risk_reward'], 2.0)
        self.assertGreater(signal['stop_loss'], signal['entry'])
        self.assertLess(signal['take_profit'], signal['entry'])

    def test_macd_histogram_uses_a_separate_signal_ema(self):
        prices = [100.0 + index * 0.1 for index in range(60)]

        self.assertGreater(calculate_macd(prices)['histogram'], 0)

    def test_dashboard_has_a_native_canvas_chart_fallback(self):
        from src.app import DASHBOARD_HTML

        self.assertIn('function drawFallbackChart(dataPoints)', DASHBOARD_HTML)
        self.assertIn('Esperando datos de mercado...', DASHBOARD_HTML)
        self.assertNotIn('cdn.jsdelivr.net/npm/chart.js', DASHBOARD_HTML)


if __name__ == '__main__':
    unittest.main()
