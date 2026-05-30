<#
PowerShell helper para desplegar el trading app en Heroku.
Editar las variables abajo con tus valores y ejecutar desde la raíz del repo.
#>

param(
    [string]$HerokuAppName = '',
    [string]$FlaskSecretKey = '',
    [string]$ShopifyApiKey = '',
    [string]$ShopifyApiSecret = '',
    [string]$ShopifyAccessToken = '',
    [string]$ShopifyShopUrl = '',
    [string]$MT5Login = '',
    [string]$MT5Password = '',
    [string]$MT5Server = '',
    [string]$MT5Path = ''
)

function Require-Heroku {
    if (-not (Get-Command heroku -ErrorAction SilentlyContinue)) {
        Write-Error 'Heroku CLI no encontrado. Instala Heroku CLI y vuelve a intentarlo.'
        exit 1
    }
}

function Set-HerokuConfig {
    param(
        [string]$AppName,
        [string]$Key,
        [string]$Value
    )
    if (-not [string]::IsNullOrEmpty($Value)) {
        heroku config:set $Key="$Value" --app $AppName | Out-Null
        Write-Host "Config set: $Key"
    }
}

if (-not $HerokuAppName) {
    Write-Error 'Debes pasar el nombre de la app Heroku en -HerokuAppName.'
    exit 1
}

Require-Heroku

Write-Host "Desplegando en Heroku: $HerokuAppName"

Write-Host '1) Comprobando app Heroku...'
$existing = heroku apps:info --app $HerokuAppName 2>$null
if (-not $?) {
    heroku create $HerokuAppName
}

Write-Host '2) Subiendo código a Heroku...'
git push heroku main
if ($LASTEXITCODE -ne 0) {
    Write-Error 'git push heroku main falló. Corrige errores y vuelve a ejecutar.'
    exit 1
}

Write-Host '3) Configurando variables de entorno Heroku...'
Set-HerokuConfig -AppName $HerokuAppName -Key 'FLASK_SECRET_KEY' -Value $FlaskSecretKey
Set-HerokuConfig -AppName $HerokuAppName -Key 'FLASK_ENV' -Value 'production'
Set-HerokuConfig -AppName $HerokuAppName -Key 'SHOPIFY_API_KEY' -Value $ShopifyApiKey
Set-HerokuConfig -AppName $HerokuAppName -Key 'SHOPIFY_API_SECRET' -Value $ShopifyApiSecret
Set-HerokuConfig -AppName $HerokuAppName -Key 'SHOPIFY_API_ACCESS_TOKEN' -Value $ShopifyAccessToken
Set-HerokuConfig -AppName $HerokuAppName -Key 'SHOPIFY_SHOP_URL' -Value $ShopifyShopUrl
Set-HerokuConfig -AppName $HerokuAppName -Key 'MT5_LOGIN' -Value $MT5Login
Set-HerokuConfig -AppName $HerokuAppName -Key 'MT5_PASSWORD' -Value $MT5Password
Set-HerokuConfig -AppName $HerokuAppName -Key 'MT5_SERVER' -Value $MT5Server
Set-HerokuConfig -AppName $HerokuAppName -Key 'MT5_PATH' -Value $MT5Path

Write-Host '4) Abriendo app en Heroku...'
heroku open --app $HerokuAppName

Write-Host '5) Ver logs...' 
heroku logs --tail --app $HerokuAppName
