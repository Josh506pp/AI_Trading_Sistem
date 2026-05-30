"""
SISTEMA DE PREDICCIONES - Pronósticos de precios y señales de trading
Utiliza series temporales, análisis técnico y machine learning para predecir movimientos
"""

import numpy as np
from typing import Dict, List, Tuple
import json


class PredictionEngine:
    """Motor de predicciones para análisis técnico y pronósticos de precios"""
    
    def __init__(self):
        self.historical_predictions = []
        self.accuracy_score = 0.0
        self.prediction_history = []
        
    def predict_next_price(self, prices: List[float], periods: int = 5) -> Dict:
        """
        Predice el próximo movimiento de precio usando múltiples técnicas
        
        Args:
            prices: Histórico de precios
            periods: Períodos a predecir (default 5)
        
        Returns:
            Diccionario con predicción, dirección y probabilidades
        """
        if len(prices) < 10:
            return {
                'prediction': prices[-1] if prices else 0,
                'direction': 'NEUTRAL',
                'confidence': 0.0,
                'method': 'insufficient_data'
            }
        
        # Método 1: Moving Average Exponencial
        ema_prediction = self._ema_prediction(prices, periods)
        
        # Método 2: Regresión Lineal Simple
        linear_prediction = self._linear_regression_prediction(prices, periods)
        
        # Método 3: Momentum y Tendencia
        momentum_prediction = self._momentum_prediction(prices, periods)
        
        # Método 4: Volatilidad Media
        volatility_prediction = self._volatility_adjusted_prediction(prices, periods)
        
        # Combinar predicciones (promedio ponderado)
        final_prediction = (
            ema_prediction['price'] * 0.30 +
            linear_prediction['price'] * 0.25 +
            momentum_prediction['price'] * 0.25 +
            volatility_prediction['price'] * 0.20
        )
        
        current_price = prices[-1]
        price_change = final_prediction - current_price
        change_percent = (price_change / current_price * 100) if current_price != 0 else 0
        
        # Determinar dirección
        if abs(change_percent) < 0.05:
            direction = 'LATERAL'
            confidence = 0.55
        elif change_percent > 0.05:
            direction = 'ALCISTA'
            confidence = min(0.95, 0.60 + (abs(change_percent) / 2))
        else:
            direction = 'BAJISTA'
            confidence = min(0.95, 0.60 + (abs(change_percent) / 2))
        
        return {
            'current_price': current_price,
            'predicted_price': final_prediction,
            'price_change': round(price_change, 6),
            'change_percent': round(change_percent, 2),
            'direction': direction,
            'confidence': round(min(confidence, 0.95), 2),
            'methods': {
                'ema': round(ema_prediction['price'], 6),
                'linear': round(linear_prediction['price'], 6),
                'momentum': round(momentum_prediction['price'], 6),
                'volatility': round(volatility_prediction['price'], 6),
            },
            'periods': periods,
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }
    
    def _ema_prediction(self, prices: List[float], periods: int) -> Dict:
        """Predicción usando Media Móvil Exponencial"""
        if len(prices) < 2:
            return {'price': prices[-1] if prices else 0}
        
        alpha = 2 / (len(prices) + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema
        
        # Extrapolación: asumir que la tendencia EMA continúa
        last_change = prices[-1] - prices[-2]
        predicted = ema + (last_change * periods * 0.1)
        
        return {'price': predicted}
    
    def _linear_regression_prediction(self, prices: List[float], periods: int) -> Dict:
        """Predicción usando regresión lineal simple"""
        n = len(prices)
        x = np.arange(n)
        y = np.array(prices)
        
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
        momentum = prices[-1] - prices[-5]
        
        # Asumir que el momentum continúa
        predicted = prices[-1] + (momentum * periods / 5)
        
        return {'price': predicted}
    
    def _volatility_adjusted_prediction(self, prices: List[float], periods: int) -> Dict:
        """Predicción ajustada por volatilidad"""
        if len(prices) < 2:
            return {'price': prices[-1]}
        
        # Calcular volatilidad
        returns = np.diff(prices) / prices[:-1]
        volatility = np.std(returns)
        
        # Predicción base = último precio
        base_price = prices[-1]
        
        # Trend = cambio reciente
        recent_trend = prices[-1] - prices[-10] if len(prices) >= 10 else prices[-1] - prices[0]
        
        # Predicción final = base + trend ajustado por volatilidad
        trend_strength = min(abs(recent_trend) * periods, base_price * 0.02)
        direction = 1 if recent_trend > 0 else -1
        predicted = base_price + (direction * trend_strength)
        
        return {'price': predicted}
    
    def get_trading_levels(self, prices: List[float]) -> Dict:
        """
        Calcula niveles clave de soporte y resistencia para operaciones
        
        Returns:
            Diccionario con support, resistance, entry, stop loss, take profit
        """
        if len(prices) < 10:
            return {
                'support': 0,
                'resistance': 0,
                'entry': 0,
                'stop_loss': 0,
                'take_profit': 0
            }
        
        # Usar últimos 50 precios
        recent_prices = prices[-50:]
        
        high = max(recent_prices)
        low = min(recent_prices)
        current = recent_prices[-1]
        
        # Pivot Points (clásico)
        pivot = (high + low + current) / 3
        resistance1 = (2 * pivot) - low
        support1 = (2 * pivot) - high
        
        # ATR para stop loss y take profit
        atr = self._calculate_atr(recent_prices)
        
        # Determinar entry según la tendencia
        if current > pivot:
            entry = support1
            stop_loss = entry - atr
            take_profit = entry + (atr * 2)
        else:
            entry = resistance1
            stop_loss = entry + atr
            take_profit = entry - (atr * 2)
        
        return {
            'support': round(support1, 6),
            'support2': round(low, 6),
            'resistance': round(resistance1, 6),
            'resistance2': round(high, 6),
            'pivot': round(pivot, 6),
            'entry': round(entry, 6),
            'stop_loss': round(stop_loss, 6),
            'take_profit': round(take_profit, 6),
            'current_price': round(current, 6)
        }
    
    def _calculate_atr(self, prices: List[float], period: int = 14) -> float:
        """Calcula el Average True Range"""
        if len(prices) < 2:
            return 0.001
        
        true_ranges = []
        for i in range(1, len(prices)):
            high_low = abs(prices[i] - prices[i-1])
            true_ranges.append(high_low)
        
        atr = np.mean(true_ranges) if true_ranges else 0.001
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
        
        # Calcular volatilidad para determinar el rango
        returns = np.diff(prices) / prices[:-1] if len(prices) > 1 else [0]
        volatility = np.std(returns) if len(returns) > 0 else 0.001
        
        predicted_price = prediction['predicted_price']
        current_price = prices[-1]
        
        # El rango se expande con la volatilidad
        margin = current_price * (volatility * periods * 10)
        margin = max(margin, current_price * 0.001)  # Mínimo 0.1%
        
        return {
            'predicted_price': round(predicted_price, 6),
            'expected_high': round(predicted_price + margin, 6),
            'expected_low': round(predicted_price - margin, 6),
            'confidence': prediction['confidence'],
            'direction': prediction['direction'],
            'volatility': round(volatility * 100, 2),
            'periods': periods
        }
    
    def get_prediction_signal(self, prices: List[float], rsi: float, 
                             macd: float, bb_high: float, bb_low: float) -> Dict:
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
        prediction = self.predict_next_price(prices, periods=5)
        levels = self.get_trading_levels(prices)
        
        current = prices[-1]
        predicted = prediction['predicted_price']
        
        # Score basado en múltiples factores
        score = 0.0
        reasons = []
        
        # Factor 1: Predicción
        if prediction['direction'] == 'ALCISTA':
            score += prediction['confidence'] * 30
            reasons.append(f"Predicción alcista con {int(prediction['confidence']*100)}% confianza")
        elif prediction['direction'] == 'BAJISTA':
            score -= prediction['confidence'] * 30
            reasons.append(f"Predicción bajista con {int(prediction['confidence']*100)}% confianza")
        
        # Factor 2: RSI
        if rsi < 30:
            score += (30 - rsi) / 30 * 20
            reasons.append(f"RSI sobreventa ({int(rsi)})")
        elif rsi > 70:
            score -= (rsi - 70) / 30 * 20
            reasons.append(f"RSI sobrecompra ({int(rsi)})")
        
        # Factor 3: MACD
        if macd > 0:
            score += abs(macd) * 20
            reasons.append("MACD positivo (bullish)")
        else:
            score -= abs(macd) * 20
            reasons.append("MACD negativo (bearish)")
        
        # Factor 4: Bandas de Bollinger
        if current > bb_high:
            score -= 15
            reasons.append("Precio por encima de banda superior")
        elif current < bb_low:
            score += 15
            reasons.append("Precio por debajo de banda inferior")
        
        # Normalizar score
        signal_strength = max(-100, min(100, score))
        
        # Determinar señal
        if signal_strength > 40:
            signal = 'COMPRA_FUERTE'
            color = 'green'
        elif signal_strength > 15:
            signal = 'COMPRA'
            color = 'lightgreen'
        elif signal_strength < -40:
            signal = 'VENTA_FUERTE'
            color = 'red'
        elif signal_strength < -15:
            signal = 'VENTA'
            color = 'lightcoral'
        else:
            signal = 'NEUTRAL'
            color = 'yellow'
        
        return {
            'signal': signal,
            'strength': round(signal_strength, 2),
            'color': color,
            'confidence': round(abs(signal_strength) / 100, 2),
            'reasons': reasons,
            'entry': levels['entry'],
            'stop_loss': levels['stop_loss'],
            'take_profit': levels['take_profit'],
            'predicted_price': predicted,
            'direction': prediction['direction']
        }
    
    def update_accuracy(self, actual_direction: str, predicted_direction: str) -> None:
        """Actualiza la precisión del modelo basado en resultados reales"""
        if actual_direction == predicted_direction:
            self.accuracy_score += 1
        
        total = len(self.prediction_history) + 1
        self.accuracy_score = self.accuracy_score / total if total > 0 else 0


# Instancia global del motor de predicciones
prediction_engine = PredictionEngine()
