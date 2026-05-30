# 🚀 Trading System - Guía de Despliegue a Shopify

## Descripción General

Sistema de Trading Inteligente con IA integrada, compatible con MetaTrader 5 y listo para producción. Diseñado para funcionar como una aplicación privada en Shopify con capacidades de trading automático y análisis técnico avanzado.

## 📋 Requisitos Previos

- Docker instalado (para despliegue en contenedores)
- Git
- Cuenta en Shopify (para instalación como aplicación privada)
- Credenciales de MetaTrader 5 (opcional, para trading real)
- Heroku CLI o servicio similar (si despliegas en Heroku)

## 🏗️ Estructura del Proyecto

```
.
├── src/                      # Código fuente
│   ├── app.py               # Aplicación principal Flask
│   ├── mt5_integration.py    # Integración MetaTrader 5
│   ├── professional_trading_system.py  # Sistema profesional
│   ├── mt5_config.py        # Configuración de MT5
│   └── __init__.py          # Módulo Python
├── tests/                    # Tests unitarios
├── docs/                     # Documentación
├── templates/               # Archivos HTML/CSS
├── Dockerfile               # Imagen Docker
├── docker-compose.prod.yml  # Composición Docker producción
├── requirements.txt         # Dependencias Python
├── Procfile                 # Configuración Heroku
├── wsgi.py                  # Entrada WSGI
├── .env.production          # Variables de entorno
└── README.md                # Este archivo
```

## 📦 Instalación Local (Desarrollo)

### 1. Clonar y configurar el proyecto

```bash
git clone <tu-repo>
cd proyectos
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```bash
cp .env.production .env
# Editar .env con tus credenciales
```

### 3. Ejecutar localmente

```bash
python src/app.py
```

La aplicación estará disponible en `http://localhost:5000`

## 🐳 Despliegue con Docker

### 1. Construir imagen

```bash
docker build -t trading-system:latest .
```

### 2. Ejecutar contenedor

```bash
docker run -p 8080:8080 \
  --env-file .env.production \
  trading-system:latest
```

### 3. Usar Docker Compose (recomendado)

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## ☁️ Despliegue en Heroku

### 1. Crear aplicación

```bash
heroku create tu-app-name
heroku config:set FLASK_SECRET_KEY=tu-secret-key
heroku config:set MT5_LOGIN=tu-login
heroku config:set MT5_PASSWORD=tu-password
heroku config:set MT5_SERVER=tu-server
```

### 2. Desplegar

```bash
git push heroku main
```

### 3. Ver logs

```bash
heroku logs --tail
```

## 🛍️ Integración con Shopify

### Crear Aplicación Privada en Shopify

1. **Dashboard de Shopify** → Settings → Apps and integrations → Develop apps
2. **Create an app** → Select "App"
3. **Configurar permisos**:
   - `read_checkouts`
   - `write_checkouts`
   - `read_orders`
   - `write_orders`
4. **Configurar URLs**:
   - App URL: `https://tu-dominio.com` (o tu URL de despliegue)
   - Redirect URLs: `https://tu-dominio.com/auth/shopify/callback`
5. **Copiar credenciales**:
   - API Key
   - API Secret
   - Access Token

### Variables de Entorno para Shopify

```bash
SHOPIFY_API_KEY=tu-api-key
SHOPIFY_API_SECRET=tu-api-secret
SHOPIFY_API_ACCESS_TOKEN=tu-access-token
SHOPIFY_SHOP_URL=tu-tienda.myshopify.com
SHOPIFY_APP_URL=https://tu-app-name.herokuapp.com
```

### Instalación OAuth de Shopify
Para iniciar el flujo OAuth, usa la URL:

```text
https://tu-app-name.herokuapp.com/shopify/install?shop=tu-tienda.myshopify.com
```

Esto redirige al cliente Shopify para autorizar la app y luego devuelve el callback a:

```text
https://tu-app-name.herokuapp.com/auth/shopify/callback
```

### Instalar en tu tienda Shopify

1. Dashboard → Apps and integrations → Apps and sales channels
2. Seleccionar tu aplicación privada
3. Instalar en la tienda

## 🔧 Configuración de Producción

### 1. Variables críticas (.env)

