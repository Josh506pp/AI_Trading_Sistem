"""Prediction signal assembly shared by the dashboard and demo harness."""

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
