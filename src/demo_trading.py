"""Guarded, explicit MT5 demo-order preparation for manual test runs."""

import math
import time
from dataclasses import dataclass


DEMO_TARGET_PROFIT_USD = 1.0
DEMO_MIN_TARGET_PROFIT_USD = 5.0
DEMO_MAX_TARGET_PROFIT_USD = 15.0
DEMO_EARLY_CLOSE_PROFIT_USD = 1.0
DEMO_MAX_LOSS_USD = 5.0
DEMO_MAX_VOLUME = 0.10
DEMO_MAX_BAR_AGE_SECONDS = 120
DEMO_MAGIC = 26110101
DEMO_REVERSAL_VOLATILITY_MULTIPLIER = 1.5
DEMO_MONITOR_MAX_SECONDS = 900
SUPPORTED_TEST_SYMBOLS = frozenset({'EURUSD', 'XAUUSD'})


class DemoTradeRejected(RuntimeError):
    """A demo order was refused by a safety or signal check."""


@dataclass(frozen=True)
class DemoOrderPlan:
    request: dict
    estimated_target_usd: float
    estimated_stop_loss_usd: float
    volume: float
    entry_price: float
    target_goal_usd: float


def _require_demo_permissions(mt5):
    terminal = mt5.terminal_info()
    account = mt5.account_info()
    if terminal is None or account is None:
        raise DemoTradeRejected('No hay terminal/cuenta MT5 conectado.')
    if not getattr(terminal, 'connected', False):
        raise DemoTradeRejected('El terminal MT5 no está conectado.')
    if account.trade_mode != getattr(mt5, 'ACCOUNT_TRADE_MODE_DEMO', 0):
        raise DemoTradeRejected('El ejecutor solo permite cuentas demo.')
    if not getattr(account, 'trade_allowed', False):
        raise DemoTradeRejected('La cuenta MT5 no permite operar.')
    if not getattr(terminal, 'trade_allowed', False):
        raise DemoTradeRejected('Algo Trading está deshabilitado en MT5.')
    if getattr(terminal, 'tradeapi_disabled', True):
        raise DemoTradeRejected('MT5 tiene deshabilitado el trading desde Python.')
    if getattr(account, 'currency', None) != 'USD':
        raise DemoTradeRejected('La cuenta demo debe estar denominada en USD.')


def _require_no_existing_orders(mt5, symbol):
    positions = mt5.positions_get(symbol=symbol)
    if positions is None:
        raise DemoTradeRejected(f'No se pudieron leer posiciones MT5: {mt5.last_error()}')
    if positions:
        raise DemoTradeRejected(f'Ya existe una posición abierta en {symbol}.')

    orders = mt5.orders_get(symbol=symbol)
    if orders is None:
        raise DemoTradeRejected(f'No se pudieron leer órdenes MT5: {mt5.last_error()}')
    if orders:
        raise DemoTradeRejected(f'Ya existe una orden pendiente en {symbol}.')


def _profit(mt5, order_type, symbol, volume, entry, exit_price):
    result = mt5.order_calc_profit(order_type, symbol, volume, entry, exit_price)
    if result is None or not math.isfinite(float(result)):
        raise DemoTradeRejected(
            f'No se pudo estimar el PnL en USD: {mt5.last_error()}'
        )
    return float(result)


def _volume_precision(step):
    text = f'{step:.10f}'.rstrip('0')
    return len(text.partition('.')[2])


def _candidate_filling_modes(mt5, symbol_info):
    modes = []
    filling_flags = int(getattr(symbol_info, 'filling_mode', 0))
    if filling_flags & 1:
        modes.append(mt5.ORDER_FILLING_FOK)
    if filling_flags & 2:
        modes.append(mt5.ORDER_FILLING_IOC)
    market_execution = getattr(mt5, 'SYMBOL_TRADE_EXECUTION_MARKET', 2)
    if getattr(symbol_info, 'trade_exemode', None) != market_execution:
        modes.append(mt5.ORDER_FILLING_RETURN)
    return list(dict.fromkeys(modes))


