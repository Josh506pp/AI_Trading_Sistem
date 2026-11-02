#!/usr/bin/env python3
"""Manually preview or send one guarded MT5 demo order from a fresh AI signal."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import MetaTrader5 as mt5

from src.demo_trading import DemoTradeRejected, prepare_demo_order, send_demo_order
from src.prediction_system import prediction_engine
from src.trading_signals import build_prediction_signal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--symbol', choices=('EURUSD', 'XAUUSD'), default='EURUSD')
    parser.add_argument(
        '--execute-demo-order',
        action='store_true',
        help='Send one checked order on a verified demo account; otherwise preview only.'
    )
    parser.add_argument(
        '--target-profit-usd',
        type=float,
        default=1.0,
        help='Gross broker-estimated TP objective in USD (default: 1.00).'
    )
    parser.add_argument(
        '--max-loss-usd',
        type=float,
        default=1.0,
        help='Maximum broker-estimated stop loss in USD (default: 1.00).'
    )
    args = parser.parse_args()

    if not mt5.initialize():
        print(f'No se pudo conectar con MT5: {mt5.last_error()}')
        return 2

    try:
        account = mt5.account_info()
        terminal = mt5.terminal_info()
        if account is None or terminal is None or account.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
            print('No se opera: no hay una cuenta demo verificada.')
            return 0
        if not terminal.trade_allowed or terminal.tradeapi_disabled or not account.trade_allowed:
            print('No se opera: MT5 no permite trading desde este terminal.')
            return 0

        rates = mt5.copy_rates_from_pos(args.symbol, mt5.TIMEFRAME_M1, 0, 200)
        if rates is None or len(rates) < 60:
            print(f'No se opera: MT5 no entregó suficientes velas M1 para {args.symbol}.')
            return 0

        latest_bar_time = int(rates[-1]['time'])
        signal = build_prediction_signal(
            [float(rate['close']) for rate in rates],
            periods=15,
            engine=prediction_engine
        )
        print(
            f"{args.symbol}: señal={signal['signal']}, "
            f"permitida={signal['trade_allowed']}, "
            f"walk-forward={signal['prediction'].get('walk_forward_accuracy')}, "
            f"muestras={signal['prediction'].get('walk_forward_samples')}"
        )

        try:
            plan = prepare_demo_order(
                mt5,
                args.symbol,
                signal,
                latest_bar_time,
                target_profit_usd=args.target_profit_usd,
                max_loss_usd=args.max_loss_usd
            )
        except DemoTradeRejected as exc:
            print(f'No se envió ninguna orden: {exc}')
            return 0

        print(
            f"Plan validado: volumen={plan.volume}, "
            f"TP bruto estimado=${plan.estimated_target_usd:.2f}, "
            f"pérdida estimada al SL=${plan.estimated_stop_loss_usd:.2f}, "
            f"TP={plan.request['tp']}."
        )
        if not args.execute_demo_order:
            print('Vista previa solamente. Usa --execute-demo-order para una orden demo.')
            return 0

        try:
            result = send_demo_order(mt5, args.symbol, plan)
        except DemoTradeRejected as exc:
            print(f'La orden no se completó: {exc}')
            return 1
        print(
            f"Orden demo enviada: retcode={result.retcode}, "
            f"order={getattr(result, 'order', 0)}, deal={getattr(result, 'deal', 0)}."
        )
        print('El TP/SL queda en el servidor MT5; el PnL final puede variar por costos y ejecución.')
        return 0
    finally:
        mt5.shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
