#!/usr/bin/env python3
"""
Analizador Inteligente de Precios
Selecciona precios relevantes en lugar de todos los disponibles
Detecta soporte/resistencia, volatilidad, tendencias
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURACIÓN
# =============================================================================
DEFAULT_PRICE_WINDOW = 100  # Cantidad de precios a analizar
SUPPORT_RESISTANCE_WINDOW = 20  # Ventana para S/R local
VOLATILITY_WINDOW = 30
TREND_DETECTION_WINDOW = 50


# =============================================================================
# DATA STRUCTURES
# =============================================================================
@dataclass
class PriceAnalysisResult:
    """Resultado del análisis de precios"""
    most_recent: np.ndarray
    support_levels: List[Tuple[int, float]]
    resistance_levels: List[Tuple[int, float]]
    current_volatility: float
    avg_volatility: float
    volatility_status: str  # 'LOW', 'NORMAL', 'HIGH'
    trend_direction: int  # 1 = UP, -1 = DOWN, 0 = NEUTRAL
    trend_strength: float  # 0-1
    breakpoints: List[int]
    selected_count: int
    total_analyzed: int


@dataclass
class TechnicalFeatures:
    """Features técnicos extraídos"""
    trend_strength: float  # Cuán fuerte es la tendencia (-1 a +1)
    sma_crossover: int  # 1 = alcista, -1 = bajista
    rsi: float  # 0-100
    momentum: float  # Cambio de precio
    volatility_ratio: float  # ATR como % del precio
    bb_position: float  # 0-1, posición en bandas de Bollinger
    volume_ratio: Optional[float] = None  # Ratio de volumen si disponible
    macd: Optional[float] = None  # MACD si disponible


# =============================================================================
# SMART PRICE ANALYZER
# =============================================================================
class SmartPriceAnalyzer:
    """
    Selecciona precios relevantes en lugar de todos los disponibles
    """
    
    def __init__(
        self,
        price_window: int = DEFAULT_PRICE_WINDOW,
        sr_window: int = SUPPORT_RESISTANCE_WINDOW,
        vol_window: int = VOLATILITY_WINDOW
    ):
        self.price_window = price_window
        self.sr_window = sr_window
        self.vol_window = vol_window
    
    def analyze_prices(
        self,
        all_prices: np.ndarray,
        price_times: Optional[np.ndarray] = None
    ) -> PriceAnalysisResult:
        """
        Selecciona precios relevantes y analiza mercado
        
        Estrategia:
        1. Últimos N precios (siempre relevantes)
        2. Niveles de soporte/resistencia
        3. Zonas de volatilidad alta
        4. Puntos de quiebre de tendencia
        
        Returns:
            PriceAnalysisResult con análisis completo
        """
        
        if len(all_prices) == 0:
            logger.warning("No prices provided for analysis")
            return self._create_empty_result()
        
        # Limitar a ventana de análisis
        prices = all_prices[-self.price_window:] if len(all_prices) > self.price_window else all_prices
        
        total_analyzed = len(prices)
        
        # 1. PRECIOS MÁS RECIENTES (Siempre relevantes)
        most_recent = prices[-20:]
        
        # 2. DETECTAR SOPORTE/RESISTENCIA
        support_levels, resistance_levels = self._find_support_resistance(prices)
        
        # 3. ANALIZAR VOLATILIDAD
        volatility_data = self._analyze_volatility(prices)
        
        # 4. DETECTAR TENDENCIA
        trend_direction, trend_strength = self._analyze_trend(prices)
        
        # 5. IDENTIFICAR PUNTOS DE QUIEBRE
        breakpoints = self._identify_breakpoints(prices)
        
        # Contar total de precios seleccionados
        # 20 recientes + 5 S/R + 5 R + 5 volatilidad = ~40
        selected_count = min(
            len(most_recent) + len(support_levels) + len(resistance_levels),
            len(prices)
        )
        
        result = PriceAnalysisResult(
            most_recent=most_recent,
            support_levels=support_levels[-5:],  # Últimos 5
            resistance_levels=resistance_levels[-5:],
            current_volatility=volatility_data['current_volatility'],
            avg_volatility=volatility_data['avg_volatility'],
            volatility_status=volatility_data['status'],
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            breakpoints=breakpoints[-10:],  # Últimos 10
            selected_count=selected_count,
            total_analyzed=total_analyzed
        )
        
        logger.info(
            f"Price analysis: {total_analyzed} analyzed, {selected_count} relevant | "
            f"Trend: {'UP' if trend_direction > 0 else 'DOWN' if trend_direction < 0 else 'NEUTRAL'} ({trend_strength:.2f}) | "
            f"Volatility: {result.volatility_status}"
        )
        
        return result
    
    def _find_support_resistance(self, prices: np.ndarray) -> Tuple[List, List]:
        """
        Encuentra máximos y mínimos locales
        """
        if len(prices) < self.sr_window * 2:
            return [], []
        
        support_levels = []
        resistance_levels = []
        
        # Buscar máximos y mínimos locales
        for i in range(self.sr_window, len(prices) - self.sr_window):
            window_start = i - self.sr_window
            window_end = i + self.sr_window
            
            # Máximo local = resistencia
            if prices[i] == np.max(prices[window_start:window_end]):
                resistance_levels.append((i, prices[i]))
            
            # Mínimo local = soporte
            if prices[i] == np.min(prices[window_start:window_end]):
                support_levels.append((i, prices[i]))
        
        return support_levels, resistance_levels
    
    def _analyze_volatility(self, prices: np.ndarray) -> Dict:
        """
        Analiza volatilidad usando retornos
        """
        if len(prices) < 2:
            return {
                'current_volatility': 0.0,
                'avg_volatility': 0.0,
                'status': 'UNKNOWN'
            }
        
        # Calcular retornos porcentuales
        returns = np.diff(prices) / prices[:-1]
        
        # Volatilidad histórica (desviación estándar de retornos)
        if len(returns) >= self.vol_window:
            volatility_series = pd.Series(returns).rolling(self.vol_window).std()
            current_volatility = volatility_series.iloc[-1]
            avg_volatility = volatility_series.mean()
        else:
            current_volatility = np.std(returns)
            avg_volatility = current_volatility
        
        # Clasificar volatilidad
        if current_volatility > avg_volatility * 1.5:
            status = 'HIGH'
        elif current_volatility < avg_volatility * 0.7:
            status = 'LOW'
        else:
            status = 'NORMAL'
        
        return {
            'current_volatility': float(current_volatility),
            'avg_volatility': float(avg_volatility),
            'status': status
        }
    
    def _analyze_trend(self, prices: np.ndarray) -> Tuple[int, float]:
        """
        Analiza tendencia usando SMA y pendiente
        """
        if len(prices) < 50:
            return 0, 0.0
        
        # SMA rápida (10) y lenta (20)
        sma_fast = self._sma(prices, 10)
        sma_slow = self._sma(prices, 20)
        
        if len(sma_fast) == 0 or len(sma_slow) == 0:
            return 0, 0.0
        
        # Dirección: Si SMA rápida > SMA lenta = tendencia alcista
        if sma_fast[-1] > sma_slow[-1]:
            trend_direction = 1
        elif sma_fast[-1] < sma_slow[-1]:
            trend_direction = -1
        else:
            trend_direction = 0
        
        # Fortaleza de tendencia: Diferencia porcentual entre SMAs
        if sma_slow[-1] != 0:
            trend_strength = abs((sma_fast[-1] - sma_slow[-1]) / sma_slow[-1])
            trend_strength = min(trend_strength, 1.0)  # Max 1.0
        else:
            trend_strength = 0.0
        
        # Limitar fortaleza
        trend_strength = float(trend_strength) * trend_direction if trend_direction != 0 else 0.0
        
        return trend_direction, trend_strength
    
    def _identify_breakpoints(self, prices: np.ndarray) -> List[int]:
        """
        Identifica puntos de quiebre (cambios de dirección)
        """
        if len(prices) < 3:
            return []
        
        # Calcular derivada (cambio de precio)
        price_change = np.diff(prices)
        
        # Detectar cambios de signo (picos y valles)
        direction_change = np.diff(np.sign(price_change))
        
        # Indices donde hay cambio de dirección
        breakpoints = np.where(direction_change != 0)[0].tolist()
        
        return breakpoints
    
    @staticmethod
    def _sma(prices: np.ndarray, period: int) -> np.ndarray:
        """Calcula SMA"""
        if len(prices) < period:
            return np.array([])
        return pd.Series(prices).rolling(window=period, min_periods=1).mean().values
    
    @staticmethod
    def _ema(prices: np.ndarray, period: int) -> np.ndarray:
        """Calcula EMA"""
        if len(prices) < period:
            return np.array([])
        return pd.Series(prices).ewm(span=period, adjust=False).mean().values
    
    def _create_empty_result(self) -> PriceAnalysisResult:
        """Crea resultado vacío para casos sin datos"""
        return PriceAnalysisResult(
            most_recent=np.array([]),
            support_levels=[],
            resistance_levels=[],
            current_volatility=0.0,
            avg_volatility=0.0,
            volatility_status='UNKNOWN',
            trend_direction=0,
            trend_strength=0.0,
            breakpoints=[],
            selected_count=0,
            total_analyzed=0
        )


# =============================================================================
# TECHNICAL FEATURE EXTRACTOR
# =============================================================================
class TechnicalFeatureExtractor:
    """
    Extrae features técnicos relevantes (no todos posibles)
    """
    
    def __init__(self, point_size: float = 0.00001):
        self.point_size = point_size
    
    def extract_features(
        self,
        prices: np.ndarray,
        volume: Optional[np.ndarray] = None,
        current_price: Optional[float] = None
    ) -> TechnicalFeatures:
        """
        Extrae SOLO los features más predictivos
        """
        
        if current_price is None:
            current_price = prices[-1] if len(prices) > 0 else 0
        
        # 1. TENDENCIA (2 features)
        sma_20 = self._sma(prices, 20)
        sma_50 = self._sma(prices, 50)
        
        if len(sma_50) > 0 and sma_50[-1] != 0:
            trend_strength = (current_price - sma_50[-1]) / sma_50[-1]
        else:
            trend_strength = 0.0
        
        sma_crossover = 1 if (len(sma_20) > 0 and len(sma_50) > 0 and sma_20[-1] > sma_50[-1]) else -1
        
        # 2. MOMENTUM (2 features)
        rsi = self._rsi(prices, 14)
        rsi_value = rsi[-1] if len(rsi) > 0 else 50
        
        momentum = (current_price - prices[-20]) if len(prices) >= 20 else 0
        
        # 3. VOLATILIDAD (1 feature)
        atr = self._atr(prices, 14)
        volatility_ratio = (atr[-1] / current_price * 100) if len(atr) > 0 and current_price > 0 else 0
        
        # 4. BANDAS DE BOLLINGER (1 feature)
        bb_upper, bb_middle, bb_lower = self._bollinger_bands(prices, 20)
        if len(bb_upper) > 0 and (bb_upper[-1] - bb_lower[-1]) > 0:
            bb_position = (current_price - bb_lower[-1]) / (bb_upper[-1] - bb_lower[-1])
            bb_position = np.clip(bb_position, 0, 1)
        else:
            bb_position = 0.5
        
        # 5. VOLUMEN (si disponible)
        volume_ratio = None
        if volume is not None and len(volume) >= 20:
            recent_vol = np.mean(volume[-5:])
            historical_vol = np.mean(volume[-20:])
            volume_ratio = recent_vol / historical_vol if historical_vol > 0 else 1.0
        
        # 6. MACD (opcional)
        macd_value = None
        ema_12 = self._ema(prices, 12)
        ema_26 = self._ema(prices, 26)
        if len(ema_12) > 0 and len(ema_26) > 0:
            macd_value = ema_12[-1] - ema_26[-1]
        
        features = TechnicalFeatures(
            trend_strength=float(trend_strength),
            sma_crossover=sma_crossover,
            rsi=float(rsi_value),
            momentum=float(momentum),
            volatility_ratio=float(volatility_ratio),
            bb_position=float(bb_position),
            volume_ratio=volume_ratio,
            macd=macd_value
        )
        
        logger.debug(
            f"Features extracted: Trend={features.trend_strength:.4f}, "
            f"RSI={features.rsi:.1f}, Vol={features.volatility_ratio:.2f}%, "
            f"BB={features.bb_position:.2f}"
        )
        
        return features
    
    @staticmethod
    def _sma(prices: np.ndarray, period: int) -> np.ndarray:
        """SMA"""
        if len(prices) < period:
            return np.array([])
        return pd.Series(prices).rolling(window=period, min_periods=1).mean().values
    
    @staticmethod
    def _ema(prices: np.ndarray, period: int) -> np.ndarray:
        """EMA"""
        if len(prices) < period:
            return np.array([])
        return pd.Series(prices).ewm(span=period, adjust=False).mean().values
    
    @staticmethod
    def _rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
        """RSI"""
        if len(prices) < period:
            return np.array([])
        
        deltas = np.diff(prices)
        seed = deltas[:period+1]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        
        rs = up / down if down != 0 else 0
        rsi_values = [100.0 - 100.0 / (1.0 + rs)]
        
        for i in range(period, len(prices)):
            delta = deltas[i-1]
            if delta > 0:
                upval = delta
                downval = 0.0
            else:
                upval = 0.0
                downval = -delta
            
            up = (up * (period - 1) + upval) / period
            down = (down * (period - 1) + downval) / period
            
            rs = up / down if down != 0 else 0
            rsi_values.append(100.0 - 100.0 / (1.0 + rs))
        
        return np.array(rsi_values)
    
    @staticmethod
    def _atr(prices: np.ndarray, period: int = 14) -> np.ndarray:
        """ATR (Average True Range)"""
        if len(prices) < period:
            return np.array([])
        
        # Usar precios como proxy (en casos reales, necesitarías high, low, close)
        tr = np.abs(np.diff(prices))
        atr_values = pd.Series(tr).rolling(window=period, min_periods=1).mean().values
        
        return atr_values
    
    @staticmethod
    def _bollinger_bands(prices: np.ndarray, period: int = 20) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Bandas de Bollinger"""
        if len(prices) < period:
            return np.array([]), np.array([]), np.array([])
        
        sma = pd.Series(prices).rolling(window=period, min_periods=1).mean().values
        std = pd.Series(prices).rolling(window=period, min_periods=1).std().values
        
        upper = sma + (std * 2)
        lower = sma - (std * 2)
        
        return upper, sma, lower
    
    def get_features_summary(self, features: TechnicalFeatures) -> str:
        """Genera resumen de features"""
        return f"""
Technical Features Summary:
  Trend Strength:    {features.trend_strength:>7.4f}
  SMA Crossover:     {'BULLISH' if features.sma_crossover > 0 else 'BEARISH':>10}
  RSI:               {features.rsi:>7.1f}
  Momentum:          {features.momentum:>7.4f}
  Volatility Ratio:  {features.volatility_ratio:>7.2f}%
  Bollinger Pos:     {features.bb_position:>7.2f}
        """.strip()
