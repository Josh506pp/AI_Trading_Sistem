#!/usr/bin/env pwsh
# Setup script for Trading Bot project

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "Trading Bot Project Setup" -ForegroundColor Green
Write-Host "=" * 70

# Check Python
Write-Host "`n[1/3] Checking Python..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Found: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "✗ Python not found!" -ForegroundColor Red
    exit 1
}

# Install dependencies
Write-Host "`n[2/3] Installing dependencies..." -ForegroundColor Yellow
python -m pip install -r requirements.txt --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to install dependencies" -ForegroundColor Red
    exit 1
}

# Verify code compiles
Write-Host "`n[3/3] Verifying code compilation..." -ForegroundColor Yellow
python -m py_compile trading_bot.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Code compiles successfully" -ForegroundColor Green
} else {
    Write-Host "✗ Code compilation failed" -ForegroundColor Red
    exit 1
}

Write-Host "`n" + ("=" * 70) -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "=" * 70
Write-Host "`nTo run the bot:" -ForegroundColor Cyan
Write-Host "  python trading_bot.py`n" -ForegroundColor White

Write-Host "To debug in VS Code:" -ForegroundColor Cyan
Write-Host "  Press F5 and select 'Python: Trading Bot (Debug)'`n" -ForegroundColor White
