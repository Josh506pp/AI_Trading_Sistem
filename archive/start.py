#!/usr/bin/env python3
"""
🚀 PUNTO DE ENTRADA - PROFESSIONAL TRADING SYSTEM
Sistema de Trading Profesional - Lanzador Funcional
"""

import os
import sys
import time
import webbrowser
from datetime import datetime

# Agregar ruta del proyecto
sys.path.insert(0, os.path.dirname(__file__))

def start_trading_system():
    """Inicia el sistema de trading profesional"""
    
    print("\n" + "=" * 80)
    print("🚀 PROFESSIONAL TRADING SYSTEM v2.0.0")
    print("=" * 80)
    print("Sistema de Trading Inteligente con Seguridad Avanzada")
    print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")
    
    try:
        print("📦 Importando módulos...")
        from professional_trading_system import (
            ProfessionalTradingSystem,
            ProfessionalTradingDashboard,
            SecurityConfig
        )
        print("✅ Módulos cargados correctamente\n")
        
    except ImportError as e:
        print(f"❌ Error importando módulos: {e}")
        print("\n📋 Instalando dependencias...")
        os.system("pip install -r requirements.txt")
        sys.exit(1)
    
    try:
        # Crear sistema
        print("🔧 Inicializando sistema de trading...")
        trading_system = ProfessionalTradingSystem()
        print("✅ Sistema inicializado\n")
        
        # Crear dashboard
        print("🎨 Inicializando dashboard...")
        dashboard = ProfessionalTradingDashboard(trading_system)
        print("✅ Dashboard listo\n")
        
        # Información de acceso
        print("=" * 80)
        print("🌐 ACCESO AL SISTEMA")
        print("=" * 80)
        print(f"📱 URL:      http://localhost:5000")
        print(f"👤 Admin:    admin")
        print(f"🔑 Password: RyzA_jjITjuPQtV66Wwf0A")
        print(f"🎮 Demo:     demo / demo123")
        print("=" * 80 + "\n")
        
        print("🔒 SEGURIDAD IMPLEMENTADA:")
        print("  ✅ Autenticación segura (SHA256)")
        print("  ✅ Control de dispositivos (single-device)")
        print("  ✅ Encriptación de datos")
        print("  ✅ Rate limiting")
        print("  ✅ Logging de auditoría completo")
        print("  ✅ IA con protecciones anti-manipulación")
        print("  ✅ Validación de parámetros de trading\n")
        
        print("💾 BASE DE DATOS:")
        print("  ✅ Clientes: Registro y autenticación")
        print("  ✅ Dispositivos: Fingerprinting único")
        print("  ✅ Sesiones: Token-based con expiración")
        print("  ✅ Pagos: Integración Stripe")
        print("  ✅ Auditoría: Logging completo")
        print("  ✅ Intentos bloqueados: Rastreo de accesos\n")
        
        print("=" * 80)
        print("🎯 PRÓXIMO PASO: Abriendo dashboard...")
        print("=" * 80 + "\n")
        
        # Esperar un poco y abrir navegador
        time.sleep(2)
        
        try:
            print("🌐 Abriendo navegador automáticamente...")
            webbrowser.open('http://localhost:5000')
        except Exception as e:
            print(f"⚠️  No se pudo abrir navegador automáticamente: {e}")
            print("   Accede manualmente a: http://localhost:5000")
        
        print("\n🚀 Iniciando servidor...")
        print("   Presiona CTRL+C para detener\n")
        
        # Iniciar dashboard
        dashboard.run(host='0.0.0.0', port=5000, debug=True)
        
    except KeyboardInterrupt:
        print("\n\n🛑 Sistema detenido por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    start_trading_system()