```bash
# Security
FLASK_SECRET_KEY=tu-clave-segura-cambiar
FLASK_ENV=production
FLASK_DEBUG=0

# MetaTrader 5 (opcional)
MT5_LOGIN=tu-numero-cuenta
MT5_PASSWORD=tu-password
MT5_SERVER=tu-servidor-mt5
MT5_PATH=/ruta/a/terminal64.exe  # Windows específico

# Trading
TRADING_SYMBOL=EURUSD
DEFAULT_VOLUME=0.01
USE_REAL_ACCOUNT=False  # Cambiar a True solo en producción verificada

# Rate limiting
ENABLE_RATE_LIMITING=True
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=3600
```

### 2. SSL/TLS

```bash
# En Heroku, AWS o similar, SSL está incluido
# Para servidores propios, usar Let's Encrypt

sudo apt-get install certbot python3-certbot-nginx
sudo certbot certonly --nginx -d tu-dominio.com
```

### 3. Monitoreo y Logging

```bash
# Los logs se generan automáticamente
tail -f trading_system.log

# Para Heroku
heroku logs --tail
```

## 🧪 Testing

```bash
# Ejecutar tests
python -m pytest tests/

# Tests específicos
python -m pytest tests/test_mt5_connection.py -v
```

## 🎯 Endpoints Disponibles

### API Pública

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Dashboard principal |
| `/api/status` | GET | Estado del sistema |
| `/api/buy` | POST | Ejecutar compra |
| `/api/sell` | POST | Ejecutar venta |
| `/api/close-all` | POST | Cerrar posiciones |
| `/api/toggle-auto` | POST | Alternar IA automática |
| `/api/mt5/connect` | POST | Conectar MT5 |
| `/api/mt5/status` | GET | Estado de MT5 |
| `/api/professional-analysis` | GET | Análisis IA |
| `/api/chat` | POST | Chat con IA |
| `/api/chat/history` | GET | Historial chat |

### Endpoints del Bot

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/bot/status` | GET | Estado del bot |
| `/api/bot/start` | POST | Iniciar bot |
| `/api/bot/stop` | POST | Detener bot |
| `/api/bot/positions` | GET | Posiciones abiertas |

## 🔐 Seguridad

### Recomendaciones

1. **HTTPS obligatorio** en producción
2. **Rate limiting** habilitado (100 requests/hora por defecto)
3. **Validación de inputs** en todos los endpoints
4. **CSRF protection** habilitado
5. **Secrets management** con variables de entorno
6. **Backup periódico** de configuración

### Cambios recomendados

- Cambiar `FLASK_SECRET_KEY` con una clave aleatoria segura:
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```

- Usar contraseñas fuertes para MT5

- No compartir credenciales en el código

## 🐛 Troubleshooting

### Error: "MetaTrader5 not available"
- Normal en contenedores Linux (MT5 es Windows-only)
- El sistema funciona en modo simulación automáticamente
- Para MT5 real, desplegar en servidor Windows

### Error: "Connection refused"
- Verificar que el puerto 8080 está abierto
- Revisar logs: `docker logs trading-system-prod`

### Pobre rendimiento
- Aumentar timeout de Waitress: `--channel-timeout=180`
- Usar máquina con más recursos
- Implementar caché

## 📊 Monitoreo en Producción

### Health Check

```bash
curl https://tu-dominio.com/api/status
```

### Métricas

- Tiempo de respuesta API
- Uso de CPU/memoria
- Errores 4xx/5xx
- Uptime

### Alertas sugeridas

- Aplicación down > 5 min
- Error rate > 5%
- Response time > 5s
- Espacio en disco < 10%

## 🎓 Documentación Adicional

- [Flask Production Checklist](https://flask.palletsprojects.com/en/2.3.x/deploying/)
- [Waitress Documentation](https://docs.pylonsproject.org/projects/waitress/)
- [MetaTrader 5 Python API](https://www.mql5.com/en/docs/integration/python_metatrader5)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

## 📞 Soporte

Para problemas o preguntas:

1. Revisar logs completos
2. Ejecutar tests de diagnóstico
3. Consultar documentación oficial
4. Contactar soporte técnico

## 📝 Changelog

### v1.0.0 (Producción)
- ✅ Dashboard web funcional
- ✅ IA con análisis técnico
- ✅ Integración MetaTrader 5
- ✅ Chat inteligente
- ✅ Sistema de aprendizaje
- ✅ Rate limiting
- ✅ Logging completo

## 📄 Licencia

Reservados todos los derechos (2026)

---

**Última actualización**: May 29, 2026  
**Estado**: ✅ Listo para producción
