"""Prediction signal assembly shared by the dashboard and demo harness."""

import math

try:
    from .technical_indicators import (
        calculate_bollinger_bands,
        calculate_macd,
        calculate_rsi,
    )
except ImportError:
    from technical_indicators import (
        calculate_bollinger_bands,
        calculate_macd,
        calculate_rsi,
    )


def build_prediction_signal(prices, periods=15, engine=None):
    if engine is None:
        current = float(prices[-1]) if prices else 0.0
        prediction = {
            'current_price': current,
            'predicted_price': current,
            'price_change': 0.0,
            'change_percent': 0.0,
            'direction': 'NEUTRAL',
            'confidence': 0.0,
            'model_agreement': 0.0,
            'expected_high': current,
            'expected_low': current,
            'walk_forward_accuracy': None,
            'walk_forward_samples': 0,
            'confidence_basis': 'model_unavailable'
        }
        levels = {
            'entry': round(current, 6),
            'stop_loss': None,
            'take_profit': None,
            'risk_reward': 0.0,
            'direction': 'NEUTRAL'
        }
        return {
            'signal': 'ESPERA',
            'strength': 0.0,
            'confidence': 0.0,
            'model_agreement': 0.0,
            'confidence_basis': 'model_unavailable',
            'reasons': ['Motor de predicción no disponible'],
            'prediction': prediction,
            'prediction_range': {
                'predicted_price': current,
                'expected_high': current,
                'expected_low': current,
                'confidence': 0.0,
                'direction': 'NEUTRAL',
                'periods': periods,
                'horizon_minutes': periods
            },
            'levels': levels,
            'risk_reward': 0.0,
            'trade_allowed': False,
            'risk_note': (
                'El ratio estimado no incluye spread, comisiones ni '
                'deslizamiento; no garantiza ganancias.'
            )
        }

    rsi = calculate_rsi(prices)
    macd = calculate_macd(prices)['histogram']
    bands = calculate_bollinger_bands(prices)
    trade = engine.get_prediction_signal(
        prices, rsi, macd, bands['upper'], bands['lower'], periods=periods
    )
    prediction = trade['prediction']
    trade['prediction_range'] = {
        'predicted_price': prediction['predicted_price'],
        'expected_high': prediction['expected_high'],
        'expected_low': prediction['expected_low'],
        'confidence': prediction['confidence'],
        'direction': prediction['direction'],
        'volatility': prediction.get('volatility', 0.0),
        'walk_forward_accuracy': prediction.get('walk_forward_accuracy'),
        'walk_forward_samples': prediction.get('walk_forward_samples', 0),
        'periods': prediction.get('periods', periods),
        'horizon_minutes': periods
    }
    return trade


def build_experimental_demo_signal(prices, periods=15, engine=None):
    """Expose raw model direction for an explicitly opted-in demo experiment."""
    signal = build_prediction_signal(prices, periods, engine)
    if signal.get('trade_allowed') or engine is None:
        return signal

    prediction = signal.get('prediction') or {}
    try:
        price_change = float(prediction['price_change'])
        current_price = float(prediction['current_price'])
        predicted_price = float(prediction['predicted_price'])
        model_agreement = float(prediction['model_agreement'])
        walk_forward_samples = int(prediction.get('walk_forward_samples', 0))
        atr = float(engine._calculate_atr([float(price) for price in prices[-50:]]))
    except (KeyError, TypeError, ValueError, OverflowError):
        return signal

    minimum_move = max(atr * 0.25, current_price * 0.0001)
    if (
        not all(math.isfinite(value) for value in (
            price_change, current_price, predicted_price, model_agreement, atr
        )) or
        current_price <= 0 or atr <= 0 or
        model_agreement < 0.75 or
        walk_forward_samples < 8 or
        abs(price_change) < minimum_move
    ):
        return signal

    direction = 'ALCISTA' if price_change > 0 else 'BAJISTA'
    if (direction == 'ALCISTA' and predicted_price <= current_price) or (
        direction == 'BAJISTA' and predicted_price >= current_price
    ):
        return signal

    levels = engine.get_trading_levels(prices, direction, predicted_price)
    if (
        levels.get('direction') != direction or
        levels.get('stop_loss') is None or
        levels.get('take_profit') is None
    ):
        return signal

    experimental = dict(signal)
    experimental_prediction = dict(prediction)
    experimental_prediction['direction'] = direction
    experimental['prediction'] = experimental_prediction
    methods = prediction.get('methods') or {}
    method_prices = []
    for value in methods.values():
        try:
            method_price = float(value)
        except (TypeError, ValueError, OverflowError):
            continue
        if math.isfinite(method_price):
            method_prices.append(method_price)
    up_votes = sum(value > current_price for value in method_prices)
    down_votes = sum(value < current_price for value in method_prices)
    dominant_direction = (
        'ALCISTA' if up_votes > down_votes else
        'BAJISTA' if down_votes > up_votes else
        None
    )
    conflicts = (
        [f'La dirección ponderada {direction} contradice los votos componentes {dominant_direction}.']
        if dominant_direction and dominant_direction != direction else
        []
    )
    experimental['signal'] = 'COMPRA' if direction == 'ALCISTA' else 'VENTA'
    experimental['trade_allowed'] = True
    experimental['experimental_demo_only'] = True
    experimental['direction'] = direction
    experimental['model_agreement'] = model_agreement
    experimental['entry'] = levels['entry']
    experimental['stop_loss'] = levels['stop_loss']
    experimental['take_profit'] = levels['take_profit']
    experimental['levels'] = levels
    experimental['risk_reward'] = levels['risk_reward']
    experimental['confidence_basis'] = 'unvalidated_raw_model_direction'
    experimental['experimental_conflicts'] = conflicts
    experimental_range = dict(experimental.get('prediction_range') or {})
    experimental_range['direction'] = direction
    experimental['prediction_range'] = experimental_range
    experimental['reasons'] = [
        'Prueba demo experimental: dirección cruda, sin validación del filtro habitual.',
        *conflicts
    ]
    return experimental
