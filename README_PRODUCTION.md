# 🤖 Trading System - Guía de Producción

<div align="center">

![Trading System](https://img.shields.io/badge/status-production%20ready-brightgreen)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue)
![Flask 2.3](https://img.shields.io/badge/flask-2.3-black)
![License](https://img.shields.io/badge/license-proprietary-red)

**Sistema profesional de trading con IA, análisis técnico avanzado e integración MetaTrader 5**

[Características](#características) • [Inicio Rápido](#inicio-rápido) • [Despliegue](#despliegue) • [Documentación](#documentación)

</div>

---

## ✨ Características

### 🤖 Inteligencia Artificial
- **Análisis técnico avanzado**: RSI, MACD, Bandas de Bollinger
- **Machine Learning**: Aprendizaje de patrones de trading exitosos
- **Señales automáticas**: Genera señales de compra/venta basadas en múltiples indicadores
- **Chat IA**: Asistente inteligente para control y consultas

### 💹 Trading
- **Operaciones manuales y automáticas**: Control total sobre tus trades
- **Integración MetaTrader 5**: Conecta tu cuenta real (opcional)
- **Modo simulación**: Practica sin riesgo
- **Gestión de posiciones**: Cierra todos los trades con un click

### 📊 Dashboard
- **Interfaz web moderna**: Diseño profesional y responsive
- **Gráficos en tiempo real**: Visualización interactiva de precios
- **Panel de control intuitivo**: Todo lo que necesitas en una pantalla
- **Historial de operaciones**: Registro completo de todas tus transacciones

### 🔒 Seguridad
- **Rate limiting**: Protección contra abuso
- **Encriptación**: Credenciales protegidas
- **Variables de entorno**: No hardcodear secretos
- **HTTPS**: SSL/TLS en producción

### 🚀 Producción Ready
- **Docker optimizado**: Imagen compacta y eficiente
- **WSGI completo**: Compatible con Heroku, AWS, Azure, Shopify
- **Health checks**: Monitoreo automático
- **Logging estructurado**: Diagnóstico fácil

---

## 🚀 Inicio Rápido

### Requisitos
- Python 3.12+
- pip o conda
- Navegador web moderno

### Instalación (60 segundos)

```bash
# 1. Clonar repositorio
git clone <url>
cd proyectos

# 2. Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar aplicación en modo producción
python production.py
```

La aplicación estará disponible en: **http://localhost:8080**

---

## 📦 Despliegue en Producción

### ☁️ Heroku (5 minutos)

```bash
# 1. Login en Heroku
heroku login

# 2. Crear app
heroku create tu-app-name

# 3. Configurar variables
heroku config:set FLASK_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')
heroku config:set MT5_LOGIN=tu-login
heroku config:set MT5_PASSWORD=tu-password
heroku config:set MT5_SERVER=tu-server

# 4. Desplegar
git push heroku main

# 5. Ver logs
heroku logs --tail
```

Tu app estará en: `https://tu-app-name.herokuapp.com`

### 🐳 Docker + Servidor Linux

```bash
# 1. Construir imagen
docker build -t trading-system .

# 2. Crear .env en servidor
cat > .env.production << EOF
FLASK_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')
MT5_LOGIN=tu-login
MT5_PASSWORD=tu-password
MT5_SERVER=tu-server
FLASK_ENV=production
FLASK_DEBUG=0
PORT=8080
EOF

# 3. Ejecutar con docker-compose
docker-compose -f docker-compose.prod.yml up -d

# 4. Verificar salud
docker logs trading-system-prod
curl http://localhost:8080/api/status
```

### 🛍️ Shopify (Aplicación Privada)

Sigue la guía completa en [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md#-integración-con-shopify)

Resumen rápido:
1. Dashboard Shopify → Apps → Develop apps
2. Crear app privada
3. Obtener API credentials
4. Desplegar en Heroku/Docker
5. Configurar webhooks
6. Instalar en tienda

---

## 🛠️ Configuración Esencial

### Variables de Entorno

Copiar `.env.production` y personalizar:

```bash
# Flask
FLASK_ENV=production
FLASK_DEBUG=0
FLASK_SECRET_KEY=tu-clave-segura-cambiar-esto

# MetaTrader 5 (opcional para simulación)
MT5_LOGIN=123456
MT5_PASSWORD=tu-password
MT5_SERVER=ICMarketsDemoEU-05
MT5_PATH=/ruta/a/terminal64.exe  # Windows

# Trading
TRADING_SYMBOL=EURUSD
DEFAULT_VOLUME=0.01
USE_REAL_ACCOUNT=False  # Cambiar a True con cuidado

# Seguridad
ENABLE_RATE_LIMITING=True
RATE_LIMIT_REQUESTS=100
```

### Generar clave segura

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 📚 Documentación Completa

- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Guía extensiva de despliegue
- **[MT5_SETUP.md](docs/MT5_SETUP.md)** - Integración MetaTrader 5
- **[TRADING_BOT_READY.md](TRADING_BOT_READY.md)** - Verificación final

---

## 📊 API Endpoints

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/` | GET | Dashboard web |
| `/api/status` | GET | Estado del sistema |
| `/api/buy` | POST | Ejecutar compra |
| `/api/sell` | POST | Ejecutar venta |
| `/api/close-all` | POST | Cerrar todas las posiciones |
| `/api/toggle-auto` | POST | Activar/desactivar IA automática |
| `/api/professional-analysis` | GET | Análisis técnico IA |
| `/api/chat` | POST | Enviar mensaje a IA |
| `/api/mt5/connect` | POST | Conectar MetaTrader 5 |
| `/api/mt5/status` | GET | Estado de conexión MT5 |

---

## 🔍 Health Checks

### Local
```bash
curl http://localhost:5000/api/status
```

### Producción (Heroku)
```bash
curl https://tu-app.herokuapp.com/api/status
```

### Docker
```bash
docker exec trading-system-prod curl http://localhost:8080/api/status
```

Response esperado:
```json
{
  "status": "connected",
  "balance": 10000.00,
  "equity": 10000.00,
  "positions": 0,
  "uptime_seconds": 3600
}
```

---

## 🧪 Testing

```bash
# Verificar instalación
python -m pytest tests/ -v

# Test específico
python -m pytest tests/test_mt5_connection.py -v

# Verificar sintaxis
python -m py_compile src/*.py
```

---

## 🚨 Troubleshooting

### Error: "ModuleNotFoundError: No module named 'src'"

Solución:
```bash
# Asegurar que estás en directorio raíz
pwd  # Debe mostrar .../proyectos

# Reinstalar paquetes
pip install --upgrade -r requirements.txt
```

### Error: "Port 5000 already in use"

Solución:
```bash
# Linux/Mac
kill -9 $(lsof -ti:5000)

# Windows (PowerShell)
Get-Process -Id (Get-NetTCPConnection -LocalPort 5000).OwningProcess | Stop-Process
```

### MT5 not responding

Solución:
1. Verificar MetaTrader 5 está abierto en Windows
2. Comprobación credenciales: login, password, server
3. Usar cuenta demo para test
4. Ver logs: `docker logs trading-system-prod`

### CORS errors

Solución - Agregar header CORS:
```python
# En src/app.py (ya incluido)
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response
```

---

## 📈 Monitoreo en Producción

### Logs en Heroku
```bash
heroku logs --tail
heroku logs --tail --ps web
```

### Logs en Docker
```bash
docker logs -f trading-system-prod
```

### Métricas a monitorear

- **Response time** < 500ms
- **Error rate** < 1%
- **Uptime** > 99%
- **CPU usage** < 50%
- **Memory usage** < 256MB

---

## 🔐 Seguridad

### Checklist de producción

- ✅ `FLASK_SECRET_KEY` cambiado a valor aleatorio
- ✅ `FLASK_DEBUG=0` en producción
- ✅ `FLASK_ENV=production`
- ✅ HTTPS habilitado
- ✅ Rate limiting activo
- ✅ No secretos en código
- ✅ Credenciales en variables de entorno
- ✅ Backups configurados
- ✅ Monitoreo activo
- ✅ Logs centralizados

---

## 📦 Stack Tecnológico

```
Backend:
  - Python 3.12
  - Flask 2.3.3
  - Waitress 2.1.2

ML/AI:
  - scikit-learn 1.3
  - XGBoost 1.7.6
  - NumPy 1.24.3

Trading:
  - MetaTrader5 SDK

Frontend:
  - HTML5/CSS3
  - Chart.js
  - Vanilla JavaScript

Deployment:
  - Docker
  - Docker Compose
  - Heroku
  - Linux/Windows servers
```

---

## 📞 Soporte

- 🐛 Reportar bugs: Abre un issue
- 💬 Preguntas: Ver FAQ en docs/
- 📚 Documentación: Ver carpeta docs/
- 📧 Contacto: soporte@ejemplo.com

---

<div align="center">

### ⭐ Sistema profesional de trading, listo para escala

**Versión**: 1.0.0  
**Estado**: ✅ Production Ready  
**Última actualización**: May 29, 2026  
**Licencia**: Propietaria (Todos los derechos reservados)

</div>
