#!/usr/bin/env python3
"""
🤖 MOTOR DE IA - ANÁLISIS Y PREDICCIONES DE TRADING
Sistema simplificado sin dependencias pesadas
"""

from datetime import datetime
from typing import Dict, List

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False

class AIAnalyzer:
    """Analizador de IA para trading - SIN NUMPY"""
    
    def __init__(self):
        self.window_size = 20
        
    def analyze_prices(self, prices: List[float]) -> Dict:
        """Analiza precios y retorna señales"""
        if len(prices) < self.window_size:
            return {'error': 'Datos insuficientes'}
        
        recent = prices[-self.window_size:]
        indicators = self._indicators(recent)
        signal = self._signal(indicators, recent)
        prediction = self._predict(recent)
        
        return {
            'current_price': float(prices[-1]),
            'indicators': indicators,
            'signal': signal,
            'prediction': prediction,
            'confidence': signal['confidence'],
            'action': signal['action'],
            'timestamp': datetime.now().isoformat()
        }
    
    def _indicators(self, prices: List[float]) -> Dict:
        """Calcula indicadores"""
        sma_5 = sum(prices[-5:]) / min(5, len(prices))
        sma_10 = sum(prices[-10:]) / min(10, len(prices))
        sma_20 = sum(prices) / len(prices)
        
        # RSI
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = sum([d for d in deltas if d > 0]) / len(deltas) if deltas else 0.0001
        losses = sum([abs(d) for d in deltas if d < 0]) / len(deltas) if deltas else 0.0001
        
        rs = gains / losses if losses > 0 else 1
        rsi = 100 - (100 / (1 + rs)) if rs > 0 else 50
        
        # Trend
        trend = 'UP' if sma_5 > sma_10 > sma_20 else ('DOWN' if sma_5 < sma_10 < sma_20 else 'SIDE')
        
        return {
            'sma_5': float(sma_5),
            'sma_10': float(sma_10),
            'sma_20': float(sma_20),
            'rsi': float(rsi),
            'trend': trend
        }
    
    def _signal(self, ind: Dict, prices: List[float]) -> Dict:
        """Genera señal"""
        score = 0
        
        if ind['trend'] == 'UP':
            score += 2
        elif ind['trend'] == 'DOWN':
            score -= 2
        
        if ind['rsi'] < 30:
            score += 2
        elif ind['rsi'] > 70:
            score -= 2
        
        current = prices[-1]
        mean = ind['sma_20']
        if current < mean * 0.98:
            score += 1
        elif current > mean * 1.02:
            score -= 1
        
        confidence = min(abs(score) / 5.0, 0.95)
        action = 'BUY' if score > 1.5 else ('SELL' if score < -1.5 else 'HOLD')
        
        return {'action': action, 'score': float(score), 'confidence': float(confidence)}
    
    def _predict(self, prices: List[float]) -> Dict:
        """Predice precio"""
        change = sum([prices[i] - prices[i-1] for i in range(max(0, len(prices)-5), len(prices))])
        avg_change = change / min(5, len(prices))
        
        return {
            'next_5': float(prices[-1] + avg_change * 5),
            'next_10': float(prices[-1] + avg_change * 10),
            'direction': 'UP' if avg_change > 0 else 'DOWN'
        }


