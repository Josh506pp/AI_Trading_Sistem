# =============================================================================
# CONFIGURACIÓN DEL LAUNCHER
# Personaliza el comportamiento del sistema de trading
# =============================================================================

LAUNCH_CONFIG = {
    # 🚀 INICIO AUTOMÁTICO
    "auto_start_dashboard": True,      # Iniciar dashboard web automáticamente
    "auto_start_chat": False,          # Iniciar interfaz de chat automáticamente
    "auto_open_browser": True,        # Abrir navegador con dashboard

    # 🌐 DASHBOARD
    "dashboard_port": 5000,           # Puerto del servidor web
    "dashboard_host": "localhost",    # Host del servidor (localhost o 0.0.0.0)

    # 🔍 VERIFICACIONES
    "check_mt5_connection": True,     # Verificar conexión MT5 al inicio
    "install_missing_deps": True,     # Instalar dependencias faltantes
    "validate_files": True,           # Verificar que existan todos los archivos

    # 📊 LOGGING
    "verbose": True,                  # Mostrar logs detallados
    "log_to_file": False,             # Guardar logs en archivo
    "log_file": "launcher.log",       # Nombre del archivo de log

    # ⚙️ SISTEMA DE TRADING
    "default_risk_percent": 2.0,      # Riesgo por defecto (%)
    "default_max_positions": 10,      # Máximo posiciones por defecto
    "default_stop_loss": 50,          # Stop loss por defecto (pips)
    "default_take_profit": 150,       # Take profit por defecto (pips)

    # 🎯 IA Y APRENDIZAJE
    "auto_retrain_ai": True,          # Reentrenar IA automáticamente
    "retrain_interval": 50,           # Trades entre reentrenamientos
    "market_adaptation": True,        # Detectar cambios de mercado

    # 🛡️ SEGURIDAD
    "confirm_real_trading": True,     # Confirmar antes de trading real
    "max_daily_loss": 5.0,            # Máximo pérdida diaria (%)
    "emergency_stop": True,           # Parada de emergencia en drawdown alto

    # 🎨 INTERFAZ
    "theme": "dark",                  # Tema: "light" o "dark"
    "language": "es",                 # Idioma: "es" (español) o "en" (inglés)
    "show_advanced_options": False,   # Mostrar opciones avanzadas en menú
}

# =============================================================================
# CONFIGURACIONES PRESET
# =============================================================================

# Configuración CONSERVADORA (recomendada para empezar)
CONSERVATIVE_CONFIG = {
    "default_risk_percent": 1.5,
    "default_max_positions": 5,
    "default_stop_loss": 100,
    "default_take_profit": 150,
    "max_daily_loss": 3.0,
    "confirm_real_trading": True,
}

# Configuración MODERADA
MODERATE_CONFIG = {
    "default_risk_percent": 2.0,
    "default_max_positions": 10,
    "default_stop_loss": 50,
    "default_take_profit": 150,
    "max_daily_loss": 5.0,
    "confirm_real_trading": True,
}

# Configuración AGRESIVA (NO RECOMENDADA)
AGGRESSIVE_CONFIG = {
    "default_risk_percent": 3.0,
    "default_max_positions": 15,
    "default_stop_loss": 30,
    "default_take_profit": 100,
    "max_daily_loss": 10.0,
    "confirm_real_trading": True,
}

# =============================================================================
# FUNCIONES DE CONFIGURACIÓN
# =============================================================================

def get_config(preset=None):
    """
    Obtiene la configuración completa

    Args:
        preset: "conservative", "moderate", "aggressive" o None
    """
    config = LAUNCH_CONFIG.copy()

    if preset == "conservative":
        config.update(CONSERVATIVE_CONFIG)
    elif preset == "moderate":
        config.update(MODERATE_CONFIG)
    elif preset == "aggressive":
        config.update(AGGRESSIVE_CONFIG)

    return config

def save_config(config, filename="launcher_config.py"):
    """Guarda la configuración en un archivo"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("# Configuración personalizada del launcher\n")
        f.write("# Generada automáticamente\n\n")
        f.write("CUSTOM_CONFIG = {\n")
        for key, value in config.items():
            if isinstance(value, str):
                f.write(f'    "{key}": "{value}",\n')
            else:
                f.write(f'    "{key}": {value},\n')
        f.write("}\n")

def load_custom_config(filename="custom_launcher_config.py"):
    """Carga configuración personalizada"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
            # Ejecutar el archivo para obtener la configuración
            local_vars = {}
            exec(content, {}, local_vars)
            return local_vars.get('CUSTOM_CONFIG', LAUNCH_CONFIG)
    except FileNotFoundError:
        return LAUNCH_CONFIG
    except Exception as e:
        print(f"Error cargando configuración: {e}")
        return LAUNCH_CONFIG

# =============================================================================
# CONFIGURACIÓN ACTIVA
# =============================================================================

# Usar configuración por defecto directamente
ACTIVE_CONFIG = LAUNCH_CONFIG

# Si quieres usar un preset específico, descomenta una línea:
# ACTIVE_CONFIG = get_config("conservative")  # Configuración conservadora
# ACTIVE_CONFIG = get_config("moderate")     # Configuración moderada
# ACTIVE_CONFIG = get_config("aggressive")   # Configuración agresiva (NO RECOMENDADO)