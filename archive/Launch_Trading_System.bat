@echo off
REM =============================================================================
REM LAUNCHER PARA SISTEMA DE TRADING INTELIGENTE
REM Un solo click para iniciar todo
REM =============================================================================

echo.
echo ================================================================================
echo 🚀 INICIANDO SISTEMA DE TRADING INTELIGENTE v2.0
echo ================================================================================
echo.

REM Cambiar al directorio del proyecto
cd /d "%~dp0"

REM Verificar si Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: Python no está instalado o no está en PATH
    echo.
    echo Solución:
    echo 1. Instala Python desde https://python.org
    echo 2. Asegúrate de marcar "Add Python to PATH" durante la instalación
    echo.
    pause
    exit /b 1
)

echo ✅ Python encontrado
echo.

REM Ejecutar el launcher principal
python LAUNCH_TRADING_SYSTEM.py

REM Pausar al final para ver cualquier mensaje
echo.
echo Presiona cualquier tecla para cerrar...
pause >nul