class TradingEngine:
    """Motor de trading"""
    
    def __init__(self):
        self.trades = {}
        self.closed = []
        self.balance = 10000.0
        self.equity = 10000.0
        self.id = 1
        self.ai = AIAnalyzer()
        self.use_mt5 = MT5_AVAILABLE
    
    def open_trade(self, action: str, price: float) -> Dict:
        """Abre trade"""
        tid = self.id
        self.id += 1
        
        trade = {
            'id': tid,
            'action': action,
            'entry': float(price),
            'time': datetime.now().isoformat(),
            'size': 0.01,  # Volume for MT5
            'sl': float(price - 0.001) if action == 'BUY' else float(price + 0.001),
            'tp': float(price + 0.002) if action == 'BUY' else float(price - 0.002),
            'pl': 0,
            'pct': 0,
            'ticket': None
        }
        
        if self.use_mt5:
            order_type = mt5.ORDER_TYPE_BUY if action == 'BUY' else mt5.ORDER_TYPE_SELL
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": "EURUSD",
                "volume": trade['size'],
                "type": order_type,
                "price": price,
                "sl": trade['sl'],
                "tp": trade['tp'],
                "deviation": 20,
                "magic": 234000,
                "comment": f"AI Trade {tid}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                trade['ticket'] = result.order
            else:
                # If MT5 fails, still simulate
                pass
        
        self.trades[tid] = trade
        return trade
    
    def update(self, price: float):
        """Actualiza trades"""
        for tid, t in list(self.trades.items()):
            if t['action'] == 'BUY':
                t['pl'] = (price - t['entry']) * t['size']
            else:
                t['pl'] = (t['entry'] - price) * t['size']
            t['pct'] = (t['pl'] / (t['entry'] * t['size'])) * 100
            
            should_close = False
            if t['action'] == 'BUY':
                if price <= t['sl']:
                    should_close = True
                elif price >= t['tp']:
                    if t['pct'] >= 1.5 or price >= t['tp'] * 1.2:
                        should_close = True
            else:
                if price >= t['sl']:
                    should_close = True
                elif price <= t['tp']:
                    if t['pct'] >= 1.5 or price <= t['tp'] * 0.8:
                        should_close = True
            
            if should_close:
                self.balance += t['pl']
                self.closed.append(t)
                del self.trades[tid]
        
        self.equity = self.balance + sum([t['pl'] for t in self.trades.values()])
    
    def close_trade(self, trade_id: int, price: float = None) -> Dict:
        """Cierra un trade manualmente"""
        if trade_id not in self.trades:
            return {}
        trade = self.trades[trade_id]
        if price is None:
            price = trade['entry']
        
        if self.use_mt5 and trade.get('ticket'):
            try:
                close_request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": "EURUSD",
                    "volume": trade['size'],
                    "type": mt5.ORDER_TYPE_SELL if trade['action'] == 'BUY' else mt5.ORDER_TYPE_BUY,
                    "position": trade['ticket'],
                    "price": price,
                    "deviation": 20,
                    "magic": 234000,
                    "comment": f"Close AI Trade {trade_id}",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
                result = mt5.order_send(close_request)
                if result and result.retcode != mt5.TRADE_RETCODE_DONE:
                    # If MT5 fails, still close locally
                    pass
            except Exception:
                pass
        
        if trade['action'] == 'BUY':
            trade['pl'] = (price - trade['entry']) * (trade['size'] * 100000)
        else:
            trade['pl'] = (trade['entry'] - price) * (trade['size'] * 100000)
        trade['pct'] = (trade['pl'] / (trade['entry'] * trade['size'] * 100000)) * 100
        self.balance += trade['pl']
        self.closed.append(trade)
        del self.trades[trade_id]
        self.equity = self.balance + sum([t['pl'] for t in self.trades.values()])
        return trade

    def close_all(self, price: float = None) -> List[Dict]:
        """Cierra todos los trades abiertos"""
        closed = []
        for trade_id in list(self.trades.keys()):
            closed_trade = self.close_trade(trade_id, price)
            if closed_trade:
                closed.append(closed_trade)
        return closed

    def stats(self) -> Dict:
        """Estadísticas"""
        if not self.closed:
            return {'total': 0, 'wins': 0, 'losses': 0, 'wr': 0, 'pl': 0}
        
        wins = len([t for t in self.closed if t['pl'] > 0])
        losses = len([t for t in self.closed if t['pl'] < 0])
        pl = sum([t['pl'] for t in self.closed])
        
        return {
            'total': len(self.closed),
            'wins': wins,
            'losses': losses,
            'wr': float(wins / len(self.closed) * 100) if self.closed else 0,
            'pl': float(pl)
        }
