import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.demo_trading import (
    DEMO_MAX_LOSS_USD,
    DEMO_TARGET_PROFIT_USD,
    DemoTradeRejected,
    close_demo_position,
    prepare_demo_order,
    send_demo_order,
    should_close_early_for_reversal,
)
from src.trading_signals import build_experimental_demo_signal


class FakeMT5:
    ACCOUNT_TRADE_MODE_DEMO = 0
    SYMBOL_TRADE_MODE_FULL = 4
    SYMBOL_TRADE_EXECUTION_MARKET = 2
    TRADE_ACTION_DEAL = 1
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_FILLING_FOK = 0
    ORDER_FILLING_IOC = 1
    ORDER_FILLING_RETURN = 2
    ORDER_TIME_GTC = 0
    TRADE_RETCODE_DONE = 10009
    TRADE_RETCODE_DONE_PARTIAL = 10010

    def __init__(self):
        self.terminal = SimpleNamespace(
            connected=True,
            trade_allowed=True,
            tradeapi_disabled=False
        )
        self.account = SimpleNamespace(
            trade_mode=self.ACCOUNT_TRADE_MODE_DEMO,
            trade_allowed=True,
            currency='USD'
        )
        self.symbol = SimpleNamespace(
            trade_mode=self.SYMBOL_TRADE_MODE_FULL,
            visible=True,
            filling_mode=3,
            trade_exemode=self.SYMBOL_TRADE_EXECUTION_MARKET,
            trade_stops_level=0,
            point=0.00001,
            trade_tick_size=0.00001,
            digits=5,
            volume_min=0.01,
            volume_step=0.01,
            volume_max=100
        )
        self.tick = SimpleNamespace(time=1000, bid=1.10000, ask=1.10010)
        self.positions = ()
        self.orders = ()
        self.checked_requests = []
        self.sent_requests = []
        self.check_retcode = 0

    def terminal_info(self):
        return self.terminal

    def account_info(self):
        return self.account

    def positions_get(self, symbol):
        return self.positions

    def orders_get(self, symbol):
        return self.orders

    def symbol_info(self, symbol):
        return self.symbol

    def symbol_info_tick(self, symbol):
        return self.tick

    def symbol_select(self, symbol, selected):
        return True

    def order_calc_profit(self, order_type, symbol, volume, entry, exit_price):
        direction = 1 if order_type == self.ORDER_TYPE_BUY else -1
        return (exit_price - entry) * direction * volume * 100000

    def order_check(self, request):
        self.checked_requests.append(dict(request))
        return SimpleNamespace(retcode=self.check_retcode, comment='check')

    def order_send(self, request):
        self.sent_requests.append(dict(request))
        return SimpleNamespace(
            retcode=self.TRADE_RETCODE_DONE,
            order=23,
            deal=24,
            comment='done'
        )

    def last_error(self):
        return (0, 'ok')


def valid_buy_signal():
    return {
        'signal': 'COMPRA',
        'trade_allowed': True,
        'stop_loss': 1.09960,
        'take_profit': 1.10120,
        'prediction': {
            'walk_forward_accuracy': 0.60,
            'walk_forward_samples': 20
        }
    }


class RawDirectionEngine:
    def __init__(self):
        self.stop_atr_multiple = None

    def _calculate_atr(self, prices):
        return 1.0

    def get_trading_levels(
        self,
        prices,
        direction,
        target_price,
        stop_atr_multiple=1.0
    ):
        self.stop_atr_multiple = stop_atr_multiple
        if direction == 'ALCISTA':
            return {
                'direction': direction,
                'entry': 100.0,
                'stop_loss': 99.0,
                'take_profit': 103.0,
                'risk_reward': 0.5
            }
        return {
            'direction': direction,
            'entry': 100.0,
            'stop_loss': 101.0,
            'take_profit': 97.0,
            'risk_reward': 3.0
        }


