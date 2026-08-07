$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$cloudflaredCmd = $null
$cloudflaredFromPath = Get-Command cloudflared -ErrorAction SilentlyContinue
if ($cloudflaredFromPath) {
	$cloudflaredCmd = $cloudflaredFromPath.Source
}
if (-not $cloudflaredCmd) {
	$fallbackCloudflared = 'C:\Program Files (x86)\cloudflared\cloudflared.exe'
	if (Test-Path $fallbackCloudflared) {
		$cloudflaredCmd = $fallbackCloudflared
	}
}
if (-not $cloudflaredCmd) {
	Write-Host "cloudflared no está instalado o no se puede localizar." -ForegroundColor Red
	Write-Host "Instálalo desde: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/" -ForegroundColor Yellow
	exit 1
}

$pythonCmd = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $pythonCmd)) {
	$pythonFromPath = Get-Command python -ErrorAction SilentlyContinue
	if ($pythonFromPath) {
		$pythonCmd = $pythonFromPath.Source
	} else {
		Write-Host "python no está disponible en PATH y no existe .venv\\Scripts\\python.exe" -ForegroundColor Red
		exit 1
	}
}

$env:FLASK_PORT = if ($env:FLASK_PORT) { $env:FLASK_PORT } else { '5080' }
$port = [int]$env:FLASK_PORT
$env:PORT = [string]$port
$tunnelName = $env:CF_TUNNEL_NAME
$tunnelConfig = $env:CF_TUNNEL_CONFIG
$tunnelHostname = $env:CF_TUNNEL_HOSTNAME
$tunnelRef = $null

# Prefer named tunnel when a config file exists, even if env vars were not set.
if (-not $tunnelConfig) {
	$defaultConfig = Join-Path $PSScriptRoot 'cloudflared\config.yml'
	if (Test-Path $defaultConfig) {
		$tunnelConfig = $defaultConfig
	}
}

if ($tunnelName) {
	$tunnelRef = $tunnelName
}
elseif ($tunnelConfig -and (Test-Path $tunnelConfig)) {
	$tunnelIdLine = Select-String -Path $tunnelConfig -Pattern '^\s*tunnel\s*:\s*(.+)\s*$' | Select-Object -First 1
	if ($tunnelIdLine) {
		$tunnelRef = $tunnelIdLine.Matches[0].Groups[1].Value.Trim()
	}
}

Write-Host "Iniciando servidor de producción (Waitress) en puerto $port..." -ForegroundColor Cyan

# Inicia servidor en modo oculto para no bloquear la consola.
$pythonProc = Start-Process -FilePath $pythonCmd -ArgumentList '-m', 'waitress', "--listen=127.0.0.1:$port", 'wsgi:app' -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru

# Espera breve activa a que el servidor responda.
$serverReady = $false
for ($i = 0; $i -lt 15; $i++) {
	try {
		$resp = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$port/api/ping" -TimeoutSec 2
		if ($resp.StatusCode -eq 200) {
			$serverReady = $true
			break
		}
	}
	catch {
		Start-Sleep -Milliseconds 700
	}
}

if (-not $serverReady) {
	Write-Host "El servidor local no respondió a tiempo. Revisa logs/procesos y vuelve a intentar." -ForegroundColor Red
	if ($pythonProc -and -not $pythonProc.HasExited) {
		Stop-Process -Id $pythonProc.Id -Force -ErrorAction SilentlyContinue
	}
	exit 1
}

Write-Host "Levantando túnel de Cloudflare..." -ForegroundColor Cyan
if ($tunnelConfig) {
	if ($tunnelRef) {
		Write-Host "Usando túnel nombrado: $tunnelRef" -ForegroundColor Green
	} else {
		Write-Host "Usando túnel nombrado desde config: $tunnelConfig" -ForegroundColor Green
	}
	if ($tunnelHostname) {
		Write-Host "Hostname público: $tunnelHostname" -ForegroundColor Green
	}
	Write-Host "Nota: este modo usa el túnel nombrado configurado en Cloudflare." -ForegroundColor Yellow
}
elseif ($tunnelName -and $tunnelHostname) {
	Write-Host "Usando túnel nombrado: $tunnelName" -ForegroundColor Green
	Write-Host "Hostname público: $tunnelHostname" -ForegroundColor Green
	Write-Host "Nota: este modo requiere que el túnel y DNS estén creados en Cloudflare." -ForegroundColor Yellow
}
else {
	Write-Host "Cuando veas una URL https://*.trycloudflare.com, compártela y podrás acceder desde cualquier dispositivo." -ForegroundColor Green
	Write-Host "Nota: este modo requiere que este PC siga encendido." -ForegroundColor Yellow
}
try {
	if ($tunnelConfig) {
		if (-not $tunnelRef) {
			throw 'No se pudo determinar el nombre o ID del túnel desde CF_TUNNEL_NAME ni desde cloudflared/config.yml.'
		}
		& $cloudflaredCmd tunnel --config $tunnelConfig run $tunnelRef
	}
	elseif ($tunnelName -and $tunnelHostname) {
		throw 'CF_TUNNEL_NAME y CF_TUNNEL_HOSTNAME están definidos, pero no existe CF_TUNNEL_CONFIG ni cloudflared/config.yml.'
	}
	else {
		& $cloudflaredCmd tunnel --url "http://127.0.0.1:$port"
	}
}
finally {
	if ($pythonProc -and -not $pythonProc.HasExited) {
		Write-Host "Deteniendo servidor local..." -ForegroundColor DarkYellow
		Stop-Process -Id $pythonProc.Id -Force -ErrorAction SilentlyContinue
	}
}
