# Shopify Local App - Ejecución en la misma PC

Este proyecto ya está preparado para ejecutarse localmente como una aplicación en la misma PC.
Si quieres usarlo como una app local conectada a Shopify, aquí están los pasos y los archivos necesarios.

## Qué ya tienes listo

- Ejecutable local empaquetado: `release/dist/TradingSystem/TradingSystem.exe`
- Lanzador de Windows: `build_executable.bat`
- Generador de ejecutable en Python: `copy_and_package.py`
- Configuración de producción: `.env.example`
- Servidor WSGI y Docker: `wsgi.py`, `production.py`, `Dockerfile`, `docker-compose.yml`
- Documentación de despliegue: `PRODUCTION_DEPLOYMENT.md`

## Requisitos para ejecutar localmente

1. Windows PC
2. MetaTrader 5 instalado y configurado (si vas a usar trading real)
3. Python si quieres ejecutar el código fuente en lugar del `.exe`
4. Variables de entorno o archivo `.env` con credenciales MT5 y `FLASK_SECRET_KEY`

## Cómo ejecutar la app localmente

### Opción 1: Ejecutable ya empaquetado

1. Abre `release\\dist\\TradingSystem`
2. Ejecuta `TradingSystem.exe`
3. Abre el navegador en `http://127.0.0.1:8080` si el dashboard no se abre automáticamente

### Opción 2: Ejecutar desde el código fuente

1. Copia `.env.example` a `.env`
2. Rellena variables como `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER`, `FLASK_SECRET_KEY`
3. Instala dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. Ejecuta en producción:
   ```bash
   python production.py
   ```

## Cómo usarlo con Shopify como app local

Shopify permite desarrollar apps locales mediante la creación de apps personalizadas y el uso de URLs locales o túneles (`ngrok`, `localtunnel`).

### 1. Crea una app personalizada en Shopify

- En tu tienda Shopify, ve a **Apps** > **Desarrollar apps**
- Crea una nueva app personalizada
- En la configuración de la app, apunta el **App URL** a tu app local

### 2. Exponer tu app local via túnel seguro

Shopify no puede usar `http://127.0.0.1` directamente en entornos externos. Usa un túnel seguro para desarrollo.

#### Con `ngrok`

1. Instala ngrok: https://ngrok.com/
2. Corre tu app local:
   ```bash
   python production.py
   ```
3. En otra terminal, corre:
   ```bash
   ngrok http 8080
   ```
4. Copia la URL pública que te entrega ngrok, por ejemplo `https://abc123.ngrok.io`
5. Usa esa URL como `App URL` y `Allowed redirection URL` en Shopify

### 3. Aún sin OAuth completo

Esta aplicación aún no tiene un flujo OAuth de Shopify. Por ahora puedes usarla como:

- un servicio local que abre en el navegador
- una app de desarrollo local para pruebas
- un recurso que puedes compartir internamente con tu equipo

Para integración completa con Shopify necesitarás añadir:

- OAuth 2.0 para instalar la app
- endpoints `/auth`, `/callback`
- verificación de HMAC y permisos de Shopify

## Archivos clave para el despliegue local

- `SHOPIFY_LOCAL_APP.md`  ← esta guía
- `release/dist/TradingSystem/TradingSystem.exe`  ← ejecutable local final
- `build_executable.bat`  ← regenerar ejecutable en Windows
- `.env.example`  ← plantilla de entorno
- `PRODUCTION_DEPLOYMENT.md`  ← guía de producción adicional
- `wsgi.py`  ← interfaz WSGI para servidor de producción
- `production.py`  ← servidor Waitress en producción

## Recomendación de uso inmediato

1. Ejecuta `release/dist/TradingSystem/TradingSystem.exe`
2. Abre `http://127.0.0.1:8080`
3. Si quieres conectar con Shopify en desarrollo, usa ngrok y configura la URL pública en tu app personalizada en Shopify

---

## Nota final

Para comenzar a generar ventas desde Shopify, la mejor estrategia ahora es:

1. tener la app funcionando localmente en tu PC
2. empaquetar el ejecutable y preparar una oferta digital o una app personalizada
3. si quieres venta real, crea una tienda de desarrollo Shopify y usa una app personalizada para conectar el flujo

Si necesitas, puedo crear también un ejemplo de `ngrok` + `Shopify CLI` y la estructura mínima de OAuth para una app Shopify real. 