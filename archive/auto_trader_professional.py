#!/usr/bin/env python3
"""
AUTO TRADER PROFESIONAL - Trading Automático con IA Avanzada
Sistema que ejecuta operaciones automáticas basadas en razonamiento mejorado
"""

import os
import time
import threading
import json
from datetime import datetime
from typing import Dict, List, Optional

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

# Importar los componentes de profesional
try:
    from professional_trading_system import AIAnalyzer, TradingEngine, logger
except ImportError:
    print("⚠️ Error importando professional_trading_system.py")
    # Fallback a importación desde app.py
    from app import analyze_signal, TRADING_DATA, PRICE_LOCK
    AIAnalyzer = None
    TradingEngine = None


class RazonamientoAvanzado:
    """Sistema de razonamiento mejorado para decisiones de trading más asertadas"""
    
    def __init__(self):
        self.historial_decisiones = []
        self.umbral_confirmacion = 0.75  # 75% de confirmación requerida
    
    def analizar_consistencia(self, signal: Dict, indicators: Dict) -> float:
        """Analiza consistencia entre indicadores para confirmar señal"""
        consistencia = 0.0
        factores = 0
        
        action = signal['action']
        
        # 1. RSI confirmación
        if 'rsi' in indicators:
            rsi = indicators['rsi'].get('value', 50)
            if action == 'BUY' and rsi < 70:  # No sobrecomprado
                consistencia += 0.2
            elif action == 'SELL' and rsi > 30:  # No sobrevendido
                consistencia += 0.2
            factores += 1
        
        # 2. MACD confirmación
        if 'macd' in indicators:
            macd_signal = indicators['macd'].get('signal', 0)
            if action == 'BUY' and macd_signal > 0:
                consistencia += 0.2
            elif action == 'SELL' and macd_signal < 0:
                consistencia += 0.2
            factores += 1
        
        # 3. Bollinger Bands confirmación
        if 'bollinger_bands' in indicators:
            bb = indicators['bollinger_bands']
            if action == 'BUY' and bb.get('position', 'middle') == 'lower':
                consistencia += 0.15
            elif action == 'SELL' and bb.get('position', 'middle') == 'upper':
                consistencia += 0.15
            factores += 1
        
        # 4. Stochastic confirmación
        if 'stochastic' in indicators:
            stoch_k = indicators['stochastic'].get('k', 50)
            if action == 'BUY' and stoch_k < 80:
                consistencia += 0.15
            elif action == 'SELL' and stoch_k > 20:
                consistencia += 0.15
            factores += 1
        
        # 5. Momentum confirmación
        if 'momentum' in indicators:
            momentum = indicators['momentum'].get('value', 0)
            if action == 'BUY' and momentum > 0:
                consistencia += 0.15
            elif action == 'SELL' and momentum < 0:
                consistencia += 0.15
            factores += 1
        
        # 6. Patrón de precio confirmación
        pattern = signal.get('pattern', 'UNKNOWN')
        if action == 'BUY' and pattern in ['BULLISH_ENGULFING', 'ASCENDING']:
            consistencia += 0.15
        elif action == 'SELL' and pattern in ['BEARISH_REJECTION', 'DESCENDING']:
            consistencia += 0.15
        factores += 1
        
        return consistencia / factores if factores > 0 else 0.0
    
    def evaluar_riesgo_rentabilidad(self, signal: Dict, indicators: Dict) -> Dict:
        """Evalúa el ratio riesgo/rentabilidad potencial"""
        atr = indicators.get('atr', 0.001)
        confidence = signal.get('confidence', 0)
        
        # Calcular SL y TP basado en ATR
        sl_distance = atr * 2  # 2x ATR stop loss
        tp_distance = atr * 4  # 4x ATR take profit (ratio 1:4)
        
        # Evaluar calidad del setup
        calidad_setup = 0.0
        
        # 1. Confianza de la señal
        calidad_setup += confidence * 0.4
        
        # 2. Consistencia de indicadores
        consistencia = self.analizar_consistencia(signal, indicators)
        calidad_setup += consistencia * 0.4
        
        # 3. Volatilidad apropiada
        volatility = indicators.get('volatility', {}).get('regime', 'NORMAL')
        if volatility == 'NORMAL':
            calidad_setup += 0.2
        elif volatility == 'HIGH':
            calidad_setup += 0.1  # Menos favorable
        
        return {
            'ratio_riesgo_rentabilidad': tp_distance / sl_distance if sl_distance > 0 else 0,
            'calidad_setup': calidad_setup,
            'sl_distance': sl_distance,
            'tp_distance': tp_distance,
            'consistencia': consistencia
        }
    
    def decision_final(self, signal: Dict, indicators: Dict) -> Dict:
        """Toma decisión final con razonamiento mejorado"""
        
        # Evaluar consistencia
        consistencia = self.analizar_consistencia(signal, indicators)
        
        # Evaluar riesgo/rentabilidad
        evaluacion_rr = self.evaluar_riesgo_rentabilidad(signal, indicators)
        
        # Puntuación final
        puntuacion_final = (
            signal.get('confidence', 0) * 0.4 +  # Confianza original
            consistencia * 0.4 +                  # Consistencia
            evaluacion_rr['calidad_setup'] * 0.2  # Calidad del setup
        )
        
        # Decisión basada en umbrales
        if puntuacion_final >= self.umbral_confirmacion and signal['action'] != 'HOLD':
            decision = 'EJECUTAR'
        elif puntuacion_final >= 0.6:
            decision = 'OBSERVAR'
        else:
            decision = 'RECHAZAR'
        
        # Registrar decisión
        self.historial_decisiones.append({
            'timestamp': datetime.now().isoformat(),
            'signal': signal,
            'consistencia': consistencia,
            'evaluacion_rr': evaluacion_rr,
            'puntuacion_final': puntuacion_final,
            'decision': decision
        })
        
        # Mantener solo últimas 100 decisiones
        if len(self.historial_decisiones) > 100:
            self.historial_decisiones = self.historial_decisiones[-100:]
        
        return {
            'decision': decision,
            'puntuacion_final': puntuacion_final,
            'razones': {
                'consistencia_indicadores': f"{consistencia:.1%}",
                'ratio_rr': f"{evaluacion_rr['ratio_riesgo_rentabilidad']:.1f}:1",
                'calidad_setup': f"{evaluacion_rr['calidad_setup']:.1%}",
                'confianza_original': f"{signal.get('confidence', 0):.1%}"
            },
            'recomendacion': self._generar_recomendacion(decision, evaluacion_rr)
        }
    
    def _generar_recomendacion(self, decision: str, evaluacion_rr: Dict) -> str:
        """Genera recomendación detallada"""
        if decision == 'EJECUTAR':
            ratio = evaluacion_rr['ratio_riesgo_rentabilidad']
            if ratio >= 3:
                return "Excelente setup con alto ratio riesgo/rentabilidad. Ejecutar inmediatamente."
            elif ratio >= 2:
                return "Buen setup con ratio aceptable. Ejecutar con posición normal."
            else:
                return "Setup aceptable pero con ratio bajo. Considerar reducción de posición."
        
        elif decision == 'OBSERVAR':
            return "Setup prometedor pero requiere más confirmación. Observar próximos precios."
        
        else:
            return "Setup no cumple criterios mínimos. Esperar mejor oportunidad."


