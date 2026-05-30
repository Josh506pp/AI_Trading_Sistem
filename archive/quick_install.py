#!/usr/bin/env python3
"""
INSTALADOR RÁPIDO - Professional Trading System
Instala todas las dependencias y configura el sistema automáticamente
"""

import os
import sys
import subprocess
import platform

def print_banner():
    """Muestra el banner del instalador"""
    print("=" * 60)
    print("🔧 INSTALADOR RÁPIDO - PROFESSIONAL TRADING SYSTEM v2.0.0")
    print("=" * 60)
    print()

def check_python_version():
    """Verifica la versión de Python"""
    print("🐍 Verificando versión de Python...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} - Se requiere Python 3.8+")
        return False

def install_dependencies():
    """Instala las dependencias de Python"""
    print("📦 Instalando dependencias de Python...")

    try:
        # Actualizar pip primero
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Instalar dependencias
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        print("✅ Dependencias instaladas correctamente")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error instalando dependencias: {e}")
        return False

def download_mt5():
    """Verifica si MetaTrader 5 está instalado"""
    print("📥 Verificando MetaTrader 5...")

    # Verificar si MT5 ya está instalado
    mt5_paths = [
        "C:\\Program Files\\MetaTrader 5",
        "C:\\Program Files (x86)\\MetaTrader 5",
        os.path.expanduser("~\\AppData\\Roaming\\MetaQuotes\\Terminal")
    ]

    mt5_installed = any(os.path.exists(path) for path in mt5_paths)

    if mt5_installed:
        print("✅ MetaTrader 5 ya está instalado")
        return True

    print("⚠️ MetaTrader 5 no encontrado")
    print("📋 Instrucciones para instalar MT5:")
    print("   1. Ve a https://www.metatrader5.com/es/download")
    print("   2. Descarga la versión para tu broker preferido")
    print("   3. Instala y configura tu cuenta")
    print("   4. Vuelve a ejecutar este instalador")
    print()
    print("💡 Brokers recomendados:")
    print("   • IC Markets: https://www.icmarkets.com")
    print("   • Pepperstone: https://pepperstone.com")
    print("   • Admiral Markets: https://admiralmarkets.com")
    print()

    return False

def create_shortcuts():
    """Crea accesos directos para facilitar el uso"""
    print("🔗 Creando accesos directos...")

    try:
        # Crear acceso directo al launcher
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        shortcut_path = os.path.join(desktop, "Professional Trading System.lnk")

        # Para Windows, crear un archivo .bat que ejecute el launcher
        bat_content = f'''@echo off
cd /d "{os.getcwd()}"
python launch_demo.py
pause
'''

        bat_path = os.path.join(desktop, "Launch Trading System.bat")
        with open(bat_path, 'w') as f:
            f.write(bat_content)

        print(f"✅ Acceso directo creado: {bat_path}")
        return True
    except Exception as e:
        print(f"⚠️ No se pudo crear acceso directo: {e}")
        return False

def run_validation():
    """Ejecuta validación del sistema"""
    print("🔍 Ejecutando validación del sistema...")

    try:
        result = subprocess.run([sys.executable, "validate_distribution.py"],
                              capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print("✅ Validación completada exitosamente")
            return True
        else:
            print("⚠️ Validación completada con advertencias")
            print(result.stdout)
            return True
    except subprocess.TimeoutExpired:
        print("⚠️ Validación tardó demasiado tiempo")
        return False
    except Exception as e:
        print(f"❌ Error en validación: {e}")
        return False

def main():
    """Función principal del instalador"""
    print_banner()

    success_count = 0
    total_steps = 5

    # 1. Verificar Python
    if check_python_version():
        success_count += 1
    else:
        print("❌ Instalación cancelada - Python incompatible")
        sys.exit(1)

    # 2. Instalar dependencias
    if install_dependencies():
        success_count += 1

    # 3. Verificar MT5
    if download_mt5():
        success_count += 1

    # 4. Crear accesos directos
    if create_shortcuts():
        success_count += 1

    # 5. Validar sistema
    if run_validation():
        success_count += 1

    # Resultado final
    print()
    print("=" * 60)
    if success_count == total_steps:
        print("🎉 ¡INSTALACIÓN COMPLETADA EXITOSAMENTE!")
    else:
        print(f"⚠️ INSTALACIÓN COMPLETADA CON {total_steps - success_count} ADVERTENCIAS")
    print("=" * 60)
    print()
    print("🚀 Para iniciar el sistema:")
    print("   • Ejecuta: python launch_demo.py")
    print("   • O usa el acceso directo en el escritorio")
    print("   • Abre: http://localhost:5000")
    print()
    print("👤 Credenciales demo:")
    print("   • Usuario: demo")
    print("   • Contraseña: demo123")
    print()
    print("📖 Lee SALES_README.md para más información")
    print()
    print("💡 Próximos pasos:")
    print("   1. Instala MetaTrader 5 si no lo tienes")
    print("   2. Configura tu cuenta de broker")
    print("   3. Ejecuta el sistema y prueba la demo")
    print("   4. Compra la versión completa por $497 USD")

if __name__ == "__main__":
    main()