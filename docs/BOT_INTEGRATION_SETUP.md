# 🤖 Bot + IA + MT5 - Sistema Integrado

**Tu sistema de trading automático está 100% listo para operar.**

## ✅ Componentes Integrados

1. **Bot Automático** - Genera señales de trading continuamente
2. **IA Profesional** - Análisis con 8 factores de confianza y razonamiento mejorado
3. **MT5 Integration** - Conexión directa a MetaTrader5 para ejecución real
4. **Dashboard Web** - Control y monitoreo en tiempo real

---

## 🚀 Cómo Iniciar

### Paso 1: Configurar Credenciales MT5

Edita `mt5_config.py` y completa tus credenciales:

```python
# mt5_config.py
MT5_LOGIN = 123456789          # Tu número de cuenta
MT5_PASSWORD = "tu_password"   # Tu contraseña de trading
MT5_SERVER = "Broker-Demo"     # Nombre del servidor (ej: ICMarkets-Demo, Exness-Demo)
MT5_PATH = None                # Opcional: ruta a MT5 terminal
TRADING_SYMBOL = "EURUSD"      # Par de divisas a tradear
DEFAULT_VOLUME = 0.01          # Volumen inicial
```

**💡 Nota:** Para pruebas, usa una **cuenta demo** sin dinero real.

### Paso 2: Iniciar el Dashboard

```bash
python app.py
```

Luego abre en tu navegador:
```
http://localhost:5000
```

### Paso 3: Conectar MT5

En el dashboard, en la sección **"🤖 Bot + IA + MT5"**, haz clic en **"🔐 Conectar MT5"**

Se te pedirá:
- Número de cuenta MT5
- Contraseña
- Servidor MT5

### Paso 4: Iniciar Trading Automático

Haz clic en **"▶ Iniciar Bot"** para comenzar el trading automático.

Opciones:
- Sin duración: El bot continúa hasta que lo detengas manualmente
- Con duración: Especifica minutos (ej: 120 para 2 horas)

---

## 📊 Panel de Control

El dashboard muestra en tiempo real:

### Estado del Bot
- **Estado**: 🟢 Ejecutando / 🔴 Detenido
- **MT5 Conectado**: Conexión a la plataforma
- **Posiciones Abiertas**: Trades activos
- **Señales Generadas**: Total de análisis realizados
- **Trades Ejecutados**: Total de operaciones completadas

### Indicadores Técnicos
- RSI, MACD, Stochastic, ATR
- Tendencia (Alcista/Bajista)
- Patrones Identificados
- Volatilidad del Mercado

### Posiciones
- Tabla con todos los trades abiertos
- Entry price, Stop Loss, Take Profit
- P&L en tiempo real

---

## 🎯 Estrategia del Bot

El sistema utiliza **razonamiento mejorado** para decisiones asertivas:

### 1️⃣ Análisis Técnico (8 Factores)
- **Tendencia** (25%) - SMA 5/10/20/50
- **RSI** (20%) - Momentum oscilador
- **MACD** (20%) - Tendencia momentum
- **Bandas Bollinger** (15%) - Sobrecompra/sobreventa
- **Estocástico** (10%) - Confluencia
- **Patrones** (10%) - Engulfing, Rechazo
- **Momentum** (10%) - ROC, aceleración
- **Volatilidad** (bonus) - ATR, volatilidad régimen

### 2️⃣ Consistencia
Verifica que **5+ indicadores converjan** en la misma dirección

### 3️⃣ Riesgo/Rentabilidad
- Stop Loss = 2x ATR
- Take Profit = 4x ATR (ratio 4:1)
- Tamaño = 0.01 - 0.05 lotes (escalado por confianza)

### 4️⃣ Decisión Final
```
Confianza (40%) + Consistencia (40%) + Calidad (20%) = EJECUTAR / OBSERVAR / RECHAZAR
```

---

## 📈 Funciones API del Bot

El dashboard comunica con estos endpoints:

### Status
```
GET /api/bot/status
```
Obtiene estado completo del bot integrado

