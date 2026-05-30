# 📖 GUÍA COMPLETA DE INSTALACIÓN

**Professional Trading System v2.0.0**

---

## 📋 TABLA DE CONTENIDOS

1. [Requisitos Previos](#requisitos-previos)
2. [Instalación Automática](#instalación-automática)
3. [Instalación Manual](#instalación-manual)
4. [Configuración](#configuración)
5. [Verificación](#verificación)
6. [Primeros Pasos](#primeros-pasos)
7. [Troubleshooting](#troubleshooting)

---

## ✅ REQUISITOS PREVIOS

### Hardware Mínimo
- **CPU:** Intel i5 / AMD Ryzen 5 o superior
- **RAM:** 4 GB mínimo (8 GB recomendado)
- **Disco:** 2 GB de espacio libre
- **Conexión:** Internet estable

### Hardware Recomendado
- **CPU:** Intel i7 / AMD Ryzen 7
- **RAM:** 16 GB
- **Disco:** SSD con 5 GB libre
- **Conexión:** Fibra óptica (mínimo 50 Mbps)

### Software Requerido
- **Windows:** Windows 10/11 Pro (64-bit)
- **macOS:** macOS 10.15 o superior
- **Linux:** Ubuntu 20.04 LTS o superior
- **Python:** 3.8 o superior
- **MetaTrader 5:** (Opcional para demo, requerido para trading real)

---

## 🚀 INSTALACIÓN AUTOMÁTICA (RECOMENDADO)

### Paso 1: Descargar el Instalador

```bash
# Windows
# Descargar install.py desde el paquete o ejecutar:
python install.py

# macOS / Linux
python3 install.py
```

### Paso 2: Ejecutar el Instalador

```bash
# Windows
python install.py

# macOS / Linux  
python3 install.py
```

El instalador automaticamente:
✅ Verificará Python 3.8+
✅ Instalará todas las dependencias
✅ Validará los archivos requeridos
✅ Probará el sistema
✅ Creará atajos

---

## 🔧 INSTALACIÓN MANUAL

### Paso 1: Instalar Python

#### Windows
1. Ir a [python.org](https://www.python.org/downloads/)
2. Descargar Python 3.10 o superior
3. Ejecutar instalador
4. ✅ Marcar "Add Python to PATH"
5. Click "Install Now"

#### macOS
```bash
# Usando Homebrew (recomendado)
brew install python3

# O descargar desde python.org
```

#### Linux
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3 python3-pip

# Fedora
sudo dnf install python3 python3-pip
```

### Paso 2: Verificar Python

```bash
python --version
# Debe mostrar: Python 3.8 o superior
```

### Paso 3: Descargar el Sistema

Opción A - Git:
```bash
git clone https://github.com/your-repo/professional-trading-system.git
cd professional-trading-system
```

Opción B - ZIP:
```bash
# Descargar ZIP desde la web
# Extraer a tu carpeta deseada
cd professional-trading-system
```

### Paso 4: Instalar Dependencias

```bash
# Crear entorno virtual (recomendado)
python -m venv venv

# Activar entorno virtual
# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### Paso 5: Verificar Instalación

```bash
# Verificar imports
python -c "import numpy, pandas, flask, cryptography; print('✅ Todas las dependencias instaladas')"
```

---

## ⚙️ CONFIGURACIÓN

### Paso 1: Editar Configuración

Abre `config_secure.py`:

```python
# Configuración para DEMO (sin dinero real)
MT5_CONFIG = {
    'login': '123456',                    # Demo login
    'password': 'DemoPassword',
    'server': 'MetaQuotes-Demo',
    'enable_real_trading': False          # ← IMPORTANTE: Mantener False para demo
}

# Configuración para TRADING REAL
MT5_CONFIG = {
    'login': 'tu_login_mt5',             # Tu login real
    'password': 'tu_password_mt5',       # Tu password
    'server': 'tu_server_mt5',           # Tu broker
    'enable_real_trading': True          # ⚠️ Cambiar solo si estás seguro
}
```

### Paso 2: Configuración Avanzada

```python
TRADING_CONFIG = {
    'symbols': ['EURUSD', 'GBPUSD', 'USDJPY'],  # Pares a tradear
    'max_concurrent_trades': 5,                  # Máximo de operaciones
    'max_daily_loss_percent': 5.0,              # Pérdida máxima diaria
    'risk_percent': 2.0,                        # Riesgo por operación
}

AI_CONFIG = {
    'model_type': 'neural_network',             # Tipo de modelo
    'confidence_threshold': 0.6,                # Confianza mínima
    'min_hold_minutes': 30,                     # Tiempo mínimo operación
}
```

### Paso 3: Variables de Entorno (Opcional)

Crear archivo `.env`:

```bash
# .env (NO compartir este archivo)
MT5_LOGIN=tu_login
MT5_PASSWORD=tu_password
MT5_SERVER=tu_servidor

TELEGRAM_TOKEN=tu_token
EMAIL_USER=tu_email@gmail.com
```

---

## ✔️ VERIFICACIÓN

### Test 1: Validar Sistema

```bash
python launcher.py --validate
```

Debe mostrar:
```
✅ Entorno validado correctamente
✅ Python versión correcta
✅ Dependencias instaladas
✅ Configuración validada
```

### Test 2: Ejecutar Demo

```bash
python launcher.py --demo
```

Debe mostrar:
```
✅ Sistema inicializado
📊 Análisis de mercado: [data]
🎯 Evaluación de entrada: [data]
🔒 Seguridad verificada
🎉 ¡Demostración completada!
```

### Test 3: Dashboard

```bash
python launcher.py --dashboard
```

Debe iniciar servidor en `http://localhost:5000`

---

## 🎯 PRIMEROS PASOS

### Inicio Rápido (5 minutos)

```bash
# 1. Instalar
python install.py

# 2. Configurar (dejar valores por defecto para demo)
# Edita config_secure.py si es necesario

# 3. Ejecutar dashboard
python launcher.py --dashboard

# 4. Abrir navegador
# http://localhost:5000

# 5. ¡Usar el sistema!
```

### Configuración de Primer Uso

1. **Accede al Dashboard**
   - Abre http://localhost:5000
   - Username: `admin`
   - Password: `admin` (cambiar después)

2. **Explora las Características**
   - Analiza el mercado
   - Revisa indicadores técnicos
   - Prueba el chat IA

3. **Revisa la Documentación**
   - Lee README.md
   - Estudia PROFESSIONAL_README.md
   - Entiende los riesgos

4. **Configura Tus Preferencias**
   - Símbolos a tradear
   - Nivel de riesgo
   - Horarios de trading

---

## 🔍 TROUBLESHOOTING

### ❌ Error: "Python not found"

**Solución:**
```bash
# Verificar instalación
python --version

# Si falla:
# Windows: Reinstalar Python con "Add to PATH"
# macOS/Linux: Usar python3 en lugar de python
```

### ❌ Error: "No module named 'cryptography'"

**Solución:**
```bash
pip install --upgrade cryptography
pip install -r requirements.txt
```

### ❌ Error: "Address already in use"

**Solución:**
```bash
# El puerto 5000 ya está en uso
# Opción 1: Detener otro proceso
# Opción 2: Usar otro puerto
python launcher.py --dashboard --port 8000
```

### ❌ Error: "MT5 connection failed"

**Solución:**
1. Verificar que MetaTrader 5 está instalado
2. Verificar credenciales en config_secure.py
3. Verificar conexión a internet
4. Probar en demo primero

### ❌ Dashboard no carga

**Solución:**
```bash
# Reiniciar servidor
# Presionar Ctrl+C
# Ejecutar de nuevo
python launcher.py --dashboard

# Limpiar cache del navegador
# Presionar Ctrl+Shift+Delete
```

### ⚠️ Rendimiento lento

**Solución:**
1. Cerrar otras aplicaciones
2. Aumentar RAM asignada
3. Usar un disco SSD
4. Reducir número de símbolos

### ⚠️ No se conecta a MT5

**Solución:**
1. Abrir MetaTrader 5
2. Verificar Internet
3. Revisar credenciales
4. Contactar al broker

---

## 📊 VERIFICACIÓN FINAL

Checklist de instalación:

- [ ] Python 3.8+ instalado
- [ ] Dependencias instaladas (requirements.txt)
- [ ] config_secure.py configurado
- [ ] Test de validación pasó
- [ ] Dashboard abre en localhost:5000
- [ ] Demo ejecuta sin errores
- [ ] Puedes hacer login
- [ ] Sistema responde a comandos

---

## 🆘 SOPORTE

Si tienes problemas:

1. **Lee la documentación:**
   - README.md
   - PROFESSIONAL_README.md
   - Este archivo

2. **Ejecuta el validador:**
   ```bash
   python launcher.py --validate
   ```

3. **Contacta a soporte:**
   - 📧 support@professional-trading-system.com
   - 💬 Chat: support.professional-trading-system.com
   - 📱 +1 (800) TRADING-1

4. **Incluye en tu reporte:**
   - Sistema operativo
   - Versión de Python
   - Output completo del error
   - Pasos para reproducir

---

## 🎓 PRÓXIMOS PASOS

Después de instalar:

1. ✅ Lee [PROFESSIONAL_README.md](PROFESSIONAL_README.md)
2. ✅ Revisa [SALES_PACKAGE.md](SALES_PACKAGE.md)
3. ✅ Estudia la [API Documentation](docs/api.md)
4. ✅ Únete a la [Comunidad](https://discord.gg/trading-system)
5. ✅ Comienza a tradear en DEMO
6. ✅ Después: Pasa a REAL con caución

---

## ✨ ¡ÉXITO!

Tu instalación está completa. 🎉

**Próximo paso:** Abre http://localhost:5000 y ¡comienza a tradear!

---

*Professional Trading System v2.0.0*
*Última actualización: 29 de Abril de 2026*