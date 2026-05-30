@echo off
REM Copia y empaqueta el proyecto en un ejecutable con PyInstaller
SETLOCAL
python copy_and_package.py
echo.
echo Empaquetado completado. Revisa la carpeta release\dist\TradingSystem
echo.
pause
