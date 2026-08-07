param(
    [string]$Domain = 'candlekiller.dpdns.org',
    [string]$TunnelName = 'trading-system',
    [int]$LocalPort = 5000
)

$ErrorActionPreference = 'Stop'

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "No se encontró el comando '$Name' en PATH."
    }
}

Require-Command 'cloudflared'

$cloudflaredHome = Join-Path $env:USERPROFILE '.cloudflared'
$originCert = Join-Path $cloudflaredHome 'cert.pem'

if (-not (Test-Path $originCert)) {
    Write-Host "No existe cert.pem en $cloudflaredHome" -ForegroundColor Yellow
    Write-Host "Ejecuta: cloudflared tunnel login" -ForegroundColor Yellow
    throw 'Falta autenticación de Cloudflare Tunnel.'
}

Write-Host "Verificando/creando túnel '$TunnelName'..." -ForegroundColor Cyan
$createOutput = (& cmd /c "cloudflared tunnel create $TunnelName 2>&1" | Out-String)

$uuidRegex = '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}'
$tunnelId = $null

if ($createOutput -match $uuidRegex) {
    $tunnelId = $matches[0]
}

if (-not $tunnelId) {
    $listOutput = (& cmd /c "cloudflared tunnel list 2>&1" | Out-String)
    $nameLine = $listOutput -split "`r?`n" | Where-Object { $_ -match "\b$([regex]::Escape($TunnelName))\b" } | Select-Object -First 1
    if ($nameLine -and $nameLine -match $uuidRegex) {
        $tunnelId = $matches[0]
    }
}

if (-not $tunnelId) {
    throw "No se pudo resolver el Tunnel ID para '$TunnelName'.\nSalida create:\n$createOutput"
}

Write-Host "Tunnel ID: $tunnelId" -ForegroundColor Green

Write-Host "Creando/actualizando DNS route para $Domain..." -ForegroundColor Cyan
$routeOutput = (& cmd /c "cloudflared tunnel route dns $TunnelName $Domain 2>&1" | Out-String)

if ($LASTEXITCODE -ne 0) {
    throw "No se pudo crear/actualizar la ruta DNS para '$Domain'.\nSalida:\n$routeOutput"
}

$credentialsFile = Join-Path $cloudflaredHome "$tunnelId.json"
if (-not (Test-Path $credentialsFile)) {
    throw "No se encontró credentials file esperado: $credentialsFile"
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$configDir = Join-Path $projectRoot 'cloudflared'
if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir | Out-Null
}

$configPath = Join-Path $configDir 'config.yml'

$configYaml = @"
tunnel: $tunnelId
credentials-file: $credentialsFile

ingress:
  - hostname: $Domain
    service: http://127.0.0.1:$LocalPort
  - service: http_status:404
"@

Set-Content -Path $configPath -Value $configYaml -Encoding UTF8

Write-Host "Configuración generada: $configPath" -ForegroundColor Green
Write-Host "" 
Write-Host "Ahora ejecuta:" -ForegroundColor Cyan
Write-Host ('$env:CF_TUNNEL_NAME = ''' + $TunnelName + '''')
Write-Host ('$env:CF_TUNNEL_HOSTNAME = ''' + $Domain + '''')
Write-Host ('$env:CF_TUNNEL_CONFIG = ''' + $configPath + '''')
Write-Host '.\start_with_cloudflare.ps1'