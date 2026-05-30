#!/usr/bin/env python3
"""Empaqueta el proyecto en un ejecutable usando PyInstaller."""
import os
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.dirname(__file__))
RELEASE_DIR = os.path.join(ROOT, 'release')
DIST_ROOT = os.path.join(RELEASE_DIR, 'dist')
BUILD_ROOT = os.path.join(RELEASE_DIR, 'build')
ENTRY_SCRIPT = os.path.join(ROOT, 'app_launcher.py')
EXECUTABLE_NAME = 'TradingSystem'


def install_pyinstaller():
    print('Instalando PyInstaller si es necesario...')
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'])
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])


def clean_previous_builds():
    for path in [DIST_ROOT, BUILD_ROOT, os.path.join(ROOT, f'{EXECUTABLE_NAME}.spec')]:
        if os.path.exists(path):
            print(f'Eliminando {path}')
            shutil.rmtree(path, ignore_errors=True) if os.path.isdir(path) else os.remove(path)


def build_executable():
    os.makedirs(DIST_ROOT, exist_ok=True)
    os.makedirs(BUILD_ROOT, exist_ok=True)

    cmd = [
        sys.executable,
        '-m',
        'PyInstaller',
        '--noconfirm',
        '--clean',
        '--onedir',
        '--name',
        EXECUTABLE_NAME,
        '--distpath',
        DIST_ROOT,
        '--workpath',
        BUILD_ROOT,
        '--specpath',
        BUILD_ROOT,
        ENTRY_SCRIPT
    ]
    print('Ejecutando PyInstaller...')
    subprocess.check_call(cmd, cwd=ROOT)


def main():
    install_pyinstaller()
    clean_previous_builds()
    build_executable()
    print('\nEmpaquetado finalizado con éxito.')
    print(f'El ejecutable se encuentra en: {os.path.join(DIST_ROOT, EXECUTABLE_NAME)}')


if __name__ == '__main__':
    main()
