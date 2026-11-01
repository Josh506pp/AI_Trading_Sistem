"""Reusable technical indicators for prediction and analysis workflows."""


def calculate_rsi(prices, period=14):
    """Calcula RSI (Índice de Fuerza Relativa)."""
    if len(prices) <= period:
        return 50

    deltas = [prices[index] - prices[index - 1] for index in range(1, len(prices))]
    recent = deltas[-period:]
    up = sum(delta for delta in recent if delta > 0) / period
    down = sum(-delta for delta in recent if delta < 0) / period
    if down == 0:
        return 100.0 if up > 0 else 50.0
    relative_strength = up / down
    return 100 - (100 / (1 + relative_strength))


def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calcula MACD (Moving Average Convergence Divergence)."""
    if len(prices) < slow:
        return {'macd': 0, 'signal': 0, 'histogram': 0}

    def ema_series(values, period):
        multiplier = 2 / (period + 1)
        ema = float(values[0])
        result = [ema]
        for value in values[1:]:
            ema = float(value) * multiplier + ema * (1 - multiplier)
            result.append(ema)
        return result

    fast_ema = ema_series(prices, fast)
    slow_ema = ema_series(prices, slow)
    macd_series = [
        fast_value - slow_value
        for fast_value, slow_value in zip(fast_ema, slow_ema)
    ]
    macd = macd_series[-1]
    signal_line = ema_series(macd_series, signal)[-1]
    return {
        'macd': macd,
        'signal': signal_line,
        'histogram': macd - signal_line
    }


def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """Calcula Bandas de Bollinger."""
    if len(prices) < period:
        return {'upper': 0, 'middle': 0, 'lower': 0}

    recent = prices[-period:]
    middle = sum(recent) / len(recent)
    variance = sum((value - middle) ** 2 for value in recent) / len(recent)
    standard_deviation = variance ** 0.5
    return {
        'upper': middle + standard_deviation * std_dev,
        'middle': middle,
        'lower': middle - standard_deviation * std_dev
    }