class TestDemoTrading(unittest.TestCase):
    def setUp(self):
        self.mt5 = FakeMT5()

    def prepare(
        self,
        signal=None,
        latest_bar_time=1000,
        target_profit_usd=1.0,
        max_loss_usd=1.0,
        allow_unconfirmed_direction=False,
        target_profit_range=None
    ):
        return prepare_demo_order(
            self.mt5,
            'EURUSD',
            signal or valid_buy_signal(),
            latest_bar_time,
            target_profit_usd=target_profit_usd,
            max_loss_usd=max_loss_usd,
            allow_unconfirmed_direction=allow_unconfirmed_direction,
            target_profit_range=target_profit_range
        )

    def test_raw_direction_experiment_is_explicit_and_unvalidated(self):
        waiting_signal = {
            'signal': 'ESPERA',
            'trade_allowed': False,
            'prediction': {
                'price_change': 3.0,
                'current_price': 100.0,
                'predicted_price': 103.0,
                'model_agreement': 0.75,
                'walk_forward_accuracy': 0.56,
                'walk_forward_samples': 12,
                'methods': {'ema': 103.0, 'linear': 104.0, 'momentum': 102.0, 'volatility': 99.0}
            }
        }
        engine = RawDirectionEngine()
        with patch(
            'src.trading_signals.build_prediction_signal',
            return_value=waiting_signal
        ):
            signal = build_experimental_demo_signal(
                [100.0] * 60, engine=engine
            )

        self.assertEqual(signal['signal'], 'COMPRA')
        self.assertTrue(signal['trade_allowed'])
        self.assertTrue(signal['experimental_demo_only'])
        self.assertEqual(signal['confidence_basis'], 'unvalidated_raw_model_direction')
        self.assertEqual(signal['risk_reward'], 0.5)
        self.assertEqual(engine.stop_atr_multiple, 2.5)

    def test_raw_direction_experiment_rejects_conflict_with_component_votes(self):
        waiting_signal = {
            'signal': 'ESPERA',
            'trade_allowed': False,
            'prediction': {
                'price_change': 3.0,
                'current_price': 100.0,
                'predicted_price': 103.0,
                'model_agreement': 0.75,
                'walk_forward_accuracy': 0.40,
                'walk_forward_samples': 12,
                'methods': {'ema': 97.0, 'linear': 98.0, 'momentum': 99.0, 'volatility': 101.0}
            }
        }
        with patch(
            'src.trading_signals.build_prediction_signal',
            return_value=waiting_signal
        ):
            signal = build_experimental_demo_signal(
                [100.0] * 60, engine=RawDirectionEngine()
            )

        self.assertEqual(signal['signal'], 'ESPERA')
        self.assertFalse(signal.get('experimental_demo_only', False))

    def test_raw_direction_experiment_rejects_low_model_agreement(self):
        waiting_signal = {
            'signal': 'ESPERA',
            'trade_allowed': False,
            'prediction': {
                'price_change': 3.0,
                'current_price': 100.0,
                'predicted_price': 103.0,
                'model_agreement': 0.50,
                'walk_forward_accuracy': 0.40,
                'walk_forward_samples': 12
            }
        }
        with patch(
            'src.trading_signals.build_prediction_signal',
            return_value=waiting_signal
        ):
            signal = build_experimental_demo_signal(
                [100.0] * 60, engine=RawDirectionEngine()
            )

        self.assertEqual(signal['signal'], 'ESPERA')
        self.assertFalse(signal.get('experimental_demo_only', False))

    def test_raw_direction_experiment_rejects_low_walk_forward_accuracy(self):
        waiting_signal = {
            'signal': 'ESPERA',
            'trade_allowed': False,
            'prediction': {
                'price_change': 3.0,
                'current_price': 100.0,
                'predicted_price': 103.0,
                'model_agreement': 0.75,
                'walk_forward_accuracy': 0.40,
                'effective_walk_forward_accuracy': 0.40,
                'walk_forward_samples': 12,
                'methods': {'ema': 103.0, 'linear': 104.0, 'momentum': 102.0, 'volatility': 99.0}
            }
        }
        with patch(
            'src.trading_signals.build_prediction_signal',
            return_value=waiting_signal
        ):
            signal = build_experimental_demo_signal(
                [100.0] * 60, engine=RawDirectionEngine()
            )

        self.assertEqual(signal['signal'], 'ESPERA')
        self.assertFalse(signal.get('experimental_demo_only', False))

    def test_unconfirmed_signal_is_accepted_only_in_explicit_demo_mode(self):
        signal = valid_buy_signal()
        signal['signal'] = 'COMPRA'
        signal['trade_allowed'] = False
        signal['experimental_demo_only'] = True
        signal['model_agreement'] = 0.75
        signal['prediction']['walk_forward_accuracy'] = 0.56

        with self.assertRaisesRegex(DemoTradeRejected, 'no autorizó'):
            self.prepare(signal)

        plan = self.prepare(
            signal,
            max_loss_usd=5.12,
            allow_unconfirmed_direction=True
        )
        self.assertAlmostEqual(plan.estimated_target_usd, 1.0)

    def test_demo_executor_rejects_low_accuracy_even_with_raw_direction_opt_in(self):
        signal = valid_buy_signal()
        signal['experimental_demo_only'] = True
        signal['model_agreement'] = 0.75
        signal['prediction']['walk_forward_accuracy'] = 0.28

        with self.assertRaisesRegex(DemoTradeRejected, 'walk-forward'):
            self.prepare(
                signal,
                max_loss_usd=5.0,
                allow_unconfirmed_direction=True
            )
        self.assertEqual(self.mt5.checked_requests, [])
        self.assertEqual(self.mt5.sent_requests, [])

    def test_prepares_usd_bounded_bracketed_demo_order(self):
        plan = self.prepare()

        self.assertEqual(plan.request['volume'], 0.01)
        self.assertEqual(plan.request['sl'], 1.09960)
        self.assertEqual(plan.request['tp'], 1.10110)
        self.assertAlmostEqual(plan.estimated_target_usd, DEMO_TARGET_PROFIT_USD)
        self.assertLessEqual(plan.estimated_stop_loss_usd, DEMO_MAX_LOSS_USD)
        self.assertAlmostEqual(plan.estimated_risk_reward, 2.0)
        self.assertEqual(len(self.mt5.checked_requests), 1)
        self.assertEqual(self.mt5.sent_requests, [])

    def test_rejects_live_quote_risk_reward_below_two_to_one(self):
        signal = valid_buy_signal()
        signal['stop_loss'] = 1.09950

        with self.assertRaisesRegex(DemoTradeRejected, 'excede el rango autorizado'):
            self.prepare(signal)
        self.assertEqual(self.mt5.checked_requests, [])
        self.assertEqual(self.mt5.sent_requests, [])

    def test_tp_moves_toward_entry_to_target_one_gross_dollar(self):
        plan = self.prepare(target_profit_usd=1.0, max_loss_usd=5.12)

        self.assertEqual(plan.request['tp'], 1.10110)
        self.assertAlmostEqual(plan.estimated_target_usd, 1.0)
        self.assertLessEqual(plan.estimated_stop_loss_usd, 5.12)

    def test_dynamic_target_uses_ai_projected_profit_clamped_to_five_to_fifteen(self):
        plan = self.prepare(target_profit_range=(5, 15), max_loss_usd=5)

        self.assertAlmostEqual(plan.target_goal_usd, 5.0)
        self.assertAlmostEqual(plan.estimated_target_usd, 5.0)
        self.assertLessEqual(plan.estimated_stop_loss_usd, 5.0)

    def test_dynamic_target_moves_a_few_ticks_to_preserve_two_to_one_ratio(self):
        signal = valid_buy_signal()
        signal['stop_loss'] = 1.09959

        plan = self.prepare(
            signal,
            target_profit_range=(5, 15),
            max_loss_usd=5
        )

        self.assertAlmostEqual(plan.target_goal_usd, 5.1)
        self.assertGreaterEqual(plan.estimated_risk_reward, 2.0)
        self.assertLessEqual(plan.estimated_stop_loss_usd, 5.0)

    def test_dynamic_target_caps_large_ai_target_at_fifteen(self):
        signal = valid_buy_signal()
        signal['take_profit'] = 1.12010

        plan = self.prepare(
            signal,
            target_profit_range=(5, 15),
            max_loss_usd=5
        )

        self.assertAlmostEqual(plan.target_goal_usd, 15.0)
        self.assertAlmostEqual(plan.estimated_target_usd, 15.0)

    def test_rejects_stop_loss_above_custom_demo_cap(self):
        signal = valid_buy_signal()
        signal['stop_loss'] = 1.09480
        signal['take_profit'] = 1.11000

        with self.assertRaisesRegex(DemoTradeRejected, 'USD 5.12'):
            self.prepare(signal, max_loss_usd=5.12)
        self.assertEqual(self.mt5.sent_requests, [])

    def test_rejects_live_account_before_order_check(self):
        self.mt5.account.trade_mode = 1

        with self.assertRaisesRegex(DemoTradeRejected, 'solo permite cuentas demo'):
            self.prepare()

        self.assertEqual(self.mt5.checked_requests, [])
        self.assertEqual(self.mt5.sent_requests, [])

    def test_rejects_disabled_terminal_and_python_api(self):
        self.mt5.terminal.trade_allowed = False
        with self.assertRaisesRegex(DemoTradeRejected, 'Algo Trading'):
            self.prepare()

        self.mt5.terminal.trade_allowed = True
        self.mt5.terminal.tradeapi_disabled = True
        with self.assertRaisesRegex(DemoTradeRejected, 'trading desde Python'):
            self.prepare()
        self.assertEqual(self.mt5.checked_requests, [])

    def test_rejects_wait_signal_and_stale_candles(self):
        signal = valid_buy_signal()
        signal['signal'] = 'ESPERA'
        signal['trade_allowed'] = False
        with self.assertRaisesRegex(DemoTradeRejected, 'no autorizó'):
            self.prepare(signal)

        with self.assertRaisesRegex(DemoTradeRejected, 'desfasadas'):
            self.prepare(latest_bar_time=700)
        self.assertEqual(self.mt5.checked_requests, [])

    def test_rejects_insufficient_walk_forward_validation(self):
        signal = valid_buy_signal()
        signal['prediction']['walk_forward_accuracy'] = 0.54

        with self.assertRaisesRegex(DemoTradeRejected, 'walk-forward'):
            self.prepare(signal)
        self.assertEqual(self.mt5.checked_requests, [])

    def test_rejects_existing_position_or_pending_order(self):
        self.mt5.positions = (SimpleNamespace(ticket=9),)
        with self.assertRaisesRegex(DemoTradeRejected, 'posición abierta'):
            self.prepare()

        self.mt5.positions = ()
        self.mt5.orders = (SimpleNamespace(ticket=10),)
        with self.assertRaisesRegex(DemoTradeRejected, 'orden pendiente'):
            self.prepare()
        self.assertEqual(self.mt5.checked_requests, [])

    def test_rejects_stop_loss_above_usd_cap(self):
        signal = valid_buy_signal()
        signal['stop_loss'] = 1.09500
        signal['take_profit'] = 1.11000

        with self.assertRaisesRegex(DemoTradeRejected, 'pérdida máxima'):
            self.prepare(signal)
        self.assertEqual(self.mt5.sent_requests, [])

    def test_rejects_unchecked_order(self):
        self.mt5.check_retcode = 10016

        with self.assertRaisesRegex(DemoTradeRejected, 'comprobación previa'):
            self.prepare()
        self.assertEqual(self.mt5.sent_requests, [])

    def test_sends_only_a_prechecked_order_on_demo(self):
        plan = self.prepare()

        result = send_demo_order(self.mt5, 'EURUSD', plan)

        self.assertEqual(result.order, 23)
        self.assertEqual(len(self.mt5.sent_requests), 1)

    def test_rechecks_demo_mode_before_sending(self):
        plan = self.prepare()
        self.mt5.account.trade_mode = 1

        with self.assertRaisesRegex(DemoTradeRejected, 'solo permite cuentas demo'):
            send_demo_order(self.mt5, 'EURUSD', plan)

        self.assertEqual(self.mt5.sent_requests, [])

    def test_early_close_requires_minimum_profit_reversal_and_volatility_expansion(self):
        self.assertFalse(should_close_early_for_reversal(
            0.99, True, 'BAJISTA', 2.0, 1.0
        ))
        self.assertFalse(should_close_early_for_reversal(
            1.2, True, 'BAJISTA', 1.4, 1.0
        ))
        self.assertFalse(should_close_early_for_reversal(
            1.2, True, 'ALCISTA', 2.0, 1.0
        ))
        self.assertTrue(should_close_early_for_reversal(
            1.0, True, 'BAJISTA', 1.5, 1.0
        ))

    def test_early_close_checks_current_gross_profit_and_demo_owned_position(self):
        position = SimpleNamespace(
            symbol='EURUSD',
            magic=26110101,
            type=FakeMT5.ORDER_TYPE_BUY,
            volume=0.01,
            price_open=1.1001,
            ticket=23
        )
        self.mt5.tick.bid = 1.1012
        result = close_demo_position(self.mt5, position, min_profit_usd=1.0)

        self.assertEqual(result.order, 23)
        self.assertEqual(len(self.mt5.sent_requests), 1)
        self.assertEqual(self.mt5.sent_requests[0]['position'], 23)

    def test_early_close_refuses_below_one_dollar_or_foreign_position(self):
        position = SimpleNamespace(
            symbol='EURUSD',
            magic=26110101,
            type=FakeMT5.ORDER_TYPE_BUY,
            volume=0.01,
            price_open=1.1001,
            ticket=23
        )
        self.mt5.tick.bid = 1.1002
        with self.assertRaisesRegex(DemoTradeRejected, 'menor al mínimo'):
            close_demo_position(self.mt5, position, min_profit_usd=1.0)
        self.assertEqual(self.mt5.sent_requests, [])

        position.magic = 7
        with self.assertRaisesRegex(DemoTradeRejected, 'solo puede cerrar posiciones'):
            close_demo_position(self.mt5, position, min_profit_usd=0.0)
        self.assertEqual(self.mt5.sent_requests, [])


if __name__ == '__main__':
    unittest.main()
