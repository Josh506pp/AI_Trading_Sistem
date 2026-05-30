#!/usr/bin/env python3
"""
Interfaz Interactiva de Chat para Control del Bot de Trading
Permite comandos tipo chat para controlar el bot
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import json

logger = logging.getLogger(__name__)

# =============================================================================
# ENUMS
# =============================================================================
class CommandCategory(Enum):
    """Categorías de comandos"""
    OPERATION = "Operación"
    CONTROL = "Control"
    ANALYSIS = "Análisis"
    CONFIGURATION = "Configuración"
    INFORMATION = "Información"
    HELP = "Ayuda"


# =============================================================================
# COMMAND REGISTRY
# =============================================================================
class Command:
    """Descripción de un comando"""
    
    def __init__(
        self,
        name: str,
        category: CommandCategory,
        description: str,
        usage: str,
        aliases: List[str] = None,
        callback: Callable = None
    ):
        self.name = name
        self.category = category
        self.description = description
        self.usage = usage
        self.aliases = aliases or []
        self.callback = callback


# =============================================================================
# TRADING BOT CHAT INTERFACE
# =============================================================================
class TradingBotChatInterface:
    """
    Interfaz CLI/Chat para controlar bot de trading
    """
    
    def __init__(self, trading_bot_instance):
        """
        trading_bot_instance: Instancia del bot de trading
        """
        self.bot = trading_bot_instance
        self.running = False
        self.paused = False
        self.auto_stop_time = None
        self.command_history = []
        self.registered_commands = {}
        
        self._register_default_commands()
    
    def _register_default_commands(self):
        """Registra comandos por defecto"""
        
        commands = [
            # OPERACIÓN
            Command(
                name="open_trades",
                category=CommandCategory.OPERATION,
                description="Abre N operaciones",
                usage="abre <cantidad> | abre X operaciones",
                aliases=["abre", "open", "oper"],
                callback=self.cmd_open_trades
            ),
            Command(
                name="close_all",
                category=CommandCategory.OPERATION,
                description="Cierra todas las posiciones",
                usage="cierra todas | close all",
                aliases=["cierra todas", "close_all", "close all"],
                callback=self.cmd_close_all
            ),
            Command(
                name="close_position",
                category=CommandCategory.OPERATION,
                description="Cierra posición específica",
                usage="cierra <ID>",
                aliases=["cierra"],
                callback=self.cmd_close_position
            ),
            
            # CONTROL
            Command(
                name="pause",
                category=CommandCategory.CONTROL,
                description="Pausa el bot",
                usage="pausa | pause",
                aliases=["pausa", "pause"],
                callback=self.cmd_pause
            ),
            Command(
                name="resume",
                category=CommandCategory.CONTROL,
                description="Reanuda el bot",
                usage="resume | continuar",
                aliases=["resume", "continuar", "reanudar"],
                callback=self.cmd_resume
            ),
            Command(
                name="trade_for_duration",
                category=CommandCategory.CONTROL,
                description="Tradea por X minutos",
                usage="tradea <minutos> | trade for <minutos> minutes",
                aliases=["tradea", "trade for"],
                callback=self.cmd_trade_for_duration
            ),
            
            # INFORMACIÓN
            Command(
                name="status",
                category=CommandCategory.INFORMATION,
                description="Estado actual del bot",
                usage="status | estado",
                aliases=["status", "estado", "info"],
                callback=self.cmd_status
            ),
            Command(
                name="history",
                category=CommandCategory.INFORMATION,
                description="Historial de operaciones",
                usage="historial | history [N]",
                aliases=["historial", "history", "trades"],
                callback=self.cmd_history
            ),
            Command(
                name="positions",
                category=CommandCategory.INFORMATION,
                description="Posiciones abiertas",
                usage="posiciones | positions",
                aliases=["posiciones", "positions", "open"],
                callback=self.cmd_positions
            ),
            Command(
                name="score",
                category=CommandCategory.INFORMATION,
                description="Puntuación total",
                usage="puntos | score | scorecard",
                aliases=["puntos", "score", "scorecard"],
                callback=self.cmd_score
            ),
            Command(
                name="analysis",
                category=CommandCategory.ANALYSIS,
                description="Análisis técnico actual",
                usage="análisis | analysis",
                aliases=["análisis", "analysis", "tecnico"],
                callback=self.cmd_analysis
            ),
            
            # CONFIGURACIÓN
            Command(
                name="set_risk",
                category=CommandCategory.CONFIGURATION,
                description="Configura riesgo %",
                usage="riesgo <X>% | risk <X>%",
                aliases=["riesgo", "risk"],
                callback=self.cmd_set_risk
            ),
            Command(
                name="set_max_positions",
                category=CommandCategory.CONFIGURATION,
                description="Máximo de posiciones",
                usage="max <N> | max positions <N>",
                aliases=["max", "max positions"],
                callback=self.cmd_set_max_positions
            ),
            Command(
                name="set_stop_loss",
                category=CommandCategory.CONFIGURATION,
                description="Stop loss en pips",
                usage="stop loss <pips> | sl <pips>",
                aliases=["stop loss", "sl"],
                callback=self.cmd_set_stop_loss
            ),
            Command(
                name="set_take_profit",
                category=CommandCategory.CONFIGURATION,
                description="Take profit en pips",
                usage="take profit <pips> | tp <pips>",
                aliases=["take profit", "tp"],
                callback=self.cmd_set_take_profit
            ),
            
            # AYUDA
            Command(
                name="help",
                category=CommandCategory.HELP,
                description="Muestra ayuda",
                usage="ayuda | help | ?",
                aliases=["ayuda", "help", "?"],
                callback=self.cmd_help
            ),
        ]
        
        for cmd in commands:
            self.registered_commands[cmd.name] = cmd
            for alias in cmd.aliases:
                self.registered_commands[alias] = cmd
    
    def start_interactive_mode(self):
        """Inicia modo interactivo"""
        
        self.running = True
        
        print("""
