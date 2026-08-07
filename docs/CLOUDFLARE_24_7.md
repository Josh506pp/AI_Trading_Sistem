# Acceso desde cualquier dispositivo con Cloudflare (y 24/7 sin PC encendida)

## Resumen rápido
- Si usas solo `cloudflared tunnel` en tu PC: tendrás URL pública, pero tu PC debe estar encendida.
- Si quieres 24/7 real (PC apagada): debes desplegar la app en un servidor cloud y luego conectar dominio con Cloudflare.

## Opción A: URL pública inmediata (requiere PC encendida)
1. Instala cloudflared.
2. Ejecuta desde raíz del proyecto:

```powershell
./start_with_cloudflare.ps1
```

3. Usa la URL `https://*.trycloudflare.com` que aparece en consola.

## Opción B: 24/7 real sin PC encendida (recomendado)

### Paso 1: Desplegar app en la nube
Puedes usar Heroku con el script ya incluido:

```powershell
./deploy_to_heroku.ps1 -HerokuAppName tu-app-trading -FlaskSecretKey "TU_SECRET"
```

Al terminar tendrás una URL tipo:
- `https://tu-app-trading.herokuapp.com`

### Paso 2: Poner tu dominio en Cloudflare
1. Agrega tu dominio en Cloudflare.
2. En DNS crea:
- Tipo: `CNAME`
- Nombre: `bot` (o el subdominio que prefieras)
- Target: `tu-app-trading.herokuapp.com`
- Proxy: `Proxied` (nube naranja)

3. Espera propagación DNS.

### Paso 3: SSL y seguridad
1. En Cloudflare > SSL/TLS:
- Modo recomendado: `Full` o `Full (strict)`.
2. En Cloudflare > WAF:
- Activa reglas básicas para proteger endpoints.

### Paso 4: Verificación
Comprueba:
- `https://bot.tudominio.com/`
- `https://bot.tudominio.com/api/status`

## MT5 y consideraciones importantes
- Si MT5 debe operar real, el terminal MT5 debe estar donde corre la app (PC/VM Windows).
- Si despliegas en Heroku/Linux, MT5 local no estará disponible como terminal de escritorio.
- Para trading real con MT5 y 24/7, lo ideal es una VM Windows 24/7 (Azure/AWS/etc.) con MT5 + app + cloudflared o dominio Cloudflare.

## Arquitectura recomendada para 24/7 con MT5 real
- VM Windows (encendida 24/7)
- MetaTrader 5 instalado y logueado
- App Flask corriendo como servicio
- Cloudflare Tunnel o dominio Cloudflare al servicio web

Así no depende de tu PC personal, pero sí de una máquina siempre encendida en la nube.
