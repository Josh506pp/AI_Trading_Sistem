#!/usr/bin/env python3
"""
🤖 MOTOR DE IA - ANÁLISIS Y PREDICCIONES DE TRADING
Sistema de análisis técnico con ML para decisiones de trading
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json

class AIAnalyzer:
    """Analizador de IA para trading"""
    
    def __init__(self):
        self.window_size = 20
        self.min_confidence = 0.65
        
    def analyze_prices(self, prices: List[float]) -> Dict:
        """Analiza precios y retorna señales"""
        if len(prices) < self.window_size:
            return {'error': 'No hay suficientes datos'}
        
        # Convertir a numpy array
        prices_arr = np.array(prices[-self.window_size:], dtype=float)
        
        # Calcular indicadores técnicos
        indicators = self._calculate_indicators(prices_arr)
        
        # Generar señal
        signal = self._generate_signal(indicators, prices_arr)
        
        # Predicción
        prediction = self._predict_price(prices_arr)
        
        return {
            'current_price': float(prices[-1]),
            'indicators': indicators,
            'signal': signal,
            'prediction': prediction,
            'confidence': signal['confidence'],
            'action': signal['action'],  # 'BUY', 'SELL', 'HOLD'
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_indicators(self, prices: np.ndarray) -> Dict:
        """Calcula indicadores técnicos"""
        
        # SMA (Simple Moving Average)
        sma_5 = np.mean(prices[-5:])
        sma_10 = np.mean(prices[-10:])
        sma_20 = np.mean(prices)
        
        # RSI (Relative Strength Index)
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else np.mean(gains)
        avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else np.mean(losses)
        
        rs = avg_gain / avg_loss if avg_loss != 0 else 0
        rsi = 100 - (100 / (1 + rs)) if rs > 0 else 50
        
        # MACD (Moving Average Convergence Divergence)
        ema_12 = self._ema(prices, 12)
        ema_26 = self._ema(prices, 26)
        macd = ema_12 - ema_26
        signal_line = self._ema(np.array([macd]), 9)
        
        # Bollinger Bands
        std = np.std(prices)
        bb_middle = sma_20
        bb_upper = bb_middle + (std * 2)
        bb_lower = bb_middle - (std * 2)
        
        # ATR (Average True Range)
        atr = self._calculate_atr(prices)
        
        return {
            'sma_5': float(sma_5),
            'sma_10': float(sma_10),
            'sma_20': float(sma_20),
            'rsi': float(rsi),
            'macd': float(macd),
            'signal_line': float(signal_line),
            'bb_upper': float(bb_upper),
            'bb_middle': float(bb_middle),
            'bb_lower': float(bb_lower),
            'atr': float(atr),
            'trend': 'UPTREND' if sma_5 > sma_10 > sma_20 else ('DOWNTREND' if sma_5 < sma_10 < sma_20 else 'SIDEWAYS')
        }
    
    def _ema(self, prices: np.ndarray, period: int) -> float:
        """Calcula EMA (Exponential Moving Average)"""
        if len(prices) < period:
            return np.mean(prices)
        
        multiplier = 2 / (period + 1)
        ema = np.mean(prices[:period])
        
        for price in prices[period:]:
            ema = price * multiplier + ema * (1 - multiplier)
        
        return ema
    
    def _calculate_atr(self, prices: np.ndarray) -> float:
        """Calcula ATR (Average True Range)"""
        if len(prices) < 2:
            return 0
        
        tr_list = []
        for i in range(1, len(prices)):
            tr = max(
                prices[i] - prices[i-1],
                abs(prices[i] - prices[i-1])
            )
            tr_list.append(tr)
        
        return float(np.mean(tr_list[-14:]) if len(tr_list) >= 14 else np.mean(tr_list))
    
    def _generate_signal(self, indicators: Dict, prices: np.ndarray) -> Dict:
        """Genera señal de trading basada en indicadores"""
        
        score = 0
        signals = []
        
        # Regla 1: Trend (SMA)
        if indicators['trend'] == 'UPTREND':
            score += 2
            signals.append('✅ SMA: Tendencia al alza')
        elif indicators['trend'] == 'DOWNTREND':
            score -= 2
            signals.append('❌ SMA: Tendencia a la baja')
        else:
            signals.append('➡️ SMA: Lateral')
        
        # Regla 2: RSI
        if indicators['rsi'] < 30:
            score += 2
            signals.append('✅ RSI: Sobreventa (compra)')
        elif indicators['rsi'] > 70:
            score -= 2
            signals.append('❌ RSI: Sobrecompra (venta)')
        else:
            signals.append('➡️ RSI: Neutral')
        
        # Regla 3: MACD
        if indicators['macd'] > indicators['signal_line']:
            score += 1
            signals.append('✅ MACD: Alcista')
        else:
            score -= 1
            signals.append('❌ MACD: Bajista')
        
        # Regla 4: Bollinger Bands
        current_price = prices[-1]
        if current_price < indicators['bb_lower']:
            score += 1.5
            signals.append('✅ BB: Precio bajo banda (rebote)')
        elif current_price > indicators['bb_upper']:
            score -= 1.5
            signals.append('❌ BB: Precio alto banda')
        
        # Determinar acción
        confidence = min(abs(score) / 5.0, 0.95)  # Normalizar a 0-0.95
        
        if score > 1.5:
            action = 'BUY'
        elif score < -1.5:
            action = 'SELL'
        else:
            action = 'HOLD'
        
        return {
            'action': action,
            'score': float(score),
            'confidence': float(confidence),
            'signals': signals
        }
    
    def _predict_price(self, prices: np.ndarray) -> Dict:
        """Predice precio futuro usando tendencia"""
        
        # Regresión lineal simple
        x = np.arange(len(prices))
        slope = np.polyfit(x, prices, 1)[0]
        
        # Predicción 5 períodos adelante
        next_5 = prices[-1] + (slope * 5)
        
        # Predicción 10 períodos adelante
        next_10 = prices[-1] + (slope * 10)
        
        # R-múltiple esperado (riesgo/recompensa)
        atr = self._calculate_atr(prices)
        if atr > 0:
            r_multiple = abs(next_10 - prices[-1]) / atr
        else:
            r_multiple = 1.0
        
        return {
            'next_5_periods': float(next_5),
            'next_10_periods': float(next_10),
            'expected_r_multiple': float(r_multiple),
            'direction': 'UP' if slope > 0 else 'DOWN',
            'slope': float(slope)
        }
    
    def get_market_condition(self, analysis: Dict) -> Dict:
        """Retorna condiciones del mercado"""
        
        indicators = analysis.get('indicators', {})
        signal = analysis.get('signal', {})
        
        condition = 'NEUTRAL'
        strength = 'WEAK'
        
        if signal.get('action') == 'BUY' and signal.get('confidence', 0) > 0.7:
            condition = 'BULLISH'
            strength = 'STRONG'
        elif signal.get('action') == 'BUY':
            condition = 'BULLISH'
            strength = 'WEAK'
        elif signal.get('action') == 'SELL' and signal.get('confidence', 0) > 0.7:
            condition = 'BEARISH'
            strength = 'STRONG'
        elif signal.get('action') == 'SELL':
            condition = 'BEARISH'
            strength = 'WEAK'
        
        return {
            'market_condition': condition,
            'strength': strength,
            'recommendation': signal.get('action', 'HOLD'),
            'confidence': signal.get('confidence', 0)
        }


class TradingEngine:
    """Motor de trading que ejecuta operaciones"""
    
    def __init__(self):
        self.open_trades = {}
        self.closed_trades = []
        self.balance = 10000.0  # Balance inicial
        self.equity = 10000.0
        self.max_position_size = 0.05  # 5% del balance
        self.ai_analyzer = AIAnalyzer()
        self.trade_id_counter = 1
    
    def evaluate_entry(self, analysis: Dict, current_price: float) -> Dict:
        """Evalúa si abrir una posición"""
        
        action = analysis.get('signal', {}).get('action', 'HOLD')
        confidence = analysis.get('signal', {}).get('confidence', 0)
        
        if action == 'HOLD' or confidence < 0.65:
            return {
                'should_trade': False,
                'reason': f'{action} o confianza baja ({confidence:.2%})'
            }
        
        # Calcular tamaño de posición
        indicators = analysis.get('indicators', {})
        atr = indicators.get('atr', 0.01)
        
        # Risk 1% del balance
        risk_amount = self.balance * 0.01
        position_size = risk_amount / atr if atr > 0 else 100
        
        # Limitar tamaño
        max_size = self.balance * self.max_position_size
        position_size = min(position_size, max_size)
        
        # Calcular stop loss y take profit
        if action == 'BUY':
            stop_loss = current_price - (atr * 2)
            take_profit = current_price + (atr * 4)
        else:  # SELL
            stop_loss = current_price + (atr * 2)
            take_profit = current_price - (atr * 4)
        
        # R-múltiple
        r_multiple = abs(take_profit - current_price) / abs(current_price - stop_loss) if current_price != stop_loss else 1
        
        return {
            'should_trade': True,
            'action': action,
            'entry_price': float(current_price),
            'stop_loss': float(stop_loss),
            'take_profit': float(take_profit),
            'position_size': float(position_size),
            'r_multiple': float(r_multiple),
            'confidence': float(confidence)
        }
    
    def open_trade(self, action: str, entry_price: float, stop_loss: float,
                   take_profit: float, position_size: float, symbol: str = 'EURUSD') -> Dict:
        """Abre una nueva operación"""
        
        trade_id = self.trade_id_counter
        self.trade_id_counter += 1
        
        trade = {
            'id': trade_id,
            'symbol': symbol,
            'action': action,
            'entry_price': float(entry_price),
            'stop_loss': float(stop_loss),
            'take_profit': float(take_profit),
            'position_size': float(position_size),
            'entry_time': datetime.now().isoformat(),
            'status': 'OPEN',
            'profit_loss': 0,
            'profit_loss_pct': 0
        }
        
        self.open_trades[trade_id] = trade
        
        # Actualizar equity
        self.equity = self.balance + sum([t.get('profit_loss', 0) for t in self.open_trades.values()])
        
        return trade
    
    def close_trade(self, trade_id: int, close_price: float) -> Dict:
        """Cierra una operación"""
        
        if trade_id not in self.open_trades:
            return {'error': 'Trade no encontrado'}
        
        trade = self.open_trades[trade_id]
        
        if trade['action'] == 'BUY':
            profit_loss = (close_price - trade['entry_price']) * trade['position_size']
        else:
            profit_loss = (trade['entry_price'] - close_price) * trade['position_size']
        
        profit_loss_pct = (profit_loss / (trade['entry_price'] * trade['position_size'])) * 100
        
        trade['exit_price'] = float(close_price)
        trade['close_time'] = datetime.now().isoformat()
        trade['status'] = 'CLOSED'
        trade['profit_loss'] = float(profit_loss)
        trade['profit_loss_pct'] = float(profit_loss_pct)
        
        # Actualizar balance
        self.balance += profit_loss
        
        # Mover a closed trades
        self.closed_trades.append(trade)
        del self.open_trades[trade_id]
        
        # Actualizar equity
        self.equity = self.balance + sum([t.get('profit_loss', 0) for t in self.open_trades.values()])
        
        return trade
    
    def update_trades(self, current_price: float) -> Dict:
        """Actualiza operaciones abiertas con precio actual"""
        
        updated_trades = []
        
        for trade_id, trade in list(self.open_trades.items()):
            if trade['action'] == 'BUY':
                profit_loss = (current_price - trade['entry_price']) * trade['position_size']
            else:
                profit_loss = (trade['entry_price'] - current_price) * trade['position_size']
            
            profit_loss_pct = (profit_loss / (trade['entry_price'] * trade['position_size'])) * 100
            
            trade['current_price'] = float(current_price)
            trade['profit_loss'] = float(profit_loss)
            trade['profit_loss_pct'] = float(profit_loss_pct)
            
            # Verificar stop loss o take profit
            if trade['action'] == 'BUY':
                if current_price <= trade['stop_loss']:
                    self.close_trade(trade_id, trade['stop_loss'])
                    updated_trades.append({'id': trade_id, 'reason': 'STOP LOSS'})
                elif current_price >= trade['take_profit']:
                    self.close_trade(trade_id, trade['take_profit'])
                    updated_trades.append({'id': trade_id, 'reason': 'TAKE PROFIT'})
            else:
                if current_price >= trade['stop_loss']:
                    self.close_trade(trade_id, trade['stop_loss'])
                    updated_trades.append({'id': trade_id, 'reason': 'STOP LOSS'})
                elif current_price <= trade['take_profit']:
                    self.close_trade(trade_id, trade['take_profit'])
                    updated_trades.append({'id': trade_id, 'reason': 'TAKE PROFIT'})
        
        # Actualizar equity
        self.equity = self.balance + sum([t.get('profit_loss', 0) for t in self.open_trades.values()])
        
        return {
            'closed': updated_trades,
            'balance': float(self.balance),
            'equity': float(self.equity),
            'open_trades_count': len(self.open_trades)
        }
    
    def get_statistics(self) -> Dict:
        """Retorna estadísticas de trading"""
        
        if len(self.closed_trades) == 0:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_profit_loss': 0,
                'avg_profit': 0,
                'largest_win': 0,
                'largest_loss': 0
            }
        
        winning_trades = [t for t in self.closed_trades if t['profit_loss'] > 0]
        losing_trades = [t for t in self.closed_trades if t['profit_loss'] < 0]
        
        total_profit_loss = sum([t['profit_loss'] for t in self.closed_trades])
        
        return {
            'total_trades': len(self.closed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': float(len(winning_trades) / len(self.closed_trades) * 100) if len(self.closed_trades) > 0 else 0,
            'total_profit_loss': float(total_profit_loss),
            'avg_profit': float(np.mean([t['profit_loss'] for t in self.closed_trades])) if len(self.closed_trades) > 0 else 0,
            'largest_win': float(max([t['profit_loss'] for t in winning_trades])) if winning_trades else 0,
            'largest_loss': float(min([t['profit_loss'] for t in losing_trades])) if losing_trades else 0
        }