def prepare_demo_order(
    mt5,
    symbol,
    signal,
    latest_bar_time,
    target_profit_usd=DEMO_TARGET_PROFIT_USD,
    max_loss_usd=DEMO_MAX_LOSS_USD,
    allow_unconfirmed_direction=False,
    target_profit_range=None
):
    """Validate a fresh IA signal and prepare a checked, USD-bounded demo order."""
    try:
        target_profit_usd = float(target_profit_usd)
        max_loss_usd = float(max_loss_usd)
    except (TypeError, ValueError, OverflowError):
        raise DemoTradeRejected('El objetivo y el límite de pérdida deben ser números.')
    if (
        not math.isfinite(target_profit_usd) or target_profit_usd <= 0 or
        not math.isfinite(max_loss_usd) or max_loss_usd <= 0
    ):
        raise DemoTradeRejected('El objetivo y el límite de pérdida deben ser positivos.')
    target_range = None
    if target_profit_range is not None:
        try:
            target_min, target_max = (
                float(target_profit_range[0]),
                float(target_profit_range[1])
            )
        except (IndexError, TypeError, ValueError, OverflowError):
            raise DemoTradeRejected('El rango del TP debe contener dos cantidades válidas.')
        if (
            not math.isfinite(target_min) or not math.isfinite(target_max) or
            target_min <= 0 or target_max < target_min
        ):
            raise DemoTradeRejected('El rango del TP no es válido.')
        target_range = (target_min, target_max)
    normalized_symbol = str(symbol).upper()
    if normalized_symbol not in SUPPORTED_TEST_SYMBOLS:
        raise DemoTradeRejected('El harness solo admite EURUSD y XAUUSD.')

    _require_demo_permissions(mt5)
    _require_no_existing_orders(mt5, normalized_symbol)

    experimental_raw = (
        allow_unconfirmed_direction is True and
        isinstance(signal, dict) and
        signal.get('experimental_demo_only') is True
    )
    if not isinstance(signal, dict) or (
        signal.get('trade_allowed') is not True and not experimental_raw
    ):
        raise DemoTradeRejected('La IA no autorizó una entrada; no se fuerza la señal.')
    direction = signal.get('signal')
    if direction not in ('COMPRA', 'VENTA'):
        raise DemoTradeRejected('La señal de la IA no es COMPRA/VENTA.')
    prediction = signal.get('prediction') or {}
    accuracy = prediction.get('walk_forward_accuracy')
    samples = prediction.get('walk_forward_samples', 0)
    if (
        accuracy is None or not math.isfinite(float(accuracy)) or
        (float(accuracy) < 0.55 and not experimental_raw) or int(samples) < 8
    ):
        raise DemoTradeRejected('La validación walk-forward no alcanza el 55% con 8 muestras.')
    if experimental_raw and float(signal.get('model_agreement', 0)) < 0.75:
        raise DemoTradeRejected('La dirección experimental no alcanza el 75% de consenso.')

    symbol_info = mt5.symbol_info(normalized_symbol)
    tick = mt5.symbol_info_tick(normalized_symbol)
    if symbol_info is None or tick is None:
        raise DemoTradeRejected(f'No hay especificación/cotización para {normalized_symbol}.')
    if symbol_info.trade_mode != getattr(mt5, 'SYMBOL_TRADE_MODE_FULL', 4):
        raise DemoTradeRejected(f'{normalized_symbol} no permite operar en este momento.')
    if not symbol_info.visible and not mt5.symbol_select(normalized_symbol, True):
        raise DemoTradeRejected(f'No se pudo habilitar {normalized_symbol} en Market Watch.')

    try:
        bar_age = int(tick.time) - int(latest_bar_time)
    except (TypeError, ValueError, OverflowError):
        raise DemoTradeRejected('La marca temporal de la última vela no es válida.')
    if bar_age < 0 or bar_age > DEMO_MAX_BAR_AGE_SECONDS:
        raise DemoTradeRejected(
            f'Velas MT5 desfasadas ({bar_age}s); máximo permitido '
            f'{DEMO_MAX_BAR_AGE_SECONDS}s.'
        )

    is_buy = direction == 'COMPRA'
    order_type = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL
    entry = float(tick.ask if is_buy else tick.bid)
    try:
        stop_loss = round(float(signal.get('stop_loss')), int(symbol_info.digits))
        take_profit = round(float(signal.get('take_profit')), int(symbol_info.digits))
    except (TypeError, ValueError, OverflowError):
        raise DemoTradeRejected('La señal no contiene niveles SL/TP numéricos.')
    if not all(math.isfinite(value) and value > 0 for value in (entry, stop_loss, take_profit)):
        raise DemoTradeRejected('La cotización o los niveles SL/TP no son válidos.')
    if is_buy and not stop_loss < entry < take_profit:
        raise DemoTradeRejected('Los niveles COMPRA no contienen el precio actual.')
    if not is_buy and not take_profit < entry < stop_loss:
        raise DemoTradeRejected('Los niveles VENTA no contienen el precio actual.')

    minimum_distance = max(
        float(getattr(symbol_info, 'trade_stops_level', 0)) * float(symbol_info.point),
        float(symbol_info.point)
    )
    if min(abs(entry - stop_loss), abs(take_profit - entry)) < minimum_distance:
        raise DemoTradeRejected('SL/TP están demasiado cerca según las reglas del símbolo.')

    volume_min = float(symbol_info.volume_min)
    volume_step = float(symbol_info.volume_step)
    volume_max = min(float(symbol_info.volume_max), DEMO_MAX_VOLUME)
    if (
        not all(math.isfinite(value) and value > 0 for value in (volume_min, volume_step, volume_max)) or
        volume_min > volume_max
    ):
        raise DemoTradeRejected('Los límites de volumen del símbolo no son compatibles con la prueba.')

    target_at_minimum = _profit(
        mt5, order_type, normalized_symbol, volume_min, entry, take_profit
    )
    if target_at_minimum <= 0:
        raise DemoTradeRejected('El TP no produce beneficio bruto con el tamaño mínimo.')
    target_goal = (
        min(target_range[1], max(target_range[0], target_at_minimum))
        if target_range else
        target_profit_usd
    )
    raw_volume = max(
        volume_min,
        volume_min * target_goal / target_at_minimum
    )
    steps = math.ceil(max(0.0, raw_volume - volume_min) / volume_step - 1e-12)
    volume = round(volume_min + steps * volume_step, _volume_precision(volume_step))
    if volume > volume_max + 1e-9:
        raise DemoTradeRejected(
            f'No se puede buscar USD {target_goal:.2f} bruto sin superar '
            'el límite de volumen de prueba.'
        )

    tick_size = float(getattr(symbol_info, 'trade_tick_size', 0) or symbol_info.point)
    if tick_size <= 0 or not math.isfinite(tick_size):
        raise DemoTradeRejected('El tamaño mínimo de tick del símbolo no es válido.')
    direction_sign = 1 if is_buy else -1
    available_ticks = math.floor(
        direction_sign * (take_profit - entry) / tick_size + 1e-9
    )
    if available_ticks < 1:
        raise DemoTradeRejected('El TP de la IA no deja espacio para ajustar el objetivo.')

    low_tick = 1
    high_tick = available_ticks
    while low_tick < high_tick:
        middle_tick = (low_tick + high_tick) // 2
        candidate_tp = round(
            entry + direction_sign * middle_tick * tick_size,
            int(symbol_info.digits)
        )
        candidate_profit = _profit(
            mt5, order_type, normalized_symbol, volume, entry, candidate_tp
        )
        if candidate_profit >= target_goal - 1e-8:
            high_tick = middle_tick
        else:
            low_tick = middle_tick + 1
    take_profit = round(
        entry + direction_sign * low_tick * tick_size,
        int(symbol_info.digits)
    )
    if abs(take_profit - entry) < minimum_distance:
        raise DemoTradeRejected('El TP ajustado queda demasiado cerca según MT5.')

    estimated_target = _profit(
        mt5, order_type, normalized_symbol, volume, entry, take_profit
    )
    estimated_stop = _profit(
        mt5, order_type, normalized_symbol, volume, entry, stop_loss
    )
    if estimated_target < target_goal - 1e-6:
        raise DemoTradeRejected(
            f'El beneficio bruto estimado no alcanza USD {target_goal:.2f}.'
        )
    if estimated_stop >= 0 or abs(estimated_stop) > max_loss_usd + 1e-6:
        raise DemoTradeRejected(
            f'El stop estimado excede la pérdida máxima demo de USD {max_loss_usd:.2f}.'
        )

    request = {
        'action': mt5.TRADE_ACTION_DEAL,
        'symbol': normalized_symbol,
        'volume': volume,
        'type': order_type,
        'price': round(entry, int(symbol_info.digits)),
        'sl': stop_loss,
        'tp': take_profit,
        'deviation': 20,
        'magic': DEMO_MAGIC,
        'comment': 'AI demo test',
        'type_time': mt5.ORDER_TIME_GTC
    }
    check_errors = []
    for filling_mode in _candidate_filling_modes(mt5, symbol_info):
        request['type_filling'] = filling_mode
        check = mt5.order_check(request)
        if check is not None and getattr(check, 'retcode', None) == 0:
            return DemoOrderPlan(
                request=dict(request),
                estimated_target_usd=estimated_target,
                estimated_stop_loss_usd=abs(estimated_stop),
                volume=volume,
                entry_price=entry,
                target_goal_usd=target_goal
            )
        check_errors.append(
            getattr(check, 'comment', None) or
            f'retcod={getattr(check, "retcode", "sin respuesta")}'
        )

    raise DemoTradeRejected(
        'MT5 rechazó la comprobación previa de la orden: ' +
        '; '.join(check_errors or ['no hay modo de llenado disponible'])
    )


