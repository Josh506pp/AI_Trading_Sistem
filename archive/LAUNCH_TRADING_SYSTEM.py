#!/usr/bin/env python3
"""
🚀 LAUNCHER DEL SISTEMA DE TRADING INTELIGENTE
Inicia todo el sistema con un solo click

Versión: 2.0 - Sistema Rediseñado
Fecha: 2024
"""

import os
import sys
import subprocess
import time
import threading
import webbrowser
from pathlib import Path

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

PROJECT_ROOT = Path(__file__).parent
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"
DASHBOARD_FILE = PROJECT_ROOT / "dashboard.py"
CONFIG_FILE = PROJECT_ROOT / "launcher_config.py"

# Cargar configuración
try:
    import launcher_config
    LAUNCH_CONFIG = launcher_config.ACTIVE_CONFIG
except ImportError:
    # Configuración por defecto si no existe el archivo
    LAUNCH_CONFIG = {
        "auto_start_dashboard": True,
        "dashboard_port": 5000,
        "auto_start_chat": True,
        "check_mt5_connection": True,
        "verbose": True,
        "auto_open_browser": True,
        "install_missing_deps": True,
        "validate_files": True,
    }

# =============================================================================
# UTILIDADES
# =============================================================================

def print_header():
    """Imprime el header del launcher"""
    print("\n" + "="*80)
    print("🚀 SISTEMA DE TRADING INTELIGENTE v2.0")
    print("   Launcher Automático - Un Click para Todo")
    print("="*80)
    print()

def print_step(step_num, message):
    """Imprime un paso del proceso"""
    print(f"[{step_num}] {message}")

def print_success(message):
    """Imprime mensaje de éxito"""
    print(f"✅ {message}")

def print_error(message):
    """Imprime mensaje de error"""
    print(f"❌ {message}")

def print_warning(message):
    """Imprime mensaje de advertencia"""
    print(f"⚠️  {message}")

def print_info(message):
    """Imprime mensaje informativo"""
    print(f"ℹ️  {message}")

# =============================================================================
# VERIFICACIONES DEL SISTEMA
# =============================================================================

def check_python_version():
    """Verifica la versión de Python"""
    print_step(1, "Verificando versión de Python...")

    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print_error(f"Python {version.major}.{version.minor} no es compatible. Se requiere Python 3.8+")
        return False

    print_success(f"Python {version.major}.{version.minor}.{version.micro} - OK")
    return True

def check_dependencies():
    """Verifica e instala dependencias"""
    print_step(2, "Verificando dependencias...")

    if not REQUIREMENTS_FILE.exists():
        print_error(f"No se encuentra {REQUIREMENTS_FILE}")
        return False

    try:
        # Intentar importar módulos clave
        import numpy
        import pandas
        import sklearn
        import matplotlib
        import seaborn

        print_success("Dependencias principales instaladas")
        return True

    except ImportError as e:
        print_warning(f"Faltan dependencias: {e}")
        print_info("Instalando dependencias...")

        try:
            # Instalar dependencias
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)
            ], capture_output=True, text=True, cwd=PROJECT_ROOT)

            if result.returncode == 0:
                print_success("Dependencias instaladas correctamente")
                return True
            else:
                print_error("Error instalando dependencias:")
                print(result.stderr)
                return False

        except Exception as e:
            print_error(f"Error ejecutando pip: {e}")
            return False

def check_files():
    """Verifica que existan los archivos necesarios"""
    print_step(3, "Verificando archivos del sistema...")

    required_files = [
        "integrated_trading_system.py",
        "reward_system.py",
        "price_analyzer.py",
        "decision_logic.py",
        "ai_optimizer.py",
        "chat_interface.py"
    ]

    missing_files = []
    for file in required_files:
        if not (PROJECT_ROOT / file).exists():
            missing_files.append(file)

    if missing_files:
        print_error(f"Archivos faltantes: {', '.join(missing_files)}")
        return False

    print_success("Todos los archivos del sistema presentes")
    return True

