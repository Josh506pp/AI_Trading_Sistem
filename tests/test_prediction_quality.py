import math
import importlib
import inspect
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.app import app, calculate_bollinger_bands, calculate_macd, calculate_rsi
from src.prediction_system import (
    BASE_MODEL_WEIGHTS,
    DEFAULT_STOP_ATR_MULTIPLE,
    DEFAULT_WALK_FORWARD_WINDOWS,
    PredictionEngine,
)

app_module = importlib.import_module('src.app')


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
            bands['lower'],
            periods=15
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

    def test_wider_stop_multiplier_scales_atr_distance_without_changing_entry(self):
        prices = [100.0 + index * 0.1 for index in range(60)]
        standard = self.engine.get_trading_levels(
            prices, 'ALCISTA', prices[-1] + 10.0
        )
        wider = self.engine.get_trading_levels(
            prices, 'ALCISTA', prices[-1] + 10.0, stop_atr_multiple=3.0
        )

        self.assertEqual(standard['entry'], wider['entry'])
        self.assertAlmostEqual(
            wider['entry'] - wider['stop_loss'],
            (standard['entry'] - standard['stop_loss']) * (3.0 / 2.25)
        )
        self.assertAlmostEqual(
            standard['entry'] - standard['stop_loss'],
            self.engine._calculate_atr(prices[-50:]) * DEFAULT_STOP_ATR_MULTIPLE
        )
        self.assertEqual(standard['stop_atr_multiple'], 2.25)
        self.assertEqual(wider['stop_atr_multiple'], 3.0)

    def test_risk_reward_uses_the_actual_atr_stop_distance(self):
        prices = [100.0 + index * 0.1 for index in range(60)]
        target = prices[-1] + 10.0
        levels = self.engine.get_trading_levels(
            prices, 'ALCISTA', target, stop_atr_multiple=2.25
        )
        actual_stop_distance = levels['entry'] - levels['stop_loss']

        self.assertAlmostEqual(
            levels['risk_reward'],
            abs(levels['take_profit'] - levels['entry']) / actual_stop_distance,
            places=2
        )

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
                bands['lower'],
                periods=15
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
            bands['lower'],
            periods=15
        )

        self.assertTrue(signal['trade_allowed'])
        self.assertEqual(signal['signal'], 'VENTA')
        self.assertGreaterEqual(signal['risk_reward'], 2.0)
        self.assertGreater(signal['stop_loss'], signal['entry'])
        self.assertLess(signal['take_profit'], signal['entry'])

    def test_macd_histogram_uses_a_separate_signal_ema(self):
        prices = [100.0 + index * 0.1 for index in range(60)]

        self.assertGreater(calculate_macd(prices)['histogram'], 0)

    def test_ema_forecast_projects_the_smoothed_ema_slope(self):
        prediction = self.engine._ema_prediction(
            [10.0, 10.0, 10.0, 10.0, 20.0],
            periods=4
        )

        self.assertAlmostEqual(prediction['price'], 21.6666666667)

    def test_prediction_includes_out_of_sample_directional_accuracy_and_range(self):
        prices = [100 + index * 0.08 + math.sin(index * 0.7) * 0.4 for index in range(120)]
        prediction = self.engine.predict_next_price(prices)

        self.assertGreater(prediction['expected_high'], prediction['expected_low'])
        self.assertGreater(prediction['walk_forward_samples'], 0)
        self.assertGreaterEqual(prediction['walk_forward_accuracy'], 0.0)
        self.assertLessEqual(prediction['walk_forward_accuracy'], 1.0)

    def test_walk_forward_learning_reports_per_model_accuracy_and_bounded_weights(self):
        prices = [100 + index * 0.08 + math.sin(index * 0.7) * 0.4 for index in range(120)]
        prediction = self.engine.predict_next_price(prices)

        self.assertEqual(set(prediction['model_performance']), set(BASE_MODEL_WEIGHTS))
        self.assertEqual(set(prediction['model_weights']), set(BASE_MODEL_WEIGHTS))
        self.assertAlmostEqual(sum(prediction['model_weights'].values()), 1.0)
        self.assertGreater(prediction['adaptive_walk_forward_samples'], 0)
        self.assertGreaterEqual(
            prediction['adaptive_walk_forward_accuracy'], 0.0
        )
        self.assertLessEqual(
            prediction['adaptive_walk_forward_accuracy'], 1.0
        )
        self.assertEqual(
            prediction['learning_basis'],
            'expanding_walk_forward_market_history'
        )
        self.assertEqual(
            prediction['confidence_basis'],
            'model_agreement_not_probability'
        )

    def test_adaptive_model_weights_favor_reliable_models_but_shrink_sparse_history(self):
        learned = PredictionEngine._adaptive_model_weights({
            'ema': {'correct': 18, 'samples': 20},
            'linear': {'correct': 4, 'samples': 20},
            'momentum': {'correct': 10, 'samples': 20},
            'volatility': {'correct': 5, 'samples': 5}
        })
        sparse = PredictionEngine._adaptive_model_weights({})

        self.assertGreater(learned['ema'], BASE_MODEL_WEIGHTS['ema'])
        self.assertLess(learned['linear'], BASE_MODEL_WEIGHTS['linear'])
        self.assertEqual(sparse, BASE_MODEL_WEIGHTS)
        self.assertAlmostEqual(sum(learned.values()), 1.0)

    def test_oos_calibrated_base_weights_keep_linear_as_largest_component(self):
        self.assertEqual(
            BASE_MODEL_WEIGHTS,
            {'ema': 0.20, 'linear': 0.40, 'momentum': 0.20, 'volatility': 0.20}
        )

    def test_low_walk_forward_accuracy_suppresses_directional_predictions(self):
        prices = [100.0 + index * 0.1 + math.sin(index) * 0.01 for index in range(120)]
        with patch.object(self.engine, '_walk_forward_accuracy', return_value=(0.54, 12)):
            prediction = self.engine.predict_next_price(prices)

        self.assertEqual(prediction['direction'], 'NEUTRAL')
        self.assertEqual(prediction['confidence'], 0.0)
        self.assertEqual(prediction['walk_forward_accuracy'], 0.54)

    def test_walk_forward_targets_exact_forecast_horizon_without_one_bar_leak(self):
        prices = [100.0 + (index % 2) for index in range(50)]

        def forecast_up(history, _periods):
            return {'price': history[-1] + float(_periods)}

        with patch.object(self.engine, '_ema_prediction', side_effect=forecast_up), \
                patch.object(self.engine, '_linear_regression_prediction', side_effect=forecast_up), \
                patch.object(self.engine, '_momentum_prediction', side_effect=forecast_up), \
                patch.object(self.engine, '_volatility_adjusted_prediction', side_effect=forecast_up):
            accuracy, samples = self.engine._walk_forward_accuracy(
                prices, periods=1, max_windows=20
            )

        self.assertEqual(samples, 20)
        self.assertEqual(accuracy, 0.5)

    def test_walk_forward_accuracy_excludes_model_vote_conflicts(self):
        prices = [100.0 + (index % 2) for index in range(50)]

        def forecast_up(history, _periods):
            return {'price': history[-1] + 1.0}

        def forecast_far_down(history, _periods):
            return {'price': history[-1] - 20.0}

        with patch.object(self.engine, '_ema_prediction', side_effect=forecast_up), \
                patch.object(self.engine, '_linear_regression_prediction', side_effect=forecast_up), \
                patch.object(self.engine, '_momentum_prediction', side_effect=forecast_up), \
                patch.object(self.engine, '_volatility_adjusted_prediction', side_effect=forecast_far_down):
            accuracy, samples = self.engine._walk_forward_accuracy(
                prices, periods=1, max_windows=20
            )

        self.assertIsNone(accuracy)
        self.assertEqual(samples, 0)

    def test_walk_forward_uses_longer_rolling_sample_for_market_learning(self):
        windows = inspect.signature(
            self.engine._walk_forward_accuracy
        ).parameters['max_windows'].default

        self.assertEqual(windows, DEFAULT_WALK_FORWARD_WINDOWS)
        self.assertGreater(windows, 40)

    def test_prediction_suppresses_direction_when_walk_forward_sample_is_insufficient(self):
        prices = [100 + index * 0.08 + math.sin(index * 0.7) * 0.4 for index in range(120)]
        with patch.object(self.engine, '_walk_forward_accuracy', return_value=(None, 0)):
            prediction = self.engine.predict_next_price(prices)

        self.assertEqual(prediction['direction'], 'NEUTRAL')
        self.assertEqual(prediction['confidence'], 0.0)
        self.assertIsNone(prediction['effective_walk_forward_accuracy'])

    def test_prediction_calculation_is_cached_per_symbol_during_cooldown(self):
        app_module._prediction_cache.clear()
        fake_prediction = {
            'signal': 'ESPERA',
            'prediction': {'direction': 'NEUTRAL'},
            'levels': {},
            'reasons': []
        }
        with patch.object(
            app_module, '_build_prediction_signal_uncached', return_value=fake_prediction
        ) as calculate:
            first = app_module.build_prediction_signal([100.0] * 50, 'CACHE_TEST')
            second = app_module.build_prediction_signal([101.0] * 50, 'CACHE_TEST')
            other_symbol = app_module.build_prediction_signal([101.0] * 50, 'CACHE_TEST_OTHER')

        self.assertEqual(calculate.call_count, 2)
        self.assertEqual(first['cache_status'], 'calculated')
        self.assertEqual(second['cache_status'], 'cached')
        self.assertEqual(other_symbol['cache_status'], 'calculated')
        app_module.invalidate_prediction_cache('CACHE_TEST')
        app_module.invalidate_prediction_cache('CACHE_TEST_OTHER')

    def test_free_user_cannot_call_prediction_routes(self):
        with app_module.app.app_context():
            free_user = app_module.User.query.filter_by(username='demo').one()
            user_id = free_user.id

        with patch.dict(app_module.app.config, {'TESTING': True}):
            with app_module.app.test_client() as client:
                with client.session_transaction() as state:
                    state['user_id'] = user_id
                for endpoint in (
                    '/api/predict',
                    '/api/predict/levels',
                    '/api/predict/signal'
                ):
                    self.assertEqual(client.get(endpoint).status_code, 403, endpoint)


    def test_build_prediction_signal_uses_requested_forecast_horizon(self):
        app_module.invalidate_prediction_cache('HORIZON_TEST')
        prices = [100.0 + index * 0.1 + math.sin(index) * 0.01 for index in range(60)]
        with patch.object(
            app_module.prediction_engine,
            'get_prediction_signal',
            wraps=app_module.prediction_engine.get_prediction_signal
        ) as predict:
            app_module.build_prediction_signal(prices, 'HORIZON_TEST', periods=15)

        self.assertEqual(predict.call_args.kwargs['periods'], 15)
        app_module.invalidate_prediction_cache('HORIZON_TEST')

    def test_advanced_prediction_cooldown_is_plan_specific(self):
        app_module._advanced_prediction_cache.clear()
        calculate_pro = Mock(return_value={'success': True, 'symbol': 'BTCUSD'})
        calculate_premium = Mock(return_value={'success': True, 'symbol': 'BTCUSD'})

        pro_first = app_module.get_cached_advanced_prediction('PRO', 'BTCUSD', calculate_pro)
        pro_cached = app_module.get_cached_advanced_prediction('PRO', 'BTCUSD', calculate_pro)
        premium_first = app_module.get_cached_advanced_prediction(
            'PREMIUM', 'BTCUSD', calculate_premium
        )

        self.assertEqual(calculate_pro.call_count, 1)
        self.assertEqual(calculate_premium.call_count, 1)
        self.assertEqual(pro_first['prediction_cache']['cooldown_seconds'], 300)
        self.assertEqual(pro_cached['prediction_cache']['status'], 'cached')
        self.assertEqual(pro_cached['prediction_cache']['remaining_seconds'], 300)
        self.assertEqual(premium_first['prediction_cache']['cooldown_seconds'], 120)
        app_module._advanced_prediction_cache.clear()

    def test_prediction_endpoints_share_one_calculation_within_cooldown(self):
        symbol = app_module.TRADING_DATA['symbol']
        app_module.invalidate_prediction_cache(symbol)
        premium_user = SimpleNamespace(
            id=987654,
            subscription_plan='PREMIUM',
            has_active_subscription=lambda: True
        )

        with patch.dict(app_module.app.config, {'TESTING': True}), \
                patch.object(app_module, 'get_current_user', return_value=premium_user), \
                patch.object(
                    app_module.prediction_engine,
                    'get_prediction_signal',
                    wraps=app_module.prediction_engine.get_prediction_signal
                ) as calculate:
            with app_module.app.test_client() as client:
                first = client.get('/api/predict')
                second = client.get('/api/advanced-prediction')
                third = client.get('/api/advanced-prediction')

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(third.status_code, 200)
        self.assertEqual(calculate.call_count, 1)
        self.assertEqual(first.get_json()['prediction_cache']['status'], 'calculated')
        self.assertEqual(second.get_json()['prediction_cache']['status'], 'calculated')
        self.assertEqual(third.get_json()['prediction_cache']['status'], 'cached')
        self.assertEqual(first.get_json()['prediction']['periods'], 10)
        self.assertEqual(third.get_json()['prediction_cache']['cooldown_seconds'], 120)
        app_module.invalidate_prediction_cache(symbol)

    def test_dashboard_has_a_native_canvas_chart_fallback(self):
        from src.app import DASHBOARD_HTML

        self.assertIn('function drawFallbackChart(dataPoints)', DASHBOARD_HTML)
        self.assertIn('Esperando datos de mercado...', DASHBOARD_HTML)
        self.assertNotIn('cdn.jsdelivr.net/npm/chart.js', DASHBOARD_HTML)
        self.assertIn('id="chart-tooltip"', DASHBOARD_HTML)
        self.assertIn('function showChartTooltip(event)', DASHBOARD_HTML)
        self.assertIn('id="liquidity-bias"', DASHBOARD_HTML)
        self.assertIn('PREDICTION_COOLDOWN_MS = 15000', DASHBOARD_HTML)
        self.assertIn('PREDICTION_HORIZON_MINUTES = 10', DASHBOARD_HTML)
        self.assertIn('function startAdvancedCooldown(seconds)', DASHBOARD_HTML)
        self.assertIn('id="predictions-plan-locked"', DASHBOARD_HTML)
        self.assertIn('id="chat-plan-locked"', DASHBOARD_HTML)


if __name__ == '__main__':
    unittest.main()
