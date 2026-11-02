"""
SISTEMA DE PREDICCIONES - Pronósticos de precios y señales de trading
Utiliza series temporales, análisis técnico y machine learning para predecir movimientos
"""

import numpy as np
from typing import Dict, List, Tuple
import json
import math

MIN_WALK_FORWARD_ACCURACY = 0.55
DEFAULT_STOP_ATR_MULTIPLE = 2.0
BASE_MODEL_WEIGHTS = {
    'ema': 0.30,
    'linear': 0.25,
    'momentum': 0.25,
    'volatility': 0.20
}
MIN_MODEL_LEARNING_SAMPLES = 8


class PredictionEngine:
    """Motor de predicciones para análisis técnico y pronósticos de precios"""
    
    def __init__(self):
        self.historical_predictions = []
        self.accuracy_score = 0.0
        self.prediction_history = []
        self.model_weights = dict(BASE_MODEL_WEIGHTS)
        self.model_performance = {}
        self.adaptive_walk_forward_accuracy = None
        self.adaptive_walk_forward_samples = 0
        
    def predict_next_price(self, prices: List[float], periods: int = 5) -> Dict:
        """
        Predice el próximo movimiento de precio usando múltiples técnicas
        
        Args:
            prices: Histórico de precios
            periods: Períodos a predecir (default 5)
        
        Returns:
            Diccionario con predicción, dirección y probabilidades
        """
        clean_prices = [float(price) for price in prices if math.isfinite(float(price)) and float(price) > 0]
        if len(clean_prices) < 10:
            current_price = clean_prices[-1] if clean_prices else 0.0
            return {
                'current_price': current_price,
                'predicted_price': current_price,
                'price_change': 0.0,
                'change_percent': 0.0,
                'direction': 'NEUTRAL',
                'confidence': 0.0,
                'model_agreement': 0.0,
                'confidence_basis': 'model_agreement_not_probability',
                'expected_high': current_price,
                'expected_low': current_price,
                'volatility': 0.0,
                'walk_forward_accuracy': None,
                'walk_forward_samples': 0,
                'adaptive_walk_forward_accuracy': None,
                'adaptive_walk_forward_samples': 0,
                'effective_walk_forward_accuracy': None,
                'model_performance': {},
                'model_weights': dict(BASE_MODEL_WEIGHTS),
                'method': 'insufficient_data'
            }
        
        # Método 1: Moving Average Exponencial
        ema_prediction = self._ema_prediction(clean_prices, periods)
        
        # Método 2: Regresión Lineal Simple
        linear_prediction = self._linear_regression_prediction(clean_prices, periods)
        
        # Método 3: Momentum y Tendencia
        momentum_prediction = self._momentum_prediction(clean_prices, periods)
        
        # Método 4: Volatilidad Media
        volatility_prediction = self._volatility_adjusted_prediction(clean_prices, periods)
        model_prices = {
            'ema': float(ema_prediction['price']),
            'linear': float(linear_prediction['price']),
            'momentum': float(momentum_prediction['price']),
            'volatility': float(volatility_prediction['price']),
        }

        self.model_performance = {
            name: {'accuracy': None, 'samples': 0, 'correct': 0}
            for name in BASE_MODEL_WEIGHTS
        }
        self.model_weights = dict(BASE_MODEL_WEIGHTS)
        self.adaptive_walk_forward_accuracy = None
        self.adaptive_walk_forward_samples = 0
        walk_forward_accuracy, walk_forward_samples = self._walk_forward_accuracy(
            clean_prices, periods
        )
        self.model_weights = self._adaptive_model_weights(
            self.model_performance
        )
        effective_walk_forward_accuracy = (
            self.adaptive_walk_forward_accuracy
            if self.adaptive_walk_forward_samples >= MIN_MODEL_LEARNING_SAMPLES
            else walk_forward_accuracy
        )

        final_prediction = float(
            sum(model_prices[name] * self.model_weights[name] for name in BASE_MODEL_WEIGHTS)
        )
        
        current_price = clean_prices[-1]
        price_change = final_prediction - current_price
        change_percent = (price_change / current_price * 100) if current_price != 0 else 0
        up_votes = sum(price > current_price for price in model_prices.values())
        down_votes = sum(price < current_price for price in model_prices.values())
        model_agreement = max(up_votes, down_votes) / len(model_prices)
        atr = self._calculate_atr(clean_prices[-50:])
        minimum_move = max(atr * 0.25, current_price * 0.0001)
        
        votes_match_forecast = (
            (up_votes >= 3 and price_change > 0) or
            (down_votes >= 3 and price_change < 0)
        )
        backtest_rejects_signal = (
            walk_forward_samples >= 8 and
            effective_walk_forward_accuracy is not None and
            effective_walk_forward_accuracy < MIN_WALK_FORWARD_ACCURACY
        )
        if (
            abs(price_change) < minimum_move or model_agreement < 0.75 or
            not votes_match_forecast or backtest_rejects_signal
        ):
            direction = 'NEUTRAL'
            confidence = 0.0
        elif price_change > 0:
            direction = 'ALCISTA'
            confidence = min(0.90, model_agreement)
        else:
            direction = 'BAJISTA'
            confidence = min(0.90, model_agreement)

        recent_returns = np.diff(clean_prices[-31:]) / np.array(clean_prices[-31:-1])
        volatility = float(np.std(recent_returns)) if len(recent_returns) else 0.0
        range_margin = max(
            current_price * volatility * math.sqrt(periods),
            atr * math.sqrt(periods)
        )
        
        return {
            'current_price': current_price,
            'predicted_price': final_prediction,
            'expected_high': round(final_prediction + range_margin, 6),
            'expected_low': round(max(0.0, final_prediction - range_margin), 6),
            'volatility': round(volatility * 100, 4),
            'price_change': round(float(price_change), 6),
            'change_percent': round(float(change_percent), 4),
            'direction': direction,
            'confidence': round(confidence, 2),
            'model_agreement': round(model_agreement, 2),
            'walk_forward_accuracy': (
                round(walk_forward_accuracy, 3) if walk_forward_accuracy is not None else None
            ),
            'walk_forward_samples': walk_forward_samples,
            'adaptive_walk_forward_accuracy': (
                round(self.adaptive_walk_forward_accuracy, 3)
                if self.adaptive_walk_forward_accuracy is not None else None
            ),
            'adaptive_walk_forward_samples': self.adaptive_walk_forward_samples,
            'effective_walk_forward_accuracy': (
                round(effective_walk_forward_accuracy, 3)
                if effective_walk_forward_accuracy is not None else None
            ),
            'model_performance': {
                name: {
                    'accuracy': (
                        round(metrics['accuracy'], 3)
                        if metrics['accuracy'] is not None else None
                    ),
                    'samples': metrics['samples']
                }
                for name, metrics in self.model_performance.items()
            },
            'model_weights': {
                name: round(weight, 6)
                for name, weight in self.model_weights.items()
            },
            'confidence_basis': 'model_agreement_not_probability',
            'learning_basis': 'expanding_walk_forward_market_history',
            'methods': {name: round(price, 6) for name, price in model_prices.items()},
            'periods': periods,
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }

    @staticmethod
    def _adaptive_model_weights(model_performance):
        weighted = {}
        for name, base_weight in BASE_MODEL_WEIGHTS.items():
            metrics = model_performance.get(name, {})
            samples = int(metrics.get('samples', 0))
            if samples < MIN_MODEL_LEARNING_SAMPLES:
                multiplier = 1.0
            else:
                correct = int(metrics.get('correct', 0))
                smoothed_accuracy = (correct + 4.0) / (samples + 8.0)
                multiplier = max(
                    0.5,
                    min(1.5, 1.0 + 4.0 * (smoothed_accuracy - 0.5))
                )
            weighted[name] = base_weight * multiplier
        total = sum(weighted.values())
        return {name: weight / total for name, weight in weighted.items()}

    def _walk_forward_accuracy(self, prices: List[float], periods: int, max_windows: int = 40):
        model_correct = {name: 0 for name in BASE_MODEL_WEIGHTS}
        model_samples = {name: 0 for name in BASE_MODEL_WEIGHTS}
        self.model_performance = {
            name: {'accuracy': None, 'samples': 0, 'correct': 0}
            for name in BASE_MODEL_WEIGHTS
        }
        self.model_weights = dict(BASE_MODEL_WEIGHTS)
        self.adaptive_walk_forward_accuracy = None
        self.adaptive_walk_forward_samples = 0
        if len(prices) < 40:
            return None, 0

        start = max(30, len(prices) - max_windows - periods)
        correct = 0
        samples = 0
        adaptive_correct = 0
        adaptive_samples = 0
        for index in range(start, len(prices) - periods):
            history = prices[:index]
            forecasts = {
                'ema': self._ema_prediction(history, periods)['price'],
                'linear': self._linear_regression_prediction(history, periods)['price'],
                'momentum': self._momentum_prediction(history, periods)['price'],
                'volatility': self._volatility_adjusted_prediction(history, periods)['price']
            }
            current = history[-1]
            atr = self._calculate_atr(history[-50:])
            base_forecast = sum(
                forecasts[name] * BASE_MODEL_WEIGHTS[name]
                for name in BASE_MODEL_WEIGHTS
            )
            minimum_move = max(atr * 0.25, current * 0.0001)
            if abs(base_forecast - current) < minimum_move:
                continue
            actual_change = prices[index + periods] - current
            samples += 1
            if (base_forecast - current) * actual_change > 0:
                correct += 1
            adaptive_weights = self._adaptive_model_weights({
                name: {
                    'correct': model_correct[name],
                    'samples': model_samples[name]
                }
                for name in BASE_MODEL_WEIGHTS
            })
            adaptive_forecast = sum(
                forecasts[name] * adaptive_weights[name]
                for name in BASE_MODEL_WEIGHTS
            )
            adaptive_samples += 1
            if (adaptive_forecast - current) * actual_change > 0:
                adaptive_correct += 1
            for name, forecast in forecasts.items():
                if abs(forecast - current) < minimum_move:
                    continue
                model_samples[name] += 1
                if (forecast - current) * actual_change > 0:
                    model_correct[name] += 1

        self.model_performance = {
            name: {
                'accuracy': (
                    model_correct[name] / model_samples[name]
                    if model_samples[name] else None
                ),
                'samples': model_samples[name],
                'correct': model_correct[name]
            }
            for name in BASE_MODEL_WEIGHTS
        }
        self.model_weights = self._adaptive_model_weights(self.model_performance)
        self.adaptive_walk_forward_accuracy = (
            adaptive_correct / adaptive_samples if adaptive_samples else None
        )
        self.adaptive_walk_forward_samples = adaptive_samples

        return (correct / samples, samples) if samples else (None, 0)
    
    def _ema_prediction(self, prices: List[float], periods: int) -> Dict:
        """Predicción usando Media Móvil Exponencial"""
        if len(prices) < 2:
            return {'price': prices[-1] if prices else 0}
        
        period = min(12, len(prices))
        alpha = 2 / (period + 1)
        ema = float(prices[0])
        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema
        
        slope_window = min(6, len(prices))
        trend_per_period = (prices[-1] - prices[-slope_window]) / (slope_window - 1)
        predicted = prices[-1] + trend_per_period * periods * 0.5
        
        return {'price': predicted}
    
    def _linear_regression_prediction(self, prices: List[float], periods: int) -> Dict:
        """Predicción usando regresión lineal simple"""
        recent_prices = prices[-30:]
        n = len(recent_prices)
        x = np.arange(n)
        y = np.array(recent_prices)
        
        # Calcular regresión lineal
        x_mean = np.mean(x)
        y_mean = np.mean(y)
        
        numerator = np.sum((x - x_mean) * (y - y_mean))
        denominator = np.sum((x - x_mean) ** 2)
        
        slope = numerator / denominator if denominator != 0 else 0
        intercept = y_mean - slope * x_mean
        
        # Predecir en el futuro
        future_x = n + periods
        predicted_price = slope * future_x + intercept
        
        return {'price': predicted_price}
    
    def _momentum_prediction(self, prices: List[float], periods: int) -> Dict:
        """Predicción basada en momentum"""
        if len(prices) < 5:
            return {'price': prices[-1]}
        
        # Momentum actual = precio actual - precio hace 5 períodos
        window = min(5, len(prices) - 1)
        momentum = prices[-1] - prices[-window - 1]
        predicted = prices[-1] + (momentum * periods / window)
        
        return {'price': predicted}
    
    def _volatility_adjusted_prediction(self, prices: List[float], periods: int) -> Dict:
        """Predicción ajustada por volatilidad"""
        if len(prices) < 2:
            return {'price': prices[-1]}
        
        window = min(10, len(prices) - 1)
        recent_trend = prices[-1] - prices[-window - 1]
        trend_per_period = recent_trend / window
        atr = self._calculate_atr(prices[-window - 1:])
        movement_limit = atr * math.sqrt(max(periods, 1)) * 1.5
        movement = max(-movement_limit, min(movement_limit, trend_per_period * periods))
        predicted = prices[-1] + movement
        
        return {'price': predicted}
    
    def get_trading_levels(self, prices: List[float], direction: str = 'NEUTRAL',
                           target_price: float = None,
                           stop_atr_multiple: float = DEFAULT_STOP_ATR_MULTIPLE) -> Dict:
        """
        Calcula niveles clave de soporte y resistencia para operaciones
        
        Returns:
            Diccionario con support, resistance, entry, stop loss, take profit
        """
        clean_prices = [float(price) for price in prices if math.isfinite(float(price)) and float(price) > 0]
        if len(clean_prices) < 10:
            return {
                'support': 0,
                'resistance': 0,
                'entry': 0,
                'stop_loss': None,
                'take_profit': None,
                'risk_reward': 0.0,
                'direction': 'NEUTRAL'
            }
        
        # Usar últimos 50 precios
        recent_prices = clean_prices[-50:]
        
        high = max(recent_prices)
        low = min(recent_prices)
        current = recent_prices[-1]
        
        # Pivot Points (clásico)
        pivot = (high + low + current) / 3
        resistance1 = (2 * pivot) - low
        support1 = (2 * pivot) - high
        
        # Stop based on recent volatility; target follows the forecast.
        atr = float(self._calculate_atr(recent_prices))
        normalized_direction = direction.upper()
        is_long = normalized_direction in ('ALCISTA', 'COMPRA', 'COMPRA_FUERTE', 'LONG')
        is_short = normalized_direction in ('BAJISTA', 'VENTA', 'VENTA_FUERTE', 'SHORT')
        entry = current
        stop_loss = None
        take_profit = None
        risk_reward = 0.0

        try:
            stop_atr_multiple = float(stop_atr_multiple)
        except (TypeError, ValueError, OverflowError):
            raise ValueError('stop_atr_multiple debe ser un número positivo.')
        if not math.isfinite(stop_atr_multiple) or stop_atr_multiple <= 0:
            raise ValueError('stop_atr_multiple debe ser un número positivo.')

        if atr > 0 and (is_long or is_short):
            stop_distance = atr * stop_atr_multiple
            stop_loss = entry - stop_distance if is_long else entry + stop_distance
            forecast_target = float(target_price) if target_price is not None else entry + (2 * atr if is_long else -2 * atr)
            target_is_valid = forecast_target > entry if is_long else forecast_target < entry
            if target_is_valid:
                take_profit = forecast_target
                risk_reward = float(abs(take_profit - entry) / atr)
            else:
                stop_loss = None
                normalized_direction = 'NEUTRAL'
        else:
            normalized_direction = 'NEUTRAL'
        
        return {
            'support': round(support1, 6),
            'support2': round(low, 6),
            'resistance': round(resistance1, 6),
            'resistance2': round(high, 6),
            'pivot': round(pivot, 6),
            'entry': round(entry, 6),
            'stop_loss': round(stop_loss, 6) if stop_loss is not None else None,
            'take_profit': round(take_profit, 6) if take_profit is not None else None,
            'current_price': round(current, 6),
            'risk_reward': round(risk_reward, 2),
            'direction': normalized_direction,
            'stop_atr_multiple': stop_atr_multiple
        }
    
    def _calculate_atr(self, prices: List[float], period: int = 14) -> float:
        """Calcula el Average True Range"""
        if len(prices) < 2:
            return 0.001
        
        true_ranges = []
        for i in range(1, len(prices)):
            high_low = abs(prices[i] - prices[i-1])
            true_ranges.append(high_low)
        
        atr = float(np.mean(true_ranges[-period:])) if true_ranges else 0.0
        return atr
    
    def predict_price_range(self, prices: List[float], periods: int = 5) -> Dict:
        """
        Predice el rango de precios (máximo y mínimo esperado)
        
        Args:
            prices: Histórico de precios
            periods: Períodos a predecir
        
        Returns:
            Rango esperado con máximo y mínimo
        """
        prediction = self.predict_next_price(prices, periods)
        returns = np.diff(prices[-31:]) / np.array(prices[-31:-1]) if len(prices) > 1 else [0]
        volatility = float(np.std(returns)) if len(returns) > 0 else 0.0
        return {
            'predicted_price': prediction['predicted_price'],
            'expected_high': prediction['expected_high'],
            'expected_low': prediction['expected_low'],
            'confidence': prediction['confidence'],
            'direction': prediction['direction'],
            'volatility': round(volatility * 100, 2),
            'walk_forward_accuracy': prediction['walk_forward_accuracy'],
            'walk_forward_samples': prediction['walk_forward_samples'],
            'periods': periods
        }
    
    def get_prediction_signal(self, prices: List[float], rsi: float,
                             macd: float, bb_high: float, bb_low: float,
                             periods: int = 5) -> Dict:
        """
        Combina predicción con indicadores técnicos para generar señal
        
        Args:
            prices: Histórico de precios
            rsi: Valor de RSI
            macd: Valor de MACD
            bb_high: Banda de Bollinger superior
            bb_low: Banda de Bollinger inferior
        
        Returns:
            Señal de trading combinada
        """
        prediction = self.predict_next_price(prices, periods=periods)
        
        if len(prices) < 10 or prediction['direction'] == 'NEUTRAL':
            reasons = ['Modelos sin consenso suficiente']
            validation_accuracy = prediction.get(
                'effective_walk_forward_accuracy',
                prediction.get('walk_forward_accuracy')
            )
            if (
                prediction.get('walk_forward_samples', 0) >= 8 and
                validation_accuracy is not None
            ):
                if validation_accuracy < MIN_WALK_FORWARD_ACCURACY:
                    reasons = [
                        'El backtest direccional reciente no alcanza el '
                        f'{MIN_WALK_FORWARD_ACCURACY:.0%} de aciertos'
                    ]
            return self._no_trade_signal(prediction, prices, reasons)

        current = float(prices[-1])
        predicted = prediction['predicted_price']
        direction = prediction['direction']
        is_long = direction == 'ALCISTA'
        atr = self._calculate_atr([float(price) for price in prices[-50:]])
        levels = self.get_trading_levels(prices, direction, predicted)
        reasons = []

        if atr <= 0 or levels['risk_reward'] < 2.0:
            reasons.append('Movimiento previsto menor al mínimo riesgo/beneficio de 2:1')
        if prediction['confidence'] < 0.75:
            reasons.append('Consenso de modelos inferior al 75%')

        fast_trend = np.mean(prices[-12:])
        slow_trend = np.mean(prices[-26:])
        if (is_long and (fast_trend <= slow_trend or macd <= 0 or rsi >= 85 or current > bb_high + atr * 0.5)) or (
            not is_long and (fast_trend >= slow_trend or macd >= 0 or rsi <= 15 or current < bb_low - atr * 0.5)
        ):
            reasons.append('Los indicadores de tendencia y momentum no confirman la entrada')

        can_trade = bool(not reasons and levels['risk_reward'] >= 2.0)
        signal = ('COMPRA' if is_long else 'VENTA') if can_trade else 'ESPERA'
        if not can_trade:
            levels = self.get_trading_levels(prices)
            levels['entry'] = round(current, 6)
            levels['direction'] = 'NEUTRAL'
            if not reasons:
                reasons.append('Sin ventaja suficiente para abrir una operación')
        else:
            reasons.append('Consenso direccional e indicadores alineados; riesgo/beneficio mínimo 2:1')
        
        return {
            'signal': signal,
            'strength': round(prediction['confidence'] * 100, 2) if can_trade else 0.0,
            'color': 'green' if signal == 'COMPRA' else 'red' if signal == 'VENTA' else 'yellow',
            'confidence': prediction['confidence'] if can_trade else 0.0,
            'model_agreement': prediction['model_agreement'],
            'confidence_basis': prediction['confidence_basis'],
            'reasons': reasons,
            'levels': levels,
            'risk_reward': levels['risk_reward'],
            'prediction': prediction,
            'entry': levels['entry'],
            'stop_loss': levels['stop_loss'],
            'take_profit': levels['take_profit'],
            'predicted_price': predicted,
            'direction': direction if can_trade else 'NEUTRAL',
            'trade_allowed': can_trade,
            'risk_note': 'El ratio es estimado y no incluye spread, comisiones ni deslizamiento; no garantiza ganancias.'
        }

    def _no_trade_signal(self, prediction: Dict, prices: List[float], reasons: List[str]) -> Dict:
        current = float(prices[-1]) if prices else 0.0
        levels = self.get_trading_levels(prices)
        levels['entry'] = round(current, 6)
        return {
            'signal': 'ESPERA',
            'strength': 0.0,
            'color': 'yellow',
            'confidence': 0.0,
            'model_agreement': prediction.get('model_agreement', 0.0),
            'confidence_basis': prediction.get('confidence_basis', 'model_agreement_not_probability'),
            'reasons': reasons,
            'levels': levels,
            'risk_reward': 0.0,
            'prediction': prediction,
            'entry': levels['entry'],
            'stop_loss': None,
            'take_profit': None,
            'predicted_price': prediction.get('predicted_price', current),
            'direction': 'NEUTRAL',
            'trade_allowed': False,
            'risk_note': 'El ratio es estimado y no incluye spread, comisiones ni deslizamiento; no garantiza ganancias.'
        }
    
    def update_accuracy(self, actual_direction: str, predicted_direction: str) -> None:
        """Actualiza la precisión del modelo basado en resultados reales"""
        if actual_direction == predicted_direction:
            self.accuracy_score += 1
        
        total = len(self.prediction_history) + 1
        self.accuracy_score = self.accuracy_score / total if total > 0 else 0


# Instancia global del motor de predicciones
prediction_engine = PredictionEngine()