def send_demo_order(mt5, symbol, plan):
    """Send at most one prepared demo order after repeating account/position guards."""
    _require_demo_permissions(mt5)
    _require_no_existing_orders(mt5, symbol)
    result = mt5.order_send(plan.request)
    if result is None:
        raise DemoTradeRejected(f'MT5 no devolvió resultado de orden: {mt5.last_error()}')
    allowed_retcodes = {
        getattr(mt5, 'TRADE_RETCODE_DONE', 10009),
        getattr(mt5, 'TRADE_RETCODE_DONE_PARTIAL', 10010)
    }
    if getattr(result, 'retcode', None) not in allowed_retcodes:
        raise DemoTradeRejected(
            f'MT5 rechazó la orden demo (retcode={getattr(result, "retcode", None)}, '
            f'comentario={getattr(result, "comment", "")}).'
        )
    return result


def should_close_early_for_reversal(
    profit_usd,
    is_long,
    reversal_direction,
    recent_volatility,
    baseline_volatility,
    min_profit_usd=DEMO_EARLY_CLOSE_PROFIT_USD,
    volatility_multiplier=DEMO_REVERSAL_VOLATILITY_MULTIPLIER
):
    values = (
        profit_usd,
        recent_volatility,
        baseline_volatility,
        min_profit_usd,
        volatility_multiplier
    )
    try:
        profit_usd, recent_volatility, baseline_volatility, min_profit_usd, volatility_multiplier = (
            float(value) for value in values
        )
    except (TypeError, ValueError, OverflowError):
        return False
    if not all(math.isfinite(value) for value in (
        profit_usd, recent_volatility, baseline_volatility,
        min_profit_usd, volatility_multiplier
    )):
        return False
    if (
        profit_usd < min_profit_usd or
        baseline_volatility <= 0 or
        recent_volatility < baseline_volatility * volatility_multiplier
    ):
        return False
    reversal = 'BAJISTA' if is_long else 'ALCISTA'
    return reversal_direction == reversal


