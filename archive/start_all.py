#!/usr/bin/env python3
"""
Lanzador único: importa y ejecuta la aplicación principal `app.py`.
Ejecuta todo al lanzar este archivo: hilos de precios, IA y servidor web.
"""
import os
import sys
import time
import webbrowser

# Asegurar que el directorio de trabajo sea la raíz del proyecto
ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

import subprocess

# Instalación automática de dependencias (puedes pasar --no-install para evitarlo)
if '--no-install' not in sys.argv:
    req_file = os.path.join(ROOT, 'requirements.txt')
    if os.path.exists(req_file):
        try:
            print('Instalando dependencias desde requirements.txt (si es necesario)...')
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', req_file])
        except Exception as e:
            print('Advertencia: fallo al instalar dependencias automáticamente:', e)
            print('Puedes instalar manualmente con: python -m pip install -r requirements.txt')

try:
    # Importar la función que inicia el servidor desde app.py
    from app import run_flask_app
except Exception as e:
    print("Error importando 'app.py'. Asegúrate de que las dependencias estén instaladas:")
    print(e)
    sys.exit(1)


def main():
    print("Iniciando todo: hilos, IA y servidor web...")
    # Abrir en navegador (opcional)
    try:
        webbrowser.open('http://127.0.0.1:5000')
    except Exception:
        pass

    # Ejecutar la aplicación (run_flask_app hace la selección de puerto)
    try:
        run_flask_app()
    except Exception as e:
        print('Error al iniciar la aplicación:')
        raise

if __name__ == '__main__':
    main()
