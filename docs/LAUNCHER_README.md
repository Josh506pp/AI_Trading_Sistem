# 🚀 Launcher del Sistema de Trading Inteligente

## Un Solo Click para Todo

Este launcher inicia automáticamente todo el sistema de trading inteligente con un solo click.

---

## 🎯 Inicio Rápido

### Opción 1: Doble Click (Más Fácil)
1. **Haz doble click** en `Launch_Trading_System.bat`
2. **Espera** a que se complete la verificación
3. **¡Listo!** El sistema estará funcionando

### Opción 2: PowerShell
1. **Click derecho** en `Launch_Trading_System.ps1`
2. Selecciona **"Ejecutar con PowerShell"**
3. **Espera** la inicialización

### Opción 3: Python Directo
```bash
python LAUNCH_TRADING_SYSTEM.py
```

---

## ⚙️ Qué Hace Automáticamente

### ✅ Verificaciones del Sistema
- **Python**: Verifica versión 3.8+
- **Dependencias**: Instala automáticamente si faltan
- **Archivos**: Verifica que existan todos los módulos
- **MT5**: Verifica conexión (opcional)

### ✅ Inicio de Componentes
- **Sistema de Trading**: Inicializa el motor principal
- **Dashboard Web**: Inicia servidor en puerto 5000
- **Interfaz de Chat**: Abre consola interactiva
- **Navegador**: Abre dashboard automáticamente

### ✅ Configuración Inteligente
- **Auto-detección**: Encuentra archivos y configura rutas
- **Manejo de Errores**: Recupera de problemas comunes
- **Logs Detallados**: Muestra progreso paso a paso

---

## 📁 Archivos del Launcher

```
LAUNCH_TRADING_SYSTEM.py    ← Script principal de Python
Launch_Trading_System.bat   ← Launcher para Windows (.bat)
Launch_Trading_System.ps1   ← Launcher para PowerShell (.ps1)
launcher_config.py          ← Configuración personalizable
LAUNCHER_README.md          ← Esta documentación
```

---

## 🎛️ Personalización

### Archivo de Configuración
Edita `launcher_config.py` para personalizar:

```python
LAUNCH_CONFIG = {
    "auto_start_dashboard": True,      # Iniciar dashboard
    "auto_start_chat": True,          # Iniciar chat
    "auto_open_browser": True,        # Abrir navegador
    "dashboard_port": 5000,           # Puerto del dashboard
    "check_mt5_connection": True,     # Verificar MT5
    "verbose": True,                  # Logs detallados
    # ... más opciones
}
```

### Presets Disponibles
```python
# En launcher_config.py, descomenta una línea:
ACTIVE_CONFIG = get_config("conservative")  # Conservador
ACTIVE_CONFIG = get_config("moderate")     # Moderado
ACTIVE_CONFIG = get_config("aggressive")   # Agresivo (NO RECOMENDADO)
```

---

## 📊 Proceso de Inicio

### Paso 1: Verificaciones
```
[1] Verificando versión de Python...
[2] Verificando dependencias...
[3] Verificando archivos del sistema...
[4] Verificando conexión MT5...
```

### Paso 2: Inicio de Componentes
```
[5] Iniciando dashboard web...
[6] Inicializando sistema de trading...
[7] Iniciando interfaz de chat...
```

### Paso 3: Menú Interactivo
```
🎯 SISTEMA INICIADO - ¿QUÉ QUIERES HACER?

OPCIONES:
1. 🔄 Iniciar interfaz de chat completa
2. 📊 Abrir dashboard web
3. 🤖 Ejecutar análisis de mercado
4. 📈 Ver estado del sistema
5. ⚙️  Configurar parámetros
6. 🛑 Salir
```

---

## 🛠️ Solución de Problemas

### "Python no encontrado"
**Solución:**
1. Instala Python desde https://python.org
2. Marca "Add Python to PATH" durante instalación
3. Reinicia la terminal

### "Dependencias faltantes"
**Solución:**
- El launcher las instala automáticamente
- Si falla, ejecuta: `pip install -r requirements.txt`

### "MT5 no conectado"
**Solución:**
- Es opcional, el sistema funciona en simulación
- Para real: configura `mt5_config.py`

### "Dashboard no inicia"
**Solución:**
- Verifica que el puerto 5000 esté libre
- Cambia puerto en `launcher_config.py`

### "Archivos faltantes"
**Solución:**
- Verifica que estés en el directorio correcto
- Todos los archivos deben estar en la misma carpeta

---

## 🎮 Uso Interactivo

Después del inicio, el launcher muestra un menú:

### Opción 1: Chat Interactivo
- Abre consola completa de comandos
- Comandos disponibles: `abre 5`, `status`, `historial`, etc.

### Opción 2: Dashboard Web
- Abre navegador con interfaz gráfica
- Muestra gráficos, estadísticas en tiempo real

### Opción 3: Análisis Directo
- Ejecuta análisis de mercado inmediato
- Útil para testing

### Opción 4: Estado del Sistema
- Muestra balance, posiciones, salud del sistema
- Información en tiempo real

### Opción 5: Configuración
- Ajusta parámetros del sistema
- Cambia riesgo, stops, etc.

---

## 🔧 Configuración Avanzada

### Variables de Entorno
```bash
# Puerto personalizado
set DASHBOARD_PORT=8080
python LAUNCH_TRADING_SYSTEM.py

# Sin dashboard
python LAUNCH_TRADING_SYSTEM.py --no-dashboard

# Sin chat
python LAUNCH_TRADING_SYSTEM.py --no-chat
```

### Configuración por Archivo
Crea `launcher_config.py` personalizado:
```python
CUSTOM_CONFIG = {
    "dashboard_port": 8080,
    "auto_start_dashboard": False,
    "theme": "light",
    # ... tus configuraciones
}
```

---

## 📈 Monitoreo

### Logs en Consola
- Progreso de inicialización
- Estado de componentes
- Errores y advertencias

### Dashboard Web
- Accede a `http://localhost:5000`
- Estadísticas en tiempo real
- Control del bot

### Interfaz de Chat
- Comandos interactivos
- Estado del sistema
- Control manual

---

## 🛑 Parada de Emergencia

### Desde Chat
```
TradingBot > pausa
TradingBot > salir
```

### Desde Dashboard
- Click en "⏹ Stop Bot"
- Cierra navegador

### Desde Sistema
- Ctrl+C en terminal
- Cierra procesos de Python

---

## 🎯 Checklist de Inicio

- [ ] Python 3.8+ instalado
- [ ] Archivos del proyecto completos
- [ ] Dependencias instaladas
- [ ] MT5 configurado (opcional)
- [ ] Puerto 5000 libre
- [ ] Antivirus no bloquee Python

---

## 🚀 ¡Listo para Tradear!

Con el launcher, tienes:

✅ **Sistema completo** en un click  
✅ **Verificaciones automáticas**  
✅ **Configuración inteligente**  
✅ **Interfaz múltiple** (chat + web)  
✅ **Manejo de errores**  
✅ **Logs detallados**  

**¡Haz doble click y comienza a tradear!**

---

*Launcher v1.0 - Sistema de Trading Inteligente v2.0*