class AutoTrader:
    """Sistema de auto-trading automático con IA avanzada y razonamiento mejorado"""
    
    def __init__(self):
        self.engine = TradingEngine() if TradingEngine else None
        self.ai = AIAnalyzer() if AIAnalyzer else None
        self.razonamiento = RazonamientoAvanzado()  # Sistema de razonamiento mejorado
        self.running = False
        self.config = self._load_config()
        self.stats = {
            'total_signals': 0,
            'trades_ejecutados': 0,
            'trades_observados': 0,
            'trades_rechazados': 0,
            'wins': 0,
            'losses': 0,
            'total_pl': 0,
            'start_time': datetime.now().isoformat()
        }
        
    def _load_config(self) -> Dict:
        """Carga configuración de auto-trading"""
        config_file = 'auto_trader_config.json'
        
        default_config = {
            'enabled': True,
            'min_confidence': 0.70,  # Mínimo 70% confianza
            'max_daily_trades': 50,  # Máximo 50 trades por día
            'stop_loss_pct': 2.0,  # 2% stop loss
            'take_profit_pct': 5.0,  # 5% take profit
            'risk_per_trade': 2.0,  # 2% riesgo por trade
            'max_concurrent_positions': 5,  # Máximo 5 posiciones abiertas
            'use_mt5': False,  # Usar MT5 si está disponible
            'trading_hours': {
                'start': 8,  # 8 AM
                'end': 22    # 10 PM
            }
        }
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    saved_config = json.load(f)
                    default_config.update(saved_config)
            except Exception as e:
                print(f"⚠️ Error cargando config: {e}, usando configuración por defecto")
        
        return default_config
    
    def _save_config(self):
        """Guarda configuración"""
        with open('auto_trader_config.json', 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def _is_trading_hours(self) -> bool:
        """Verifica si es horario de trading"""
        now = datetime.now()
        start = self.config['trading_hours']['start']
        end = self.config['trading_hours']['end']
        
        return start <= now.hour < end
    
    def generate_signal(self, prices: List[float]) -> Optional[Dict]:
        """Genera señal usando IA avanzada"""
        if not self.ai or len(prices) < 50:
            return None
        
        result = self.ai.analyze_prices(prices)
        
        if 'error' in result:
            return None
        
        self.stats['total_signals'] += 1
        return result
    
    def should_execute_trade(self, signal: Dict, indicators: Dict) -> Dict:
        """Verifica si se debe ejecutar un trade usando razonamiento mejorado"""
        
        # Aplicar razonamiento avanzado
        decision_razonamiento = self.razonamiento.decision_final(signal, indicators)
        
        # Criterios básicos
        criterios_basicos = [
            ('enabled', self.config['enabled']),
            ('trading_hours', self._is_trading_hours()),
            ('not_hold', signal['action'] != 'HOLD'),
            ('positions_limit', len(self.engine.trades) < self.config['max_concurrent_positions']),
            ('daily_limit', self.stats['trades_ejecutados'] < self.config['max_daily_trades'])
        ]
        
        # Verificar criterios básicos
        for check_name, result in criterios_basicos:
            if not result:
                decision_razonamiento['decision'] = 'RECHAZAR'
                decision_razonamiento['razones']['criterio_fallido'] = check_name
                break
        
        # Actualizar estadísticas según decisión
        if decision_razonamiento['decision'] == 'EJECUTAR':
            self.stats['trades_ejecutados'] += 1
        elif decision_razonamiento['decision'] == 'OBSERVAR':
            self.stats['trades_observados'] += 1
        else:
            self.stats['trades_rechazados'] += 1
        
        return decision_razonamiento
    
    def execute_trade(self, signal: Dict, indicators: Dict, current_price: float) -> Optional[Dict]:
        """Ejecuta un trade basado en la señal con razonamiento mejorado"""
        
        if not self.engine:
            return None
        
        # Verificar con razonamiento mejorado
        decision = self.should_execute_trade(signal, indicators)
        
        if decision['decision'] != 'EJECUTAR':
            print(f"❌ TRADE RECHAZADO: {decision['decision']}")
            print(f"   Razones: {decision['razones']}")
            print(f"   Recomendación: {decision['recomendacion']}")
            return None
        
        # Ejecutar trade con motor de trading
        trade = self.engine.execute_signal(signal, current_price, indicators.get('atr', 0.001))
        
        if trade:
            print(f"✅ TRADE EJECUTADO: {signal['action']} @ {current_price:.5f}")
            print(f"   Confianza: {signal['confidence']:.1%}")
            print(f"   Puntuación Final: {decision['puntuacion_final']:.1%}")
            print(f"   SL: {trade['sl']:.5f} | TP: {trade['tp']:.5f}")
            print(f"   Recomendación: {decision['recomendacion']}")
            return trade
        
        return None
    
    def update_trades(self, current_price: float):
        """Actualiza todos los trades abiertos"""
        if not self.engine:
            return
        
        self.engine.update(current_price)
        
        # Actualizar estadísticas
        recent_closed = [t for t in self.engine.closed[-10:]]  # Últimos 10 trades
        for trade in recent_closed:
            if trade['pl'] > 0:
                self.stats['wins'] += 1
            else:
                self.stats['losses'] += 1
            self.stats['total_pl'] += trade['pl']
    
    def get_status(self) -> Dict:
        """Obtiene estado actual del auto-trader"""
        if not self.engine:
            return {'error': 'Engine not available'}
        
        win_rate = (self.stats['wins'] / (self.stats['wins'] + self.stats['losses']) * 100) if (self.stats['wins'] + self.stats['losses']) > 0 else 0
        
        return {
            'running': self.running,
            'config': self.config,
            'stats': {
                **self.stats,
                'win_rate': f"{win_rate:.1f}%",
                'open_positions': len(self.engine.trades),
                'closed_trades': len(self.engine.closed),
                'balance': self.engine.balance,
                'equity': self.engine.equity,
                'daily_trades': self.stats['trades_executed']            },
            'razonamiento': {
                'ultimas_decisiones': self.razonamiento.historial_decisiones[-5:],  # Últimas 5 decisiones
                'estadisticas_razonamiento': {
                    'total_decisiones': len(self.razonamiento.historial_decisiones),
                    'ejecutadas': self.stats['trades_ejecutados'],
                    'observadas': self.stats['trades_observados'],
                    'rechazadas': self.stats['trades_rechazados']
                }            }
        }
    
    def start(self, price_generator=None):
        """Inicia el auto-trader"""
        self.running = True
        print("\n" + "="*70)
        print("  🤖 AUTO TRADER PROFESIONAL - INICIANDO")
        print("="*70)
        print(f"⚙️  Confianza mínima: {self.config['min_confidence']:.1%}")
        print(f"📍 Max posiciones: {self.config['max_concurrent_positions']}")
        print(f"💰 Trades máximos/día: {self.config['max_daily_trades']}")
        print("="*70 + "\n")
        
        prices = [1.0850 + i * 0.0001 for i in range(50)]  # Precios iniciales simulados
        
        try:
            while self.running:
                # Simular/obtener precio actual
                if price_generator:
                    prices.append(price_generator())
                else:
                    # Simulación simple
                    import random
                    prices.append(prices[-1] + random.uniform(-0.00005, 0.00005))
                
                if len(prices) > 100:
                    prices = prices[-100:]
                
                current_price = prices[-1]
                
                # Generar señal
                signal = self.generate_signal(prices)
                
                if signal and signal['signal']['action'] != 'HOLD':
                    print(f"\n📊 SEÑAL GENERADA:")
                    print(f"   Acción: {signal['signal']['action']}")
                    print(f"   Confianza: {signal['confidence']:.1%}")
                    print(f"   Precio: {current_price:.5f}")
                    
                    # Ejecutar con razonamiento mejorado
                    self.execute_trade(signal['signal'], signal.get('indicators', {}), current_price)
                
                # Actualizar trades
                self.update_trades(current_price)
                
                # Mostrar estado cada 10 segundos
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Auto-trader detenido por usuario")
        except Exception as e:
            print(f"\n❌ Error en auto-trader: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Detiene el auto-trader"""
        self.running = False
        status = self.get_status()
        
        print("\n" + "="*70)
        print("  📊 RESUMEN FINAL")
        print("="*70)
        print(f"Señales generadas: {self.stats['total_signals']}")
        print(f"Trades ejecutados: {self.stats['trades_executed']}")
        print(f"Posiciones ganadas: {self.stats['wins']}")
        print(f"Posiciones perdidas: {self.stats['losses']}")
        print(f"P&L Total: {self.stats['total_pl']:.2f}")
        if self.engine:
            print(f"Balance: ${self.engine.balance:.2f}")
            print(f"Equity: ${self.engine.equity:.2f}")
        print("="*70 + "\n")
        
        # Guardar estadísticas
        with open('auto_trader_stats.json', 'w') as f:
            json.dump(status['stats'], f, indent=2)


def run_professional_auto_trader():
    """Ejecuta el auto-trader profesional"""
    
    print("\n🚀 INICIANDO AUTO TRADER PROFESIONAL CON IA AVANZADA\n")
    
    # Crear auto-trader
    trader = AutoTrader()
    
    # Iniciar en thread separado para no bloquear
    trader_thread = threading.Thread(target=trader.start, daemon=True)
    trader_thread.start()
    
    # Mantener la consola abierta para mostrar estado
    try:
        while trader.running:
            time.sleep(30)
            status = trader.get_status()
            if 'stats' in status:
                print(f"\n📈 Estado actual:")
                print(f"   Trades abiertos: {status['stats']['open_positions']}")
                print(f"   Trades ejecutados hoy: {status['stats']['daily_trades']}")
                print(f"   Balance: ${status['stats']['balance']:.2f}")
                print(f"   Equity: ${status['stats']['equity']:.2f}")
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo auto-trader...")
        trader.stop()
        trader_thread.join(timeout=5)


if __name__ == "__main__":
    run_professional_auto_trader()
