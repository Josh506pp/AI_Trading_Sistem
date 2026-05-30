# Professional Trading System - Configuration File
# Archivo de configuración segura - NO COMPARTIR

import os
from cryptography.fernet import Fernet

# =============================================================================
# CONFIGURACIÓN SEGURA - EDITAR CON CUIDADO
# =============================================================================

# Credenciales de MT5 (encriptadas en producción)
MT5_CONFIG = {
    'login': os.environ.get('MT5_LOGIN', '123456'),  # Demo login válido
    'password': os.environ.get('MT5_PASSWORD', 'demo_password'),
    'server': os.environ.get('MT5_SERVER', 'MetaQuotes-Demo'),
    'timeout': 60000,
    'enable_real_trading': os.environ.get('ENABLE_REAL_TRADING', 'false').lower() == 'true'
}

# Configuración de Base de Datos (para futura implementación)
DATABASE_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', '5432')),
    'database': os.environ.get('DB_NAME', 'trading_system'),
    'user': os.environ.get('DB_USER', 'trader'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'ssl_mode': 'require'
}

# Configuración de Email (para notificaciones)
EMAIL_CONFIG = {
    'smtp_server': os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
    'smtp_port': int(os.environ.get('SMTP_PORT', '587')),
    'username': os.environ.get('EMAIL_USER', ''),
    'password': os.environ.get('EMAIL_PASSWORD', ''),
    'from_email': os.environ.get('FROM_EMAIL', 'noreply@tradingsystem.com'),
    'use_tls': True
}

# Configuración de Trading
TRADING_CONFIG = {
    'symbols': ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD'],
    'timeframes': ['M15', 'H1', 'H4', 'D1'],
    'max_concurrent_trades': 5,
    'min_account_balance': 100.0,
    'max_daily_loss_percent': 5.0,
    'max_daily_trades': 20,
    'enable_partial_closes': True,
    'enable_scaling_in': False
}

# Configuración de IA
AI_CONFIG = {
    'model_update_interval_hours': 24,
    'min_training_samples': 1000,
    'max_model_age_days': 30,
    'feature_importance_threshold': 0.01,
    'enable_online_learning': True,
    'confidence_calibration': True
}

# Configuración de Monitoreo
MONITORING_CONFIG = {
    'enable_telegram_bot': os.environ.get('ENABLE_TELEGRAM', 'false').lower() == 'true',
    'telegram_token': os.environ.get('TELEGRAM_TOKEN', ''),
    'telegram_chat_id': os.environ.get('TELEGRAM_CHAT_ID', ''),
    'alert_on_large_loss': True,
    'alert_threshold_pips': 50,
    'heartbeat_interval_minutes': 5
}

# Configuración de Backup
BACKUP_CONFIG = {
    'enable_auto_backup': True,
    'backup_interval_hours': 6,
    'backup_retention_days': 30,
    'backup_path': './backups/',
    'compress_backups': True
}

# =============================================================================
# UTILIDADES DE CONFIGURACIÓN
# =============================================================================

class ConfigManager:
    """Gestor de configuración con encriptación"""

    @staticmethod
    def get_encrypted_config(key: str) -> dict:
        """Obtiene configuración encriptada"""
        # En producción, implementar encriptación real
        configs = {
            'mt5': MT5_CONFIG,
            'database': DATABASE_CONFIG,
            'email': EMAIL_CONFIG,
            'trading': TRADING_CONFIG,
            'ai': AI_CONFIG,
            'monitoring': MONITORING_CONFIG,
            'backup': BACKUP_CONFIG
        }
        return configs.get(key, {})

    @staticmethod
    def validate_config() -> list:
        """Valida configuración crítica"""
        errors = []

        # Validar MT5
        if not MT5_CONFIG['login'] or MT5_CONFIG['login'] == 'demo_login':
            errors.append("MT5 login no configurado")

        # Validar email si monitoring está habilitado
        if MONITORING_CONFIG['enable_telegram_bot']:
            if not MONITORING_CONFIG['telegram_token']:
                errors.append("Telegram token requerido para monitoring")

        # Validar límites de trading
        if TRADING_CONFIG['max_daily_loss_percent'] > 10:
            errors.append("Límite de pérdida diaria muy alto (>10%)")

        return errors

# =============================================================================
# VALIDACIÓN DE CONFIGURACIÓN
# =============================================================================

if __name__ == "__main__":
    print("🔍 Validando configuración...")

    errors = ConfigManager.validate_config()

    if errors:
        print("❌ Errores de configuración encontrados:")
        for error in errors:
            print(f"  - {error}")
        print("\nPor favor, revise el archivo de configuración.")
    else:
        print("✅ Configuración válida")

    print("\n📋 Resumen de configuración:")
    print(f"  MT5 Login: {MT5_CONFIG['login']}")
    print(f"  Real Trading: {'HABILITADO' if MT5_CONFIG['enable_real_trading'] else 'DESHABILITADO'}")
    print(f"  Símbolos: {', '.join(TRADING_CONFIG['symbols'])}")
    print(f"  Max Trades Concurrentes: {TRADING_CONFIG['max_concurrent_trades']}")
    print(f"  Telegram Alerts: {'HABILITADO' if MONITORING_CONFIG['enable_telegram_bot'] else 'DESHABILITADO'}")