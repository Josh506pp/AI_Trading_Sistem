# 🚀 DEPLOY RÁPIDO - 3 OPCIONES

## Opción 1: Heroku (Más Fácil - 3 min)

```bash
# 1. Install Heroku CLI
# https://devcenter.heroku.com/articles/heroku-cli

# 2. Login
heroku login

# 3. Create app
heroku create tu-trading-bot

# 4. Set environment
heroku config:set FLASK_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')

# 5. Deploy
git push heroku main

# 6. Open
heroku open

# 7. Logs
heroku logs --tail
```

✅ **Live en**: `https://tu-trading-bot.herokuapp.com`

---

## Opción 2: Docker + Linux Server (5 min)

```bash
# 1. En tu servidor
ssh user@your-server.com

# 2. Clonar
git clone https://tu-repo.git
cd proyectos

# 3. Crear .env
nano .env.production
# Copiar contenido de .env.production y personalizar

# 4. Build y run
docker build -t trading .
docker run -d -p 8080:8080 --env-file .env.production trading

# 5. Verificar
curl http://localhost:8080/api/status

# 6. Configure nginx (SSL)
# Ver guía nginx + letsencrypt
```

✅ **Live en**: `https://tu-dominio.com:8080`

---

## Opción 3: Docker Compose Production

```bash
# 1. Preparar servidor
ssh user@your-server.com
cd /apps/trading
git clone https://tu-repo.git .

# 2. Crear .env
cp .env.production .env
# Editar con tus valores

# 3. Deploy
docker-compose -f docker-compose.prod.yml up -d

# 4. Verificar
docker-compose -f docker-compose.prod.yml ps
docker logs trading-system-prod

# 5. Monitorear
watch -n 5 'docker stats trading-system-prod'
```

✅ **Live en**: `https://tu-dominio.com:8080`

---

## 📋 Variables Requeridas

Antes de desplegar, preparar:

```
FLASK_SECRET_KEY = (generada automáticamente)
FLASK_ENV = production
FLASK_DEBUG = 0

# Opcional para trading real:
MT5_LOGIN = tu-numero
MT5_PASSWORD = tu-password
MT5_SERVER = tu-servidor
```

Generar FLASK_SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 🧪 Test Antes de Desplegar

```bash
# 1. Local test
python src/app.py
# Visita http://localhost:5000 en navegador

# 2. Docker test
docker build -t trading .
docker run -p 8080:8080 trading

# 3. Sintaxis check
python -m py_compile src/*.py

# 4. Requirements test
pip install -r requirements.txt
python -c "import flask; print('✓ OK')"
```

---

## ✅ Verificación Post-Deploy

```bash
# Health check
curl https://tu-app.herokuapp.com/api/status

# Esperado:
# {
#   "status": "connected",
#   "balance": 10000.00,
#   "uptime_seconds": 123
# }

# Dashboard
# Visita https://tu-app.herokuapp.com en navegador
```

---

## 🆘 Troubleshooting Rápido

### "Application failed to start"
```bash
heroku logs --tail
# Ver error exacto
# Revisar .env variables
```

### "Port already in use"
```bash
# Cambiar PORT en .env a valor libre
heroku config:set PORT=8081
```

### "MT5 not found"
```bash
# Normal en Linux, modo simulación automático
# Para MT5 real, usar servidor Windows o VPS
```

### "Database connection error"
```bash
# App no requiere DB
# Si creas una, actualizar requirements.txt
```

---

## 📞 Help

- Heroku docs: https://devcenter.heroku.com
- Docker docs: https://docs.docker.com
- Flask deployment: https://flask.palletsprojects.com/deploying

---

## ⚡ Para Shopify

Ver: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md#-integración-con-shopify)

---

**Estado**: ✅ LISTO PARA PRODUCCIÓN

Última actualización: May 29, 2026
