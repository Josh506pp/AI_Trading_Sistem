#!/usr/bin/env python3
"""
Sistema de Recompensas Basado en R-Múltiplos
Calcula puntos dinámicos según riesgo por operación
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURACIÓN
# =============================================================================
POINT_SIZE = 0.00001  # Para EURUSD (5 decimales)
BASE_POINTS_PER_R = 100  # 1R = 100 puntos base
TRAILING_WINDOW = 20  # Ventana para métricas de consistencia


# =============================================================================
# REWARD CALCULATOR (R-MÚLTIPLOS)
# =============================================================================
@dataclass
class TradeResult:
    """Resultado de una operación completada"""
    trade_id: int
    entry_price: float
    exit_price: float
    stop_loss: float
    take_profit: float
    direction: str  # 'BUY' o 'SELL'
    lot_size: float
    entry_time: datetime
    exit_time: datetime
    r_multiple: float = 0.0
    base_points: int = 0
    adjusted_points: int = 0


class RewardCalculator:
    """
    Calcula recompensas en R-múltiplos y puntos
    """
    
    def __init__(self, point_size: float = POINT_SIZE):
        self.point_size = point_size
        self.trade_history: List[TradeResult] = []
    
    def calculate_r_multiple(
        self,
        entry_price: float,
        stop_loss: float,
        exit_price: float,
        is_buy: bool
    ) -> float:
        """
        Calcula múltiplo de R alcanzado
        
        R = (Entry - SL) para compra, (SL - Entry) para venta
        R-Multiple = PnL en pips / R
        """
        
        try:
            # Calcular R (riesgo por operación) en pips
            if is_buy:
                R = (entry_price - stop_loss) / self.point_size
            else:
                R = (stop_loss - entry_price) / self.point_size
            
            if R <= 0:
                logger.warning(f"R inválido: {R}. Stop loss debe estar más alejado que entrada.")
                return 0.0
            
            # Calcular PnL en pips
            if is_buy:
                pnl_pips = (exit_price - entry_price) / self.point_size
            else:
                pnl_pips = (entry_price - exit_price) / self.point_size
            
            # Convertir a R-múltiplos
            r_multiple = pnl_pips / R
            
            return round(r_multiple, 2)
        
        except ZeroDivisionError:
            logger.error("División por cero en calculate_r_multiple")
            return 0.0
    
    def calculate_reward(
        self,
        entry_price: float,
        stop_loss: float,
        exit_price: float,
        is_buy: bool,
        lot_size: float = 1.0
    ) -> Dict:
        """
        Calcula recompensa completa de una operación
        
        Returns:
            {
                'r_multiple': float,
                'base_points': int,
                'pnl_pips': float,
                'pnl_percent': float
            }
        """
        
        # Calcular R-múltiple
        r_multiple = self.calculate_r_multiple(entry_price, stop_loss, exit_price, is_buy)
        
        # Calcular PnL en pips para referencia
        if is_buy:
            pnl_pips = (exit_price - entry_price) / self.point_size
        else:
            pnl_pips = (entry_price - exit_price) / self.point_size
        
        # Puntos base: 1R = 100 puntos
        base_points = int(r_multiple * BASE_POINTS_PER_R)
        
        # PnL como porcentaje (aproximado)
        pnl_percent = (pnl_pips * self.point_size) / entry_price * 100
        
        return {
            'r_multiple': r_multiple,
            'base_points': base_points,
            'pnl_pips': round(pnl_pips, 2),
            'pnl_percent': round(pnl_percent, 2),
            'lot_size': lot_size
        }
    
    def add_trade_result(
        self,
        trade_id: int,
        entry_price: float,
        exit_price: float,
        stop_loss: float,
        take_profit: float,
        direction: str,
        lot_size: float,
        entry_time: datetime,
        exit_time: datetime
    ) -> TradeResult:
        """
        Registra resultado de trade completado
        """
        
        is_buy = direction == 'BUY'
        reward_data = self.calculate_reward(
            entry_price, stop_loss, exit_price, is_buy, lot_size
        )
        
        trade = TradeResult(
            trade_id=trade_id,
            entry_price=entry_price,
            exit_price=exit_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            direction=direction,
            lot_size=lot_size,
            entry_time=entry_time,
            exit_time=exit_time,
            r_multiple=reward_data['r_multiple'],
            base_points=reward_data['base_points'],
            adjusted_points=reward_data['base_points']  # Se ajusta después
        )
        
        self.trade_history.append(trade)
        logger.info(
            f"Trade #{trade_id} completado: {direction} @ {entry_price} → {exit_price} = "
            f"{trade.r_multiple:+.2f}R ({trade.base_points:+d} pts)"
        )
        
        return trade
    
    def get_trade_history(self) -> List[TradeResult]:
        """Devuelve historial completo de trades"""
        return self.trade_history.copy()
    
    def get_recent_trades(self, n: int = TRAILING_WINDOW) -> List[TradeResult]:
        """Devuelve últimas N operaciones"""
        return self.trade_history[-n:] if len(self.trade_history) >= n else self.trade_history
    
    def calculate_total_r_multiple(self) -> float:
        """Suma total de R-múltiplos de todas las operaciones"""
        if not self.trade_history:
            return 0.0
        return sum(t.r_multiple for t in self.trade_history)
    
    def calculate_statistics(self) -> Dict:
        """
        Calcula estadísticas del historial
        """
        if not self.trade_history:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_r': 0.0,
                'avg_r_winner': 0.0,
                'avg_r_loser': 0.0,
                'profit_factor': 0.0,
                'best_trade': 0.0,
                'worst_trade': 0.0
            }
        
        trades = self.trade_history
        total = len(trades)
        
        winners = [t.r_multiple for t in trades if t.r_multiple > 0]
        losers = [t.r_multiple for t in trades if t.r_multiple < 0]
        
        winning_trades = len(winners)
        losing_trades = len(losers)
        
        total_winners_r = sum(winners) if winners else 0
        total_losers_r = sum(losers) if losers else 0
        
        win_rate = winning_trades / total if total > 0 else 0
        profit_factor = total_winners_r / abs(total_losers_r) if total_losers_r != 0 else (1 if total_winners_r > 0 else 0)
        
        return {
            'total_trades': total,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': round(win_rate, 3),
            'total_r': round(sum(t.r_multiple for t in trades), 2),
            'avg_r_winner': round(total_winners_r / winning_trades, 2) if winners else 0,
            'avg_r_loser': round(total_losers_r / losing_trades, 2) if losers else 0,
            'profit_factor': round(profit_factor, 2),
            'best_trade': round(max(t.r_multiple for t in trades), 2) if trades else 0,
            'worst_trade': round(min(t.r_multiple for t in trades), 2) if trades else 0
        }


# =============================================================================
# PENALTY SYSTEM (PENALIZACIONES POR RIESGO)
# =============================================================================
class RiskPenaltySystem:
    """
    Penaliza comportamientos de riesgo peligroso
    """
    
    def __init__(self, trade_history_ref: List[TradeResult] = None):
        self.trade_history = trade_history_ref or []
        self.peak_balance = 100.0  # Balance máximo histórico (normalizado)
        self.current_balance = 100.0  # Balance actual
    
    def update_balance(self, current_balance: float, peak_balance: float):
        """Actualiza balances para cálculo de drawdown"""
        self.current_balance = current_balance
        self.peak_balance = peak_balance
    
    def calculate_drawdown_penalty(self) -> int:
        """
        Penaliza si drawdown supera umbrales
        
        Drawdown = (Peak - Current) / Peak * 100
        """
        if self.peak_balance <= 0:
            return 0
        
        drawdown_pct = (self.peak_balance - self.current_balance) / self.peak_balance * 100
        
        if drawdown_pct > 30:  # Crítico
            penalty = -500
        elif drawdown_pct > 20:  # Alto riesgo
            penalty = -250
        elif drawdown_pct > 10:  # Moderado
            penalty = -100
        else:
            penalty = 0
        
        logger.debug(f"Drawdown: {drawdown_pct:.1f}% → Penalty: {penalty}")
        return penalty
    
    def calculate_losing_streak_penalty(self) -> int:
        """
        Penaliza rachas de pérdidas consecutivas
        """
        if not self.trade_history:
            return 0
        
        # Contar pérdidas consecutivas desde el final
        losing_streak = 0
        for trade in reversed(self.trade_history[-10:]):  # Últimos 10 trades
            if trade.r_multiple < -0.1:  # Pérdida significativa
                losing_streak += 1
            else:
                break
        
        # Tabla de penalizaciones
        streak_penalties = {
            0: 0,
            1: 0,
            2: 0,
            3: -50,      # 3 pérdidas seguidas
            4: -100,
            5: -200,     # 5+ pérdidas = penalización severa
            6: -300,
            7: -400,
            8: -500,
        }
        
        penalty = streak_penalties.get(min(losing_streak, 8), -500)
        
        if penalty < 0:
            logger.warning(f"Losing streak: {losing_streak} trades → Penalty: {penalty}")
        
        return penalty
    
    def calculate_excessive_risk_penalty(self, risk_percent: float) -> int:
        """
        Penaliza si riesgo por operación es muy alto
        """
        if risk_percent > 5:  # Más del 5% de riesgo
            return -150
        elif risk_percent > 3:
            return -75
        else:
            return 0
    
    def calculate_revenge_trading_penalty(self) -> int:
        """
        Detecta y penaliza revenge trading (aumentar lotaje tras pérdidas)
        """
        if len(self.trade_history) < 2:
            return 0
        
        last_trade = self.trade_history[-1]
        prev_trade = self.trade_history[-2]
        
        # Si pérdida anterior y ahora lotaje mucho más alto = revenge trading
        if (prev_trade.r_multiple < -0.5 and 
            last_trade.lot_size > prev_trade.lot_size * 1.5):
            logger.warning(
                f"Revenge trading detectado: Lotaje {prev_trade.lot_size} → {last_trade.lot_size} "
                f"después de pérdida {prev_trade.r_multiple:.2f}R"
            )
            return -200
        
        return 0
    
    def get_total_penalties(self, risk_percent: float = 2.0) -> Dict[str, int]:
        """
        Calcula todas las penalizaciones
        """
        return {
            'drawdown': self.calculate_drawdown_penalty(),
            'losing_streak': self.calculate_losing_streak_penalty(),
            'excessive_risk': self.calculate_excessive_risk_penalty(risk_percent),
            'revenge_trading': self.calculate_revenge_trading_penalty()
        }
    
    def get_total_penalty_amount(self, risk_percent: float = 2.0) -> int:
        """Suma total de penalizaciones"""
        penalties = self.get_total_penalties(risk_percent)
        return sum(penalties.values())


# =============================================================================
# CONSISTENCY BONUS SYSTEM (BONIFICACIÓN POR CONSISTENCIA)
# =============================================================================
class ConsistencyBonusSystem:
    """
    Bonifica comportamientos consistentes y rentables
    """
    
    def __init__(self, trade_history_ref: List[TradeResult] = None):
        self.trade_history = trade_history_ref or []
        self.window = TRAILING_WINDOW
    
    def calculate_consistency_bonus(self) -> int:
        """
        Premia consistencia en ganancias
        """
        if len(self.trade_history) < self.window:
            return 0
        
        recent_trades = self.trade_history[-self.window:]
        
        # Calcular métricas
        winners = [t.r_multiple for t in recent_trades if t.r_multiple > 0]
        losers = [t.r_multiple for t in recent_trades if t.r_multiple < 0]
        
        if not winners or not losers:
            return 0
        
        win_rate = len(winners) / len(recent_trades)
        total_winners_r = sum(winners)
        total_losers_r = sum(losers)
        profit_factor = total_winners_r / abs(total_losers_r) if total_losers_r != 0 else 0
        
        bonus = 0
        bonus_details = {}
        
        # BONUS 1: Alta tasa de ganancia (>55%)
        if win_rate > 0.60:
            win_bonus = int(win_rate * 100)
            bonus += win_bonus
            bonus_details['win_rate'] = win_bonus
            logger.info(f"Win rate bonus: {win_bonus} pts (WR: {win_rate*100:.1f}%)")
        
        # BONUS 2: Profit factor (ganancias/pérdidas)
        if profit_factor > 2:
            pf_bonus = min(int(profit_factor * 50), 200)
            bonus += pf_bonus
            bonus_details['profit_factor'] = pf_bonus
            logger.info(f"Profit factor bonus: {pf_bonus} pts (PF: {profit_factor:.2f})")
        
        # BONUS 3: Racha de ganancias
        streak_bonus = self._calculate_winning_streak_bonus(recent_trades)
        if streak_bonus > 0:
            bonus += streak_bonus
            bonus_details['winning_streak'] = streak_bonus
            logger.info(f"Winning streak bonus: {streak_bonus} pts")
        
        if bonus > 0:
            logger.debug(f"Total consistency bonus: {bonus} pts | Details: {bonus_details}")
        
        return bonus
    
    def _calculate_winning_streak_bonus(self, trades: List[TradeResult]) -> int:
        """Calcula bonus por racha de ganancias"""
        if not trades:
            return 0
        
        # Contar ganancias consecutivas desde el final
        streak = 0
        for trade in reversed(trades):
            if trade.r_multiple > 0:
                streak += 1
            else:
                break
        
        streak_bonuses = {
            0: 0, 1: 0, 2: 0, 3: 25,
            4: 50, 5: 75, 6: 100,
            7: 125, 8: 150, 9: 175, 10: 200
        }
        
        return streak_bonuses.get(min(streak, 10), 200)


# =============================================================================
# SCORECARD (PUNTUACIÓN TOTAL)
# =============================================================================
class TradingScoreCard:
    """
    Calcula puntuación total de salud del sistema
    """
    
    # Umbrales de salud
    HEALTH_THRESHOLDS = {
        'CRITICAL': (-float('inf'), -500),
        'HIGH_RISK': (-500, -200),
        'AT_RISK': (-200, 0),
        'CAUTION': (0, 200),
        'HEALTHY': (200, 500),
        'EXCELLENT': (500, float('inf'))
    }
    
    def __init__(
        self,
        reward_calculator: RewardCalculator,
        risk_penalty_system: RiskPenaltySystem,
        consistency_bonus_system: ConsistencyBonusSystem
    ):
        self.reward_calc = reward_calculator
        self.risk_penalties = risk_penalty_system
        self.consistency_bonus = consistency_bonus_system
    
    def calculate_total_score(
        self,
        base_points: int,
        risk_percent: float = 2.0
    ) -> Dict:
        """
        Scoring = BasePoints + Bonuses - Penalizaciones
        """
        
        # Calcular componentes
        consistency_bonus_amount = self.consistency_bonus.calculate_consistency_bonus()
        penalty_details = self.risk_penalties.get_total_penalties(risk_percent)
        total_penalties = sum(penalty_details.values())
        
        # Score total
        total_score = base_points + consistency_bonus_amount + total_penalties
        
        # Clasificación de salud
        health_status = self._classify_health(total_score)
        
        return {
            'total_score': total_score,
            'base_points': base_points,
            'consistency_bonus': consistency_bonus_amount,
            'penalties': penalty_details,
            'total_penalties': total_penalties,
            'health_status': health_status,
            'recommendation': self._get_recommendation(health_status, total_score)
        }
    
    def _classify_health(self, score: int) -> str:
        """Clasifica salud basada en score"""
        for status, (lower, upper) in self.HEALTH_THRESHOLDS.items():
            if lower <= score < upper:
                return status
        return 'CRITICAL'
    
    def _get_recommendation(self, health_status: str, score: int) -> str:
        """Devuelve recomendación basada en salud"""
        recommendations = {
            'CRITICAL': '🔴 PAUSA INMEDIATA: Riesgo crítico. Cierra posiciones y revisa configuración.',
            'HIGH_RISK': '🟠 ALTO RIESGO: Considera pausar. Reevalúa estrategia de entrada.',
            'AT_RISK': '🟡 CUIDADO: Sistema en riesgo. Evita operaciones agresivas.',
            'CAUTION': '🟡 PRECAUCIÓN: Operando normalmente. Monitorea de cerca.',
            'HEALTHY': '🟢 SALUDABLE: Condiciones óptimas para trading.',
            'EXCELLENT': '🟢 EXCELENTE: Máximo rendimiento. Considera aumentar tamaño de posición.'
        }
        
        return recommendations.get(health_status, 'Estado desconocido')
    
    def get_scorecard_report(self) -> str:
        """
        Genera reporte visual del scorecard
        """
        stats = self.reward_calc.calculate_statistics()
        score = self.calculate_total_score(
            int(stats.get('total_r', 0) * BASE_POINTS_PER_R)
        )
        
        report = f"""
╔════════════════════════════════════════════════════════════╗
║               TRADING SYSTEM SCORECARD                    ║
╠════════════════════════════════════════════════════════════╣
║ Total Score:        {score['total_score']:>6} pts                   ║
║ Health Status:      {score['health_status']:<25} ║
║                                                            ║
║ Base Points (R):    {score['base_points']:>6} pts                   ║
║ Bonus (Consistency):{score['consistency_bonus']:>6} pts                   ║
║ Penalties (Total):  {score['total_penalties']:>6} pts                   ║
║                                                            ║
║ Trades:             {stats['total_trades']:>6}                       ║
║ Win Rate:           {stats['win_rate']*100:>6.1f}%                    ║
║ Profit Factor:      {stats['profit_factor']:>6.2f}x                    ║
║ Total R-Multiple:   {stats['total_r']:>6.2f}R                    ║
╠════════════════════════════════════════════════════════════╣
║ {score['recommendation']}
╚════════════════════════════════════════════════════════════╝
        """
        
        return report