### Control
```
POST /api/bot/start
POST /api/bot/stop
```
Inicia/detiene el trading automático

### MT5
```
POST /api/bot/connect-mt5
GET /api/bot/positions
```
Conecta a MT5 y obtiene posiciones

### Manual
```
POST /api/bot/execute-manual
GET/POST /api/bot/config
```
Ejecuta trades manuales o actualiza configuración

---

## ⚙️ Configuración Avanzada

### Cambiar el Par de Divisas
Edita `mt5_config.py`:
```python
TRADING_SYMBOL = "GBPUSD"  # O tu par preferido
```

### Cambiar el Volumen
```python
DEFAULT_VOLUME = 0.05  # Más arriesgado
```

### Horas de Trading
El bot solo opera entre **08:00 y 22:00** (configurable)

### Confianza Mínima
Por defecto, solo ejecuta si confianza > 70%

---

## 🛡️ Gestión de Riesgo

**Razonamiento Mejorado** previene pérdidas:

1. ✅ Solo ejecuta trades con **confianza > 70%**
2. ✅ Máximo **1 operación cada 30 segundos**
3. ✅ **Stop Loss automático** en 2x ATR
4. ✅ **Take Profit automático** en 4x ATR
5. ✅ Límite de **5 trades máximo al día**
6. ✅ Monitoreo de **drawdown máximo**

---

## 📊 Monitoreo

En el dashboard observa:

- **Señales Generadas**: Crecimiento constante = sistema analizando
- **Trades Ejecutados**: Menos que señales = filtrado de baja confianza ✓
- **P&L**: Ganancia acumulada de todos los trades cerrados
- **Posiciones Abiertas**: Trades activos con SL y TP

---

## 🔧 Troubleshooting

### "Error en conexión MT5"
- Verifica número de cuenta y contraseña
- Confirma servidor correcto (ej: ICMarkets-Demo)
- MT5 terminal debe estar ejecutándose

### "Bot no genera señales"
- Revisa que el precio esté actualizando en el gráfico
- Requiere **mínimo 50 candles** para análisis
- Puede tomar 1-2 minutos en iniciar

### "Trades no se ejecutan"
- Verifica confianza > 70% en análisis profesional
- Revisa que no estés fuera de horas de trading (8AM-10PM)
- Si MT5 no está conectado, opera en simulación

### Reiniciar Sistema
```bash
# Detén el bot desde dashboard
# Cierra navegador y terminal
# Reinicia: python app.py
```

---

## 📈 Métricas Clave

El sistema rastrea automáticamente:

- **Total de Señales**: Todos los análisis
- **Trades Ejecutados**: Operaciones completadas
- **Trades Observados**: Señales monitoreadas sin ejecutar
- **Trades Rechazados**: Señales filtradas por confianza
- **Win Rate**: % de trades ganadores
- **P&L Acumulado**: Ganancia/pérdida total
- **Equity Curve**: Gráfico de capital

---

## 💡 Consejos para Mejores Resultados

1. **Comienza pequeño**: 0.01 lotes para aprender
2. **Prueba en Demo**: Antes de real
3. **Monitorea 2 horas**: Para entender comportamiento
4. **Aumenta gradualmente**: Conforme veas resultados consistentes
5. **Revisa logs**: Cada operación está registrada
6. **Ajusta confianza**: Si hay demasiados falsos positivos

---

## 📞 Soporte

Sistema completamente autónomo. Para revisar logs:

```bash
# Ver archivo de configuración
cat mt5_config.py

# Ver estado actual
curl http://localhost:5000/api/bot/status
```

---

## 🎓 Próximos Pasos

1. ✅ Configura credenciales MT5
2. ✅ Inicia app.py
3. ✅ Abre dashboard en navegador
4. ✅ Conecta MT5 desde dashboard
5. ✅ Haz clic en "Iniciar Bot"
6. ✅ Observa trading automático en acción

**¡Tu sistema está listo! 🚀**

---

*Sistema de Trading Automático Integrado - Professional IA + MT5*