def check_mt5_connection():
    """Verifica conexión con MT5 (opcional)"""
    if not LAUNCH_CONFIG["check_mt5_connection"]:
        return True

    print_step(4, "Verificando conexión MT5...")

    try:
        import MetaTrader5 as mt5

        if not mt5.initialize():
            print_warning("MT5 no está ejecutándose o no está instalado")
            print_info("El sistema puede funcionar en modo simulado")
            return True

        account_info = mt5.account_info()
        if account_info is None:
            print_warning("No hay cuenta MT5 conectada")
            print_info("Configure mt5_config.py para conexión real")
            return True

        print_success(f"MT5 conectado - Cuenta: {account_info.login}")
        mt5.shutdown()
        return True

    except ImportError:
        print_warning("MetaTrader5 no instalado - funcionando en modo simulado")
        return True
    except Exception as e:
        print_warning(f"Error verificando MT5: {e}")
        return True

# =============================================================================
# INICIO DE COMPONENTES
# =============================================================================

def start_dashboard():
    """Inicia el dashboard en un hilo separado"""
    if not LAUNCH_CONFIG["auto_start_dashboard"]:
        return None

    print_step(5, "Iniciando dashboard web...")

    if not DASHBOARD_FILE.exists():
        print_warning("Dashboard no encontrado - omitiendo")
        return None

    def run_dashboard():
        try:
            # Ejecutar dashboard
            result = subprocess.run([
                sys.executable, str(DASHBOARD_FILE)
            ], cwd=PROJECT_ROOT)

            if result.returncode != 0:
                print_error("Dashboard terminó con error")

        except Exception as e:
            print_error(f"Error iniciando dashboard: {e}")

    # Iniciar en hilo separado
    dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
    dashboard_thread.start()

    # Esperar un poco para que inicie
    time.sleep(3)

    # Abrir navegador
    dashboard_url = f"http://localhost:{LAUNCH_CONFIG['dashboard_port']}"
    try:
        webbrowser.open(dashboard_url)
        print_success(f"Dashboard iniciado en: {dashboard_url}")
    except Exception as e:
        print_warning(f"No se pudo abrir navegador: {e}")
        print_info(f"Accede manualmente a: {dashboard_url}")

    return dashboard_thread

def initialize_trading_system():
    """Inicializa el sistema de trading"""
    print_step(6, "Inicializando sistema de trading...")

    try:
        # Importar sistema
        from integrated_trading_system import IntegratedTradingSystem

        # Crear instancia
        system = IntegratedTradingSystem()

        print_success("Sistema de trading inicializado")
        return system

    except Exception as e:
        print_error(f"Error inicializando sistema: {e}")
        return None

def start_chat_interface(system):
    """Inicia la interfaz de chat"""
    if not LAUNCH_CONFIG["auto_start_chat"] or system is None:
        return

    print_step(7, "Iniciando interfaz de chat...")

    try:
        # Iniciar chat en hilo separado
        def run_chat():
            try:
                system.chat_interface.start_interactive_mode()
            except KeyboardInterrupt:
                print_info("Chat terminado por usuario")
            except Exception as e:
                print_error(f"Error en chat: {e}")

        chat_thread = threading.Thread(target=run_chat, daemon=True)
        chat_thread.start()

        print_success("Interfaz de chat iniciada")
        print_info("Escribe comandos como 'abre 5', 'status', 'ayuda'...")

        return chat_thread

    except Exception as e:
        print_error(f"Error iniciando chat: {e}")
        return None

# =============================================================================
# MENÚ PRINCIPAL
# =============================================================================

def show_menu():
    """Muestra el menú principal"""
    print("\n" + "="*80)
    print("🎯 SISTEMA INICIADO - ¿QUÉ QUIERES HACER?")
    print("="*80)
    print()
    print("OPCIONES:")
    print("1. 🔄 Iniciar interfaz de chat completa")
    print("2. 📊 Abrir dashboard web")
    print("3. 🤖 Ejecutar análisis de mercado")
    print("4. 📈 Ver estado del sistema")
    print("5. ⚙️  Configurar parámetros")
    print("6. 🛑 Salir")
    print()