def close_demo_position(mt5, position, min_profit_usd=DEMO_EARLY_CLOSE_PROFIT_USD):
    _require_demo_permissions(mt5)
    if int(getattr(position, 'magic', 0)) != DEMO_MAGIC:
        raise DemoTradeRejected('El monitor solo puede cerrar posiciones creadas por este arnés.')

    symbol = str(position.symbol)
    info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)
    if info is None or tick is None:
        raise DemoTradeRejected(f'No hay cotización para cerrar {symbol}.')
    is_long = position.type == getattr(mt5, 'POSITION_TYPE_BUY', 0)
    close_type = mt5.ORDER_TYPE_SELL if is_long else mt5.ORDER_TYPE_BUY
    close_price = float(tick.bid if is_long else tick.ask)
    estimated_profit = _profit(
        mt5,
        position.type,
        symbol,
        float(position.volume),
        float(position.price_open),
        close_price
    )
    if estimated_profit < float(min_profit_usd):
        raise DemoTradeRejected(
            f'No se cerró: PnL bruto estimado ${estimated_profit:.2f} '
            f'es menor al mínimo ${float(min_profit_usd):.2f}.'
        )

    request = {
        'action': mt5.TRADE_ACTION_DEAL,
        'symbol': symbol,
        'volume': float(position.volume),
        'type': close_type,
        'position': int(position.ticket),
        'price': round(close_price, int(info.digits)),
        'deviation': 20,
        'magic': DEMO_MAGIC,
        'comment': 'AI demo reversal exit',
        'type_time': mt5.ORDER_TIME_GTC
    }
    errors = []
    checked = False
    for filling_mode in _candidate_filling_modes(mt5, info):
        request['type_filling'] = filling_mode
        check = mt5.order_check(request)
        if check is not None and getattr(check, 'retcode', None) == 0:
            checked = True
            break
        errors.append(
            getattr(check, 'comment', None) or
            f'retcod={getattr(check, "retcode", "sin respuesta")}'
        )
    if not checked:
        raise DemoTradeRejected(
            'MT5 rechazó la comprobación del cierre: ' +
            '; '.join(errors or ['no hay modo de llenado disponible'])
        )

    result = mt5.order_send(request)
    if result is None:
        raise DemoTradeRejected(f'MT5 no devolvió resultado al cerrar: {mt5.last_error()}')
    if getattr(result, 'retcode', None) != getattr(mt5, 'TRADE_RETCODE_DONE', 10009):
        raise DemoTradeRejected(
            f'MT5 no confirmó el cierre temprano (retcode={getattr(result, "retcode", None)}, '
            f'comentario={getattr(result, "comment", "")}).'
        )
    return result


