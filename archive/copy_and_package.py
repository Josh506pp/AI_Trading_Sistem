#!/usr/bin/env python3
"""Copia el proyecto a una carpeta de release y empaqueta un ejecutable."""
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
RELEASE_DIR = os.path.join(ROOT, 'release')
DIST_DIR = os.path.join(RELEASE_DIR, 'dist')
ENTRY_SCRIPT = 'start_all.py'

EXCLUDE = {
    '.git',
    '.venv',
    '__pycache__',
    'build',
    'dist',
    'release',
    'TradingSystem.spec',
    'pyinstaller_build.log',
    'server.log',
    'trading_system.db'
}

def should_ignore(dirname, names):
    ignored = []
    for name in names:
        if name in EXCLUDE:
            ignored.append(name)
        elif name.endswith(('.pyc', '.pyo', '.pyd', '.log', '.db', '.tmp', '.bak')):
            ignored.append(name)
    return ignored


def copy_project():
    if os.path.exists(RELEASE_DIR):
        try:
            shutil.rmtree(RELEASE_DIR)
        except Exception as e:
            print(f'Advertencia: no se pudo borrar {RELEASE_DIR} directamente: {e}')
    os.makedirs(RELEASE_DIR, exist_ok=True)

    source_dir = tempfile.mkdtemp(prefix='package_source_', dir=RELEASE_DIR)

    for item in os.listdir(ROOT):
        if item in EXCLUDE:
            continue
        if item.startswith('.') and item not in {'.env.example'}:
            continue
        src_path = os.path.join(ROOT, item)
        dst_path = os.path.join(source_dir, item)
        if os.path.isdir(src_path):
            shutil.copytree(src_path, dst_path, ignore=should_ignore)
        else:
            shutil.copy2(src_path, dst_path)

    print(f'Proyecto copiado a: {source_dir}')
    return source_dir


def install_pyinstaller():
    print('Instalando PyInstaller...')
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'])
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])


def build_executable(source_dir):
    os.chdir(source_dir)
    print('Construyendo el ejecutable en release...')
    dist_path = os.path.join(source_dir, 'dist', 'TradingSystem')
    work_path = os.path.join(source_dir, 'build', 'TradingSystem')
    spec_path = os.path.join(source_dir, 'build')
    cmd = [
        sys.executable,
        '-m',
        'PyInstaller',
        '--noconfirm',
        '--clean',
        '--onedir',
        '--distpath',
        os.path.join(source_dir, 'dist'),
        '--workpath',
        work_path,
        '--specpath',
        spec_path,
        '--name',
        'TradingSystem',
        ENTRY_SCRIPT
    ]
    subprocess.check_call(cmd)

    if os.path.exists(dist_path):
        final_dist = os.path.join(DIST_DIR, 'TradingSystem')
        shutil.rmtree(final_dist, ignore_errors=True)
        shutil.copytree(dist_path, final_dist)
        print(f'Ejecutable generado en: {final_dist}')
    else:
        raise FileNotFoundError('No se encontró el directorio de distribución generado por PyInstaller.')


if __name__ == '__main__':
    source_dir = copy_project()
    install_pyinstaller()
    build_executable(source_dir)
    print('Empaquetado completado. Abre release/dist/TradingSystem')
