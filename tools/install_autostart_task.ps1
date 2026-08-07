$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$startupScript = Join-Path $root 'start_with_cloudflare.ps1'
$taskName = 'TradingSystem-AutoStart'

if (-not (Test-Path $startupScript)) {
    throw "No se encontro start_with_cloudflare.ps1 en: $startupScript"
}

$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

$action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$startupScript`""

$trigger = New-ScheduledTaskTrigger -AtLogOn -User $currentUser

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1)

$principal = New-ScheduledTaskPrincipal `
    -UserId $currentUser `
    -LogonType Interactive `
    -RunLevel Limited

$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings | Out-Null

Start-ScheduledTask -TaskName $taskName

Write-Output "Task creada y ejecutada: $taskName"
Write-Output "Usuario: $currentUser"
Write-Output "Script: $startupScript"