def monitor_demo_position(
    mt5,
    symbol,
    ticket,
    prediction_engine,
    min_profit_usd=DEMO_EARLY_CLOSE_PROFIT_USD,
    volatility_multiplier=DEMO_REVERSAL_VOLATILITY_MULTIPLIER,
    poll_seconds=5,
    max_wait_seconds=DEMO_MONITOR_MAX_SECONDS
):
    try:
        from .trading_signals import build_experimental_demo_signal
    except ImportError:
        from trading_signals import build_experimental_demo_signal

    normalized_symbol = str(symbol).upper()
    deadline = time.monotonic() + max_wait_seconds
    last_analyzed_bar = None

    while time.monotonic() < deadline:
        _require_demo_permissions(mt5)
        positions = mt5.positions_get(symbol=normalized_symbol)
        if positions is None:
            raise DemoTradeRejected(f'No se pudieron leer posiciones: {mt5.last_error()}')
        position = next(
            (item for item in positions if int(item.ticket) == int(ticket)),
            None
        )
        if position is None:
            return {'status': 'closed_by_server', 'ticket': int(ticket)}
        if int(getattr(position, 'magic', 0)) != DEMO_MAGIC:
            raise DemoTradeRejected('El monitor encontró una posición que no pertenece al arnés.')

        tick = mt5.symbol_info_tick(normalized_symbol)
        rates = mt5.copy_rates_from_pos(
            normalized_symbol, mt5.TIMEFRAME_M1, 0, 80
        )
        if tick is not None and rates is not None and len(rates) >= 40:
            prices = [float(rate['close']) for rate in rates]
            latest_bar_time = int(rates[-1]['time'])
            if (
                0 <= int(tick.time) - latest_bar_time <= DEMO_MAX_BAR_AGE_SECONDS and
                latest_bar_time != last_analyzed_bar
            ):
                last_analyzed_bar = latest_bar_time
                recent_volatility = float(
                    prediction_engine._calculate_atr(prices[-10:])
                )
                baseline_volatility = float(
                    prediction_engine._calculate_atr(prices[-40:-10])
                )
                reversal_signal = build_experimental_demo_signal(
                    prices, periods=15, engine=prediction_engine
                )
                reversal_direction = (
                    reversal_signal.get('direction')
                    if reversal_signal.get('trade_allowed')
                    else 'NEUTRAL'
                )
                is_long = position.type == getattr(mt5, 'POSITION_TYPE_BUY', 0)
                close_price = float(tick.bid if is_long else tick.ask)
                estimated_profit = _profit(
                    mt5,
                    position.type,
                    normalized_symbol,
                    float(position.volume),
                    float(position.price_open),
                    close_price
                )
                if should_close_early_for_reversal(
                    estimated_profit,
                    is_long,
                    reversal_direction,
                    recent_volatility,
                    baseline_volatility,
                    min_profit_usd,
                    volatility_multiplier
                ):
                    result = close_demo_position(
                        mt5, position, min_profit_usd=min_profit_usd
                    )
                    return {
                        'status': 'closed_early_on_reversal',
                        'ticket': int(ticket),
                        'estimated_profit_usd': estimated_profit,
                        'close_order': getattr(result, 'order', 0)
                    }

        time.sleep(max(0.1, float(poll_seconds)))

    positions = mt5.positions_get(symbol=normalized_symbol)
    if positions is None:
        raise DemoTradeRejected(f'No se pudieron leer posiciones al terminar el monitor: {mt5.last_error()}')
    position = next(
        (item for item in positions if int(item.ticket) == int(ticket)),
        None
    )
    if position is None:
        return {'status': 'closed_by_server', 'ticket': int(ticket)}
    return {
        'status': 'still_open_with_server_sl_tp',
        'ticket': int(ticket),
        'profit_usd': float(position.profit),
        'stop_loss': float(position.sl),
        'take_profit': float(position.tp)
    }