def handle_menu_choice(system):
    """Maneja la selección del menú"""
    while True:
        try:
            choice = input("Elige una opción (1-6): ").strip()

            if choice == "1":
                print_info("Iniciando chat interactivo...")
                system.chat_interface.start_interactive_mode()
                break

            elif choice == "2":
                dashboard_url = f"http://localhost:{LAUNCH_CONFIG['dashboard_port']}"
                print_info(f"Abrir dashboard: {dashboard_url}")
                webbrowser.open(dashboard_url)
                continue

            elif choice == "3":
                print_info("Ejecutando análisis de mercado...")
                # Aquí podrías agregar análisis de ejemplo
                print("Análisis completado (implementar lógica específica)")
                continue

            elif choice == "4":
                print_info("Estado del sistema:")
                status = system.get_system_status()
                print(f"  Balance: ${status['balance']:.2f}")
                print(f"  Posiciones: {status['open_positions']}")
                print(f"  R-Multiple: {status['total_r']:.2f}R")
                print(f"  Salud: {status['scorecard']['health_status']}")
                continue

            elif choice == "5":
                print_info("Configuración (editar integrated_trading_system.py):")
                print("  - risk_percent: porcentaje de riesgo por trade")
                print("  - max_positions: máximo posiciones simultáneas")
                print("  - stop_loss_pips: pips de stop loss")
                print("  - take_profit_pips: pips de take profit")
                continue

            elif choice == "6":
                print_info("¡Hasta luego!")
                break

            else:
                print_warning("Opción inválida. Elige 1-6.")

        except KeyboardInterrupt:
            print_info("\nInterrumpido por usuario")
            break
        except Exception as e:
            print_error(f"Error: {e}")
            continue

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def main():
    """Función principal del launcher"""
    print_header()

    # Verificaciones del sistema
    checks_passed = True

    if not check_python_version():
        checks_passed = False

    if not check_dependencies():
        checks_passed = False

    if not check_files():
        checks_passed = False

    if not check_mt5_connection():
        checks_passed = False

    if not checks_passed:
        print_error("Verificaciones fallidas. Revisa los errores arriba.")
        input("Presiona Enter para salir...")
        return

    print_success("✅ Todas las verificaciones pasaron")

    # Iniciar componentes
    dashboard_thread = start_dashboard()
    system = initialize_trading_system()
    chat_thread = start_chat_interface(system)

    if system is None:
        print_error("No se pudo inicializar el sistema de trading")
        input("Presiona Enter para salir...")
        return

    # Esperar un poco para que todo inicie
    time.sleep(2)

    print("\n" + "="*80)
    print("🎉 ¡SISTEMA COMPLETAMENTE INICIADO!")
    print("="*80)
    print()
    print("✅ Sistema de trading inteligente listo")
    print("✅ IA optimizada con R-múltiplos")
    print("✅ Control de riesgo avanzado")
    print("✅ Interfaz de chat interactiva")
    if dashboard_thread:
        print(f"✅ Dashboard web en http://localhost:{LAUNCH_CONFIG['dashboard_port']}")
    print()

    # Mostrar menú
    show_menu()
    handle_menu_choice(system)

    # Limpieza
    print_info("Cerrando sistema...")
    if 'mt5' in sys.modules:
        try:
            import MetaTrader5 as mt5
            mt5.shutdown()
        except:
            pass

    print_success("Sistema cerrado correctamente")

# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrumpido por usuario")
    except Exception as e:
        print(f"\n\n❌ Error fatal: {e}")
        if LAUNCH_CONFIG["verbose"]:
            import traceback
            traceback.print_exc()
    finally:
        input("\nPresiona Enter para salir...")