╔════════════════════════════════════════════════════════════╗
║        🤖 TRADING BOT IA - MODO INTERACTIVO 🤖             ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  Tipo 'ayuda' para ver comandos disponibles                ║
║  Tipo 'salir' para cerrar el bot                           ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
        """)
        
        while self.running:
            try:
                # Mostrar prompt
                prompt = "TradingBot ⏸️ > " if self.paused else "TradingBot ▶️ > "
                command_input = input(prompt).strip()
                
                if not command_input:
                    continue
                
                # Procesar comando
                response = self.process_command(command_input)
                
                # Mostrar respuesta
                print(f"\n{response}\n")
                
                # Registrar comando
                self.command_history.append({
                    'timestamp': datetime.now(),
                    'command': command_input,
                    'response': response
                })
            
            except KeyboardInterrupt:
                print("\n\n⚠️  Operación cancelada. Escribe 'ayuda' para más opciones.")
                continue
            
            except Exception as e:
                print(f"❌ Error: {e}")
                logger.error(f"Command processing error: {e}", exc_info=True)
    
    def process_command(self, user_input: str) -> str:
        """Procesa comando de usuario"""
        
        user_input = user_input.lower().strip()
        
        # Comandos especiales
        if user_input in ['salir', 'exit', 'quit']:
            self.running = False
            return "👋 Cerrando bot de trading..."
        
        # Buscar comando
        for cmd_name, cmd_obj in self.registered_commands.items():
            if user_input.startswith(cmd_name) or user_input in cmd_obj.aliases:
                try:
                    # Extraer argumentos
                    args = user_input.replace(cmd_name, '').strip().split()
                    
                    # Ejecutar callback
                    if cmd_obj.callback:
                        response = cmd_obj.callback(args)
                        return response
                    else:
                        return f"❌ Comando no implementado: {cmd_name}"
                
                except Exception as e:
                    return f"❌ Error ejecutando comando: {e}"
        
        # Comando no reconocido
        return f"❌ Comando desconocido: '{user_input}'. Escribe 'ayuda' para ver opciones."
    
    # =========================================================================
    # OPERACIÓN CALLBACKS
    # =========================================================================
    
    def cmd_open_trades(self, args: List[str]) -> str:
        """Abre N operaciones"""
        try:
            num = int(args[0]) if args else 1
            num = max(1, min(num, 10))  # Límite 1-10
            
            result = self.bot.open_multiple_trades(num)
            
            return f"✅ Intentando abrir {num} operación(es)...\n{result}"
        
        except Exception as e:
            return f"❌ Error: {e}"
    
    def cmd_close_all(self, args: List[str]) -> str:
        """Cierra todas las posiciones"""
        try:
            result = self.bot.close_all_positions()
            return f"✅ Cerrando todas las posiciones...\n{result}"
        except Exception as e:
            return f"❌ Error: {e}"
    
    def cmd_close_position(self, args: List[str]) -> str:
        """Cierra posición específica"""
        try:
            if not args:
                return "❌ Uso: cierra <ID>"
            
            position_id = int(args[0])
            result = self.bot.close_position(position_id)
            
            return f"✅ Posición {position_id} cerrada.\n{result}"
        except Exception as e:
            return f"❌ Error: {e}"
    
    # =========================================================================
    # CONTROL CALLBACKS
    # =========================================================================
    
    def cmd_pause(self, args: List[str]) -> str:
        """Pausa el bot"""
        self.paused = True
        self.bot.pause()
        return "⏸️  Bot pausado. Sin nuevas operaciones."
    
    def cmd_resume(self, args: List[str]) -> str:
        """Reanuda el bot"""
        self.paused = False
        self.bot.resume()
        return "▶️  Bot reanudado."
    
    def cmd_trade_for_duration(self, args: List[str]) -> str:
        """Tradea por X minutos"""
        try:
            minutes = int(args[0]) if args else 30
            minutes = max(1, min(minutes, 480))  # 1-480 minutos (8 horas)
            
            self.paused = False
            self.auto_stop_time = datetime.now() + timedelta(minutes=minutes)
            self.bot.resume()
            
            # Programar pausa automática
            threading.Thread(
                target=self._auto_pause_after,
                args=(minutes,),
                daemon=True
            ).start()
            
            return f"▶️  Trading por {minutes} minuto(s).\nParada programada a las {self.auto_stop_time.strftime('%H:%M:%S')}"
        
        except Exception as e:
            return f"❌ Error: {e}"
    
    def _auto_pause_after(self, minutes: int):
        """Pausa automáticamente después de N minutos"""
        time.sleep(minutes * 60)
        self.cmd_pause([])
        print(f"\n⏸️  PAUSA AUTOMÁTICA: {minutes} minuto(s) completado(s).\n")
    
    # =========================================================================
    # INFORMACIÓN CALLBACKS
    # =========================================================================
    
    def cmd_status(self, args: List[str]) -> str:
        """Estado actual del bot"""
        try:
            status = self.bot.get_status()
            
            status_str = f"""
