#!/usr/bin/env python3
"""
Lógica de Decisiones Mejorada
Entry (Entrada) y Exit (Salida) basadas en ventaja estadística
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)

# =============================================================================
# ENUMS Y DATACLASSES
# =============================================================================
class TradeDirection(Enum):
    """Dirección de operación"""
    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"


class ExitReason(Enum):
    """Razones para salir de una posición"""
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    TRAILING_STOP = "TRAILING_STOP"
    TREND_REVERSAL = "TREND_REVERSAL"
    RISK_MANAGEMENT = "RISK_MANAGEMENT"
    MANUAL = "MANUAL"


@dataclass
class EntrySignal:
    """Señal de entrada"""
    should_trade: bool
    direction: TradeDirection
    confidence: float  # 0.0 - 1.0
    reason: str
    entry_price: float
    signal_strength: Dict[str, float]  # Detalles de cada señal


@dataclass
class ExitSignal:
    """Señal de salida"""
    should_exit: bool
    exit_reason: Optional[ExitReason]
    exit_price: float
    expected_r_multiple: float
    reasoning: str


@dataclass
class ActiveTrade:
    """Posición activa"""
    trade_id: int
    direction: TradeDirection
    entry_price: float
    stop_loss: float
    take_profit: float
    lot_size: float
    entry_time: datetime
    highest_price: float  # Para trailing stop
    lowest_price: float   # Para trailing stop
    entry_r_multiple: float = 0.0


# =============================================================================
# ENTRY DECISION LOGIC
# =============================================================================
class EntryDecisionLogic:
    """
    Decide entradas COMPRADAS/VENDIDAS basadas en ventaja estadística
    """
    
    # Umbrales de confianza
    MIN_CONFIDENCE_CONSERVATIVE = 0.55  # 55% para estrategia conservadora
    MIN_CONFIDENCE_MODERATE = 0.60      # 60% para estrategia moderada
    MIN_CONFIDENCE_AGGRESSIVE = 0.70    # 70% para estrategia agresiva
    
    # Pesos de señales (cada señal contribuye)
    SIGNAL_WEIGHTS = {
        'sma_crossover': 2.0,      # Tendencia es importante
        'rsi': 1.5,                # RSI extremo es buena señal
        'momentum': 1.0,           # Momentum moderadamente importante
        'bollinger': 1.5,          # Posición en bandas es importante
        'trend_strength': 2.0,     # Tendencia fuerte es clave
    }
    
    def __init__(self, risk_tolerance: str = 'moderate'):
        """
        risk_tolerance: 'conservative', 'moderate', 'aggressive'
        """
        self.risk_tolerance = risk_tolerance
        self.min_confidence = self._get_min_confidence()
    
    def _get_min_confidence(self) -> float:
        """Obtiene confianza mínima según tolerancia"""
        tolerance_map = {
            'conservative': self.MIN_CONFIDENCE_CONSERVATIVE,
            'moderate': self.MIN_CONFIDENCE_MODERATE,
            'aggressive': self.MIN_CONFIDENCE_AGGRESSIVE
        }
        return tolerance_map.get(self.risk_tolerance, self.MIN_CONFIDENCE_MODERATE)
    
    def evaluate_entry(
        self,
        current_price: float,
        technical_features,  # TechnicalFeatures object
        price_analysis,  # PriceAnalysisResult object
        score_card: Dict,  # Scorecard report
        max_positions: int,
        current_positions: int,
        account_health: Dict
    ) -> EntrySignal:
        """
        Evalúa si debe abrirse una operación
        
        Devuelve EntrySignal con dirección y confianza
        """
        
        signal_strength = {}
        
        # ===== PARADA 1: CHEQUES DE SALUD DEL SISTEMA =====
        if not self._health_checks(max_positions, current_positions, score_card, account_health):
            return EntrySignal(
                should_trade=False,
                direction=TradeDirection.NEUTRAL,
                confidence=0.0,
                reason="System health checks failed",
                entry_price=current_price,
                signal_strength={}
            )
        
        # ===== PARADA 2: VOLATILIDAD EXTREMA =====
        if technical_features.volatility_ratio > 5.0:  # > 5% volatilidad
            return EntrySignal(
                should_trade=False,
                direction=TradeDirection.NEUTRAL,
                confidence=0.0,
                reason="Volatility too high, waiting",
                entry_price=current_price,
                signal_strength={}
            )
        
        # ===== COMPILAR SEÑALES (SCORING SYSTEM) =====
        buy_score = 0.0
        sell_score = 0.0
        
        # SEÑAL 1: CRUCE SMA (Peso: 2)
        if technical_features.sma_crossover == 1:  # SMA 20 > SMA 50
            buy_score += self.SIGNAL_WEIGHTS['sma_crossover']
            signal_strength['sma_buy'] = self.SIGNAL_WEIGHTS['sma_crossover']
        else:
            sell_score += self.SIGNAL_WEIGHTS['sma_crossover']
            signal_strength['sma_sell'] = self.SIGNAL_WEIGHTS['sma_crossover']
        
        # SEÑAL 2: RSI (Peso: 1.5)
        rsi = technical_features.rsi
        if rsi < 30:  # Sobvendido = comprar
            buy_score += self.SIGNAL_WEIGHTS['rsi']
            signal_strength['rsi_oversold'] = self.SIGNAL_WEIGHTS['rsi']
        elif rsi > 70:  # Sobrecomprado = vender
            sell_score += self.SIGNAL_WEIGHTS['rsi']
            signal_strength['rsi_overbought'] = self.SIGNAL_WEIGHTS['rsi']
        else:
            # RSI neutral
            if rsi > 50:
                buy_score += 0.3
                signal_strength['rsi_neutral_bullish'] = 0.3
            else:
                sell_score += 0.3
                signal_strength['rsi_neutral_bearish'] = 0.3
        
        # SEÑAL 3: MOMENTUM (Peso: 1)
        if technical_features.momentum > 0:
            buy_score += self.SIGNAL_WEIGHTS['momentum'] * 0.5
            signal_strength['momentum_up'] = self.SIGNAL_WEIGHTS['momentum'] * 0.5
        else:
            sell_score += self.SIGNAL_WEIGHTS['momentum'] * 0.5
            signal_strength['momentum_down'] = self.SIGNAL_WEIGHTS['momentum'] * 0.5
        
        # SEÑAL 4: POSICIÓN EN BANDAS BOLLINGER (Peso: 1.5)
        bb_pos = technical_features.bb_position
        if bb_pos < 0.2:  # Cerca del límite inferior (sobrevendido)
            buy_score += self.SIGNAL_WEIGHTS['bollinger']
            signal_strength['bb_oversold'] = self.SIGNAL_WEIGHTS['bollinger']
        elif bb_pos > 0.8:  # Cerca del límite superior (sobrecomprado)
            sell_score += self.SIGNAL_WEIGHTS['bollinger']
            signal_strength['bb_overbought'] = self.SIGNAL_WEIGHTS['bollinger']
        
        # SEÑAL 5: TENDENCIA GENERAL (Peso: 2 - MÁS IMPORTANTE)
        trend_str = technical_features.trend_strength
        if trend_str > 0.02:  # Tendencia alcista fuerte
            buy_score += self.SIGNAL_WEIGHTS['trend_strength']
            signal_strength['trend_bullish'] = self.SIGNAL_WEIGHTS['trend_strength']
        elif trend_str < -0.02:  # Tendencia bajista fuerte
            sell_score += self.SIGNAL_WEIGHTS['trend_strength']
            signal_strength['trend_bearish'] = self.SIGNAL_WEIGHTS['trend_strength']
        
        # ===== CALCULAR CONFIANZA =====
        total_signals = buy_score + sell_score
        
        if total_signals == 0:
            return EntrySignal(
                should_trade=False,
                direction=TradeDirection.NEUTRAL,
                confidence=0.0,
                reason="No clear signals",
                entry_price=current_price,
                signal_strength=signal_strength
            )
        
        # Normalizar scores a 0-1
        if buy_score > sell_score:
            confidence = buy_score / total_signals
            direction = TradeDirection.BUY
        else:
            confidence = sell_score / total_signals
            direction = TradeDirection.SELL
        
        # Verificar mínimo de confianza
        if confidence < self.min_confidence:
            return EntrySignal(
                should_trade=False,
                direction=direction,
                confidence=confidence,
                reason=f"Confidence {confidence*100:.1f}% < {self.min_confidence*100:.1f}% threshold",
                entry_price=current_price,
                signal_strength=signal_strength
            )
        
        # ===== SEÑAL VÁLIDA =====
        return EntrySignal(
            should_trade=True,
            direction=direction,
            confidence=confidence,
            reason=f"{direction.value} signal with {confidence*100:.1f}% confidence",
            entry_price=current_price,
            signal_strength=signal_strength
        )
    
    def _health_checks(
        self,
        max_positions: int,
        current_positions: int,
        score_card: Dict,
        account_health: Dict
    ) -> bool:
        """Verifica salud del sistema antes de permitir entrada"""
        
        # Chequeo 1: Posiciones máximas
        if current_positions >= max_positions:
            logger.debug("Max positions reached")
            return False
        
        # Chequeo 2: Salud del sistema
        health_status = score_card.get('health_status', 'CRITICAL')
        if health_status in ['CRITICAL', 'HIGH_RISK']:
            logger.warning(f"System in {health_status} state - skipping entry")
            return False
        
        # Chequeo 3: Saldo de la cuenta
        if account_health.get('drawdown_pct', 0) > 20:
            logger.warning(f"Drawdown {account_health['drawdown_pct']:.1f}% - skipping entry")
            return False
        
        return True
    
    def calculate_entry_parameters(
        self,
        entry_price: float,
        direction: TradeDirection,
        stop_loss_pips: int,
        take_profit_pips: int,
        account_balance: float,
        risk_percent: float = 2.0
    ) -> Dict:
        """
        Calcula parámetros de entrada (SL, TP, tamaño)
        """
        
        POINT = 0.00001
        
        # Calcular distancia en pips
        sl_distance_pips = stop_loss_pips
        tp_distance_pips = take_profit_pips
        
        # Calcular precios
        if direction == TradeDirection.BUY:
            stop_loss = entry_price - (sl_distance_pips * POINT)
            take_profit = entry_price + (tp_distance_pips * POINT)
        else:  # SELL
            stop_loss = entry_price + (sl_distance_pips * POINT)
            take_profit = entry_price - (tp_distance_pips * POINT)
        
        # Calcular tamaño de posición basado en riesgo
        # Risk = Account Balance * Risk %
        risk_amount = account_balance * (risk_percent / 100)
        
        # Lot size = Risk Amount / (Distance in pips * Point Value)
        # Simplificado para EURUSD
        distance_value = sl_distance_pips * 10  # Valor aproximado por pip
        lot_size = max(0.01, risk_amount / distance_value)
        
        return {
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'lot_size': lot_size,
            'risk_reward_ratio': tp_distance_pips / sl_distance_pips
        }


# =============================================================================
# EXIT DECISION LOGIC
# =============================================================================
class ExitDecisionLogic:
    """
    Decide salidas de posiciones
    """
    
    def __init__(self, trailing_stop_enabled: bool = True, trailing_stop_pips: int = 30, min_hold_minutes: int = 5):
        self.trailing_stop_enabled = trailing_stop_enabled
        self.trailing_stop_pips = trailing_stop_pips
        self.min_hold_minutes = min_hold_minutes
    
    def evaluate_exit(
        self,
        trade: ActiveTrade,
        current_price: float,
        technical_features,
        price_analysis
    ) -> ExitSignal:
        """
        Evalúa si debe cerrarse una posición
        """
        
        POINT = 0.00001
        
        # ===== PARADA 1: STOP LOSS =====
        if trade.direction == TradeDirection.BUY:
            if current_price <= trade.stop_loss:
                return ExitSignal(
                    should_exit=True,
                    exit_reason=ExitReason.STOP_LOSS,
                    exit_price=trade.stop_loss,
                    expected_r_multiple=-1.0,
                    reasoning="Stop loss hit"
                )
            
            # ===== PARADA 2: TAKE PROFIT =====
            if current_price >= trade.take_profit:
                pnl_pips = (trade.take_profit - trade.entry_price) / POINT
                R = (trade.entry_price - trade.stop_loss) / POINT
                expected_r = pnl_pips / R if R > 0 else 0
                
                return ExitSignal(
                    should_exit=True,
                    exit_reason=ExitReason.TAKE_PROFIT,
                    exit_price=trade.take_profit,
                    expected_r_multiple=expected_r,
                    reasoning="Take profit reached"
                )
        
        else:  # SELL
            if current_price >= trade.stop_loss:
                return ExitSignal(
                    should_exit=True,
                    exit_reason=ExitReason.STOP_LOSS,
                    exit_price=trade.stop_loss,
                    expected_r_multiple=-1.0,
                    reasoning="Stop loss hit"
                )
            
            # ===== PARADA 2: TAKE PROFIT =====
            if current_price <= trade.take_profit:
                pnl_pips = (trade.entry_price - trade.take_profit) / POINT
                R = (trade.stop_loss - trade.entry_price) / POINT
                expected_r = pnl_pips / R if R > 0 else 0
                
                return ExitSignal(
                    should_exit=True,
                    exit_reason=ExitReason.TAKE_PROFIT,
                    exit_price=trade.take_profit,
                    expected_r_multiple=expected_r,
                    reasoning="Take profit reached"
                )
        
        # ===== PARADA 3: EVITAR SALIDAS INMEDIATAS =====
        trade_age_minutes = (datetime.now() - trade.entry_time).total_seconds() / 60.0
        if trade_age_minutes < self.min_hold_minutes:
            return ExitSignal(
                should_exit=False,
                exit_reason=None,
                exit_price=current_price,
                expected_r_multiple=0.0,
                reasoning=f"Mantener posición al menos {self.min_hold_minutes} minutos antes de evaluar salida"
            )

        # ===== PARADA 4: TRAILING STOP =====
        if self.trailing_stop_enabled:
            exit_signal = self._check_trailing_stop(trade, current_price)
            if exit_signal.should_exit:
                return exit_signal
        
        # ===== PARADA 5: REVERSIÓN DE TENDENCIA =====
        exit_signal = self._check_trend_reversal(trade, current_price, technical_features)
        if exit_signal.should_exit:
            return exit_signal
        
        # No salir
        return ExitSignal(
            should_exit=False,
            exit_reason=None,
            exit_price=current_price,
            expected_r_multiple=0.0,
            reasoning="No exit signal"
        )
    
    def _check_trailing_stop(self, trade: ActiveTrade, current_price: float) -> ExitSignal:
        """Verifica trailing stop"""
        POINT = 0.00001
        trail_distance = (trade.entry_price - trade.stop_loss) / POINT * 0.5  # 0.5R de trail
        
        if trade.direction == TradeDirection.BUY:
            # Actualizar máximo
            if current_price > trade.highest_price:
                trade.highest_price = current_price
            
            # Si precio cae más de trail distance
            if current_price < trade.highest_price - (trail_distance * POINT):
                pnl_pips = (current_price - trade.entry_price) / POINT
                R = (trade.entry_price - trade.stop_loss) / POINT
                expected_r = pnl_pips / R if R > 0 else 0
                
                return ExitSignal(
                    should_exit=True,
                    exit_reason=ExitReason.TRAILING_STOP,
                    exit_price=current_price,
                    expected_r_multiple=expected_r,
                    reasoning=f"Trailing stop hit (trail: {trail_distance:.0f})"
                )
        
        else:  # SELL
            # Actualizar mínimo
            if current_price < trade.lowest_price:
                trade.lowest_price = current_price
            
            # Si precio sube más de trail distance
            if current_price > trade.lowest_price + (trail_distance * POINT):
                pnl_pips = (trade.entry_price - current_price) / POINT
                R = (trade.stop_loss - trade.entry_price) / POINT
                expected_r = pnl_pips / R if R > 0 else 0
                
                return ExitSignal(
                    should_exit=True,
                    exit_reason=ExitReason.TRAILING_STOP,
                    exit_price=current_price,
                    expected_r_multiple=expected_r,
                    reasoning=f"Trailing stop hit (trail: {trail_distance:.0f})"
                )
        
        return ExitSignal(
            should_exit=False,
            exit_reason=None,
            exit_price=current_price,
            expected_r_multiple=0.0,
            reasoning="Trailing stop not hit"
        )
    
    def _check_trend_reversal(
        self,
        trade: ActiveTrade,
        current_price: float,
        technical_features
    ) -> ExitSignal:
        """Verifica reversión de tendencia (salida táctica)"""
        
        POINT = 0.00001
        
        # Si la tendencia se revierte significativamente
        if trade.direction == TradeDirection.BUY and technical_features.sma_crossover < 0:
            # Tendencia cambió a bajista
            profit_so_far = (current_price - trade.entry_price) / POINT
            R = (trade.entry_price - trade.stop_loss) / POINT
            
            if profit_so_far > R * 0.3:  # Ganancia de al menos 0.3R
                expected_r = profit_so_far / R if R > 0 else 0
                
                return ExitSignal(
                    should_exit=True,
                    exit_reason=ExitReason.TREND_REVERSAL,
                    exit_price=current_price,
                    expected_r_multiple=expected_r,
                    reasoning="Trend reversed (SMA crossover)"
                )
        
        elif trade.direction == TradeDirection.SELL and technical_features.sma_crossover > 0:
            # Tendencia cambió a alcista
            profit_so_far = (trade.entry_price - current_price) / POINT
            R = (trade.stop_loss - trade.entry_price) / POINT
            
            if profit_so_far > R * 0.3:  # Ganancia de al menos 0.3R
                expected_r = profit_so_far / R if R > 0 else 0
                
                return ExitSignal(
                    should_exit=True,
                    exit_reason=ExitReason.TREND_REVERSAL,
                    exit_price=current_price,
                    expected_r_multiple=expected_r,
                    reasoning="Trend reversed (SMA crossover)"
                )
        
        return ExitSignal(
            should_exit=False,
            exit_reason=None,
            exit_price=current_price,
            expected_r_multiple=0.0,
            reasoning="Trend stable"
        )
