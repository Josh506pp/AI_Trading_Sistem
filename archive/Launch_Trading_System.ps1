# =============================================================================
# LAUNCHER PARA SISTEMA DE TRADING INTELIGENTE
# Un solo click para iniciar todo (PowerShell)
# =============================================================================

param(
    [switch]$NoDashboard,
    [switch]$NoChat,
    [switch]$Verbose
)

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "🚀 INICIANDO SISTEMA DE TRADING INTELIGENTE v2.0" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Cambiar al directorio del script
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Verificar Python
try {
    $pythonVersion = python --version 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Python not found"
    }
    Write-Host "✅ Python encontrado: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ ERROR: Python no está instalado o no está en PATH" -ForegroundColor Red
    Write-Host ""
    Write-Host "Solución:" -ForegroundColor Yellow
    Write-Host "1. Instala Python desde https://python.org" -ForegroundColor Yellow
    Write-Host "2. Asegúrate de marcar 'Add Python to PATH' durante la instalación" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Presiona Enter para salir"
    exit 1
}

Write-Host ""

# Configurar argumentos
$args = @()

if ($NoDashboard) {
    $args += "--no-dashboard"
}

if ($NoChat) {
    $args += "--no-chat"
}

if ($Verbose) {
    $args += "--verbose"
}

# Ejecutar el launcher principal
try {
    & python LAUNCH_TRADING_SYSTEM.py @args
} catch {
    Write-Host "❌ Error ejecutando el launcher: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "Presiona cualquier tecla para cerrar..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")