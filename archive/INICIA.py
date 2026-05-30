#!/usr/bin/env python3
"""
⚡ INICIA AQUÍ - SISTEMA DE TRADING
Ejecuta esto para que TODO funcione
"""

import os
import sys
import subprocess
import webbrowser
import time

def main():
    """Inicia el sistema completo"""
    
    print("\n" + "=" * 80)
    print("⚡ INICIANDO SISTEMA DE TRADING")
    print("=" * 80)
    print()
    
    # Verificar que estamos en la carpeta correcta
    if not os.path.exists("web.py"):
        print("❌ Error: Ejecuta desde c:\\Users\\Joshua\\Desktop\\proyectos")
        sys.exit(1)
    
    print("✅ Ubicación correcta verificada")
    print()
    
    # Limpiar BD vieja
    print("🧹 Limpiando base de datos anterior...")
    for file in os.listdir("."):
        if file.endswith(".db") or file.endswith(".db-wal") or file.endswith(".db-shm"):
            try:
                os.remove(file)
                print(f"   Eliminado: {file}")
            except:
                pass
    print()
    
    # Mostrar información
    print("🌐 ACCESO AL SISTEMA:")
    print("   URL:       http://localhost:5000")
    print()
    print("🔐 CREDENCIALES:")
    print("   Admin:     admin / RyzA_jjITjuPQtV66Wwf0A")
    print("   Demo:      trader / SecurePass123")
    print()
    print("=" * 80)
    print("🚀 Iniciando servidor en 2 segundos...")
    print("   Presiona CTRL+C para detener")
    print("=" * 80)
    print()
    
    time.sleep(2)
    
    # Intentar abrir navegador
    try:
        print("🌐 Abriendo navegador...")
        webbrowser.open("http://localhost:5000")
        time.sleep(1)
    except:
        pass
    
    # Iniciar servidor
    try:
        print("\n✅ SERVIDOR INICIADO\n")
        os.system("python web.py")
    except KeyboardInterrupt:
        print("\n\n🛑 Servidor detenido")
        sys.exit(0)

if __name__ == "__main__":
    main()