╔════════════════════════════════════════════════════════════╗
║                   ESTADO DEL BOT                          ║
╠════════════════════════════════════════════════════════════╣
║ Estado:              {'⏸️  PAUSADO' if self.paused else '▶️  ACTIVO':30} ║
║ Posiciones Abiertas: {status.get('open_positions', 0):30} ║
║ Balance:             ${status.get('balance', 0):>28.2f} ║
║ Drawdown:            {status.get('drawdown_pct', 0):>28.1f}% ║
║ Total R-Multiple:    {status.get('total_r', 0):>28.2f}R ║
║ Win Rate:            {status.get('win_rate', 0)*100:>28.1f}% ║
╚════════════════════════════════════════════════════════════╝
            """.strip()
            
            return status_str
        
        except Exception as e:
            return f"❌ Error obteniendo estado: {e}"
    
    def cmd_history(self, args: List[str]) -> str:
        """Historial de operaciones"""
        try:
            num = int(args[0]) if args else 10
            
            history = self.bot.get_trade_history(num)
            
            if not history:
                return "📊 No hay operaciones en el historial."
            
            history_str = f"\n📊 ÚLTIMAS {num} OPERACIONES:\n"
            history_str += "─" * 70 + "\n"
            history_str += f"{'ID':<5} {'TIPO':<6} {'ENTRADA':<12} {'SALIDA':<12} {'R-MULT':<8} {'RESULTADO':<8}\n"
            history_str += "─" * 70 + "\n"
            
            for trade in history:
                trade_type = "COMP" if trade['direction'] == 'BUY' else "VEND"
                r_mult = trade.get('r_multiple', 0)
                result = f"{r_mult:+.2f}R"
                
                history_str += (
                    f"{trade['id']:<5} {trade_type:<6} "
                    f"{trade['entry']:<12.5f} {trade['exit']:<12.5f} "
                    f"{result:<8} {'✅' if r_mult > 0 else '❌':<8}\n"
                )
            
            return history_str
        
        except Exception as e:
            return f"❌ Error: {e}"
    
    def cmd_positions(self, args: List[str]) -> str:
        """Posiciones abiertas"""
        try:
            positions = self.bot.get_open_positions()
            
            if not positions:
                return "📭 No hay posiciones abiertas."
            
            pos_str = f"\n📈 POSICIONES ABIERTAS ({len(positions)}):\n"
            pos_str += "─" * 80 + "\n"
            pos_str += f"{'ID':<5} {'TIPO':<6} {'ENTRADA':<12} {'ACTUAL':<12} {'SL':<12} {'TP':<12} {'LOTE':<8}\n"
            pos_str += "─" * 80 + "\n"
            
            for pos in positions:
                trade_type = "COMP" if pos['direction'] == 'BUY' else "VEND"
                
                pos_str += (
                    f"{pos['id']:<5} {trade_type:<6} "
                    f"{pos['entry']:<12.5f} {pos['current']:<12.5f} "
                    f"{pos['sl']:<12.5f} {pos['tp']:<12.5f} "
                    f"{pos['lot']:<8.2f}\n"
                )
            
            return pos_str
        
        except Exception as e:
            return f"❌ Error: {e}"
    
    def cmd_score(self, args: List[str]) -> str:
        """Puntuación total"""
        try:
            scorecard = self.bot.get_scorecard()
            
            return scorecard  # Ya es un string formateado
        
        except Exception as e:
            return f"❌ Error: {e}"
    
    def cmd_analysis(self, args: List[str]) -> str:
        """Análisis técnico actual"""
        try:
            analysis = self.bot.get_technical_analysis()
            
            analysis_str = f"""
