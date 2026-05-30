#!/usr/bin/env python3
"""Empaqueta el proyecto en un ejecutable usando PyInstaller."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

REQ_FILE = os.path.join(ROOT, 'requirements.txt')

print('Preparando entorno de empaquetado...')

try:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'])
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
except subprocess.CalledProcessError as exc:
    print('Error instalando PyInstaller:', exc)
    sys.exit(1)

pyinstaller_cmd = [
    sys.executable,
    '-m',
    'PyInstaller',
    '--noconfirm',
    '--clean',
    '--onedir',
    '--name',
    'TradingSystem',
    'start_all.py'
]

print('Empaquetando el ejecutable...')
try:
    subprocess.check_call(pyinstaller_cmd)
    print('Empaquetado completado. Revisa la carpeta dist\\TradingSystem')
except subprocess.CalledProcessError as exc:
    print('Error durante el empaquetado:', exc)
    sys.exit(1)
