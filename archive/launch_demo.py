#!/usr/bin/env python3
"""
SCRIPT DE LANZAMIENTO RÁPIDO - Professional Trading System
Ejecuta este script para iniciar el sistema de trading profesional
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

def check_requirements():
    """Verifica que las dependencias estén instaladas"""
    try:
        import flask
        import numpy
        import pandas
        import sklearn
        import MetaTrader5
        print("✅ Dependencias verificadas")
        return True
    except ImportError as e:
        print(f"❌ Falta instalar dependencias: {e}")
        print("Ejecuta: pip install -r requirements.txt")
        return False

def start_system():
    """Inicia el sistema de trading"""
    print("=" * 60)
    print("🚀 INICIANDO PROFESSIONAL TRADING SYSTEM")
    print("=" * 60)
    print()
    print("🔧 Sistema: Professional Trading System v2.0.0")
    print("🌐 Dashboard: http://localhost:5000")
    print("👤 Demo: usuario='demo', contraseña='demo123'")
    print("👑 Admin: usuario='admin', contraseña='Admin123!'")
    print()
    print("📋 Características:")
    print("   • IA Predictiva con Machine Learning")
    print("   • Dashboard Profesional Web")
    print("   • Seguridad Empresarial Avanzada")
    print("   • Integración MT5")
    print("   • Chat IA Interactivo")
    print("   • Single Device Login Enforcement")
    print()
    print("💡 Para probar:")
    print("   1. Abre http://localhost:5000 en tu navegador")
    print("   2. Haz clic en '🚀 Probar Demo Gratis'")
    print("   3. O inicia sesión con usuario 'demo' y contraseña 'demo123'")
    print()
    print("⚠️  Presiona Ctrl+C para detener el servidor")
    print()

    # Ejecutar el sistema
    try:
        # Importar y ejecutar
        from professional_trading_system import main
        main()

        # Después de main(), intentar abrir el navegador
        print("\n🌐 Abriendo dashboard en navegador...")
        time.sleep(2)
        webbrowser.open('http://localhost:5000')

    except KeyboardInterrupt:
        print("\n👋 Sistema detenido por el usuario")
    except Exception as e:
        print(f"\n❌ Error al iniciar el sistema: {e}")
        print("Verifica que todas las dependencias estén instaladas")

if __name__ == "__main__":
    print("🔍 Verificando requisitos del sistema...")

    if check_requirements():
        print("🚀 Iniciando sistema...")
        start_system()
    else:
        print("❌ No se pueden iniciar los requisitos. Instala las dependencias primero.")
        sys.exit(1)