╔════════════════════════════════════════════════════════════╗
║               ANÁLISIS TÉCNICO ACTUAL                    ║
╠════════════════════════════════════════════════════════════╣
║ Tendencia:           {analysis['trend']:30} ║
║ Fuerza Tendencia:    {analysis['trend_strength']:>28.4f} ║
║ RSI:                 {analysis['rsi']:>28.1f}              ║
║ Momentum:            {analysis['momentum']:>28.4f} ║
║ Volatilidad:         {analysis['volatility']:>27.2f}% ║
║ Posición BB:         {analysis['bb_position']:>28.2f} ║
╚════════════════════════════════════════════════════════════╝
            """.strip()
            
            return analysis_str
        
        except Exception as e:
            return f"❌ Error: {e}"
    
    # =========================================================================
    # CONFIGURACIÓN CALLBACKS
    # =========================================================================
    
    def cmd_set_risk(self, args: List[str]) -> str:
        """Configura riesgo %"""
        try:
            if not args:
                return "❌ Uso: riesgo <X>%"
            
            risk_str = args[0].replace('%', '')
            risk = float(risk_str)
            risk = max(0.5, min(risk, 10))  # 0.5% - 10%
            
            self.bot.set_risk_percent(risk)
            
            return f"✅ Riesgo configurado a {risk}%"
        
        except Exception as e:
            return f"❌ Error: {e}"
    
    def cmd_set_max_positions(self, args: List[str]) -> str:
        """Máximo de posiciones"""
        try:
            if not args:
                return "❌ Uso: max <N>"
            
            max_pos = int(args[0])
            max_pos = max(1, min(max_pos, 20))  # 1-20 posiciones
            
            self.bot.set_max_positions(max_pos)
            
            return f"✅ Máximo de posiciones: {max_pos}"
        
        except Exception as e:
            return f"❌ Error: {e}"
    
    def cmd_set_stop_loss(self, args: List[str]) -> str:
        """Stop loss en pips"""
        try:
            if not args:
                return "❌ Uso: stop loss <pips>"
            
            sl_pips = int(args[0])
            sl_pips = max(10, min(sl_pips, 500))  # 10-500 pips
            
            self.bot.set_stop_loss(sl_pips)
            
            return f"✅ Stop Loss: {sl_pips} pips"
        
        except Exception as e:
            return f"❌ Error: {e}"
    
    def cmd_set_take_profit(self, args: List[str]) -> str:
        """Take profit en pips"""
        try:
            if not args:
                return "❌ Uso: take profit <pips>"
            
            tp_pips = int(args[0])
            tp_pips = max(10, min(tp_pips, 500))  # 10-500 pips
            
            self.bot.set_take_profit(tp_pips)
            
            return f"✅ Take Profit: {tp_pips} pips"
        
        except Exception as e:
            return f"❌ Error: {e}"
    
    # =========================================================================
    # AYUDA
    # =========================================================================
    
    def cmd_help(self, args: List[str]) -> str:
        """Muestra ayuda"""
        
        help_str = """
╔════════════════════════════════════════════════════════════╗
║               COMANDOS DISPONIBLES                        ║
╠════════════════════════════════════════════════════════════╣

🔴 OPERACIONES:
  abre <N>              Abre N operaciones
  cierra todas          Cierra todas las posiciones
  cierra <ID>           Cierra posición específica

🎮 CONTROL:
  pausa                 Pausa el bot
  resume                Reanuda el bot
  tradea <min>          Tradea por X minutos

📊 INFORMACIÓN:
  status                Estado actual del bot
  historial [N]         Últimas N operaciones
  posiciones            Posiciones abiertas
  puntos                Puntuación total
  análisis              Análisis técnico

⚙️ CONFIGURACIÓN:
  riesgo <X>%           Riesgo por operación
  max <N>               Máximo posiciones
  stop loss <pips>      Stop loss en pips
  take profit <pips>    Take profit en pips

❓ OTROS:
  ayuda                 Muestra este menú
  salir                 Cierra el bot

╚════════════════════════════════════════════════════════════╝
        """.strip()
        
        return help_str
