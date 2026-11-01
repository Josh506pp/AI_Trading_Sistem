#!/usr/bin/env python
"""
Script para iniciar el servidor y probar el dashboard.
Ejecutar: python test_dashboard.py
Luego abrir: http://localhost:5000/dashboard
"""

import sys
import os
import time
import webbrowser
from threading import Thread

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from app import app, init_db
    
    def run_server():
        """Ejecutar el servidor Flask."""
        try:
            print("🚀 Iniciando servidor Flask en http://localhost:5000")
            print("📊 Dashboard disponible en: http://localhost:5000/dashboard")
            print("\n💡 INSTRUCCIONES:")
            print("   1. Abre http://localhost:5000/dashboard en tu navegador")
            print("   2. Deberías ver el gráfico de precios en dorado (#D4AF37)")
            print("   3. El gráfico debe actualizarse cada segundo")
            print("   4. Los precios deben cambiar en color (dorado subida, morado bajada)")
            print("\n⏹️  Presiona Ctrl+C para detener el servidor\n")
            
            # Inicializar base de datos
            with app.app_context():
                init_db(app)
            
            # Abrir navegador después de un pequeño delay
            time.sleep(1)
            webbrowser.open('http://localhost:5000/dashboard')
            
            # Ejecutar servidor
            app.run(debug=False, host='127.0.0.1', port=5000)
        except Exception as e:
            print(f"❌ Error al iniciar servidor: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    if __name__ == '__main__':
        try:
            run_server()
        except KeyboardInterrupt:
            print("\n\n👋 Servidor detenido")
            sys.exit(0)
            
except ImportError as e:
    print(f"❌ Error al importar: {e}")
    print("Asegúrate de que Flask está instalado: pip install -r requirements.txt")
    sys.exit(1)
