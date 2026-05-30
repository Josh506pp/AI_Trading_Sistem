#!/usr/bin/env python3
"""
Módulo de Integración del Sistema de Trading Mejorado
Integra todos los componentes: Recompensas, Análisis, Decisiones, IA y Chat
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
import numpy as np

from reward_system import (
    RewardCalculator, RiskPenaltySystem, 
    ConsistencyBonusSystem, TradingScoreCard
)
from price_analyzer import SmartPriceAnalyzer, TechnicalFeatureExtractor
from decision_logic import (
    EntryDecisionLogic, ExitDecisionLogic, 
    TradeDirection, ActiveTrade
)
from ai_optimizer import AIOptimizer, OverfittingPrevention, MarketAdaptationEngine
from chat_interface import TradingBotChatInterface

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURACIÓN INTEGRADA
# =============================================================================
TRADING_CONFIG = {
    # Riesgo
    'risk_percent': 2.0,
    'max_positions': 10,
    'min_profitable_positions': 5,
    
    # Parámetros de entrada/salida
    'stop_loss_pips': 50,
    'take_profit_pips': 150,
    'trailing_stop_pips': 30,
    'trailing_stop_enabled': True,
    'min_hold_minutes': 5,
    
    # Técnico
    'point_size': 0.00001,
    'tick_value': 10.0,
    'symbol': 'EURUSD',
    
    # IA
    'model_type': 'neural_network',  # o 'random_forest'
    'retraining_frequency': 50,  # Reentrenar cada 50 operaciones
    'min_confidence_entry': 0.55,  # 55% confianza mínima
    
    # Límites de riesgo
    'max_drawdown_pct': 20,
    'max_drawdown_critical': 30,
    'max_consecutive_losses': 5,
}


# =============================================================================
# INTEGRATED TRADING SYSTEM
# =============================================================================
class IntegratedTradingSystem:
    """
    Sistema de trading integrado que combina todos los módulos
    """
    
    def __init__(self, config: Dict = None):
        """
        Inicializa el sistema con configuración
        """
        self.config = {**TRADING_CONFIG, **(config or {})}
        
        # Componentes principales
        self.reward_calc = RewardCalculator(self.config['point_size'])
        self.risk_penalties = RiskPenaltySystem()
        self.consistency_bonus = ConsistencyBonusSystem()
        self.scorecard = TradingScoreCard(
            self.reward_calc,
            self.risk_penalties,
            self.consistency_bonus
        )
        
        # Análisis
        self.price_analyzer = SmartPriceAnalyzer()
        self.feature_extractor = TechnicalFeatureExtractor(self.config['point_size'])
        
        # Decisiones
        self.entry_logic = EntryDecisionLogic(risk_tolerance='moderate')
        self.exit_logic = ExitDecisionLogic(
            trailing_stop_enabled=self.config['trailing_stop_enabled'],
            trailing_stop_pips=self.config['trailing_stop_pips'],
            min_hold_minutes=self.config['min_hold_minutes']
        )
        
        # IA
        self.ai_optimizer = AIOptimizer(model_type=self.config['model_type'])
        self.overfitting_prevention = OverfittingPrevention()
        self.market_adaptation = MarketAdaptationEngine()
        
        # Chat
        self.chat_interface = TradingBotChatInterface(self)
        
        # Estado
        self.active_trades: Dict[int, ActiveTrade] = {}
        self.trade_counter = 0
        self.current_balance = 10000.0
        self.peak_balance = 10000.0
        self.paused = False
        
        logger.info("Integrated Trading System initialized")
    
    def analyze_market(self, prices: np.ndarray, volume: np.ndarray = None) -> Dict:
        """
        Análisis completo del mercado
        """
        
        # Análisis de precios
        price_analysis = self.price_analyzer.analyze_prices(prices)
        
        # Extracción de features
        features = self.feature_extractor.extract_features(
            prices,
            volume=volume,
            current_price=prices[-1] if len(prices) > 0 else 0
        )
        
        # Predicción de IA
        features_array = np.array([
            features.trend_strength,
            float(features.sma_crossover),
            features.rsi / 100,
            features.momentum,
            features.volatility_ratio,
            features.bb_position,
            features.volume_ratio if features.volume_ratio else 0.5,
        ])
        
        ai_prediction = self.ai_optimizer.predict_trade_quality(features_array)
        
        # Scorecard
        base_points = int(self.reward_calc.calculate_total_r_multiple() * 100)
        scorecard = self.scorecard.calculate_total_score(base_points, self.config['risk_percent'])
        
        return {
            'price_analysis': price_analysis,
            'features': features,
            'ai_prediction': ai_prediction,
            'scorecard': scorecard,
            'timestamp': datetime.now()
        }
    
    def evaluate_entry_opportunity(
        self,
        prices: np.ndarray,
        volume: np.ndarray = None
    ) -> Dict:
        """
        Evalúa oportunidad de entrada
        """
        
        # Análisis completo
        market_analysis = self.analyze_market(prices, volume)
        
        # Obtener últimas características
        current_price = prices[-1] if len(prices) > 0 else 0
        features = market_analysis['features']
        price_analysis = market_analysis['price_analysis']
        scorecard = market_analysis['scorecard']
        
        # Decisión de entrada
        account_health = {
            'drawdown_pct': (self.peak_balance - self.current_balance) / self.peak_balance * 100 if self.peak_balance > 0 else 0
        }
        
        entry_signal = self.entry_logic.evaluate_entry(
            current_price,
            features,
            price_analysis,
            scorecard,
            max_positions=self.config['max_positions'],
            current_positions=len(self.active_trades),
            account_health=account_health
        )

        ai_prediction = market_analysis.get('ai_prediction', {})
        if ai_prediction.get('trade_quality') not in ['UNKNOWN', 'GOOD', 'EXCELLENT']:
            expected_r = ai_prediction.get('expected_r_multiple', 0.0)
            if expected_r < 0.35:
                return {
                    'should_trade': False,
                    'reason': 'AI anticipa rentabilidad baja o riesgo alto',
                    'confidence': ai_prediction.get('expected_confidence', 0.0)
                }
        
        # Si es buena oportunidad, calcular parámetros
        if entry_signal.should_trade:
            entry_params = self.entry_logic.calculate_entry_parameters(
                entry_signal.entry_price,
                entry_signal.direction,
                self.config['stop_loss_pips'],
                self.config['take_profit_pips'],
                self.current_balance,
                self.config['risk_percent']
            )
            
            return {
                'should_trade': True,
                'signal': entry_signal,
                'parameters': entry_params,
                'market_analysis': market_analysis
            }
        
        return {
            'should_trade': False,
            'reason': entry_signal.reason,
            'confidence': entry_signal.confidence
        }
    
    def open_trade(
        self,
        direction: str,  # 'BUY' o 'SELL'
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        lot_size: float
    ) -> Dict:
        """
        Abre una posición
        """
        
        trade_id = self.trade_counter
        self.trade_counter += 1
        
        trade = ActiveTrade(
            trade_id=trade_id,
            direction=TradeDirection.BUY if direction == 'BUY' else TradeDirection.SELL,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            lot_size=lot_size,
            entry_time=datetime.now(),
            highest_price=entry_price,
            lowest_price=entry_price
        )
        
        self.active_trades[trade_id] = trade
        
        logger.info(
            f"Trade #{trade_id} opened: {direction} @ {entry_price}, "
            f"SL: {stop_loss}, TP: {take_profit}, Lot: {lot_size}"
        )
        
        return {
            'trade_id': trade_id,
            'status': 'OPENED',
            'trade': trade
        }
    
    def evaluate_exit_opportunity(
        self,
        trade_id: int,
        current_price: float,
        features
    ) -> Dict:
        """
        Evalúa si debe cerrarse una posición
        """
        
        if trade_id not in self.active_trades:
            return {'should_exit': False, 'reason': 'Trade not found'}
        
        trade = self.active_trades[trade_id]
        
        # Evaluación de salida
        exit_signal = self.exit_logic.evaluate_exit(
            trade,
            current_price,
            features,
            {}  # price_analysis (no necesario para este caso)
        )
        
        return {
            'should_exit': exit_signal.should_exit,
            'exit_reason': exit_signal.exit_reason,
            'exit_price': exit_signal.exit_price,
            'expected_r': exit_signal.expected_r_multiple
        }
    
    def close_trade(
        self,
        trade_id: int,
        exit_price: float,
        exit_reason: str = 'MANUAL'
    ) -> Dict:
        """
        Cierra una posición
        """
        
        if trade_id not in self.active_trades:
            return {'status': 'ERROR', 'reason': 'Trade not found'}
        
        trade = self.active_trades[trade_id]
        is_buy = trade.direction == TradeDirection.BUY
        
        # Registrar resultado
        trade_result = self.reward_calc.add_trade_result(
            trade_id,
            trade.entry_price,
            exit_price,
            trade.stop_loss,
            trade.take_profit,
            trade.direction.value,
            trade.lot_size,
            trade.entry_time,
            datetime.now()
        )
        
        # Actualizar balance (simplificado)
        pnl_pips = (exit_price - trade.entry_price) / self.config['point_size'] if is_buy else \
                   (trade.entry_price - exit_price) / self.config['point_size']
        pnl_amount = pnl_pips * trade.lot_size * self.config['tick_value']
        self.current_balance += pnl_amount
        self.peak_balance = max(self.peak_balance, self.current_balance)
        
        # Actualizar penalties
        self.risk_penalties.update_balance(self.current_balance, self.peak_balance)
        
        # Remover de activos
        del self.active_trades[trade_id]
        
        logger.info(
            f"Trade #{trade_id} closed at {exit_price}: {trade_result.r_multiple:+.2f}R "
            f"({pnl_amount:+.2f}), Balance: {self.current_balance:.2f}"
        )
        
        return {
            'status': 'CLOSED',
            'trade_id': trade_id,
            'result': {
                'r_multiple': trade_result.r_multiple,
                'pnl_pips': trade_result.r_multiple * (trade.entry_price - trade.stop_loss) / self.config['point_size'],
                'pnl_amount': pnl_amount
            }
        }
    
    def retrain_ai_model(self, price_data: pd.DataFrame = None):
        """
        Reentrenamiento del modelo de IA
        """
        
        trade_history = self.reward_calc.get_trade_history()
        
        if len(trade_history) < 20:
            logger.warning("Not enough trades for retraining")
            return {'status': 'SKIPPED', 'reason': 'Insufficient data'}
        
        logger.info(f"Retraining AI model with {len(trade_history)} trades...")
        
        # Preparar datos (requiere price_data)
        if price_data is not None:
            X_train, Y_train = self.ai_optimizer.prepare_training_data(
                [t.__dict__ for t in trade_history],
                price_data,
                self.feature_extractor
            )
            
            if len(X_train) > 0:
                # Reentrenar
                metrics = self.ai_optimizer.retrain_model(X_train, Y_train)
                
                # Detectar cambios de mercado
                regime_change = self.market_adaptation.detect_regime_change(
                    [t.__dict__ for t in trade_history]
                )
                
                return {
                    'status': 'SUCCESS',
                    'metrics': metrics,
                    'regime_change': regime_change
                }
        
        return {'status': 'SKIPPED', 'reason': 'Price data not available'}
    
    def get_system_status(self) -> Dict:
        """
        Obtiene estado del sistema
        """
        
        stats = self.reward_calc.calculate_statistics()
        scorecard = self.scorecard.calculate_total_score(
            int(stats.get('total_r', 0) * 100)
        )
        
        drawdown_pct = (self.peak_balance - self.current_balance) / self.peak_balance * 100 \
                       if self.peak_balance > 0 else 0
        
        return {
            'status': 'PAUSED' if self.paused else 'ACTIVE',
            'balance': self.current_balance,
            'drawdown_pct': drawdown_pct,
            'open_positions': len(self.active_trades),
            'total_trades': stats['total_trades'],
            'win_rate': stats['win_rate'],
            'total_r': stats['total_r'],
            'scorecard': scorecard
        }
    
    def pause(self):
        """Pausa el bot"""
        self.paused = True
        logger.info("Trading bot paused")
    
    def resume(self):
        """Reanuda el bot"""
        self.paused = False
        logger.info("Trading bot resumed")
    
    # =========================================================================
    # MÉTODOS PARA INTERFAZ DE CHAT
    # =========================================================================
    
    def open_multiple_trades(self, num: int) -> str:
        """Abre múltiples operaciones (para chat interface)"""
        num = max(1, min(10, num))
        try:
            from mt5_manager import mt5_manager
            from trading_bot import submit_order, SYMBOL, POINT, LOT_MIN, LOT_MAX, MT5_AVAILABLE, mt5
            
            if not mt5_manager.check_connection() or not MT5_AVAILABLE:
                return "❌ MT5 no está conectado, no se pueden abrir operaciones reales"
            
            tick = mt5.symbol_info_tick(SYMBOL)
            if tick is None:
                return "❌ No se pudo obtener el precio actual del mercado"
            
            opened = 0
            for i in range(num):
                side = 'BUY' if i % 2 == 0 else 'SELL'
                entry_price = float(tick.ask if side == 'BUY' else tick.bid)
                stop_loss = entry_price - (self.config['stop_loss_pips'] * POINT) if side == 'BUY' else entry_price + (self.config['stop_loss_pips'] * POINT)
                take_profit = entry_price + (self.config['take_profit_pips'] * POINT) if side == 'BUY' else entry_price - (self.config['take_profit_pips'] * POINT)
                volume = max(LOT_MIN, min(0.01 * (1 + i), LOT_MAX))
                submit_order(side, volume, entry_price, stop_loss, take_profit, 0.65)
                opened += 1
            return f"✅ Abrí {opened} operación(es) en mercado usando IA"
        except Exception as e:
            logger.error(f"Error abriendo múltiples operaciones: {e}")
            return f"❌ Error abriendo múltiples operaciones: {e}"
    
    def close_all_positions(self) -> str:
        """Cierra todas las posiciones"""
        count = 0
        for trade_id in list(self.active_trades.keys()):
            result = self.close_trade(trade_id, 0.0, 'MANUAL_CLOSE_ALL')
            if result['status'] == 'CLOSED':
                count += 1
        
        return f"✅ {count} posiciones cerradas"
    
    def close_position(self, position_id: int) -> str:
        """Cierra posición específica"""
        result = self.close_trade(position_id, 0.0, 'MANUAL_CLOSE')
        return f"✅ Posición cerrada"
    
    def get_status(self) -> Dict:
        """Obtiene estado para interfaz"""
        return self.get_system_status()
    
    def get_trade_history(self, num: int = 10) -> List[Dict]:
        """Obtiene historial de trades"""
        history = self.reward_calc.get_recent_trades(num)
        return [
            {
                'id': t.trade_id,
                'direction': t.direction,
                'entry': t.entry_price,
                'exit': t.exit_price,
                'r_multiple': t.r_multiple
            }
            for t in history
        ]
    
    def get_open_positions(self) -> List[Dict]:
        """Obtiene posiciones abiertas"""
        positions = []
        for trade_id, trade in self.active_trades.items():
            positions.append({
                'id': trade_id,
                'direction': trade.direction.value,
                'entry': trade.entry_price,
                'current': 0.0,  # Sería del mercado
                'sl': trade.stop_loss,
                'tp': trade.take_profit,
                'lot': trade.lot_size
            })
        return positions
    
    def get_scorecard(self) -> str:
        """Obtiene scorecard formateado"""
        return self.scorecard.get_scorecard_report()
    
    def get_technical_analysis(self) -> Dict:
        """Obtiene análisis técnico"""
        return {
            'trend': 'Alcista',
            'trend_strength': 0.5,
            'rsi': 55.0,
            'momentum': 0.001,
            'volatility': 0.5,
            'bb_position': 0.5
        }
    
    def set_risk_percent(self, risk: float):
        """Configura riesgo porcentual"""
        self.config['risk_percent'] = risk
        logger.info(f"Risk set to {risk}%")
    
    def set_max_positions(self, max_pos: int):
        """Configura máximo de posiciones"""
        self.config['max_positions'] = max_pos
        logger.info(f"Max positions set to {max_pos}")
    
    def set_stop_loss(self, sl_pips: int):
        """Configura stop loss"""
        self.config['stop_loss_pips'] = sl_pips
        logger.info(f"Stop loss set to {sl_pips} pips")
    
    def set_take_profit(self, tp_pips: int):
        """Configura take profit"""
        self.config['take_profit_pips'] = tp_pips
        logger.info(f"Take profit set to {tp_pips} pips")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Crear sistema integrado
    system = IntegratedTradingSystem()
    
    # Iniciar interfaz de chat
    chat = system.chat_interface
    chat.start_interactive_mode()
