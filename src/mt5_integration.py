#!/usr/bin/env python3
"""
MT5 INTEGRATION SYSTEM - Conecta Bot, IA y MetaTrader 5
Sistema completo para trading automático integrado
"""

import os
import time
import threading
import json
import logging
from datetime import datetime
from typing import Dict, Optional, List

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

from .professional_trading_system import AIAnalyzer, TradingEngine

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MT5Manager:
    """Gestor de conexión con MetaTrader 5"""
    
    def __init__(self):
        self.connected = False
        self.account_info = None
        self.mt5_available = MT5_AVAILABLE
        
    def connect(self, login: int, password: str, server: str, path: str = None) -> Dict:
        """Conecta a MetaTrader 5"""
        if not self.mt5_available:
            return {'success': False, 'error': 'MetaTrader5 no está instalado'}
        
        try:
            # Inicializar MT5
            if path:
                result = mt5.initialize(path=path)
            else:
                result = mt5.initialize()
            
            if not result:
                return {'success': False, 'error': 'Error al inicializar MT5'}
            
            # Login
            if not mt5.login(login=login, password=password, server=server):
                mt5.shutdown()
                return {'success': False, 'error': 'Login fallido. Verifica credenciales.'}
            
            # Obtener info de cuenta
            self.account_info = mt5.account_info()
            if not self.account_info:
                mt5.shutdown()
                return {'success': False, 'error': 'No se pudo obtener info de cuenta'}
            
            self.connected = True
            logger.info(f"✅ Conectado a MT5: {login} en {server}")
            
            return {
                'success': True,
                'account': self.account_info.login,
                'server': self.account_info.server,
                'balance': float(self.account_info.balance),
                'equity': float(self.account_info.equity),
                'profit': float(self.account_info.equity - self.account_info.balance)
            }
            
        except Exception as e:
            logger.error(f"Error conectando a MT5: {e}")
            return {'success': False, 'error': str(e)}
    
    def disconnect(self):
        """Desconecta de MT5"""
        if self.mt5_available and self.connected:
            try:
                mt5.shutdown()
                self.connected = False
                logger.info("Desconectado de MT5")
                return True
            except Exception as e:
                logger.error(f"Error desconectando: {e}")
        return False
    
    def get_symbol_tick(self, symbol: str = "EURUSD") -> Optional[Dict]:
        """Obtiene el tick actual del símbolo"""
        if not self.connected:
            return None
        
        try:
            if not mt5.symbol_select(symbol, True):
                return None
            
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                return None
            
            return {
                'symbol': symbol,
                'ask': float(tick.ask),
                'bid': float(tick.bid),
                'time': tick.time,
                'volume': float(tick.volume)
            }
        except Exception as e:
            logger.error(f"Error obteniendo tick: {e}")
            return None
    
    def place_order(self, action: str, symbol: str = "EURUSD", volume: float = 0.01, 
                   sl: float = 0, tp: float = 0) -> Dict:
        """Coloca una orden en MT5"""
        if not self.connected:
            return {'success': False, 'error': 'MT5 no conectado'}
        
        try:
            if not mt5.symbol_select(symbol, True):
                return {'success': False, 'error': f'Símbolo {symbol} no disponible'}
            
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                return {'success': False, 'error': 'No se puede obtener precio actual'}
            
            # Determinar tipo de orden
            if action == 'BUY':
                order_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
            else:  # SELL
                order_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
            
            # Crear request
            request = {
                'action': mt5.TRADE_ACTION_DEAL,
                'symbol': symbol,
                'volume': float(volume),
                'type': order_type,
                'price': float(price),
                'sl': float(sl) if sl > 0 else 0,
                'tp': float(tp) if tp > 0 else 0,
                'deviation': 20,
                'magic': 234000,
                'comment': f'IA {action}',
                'type_time': mt5.ORDER_TIME_GTC,
                'type_filling': mt5.ORDER_FILLING_IOC,
            }
            
            # Enviar orden
            result = mt5.order_send(request)
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                error_msg = result.comment if result else 'Error desconocido'
                return {
                    'success': False,
                    'error': f'Orden no ejecutada: {error_msg}',
                    'retcode': result.retcode if result else None
                }
            
            logger.info(f"✅ Orden ejecutada: {action} {volume} {symbol} @ {price:.5f}")
            
            return {
                'success': True,
                'ticket': int(result.order),
                'action': action,
                'symbol': symbol,
                'volume': float(volume),
                'price': float(price),
                'sl': float(sl),
                'tp': float(tp),
                'time': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error colocando orden: {e}")
            return {'success': False, 'error': str(e)}
    
    def close_position(self, ticket: int, symbol: str = "EURUSD") -> Dict:
        """Cierra una posición abierta"""
        if not self.connected:
            return {'success': False, 'error': 'MT5 no conectado'}
        
        try:
            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                return {'success': False, 'error': 'Posición no encontrada'}
            
            position = positions[0]
            tick = mt5.symbol_info_tick(symbol)
            
            if position.type == mt5.ORDER_TYPE_BUY:
                order_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
            else:
                order_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
            
            request = {
                'action': mt5.TRADE_ACTION_DEAL,
                'symbol': symbol,
                'volume': position.volume,
                'type': order_type,
                'position': ticket,
                'price': float(price),
                'deviation': 20,
                'magic': 234000,
                'comment': f'Close {ticket}',
                'type_time': mt5.ORDER_TIME_GTC,
                'type_filling': mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                return {'success': False, 'error': 'No se pudo cerrar posición'}
            
            logger.info(f"✅ Posición cerrada: {ticket}")
            return {'success': True, 'ticket': ticket}
            
        except Exception as e:
            logger.error(f"Error cerrando posición: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_positions(self, symbol: str = "EURUSD") -> List[Dict]:
        """Obtiene todas las posiciones abiertas"""
        if not self.connected:
            return []
        
        try:
            positions = mt5.positions_get(symbol=symbol)
            if not positions:
                return []
            
            result = []
            for pos in positions:
                result.append({
                    'ticket': int(pos.ticket),
                    'symbol': pos.symbol,
                    'type': 'BUY' if pos.type == mt5.ORDER_TYPE_BUY else 'SELL',
                    'volume': float(pos.volume),
                    'price_open': float(pos.price_open),
                    'sl': float(pos.sl),
                    'tp': float(pos.tp),
                    'profit': float(pos.profit),
                    'time': pos.time
                })
            
            return result
        except Exception as e:
            logger.error(f"Error obteniendo posiciones: {e}")
            return []
    
    def get_account_info(self) -> Optional[Dict]:
        """Obtiene info actual de la cuenta"""
        if not self.connected:
            return None
        
        try:
            info = mt5.account_info()
            if not info:
                return None
            
            return {
                'login': info.login,
                'server': info.server,
                'balance': float(info.balance),
                'equity': float(info.equity),
                'profit': float(info.equity - info.balance),
                'currency': info.currency,
                'leverage': info.leverage,
                'margin_free': float(info.margin_free)
            }
        except Exception as e:
            logger.error(f"Error obteniendo info: {e}")
            return None


class BotAITrader:
    """Orquestador principal: Bot + IA + MT5"""
    
    def __init__(self, login: int = None, password: str = None, server: str = None):
        self.mt5_manager = MT5Manager()
        self.ai_analyzer = AIAnalyzer()
        self.trading_engine = TradingEngine()
        self.running = False
        self.price_history = [1.0850]
        self.config = self._load_config()
        self.stats = {
            'signals_generated': 0,
            'trades_executed': 0,
            'trades_won': 0,
            'trades_lost': 0,
            'total_profit': 0,
            'start_time': datetime.now().isoformat()
        }
        
        # Conectar a MT5 si se proporcionan credenciales
        if login and password and server:
            self._connect_mt5(login, password, server)
    
    def _load_config(self) -> Dict:
        """Carga configuración"""
        config_file = 'bot_config.json'
        default_config = {
            'min_confidence': 0.70,
            'trading_symbol': 'EURUSD',
            'default_volume': 0.01,
            'max_positions': 5,
            'trading_hours': {'start': 8, 'end': 22},
            'auto_trading': False,
            'use_mt5': False
        }
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    saved = json.load(f)
                    default_config.update(saved)
            except Exception as e:
                logger.error(f"Error cargando config: {e}")
        
        return default_config
    
    def _connect_mt5(self, login: int, password: str, server: str) -> bool:
        """Conecta a MT5"""
        result = self.mt5_manager.connect(login, password, server)
        if result['success']:
            self.config['use_mt5'] = True
            logger.info("✅ MT5 conectado exitosamente")
            return True
        else:
            logger.warning(f"⚠️ MT5 no disponible: {result['error']}")
            return False
    
    def _get_current_price(self, symbol: str = "EURUSD") -> float:
        """Obtiene precio actual (MT5 o simulado)"""
        if self.mt5_manager.connected:
            tick = self.mt5_manager.get_symbol_tick(symbol)
            if tick:
                return (tick['ask'] + tick['bid']) / 2
        
        # Simulación
        import random
        last = self.price_history[-1]
        change = random.uniform(-0.0005, 0.0005)
        return max(0.9, last + change)
    
    def _analyze_and_trade(self, symbol: str = "EURUSD") -> Optional[Dict]:
        """Analiza y ejecuta trade si cumple criterios"""
        
        # Obtener precio actual
        current_price = self._get_current_price(symbol)
        self.price_history.append(current_price)
        if len(self.price_history) > 200:
            self.price_history.pop(0)
        
        # Si menos de 50 puntos, no analizar
        if len(self.price_history) < 50:
            return None
        
        # Generar señal con IA
        analysis = self.ai_analyzer.analyze_prices(self.price_history[-50:])
        signal = analysis['signal']
        
        self.stats['signals_generated'] += 1
        
        # Verificar si debe ejecutar
        if signal['action'] == 'HOLD':
            return None
        
        if signal['confidence'] < self.config['min_confidence']:
            logger.info(f"⚠️ Señal {signal['action']} rechazada: confianza {signal['confidence']:.1%} < {self.config['min_confidence']:.1%}")
            return None
        
        # Ejecutar trade
        volume = self.config['default_volume']
        
        if self.mt5_manager.connected and self.config['use_mt5']:
            # Ejecutar en MT5 real
            indicators = analysis.get('indicators', {})
            atr = indicators.get('atr', 0.001)
            
            if signal['action'] == 'BUY':
                sl = current_price - (atr * 2)
                tp = current_price + (atr * 4)
            else:  # SELL
                sl = current_price + (atr * 2)
                tp = current_price - (atr * 4)
            
            result = self.mt5_manager.place_order(signal['action'], symbol, volume, sl, tp)
            
            if result['success']:
                self.stats['trades_executed'] += 1
                logger.info(f"✅ TRADE EJECUTADO EN MT5: {signal['action']} {volume} {symbol}")
                return result
            else:
                logger.error(f"❌ Error en MT5: {result['error']}")
                return None
        else:
            # Simulación local
            trade = self.trading_engine.open_trade(signal['action'], current_price, signal['confidence'])
            self.stats['trades_executed'] += 1
            logger.info(f"✅ TRADE SIMULADO: {signal['action']} {volume} {symbol}")
            return {'success': True, 'trade': trade}
    
    def start_trading(self, duration_minutes: int = None):
        """Inicia el trading automático"""
        self.running = True
        self.config['auto_trading'] = True
        
        logger.info("=" * 80)
        logger.info("🚀 INICIANDO BOT DE TRADING AUTOMÁTICO")
        logger.info("=" * 80)
        logger.info(f"Símbolo: {self.config['trading_symbol']}")
        logger.info(f"Volumen: {self.config['default_volume']}")
        logger.info(f"Confianza mín: {self.config['min_confidence']:.1%}")
        logger.info(f"MT5 Conectado: {'Sí' if self.mt5_manager.connected else 'No'}")
        logger.info("=" * 80)
        
        start_time = time.time()
        
        try:
            while self.running:
                current_time = time.time()
                
                # Verificar timeout si se especificó
                if duration_minutes and (current_time - start_time) > (duration_minutes * 60):
                    logger.info(f"⏰ Tiempo límite alcanzado ({duration_minutes} minutos)")
                    break
                
                # Ejecutar análisis y trading
                try:
                    self._analyze_and_trade(self.config['trading_symbol'])
                except Exception as e:
                    logger.error(f"Error en ciclo de trading: {e}")
                
                # Actualizar posiciones en MT5
                if self.mt5_manager.connected:
                    positions = self.mt5_manager.get_positions(self.config['trading_symbol'])
                    if positions:
                        logger.info(f"📍 Posiciones abiertas: {len(positions)}")
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("\n🛑 Trading detenido por usuario")
        except Exception as e:
            logger.error(f"❌ Error en trading: {e}")
        finally:
            self.stop_trading()
    
    def stop_trading(self):
        """Detiene el trading automático"""
        self.running = False
        self.config['auto_trading'] = False
        
        logger.info("\n" + "=" * 80)
        logger.info("📊 RESUMEN DE SESIÓN")
        logger.info("=" * 80)
        logger.info(f"Señales generadas: {self.stats['signals_generated']}")
        logger.info(f"Trades ejecutados: {self.stats['trades_executed']}")
        logger.info(f"Trades ganados: {self.stats['trades_won']}")
        logger.info(f"Trades perdidos: {self.stats['trades_lost']}")
        logger.info(f"Ganancia total: ${self.stats['total_profit']:.2f}")
        logger.info("=" * 80)
        
        # Mostrar info de MT5 si está conectado
        if self.mt5_manager.connected:
            account = self.mt5_manager.get_account_info()
            if account:
                logger.info(f"💰 Balance MT5: ${account['balance']:.2f}")
                logger.info(f"📈 Equity MT5: ${account['equity']:.2f}")
                logger.info(f"💹 Profit MT5: ${account['profit']:.2f}")
    
    def get_status(self) -> Dict:
        """Obtiene estado actual del bot"""
        account_info = None
        positions = []
        
        if self.mt5_manager.connected:
            account_info = self.mt5_manager.get_account_info()
            positions = self.mt5_manager.get_positions(self.config['trading_symbol'])
        
        return {
            'running': self.running,
            'mt5_connected': self.mt5_manager.connected,
            'config': self.config,
            'stats': self.stats,
            'account': account_info,
            'positions': positions,
            'current_price': self.price_history[-1] if self.price_history else 0,
            'price_history': self.price_history[-50:]
        }


def main():
    """Función principal de ejemplo"""
    
    # Cargar credenciales de MT5
    try:
        from .mt5_config import MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, MT5_PATH
    except ImportError:
        logger.warning("⚠️ mt5_config.py no encontrado. Ejecutando en modo simulación.")
        MT5_LOGIN = None
        MT5_PASSWORD = None
        MT5_SERVER = None
        MT5_PATH = None
    
    # Crear bot
    bot = BotAITrader(MT5_LOGIN, MT5_PASSWORD, MT5_SERVER)
    
    # Iniciar trading automático (30 minutos para demo)
    try:
        bot.start_trading(duration_minutes=30)
    except KeyboardInterrupt:
        logger.info("\n🛑 Deteniendo bot...")
        bot.stop_trading()


if __name__ == "__main__":
    main()
