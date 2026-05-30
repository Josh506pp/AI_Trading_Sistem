# 🎯 QUICK START - Sistema Integrado Bot + IA + MT5

## ⚡ 5 Minutos para Comenzar

### 1. Configura Credenciales (30 segundos)
```python
# Abre mt5_config.py y actualiza:
MT5_LOGIN = 123456789
MT5_PASSWORD = "tu_contraseña"
MT5_SERVER = "Broker-Demo"
```

### 2. Inicia la App (10 segundos)
```bash
python app.py
```

### 3. Abre Dashboard (10 segundos)
```
http://localhost:5000
```
Login con cualquier usuario (demo)

### 4. Conecta MT5 (2 minutos)
Dashboard → "🔐 Conectar MT5" → Ingresa credenciales

### 5. ¡Comienza! (5 segundos)
Dashboard → "▶ Iniciar Bot" → El sistema tradea automáticamente

---

## 📊 Dashboard en Tiempo Real

### Sección Bot + IA + MT5
```
┌─────────────────────────────────┐
│ 🤖 Bot + IA + MT5              │
├─────────────────────────────────┤
│ Estado: 🟢 Ejecutando           │
│ MT5: ✓ Conectado                │
│ Posiciones: 2                   │
│ Señales: 45                     │
│ Trades: 12                      │
├─────────────────────────────────┤
│ [▶ Iniciar] [⏹ Detener]        │
│ [🔐 Conectar MT5] [🔄 Actualizar]
└─────────────────────────────────┘
```

### Indicadores Profesionales
- RSI, MACD, Stochastic, ATR
- Tendencia (↑ Alcista / ↓ Bajista)
- Patrón identificado
- Volatilidad régimen

### Posiciones Abiertas
| Tipo | Par | Volumen | Entry | SL | TP | P&L |
|------|-----|---------|-------|----|----|-----|
| BUY  | EUR | 0.01    | 1.098 | 1.085 | 1.135 | +$12 |

---

## 🔄 Cómo Funciona el Sistema

### Flujo Automático (cada 1 segundo)

```
1. Bot obtiene precio actual
   ↓
2. IA analiza 50+ candles
   ├─ Calcula 8 indicadores técnicos
   ├─ Identifica patrones
   ├─ Verifica consistencia
   ├─ Asigna confianza (30%-98%)
   ↓
3. Razonamiento Mejorado valida
   ├─ ¿Confianza > 70%?
   ├─ ¿5+ indicadores convergen?
   ├─ ¿Risk/reward favorable?
   ↓
4. Decisión
   ├─ EJECUTAR: Abre trade con SL+TP
   ├─ OBSERVAR: Monitorea sin abrir
   ├─ RECHAZAR: Ignora señal
   ↓
5. MT5 ejecuta la orden (si aplica)
   ├─ Coloca orden market
   ├─ Asigna stop loss (2x ATR)
   ├─ Asigna take profit (4x ATR)
   ↓
6. Monitoreo continuo
   ├─ Actualiza P&L
   ├─ Revisa stop loss
   ├─ Revisa take profit
```

---

## 🎯 Ejemplos de Uso

### Ejemplo 1: Start 30 minutos de Trading
```
Dashboard → "▶ Iniciar Bot" 
Prompt: ¿Duración en minutos? → "30"
↓
✅ Bot inicia, genera señales durante 30 min
✅ Ejecuta trades automáticamente
✅ Se detiene después de 30 minutos
```

### Ejemplo 2: Trading Indefinido
```
Dashboard → "▶ Iniciar Bot"
Prompt: ¿Duración en minutos? → (dejar en blanco)
↓
✅ Bot continúa indefinidamente
✅ Puedes detener con "⏹ Detener" cuando quieras
```

### Ejemplo 3: Ejecutar Trade Manual
```
API Call: POST /api/bot/execute-manual
{
  "action": "BUY",
  "symbol": "EURUSD",
  "volume": 0.01
}
↓
✅ Trade ejecutado inmediatamente con SL+TP automáticos
```

---

## 📱 Monitoreo desde Cualquier Dispositivo

```
Tu Laptop         →  http://localhost:5000/
Mismo Wi-Fi       →  http://[TU_IP]:5000/
```

El dashboard se actualiza cada 2 segundos automáticamente.

---

## 🛑 Parar el Bot

### Opción 1: Dashboard
Dashboard → "⏹ Detener Bot"

### Opción 2: Terminal
```
CTRL+C
```

### Opción 3: API
```bash
curl -X POST http://localhost:5000/api/bot/stop
```

---

## ✅ Verificar que Todo Funciona

### En Terminal (después de iniciar app.py):
```bash
# Ver estado del bot
curl http://localhost:5000/api/bot/status

# Ver configuración
curl http://localhost:5000/api/bot/config

# Ver posiciones
curl http://localhost:5000/api/bot/positions
```

### En Dashboard:
- ✅ Gráfico de precio se actualiza
- ✅ Indicadores técnicos visible
- ✅ Botón "Conectar MT5" disponible
- ✅ Botones "Iniciar/Detener" funcionales

---

## 🚨 Troubleshooting Rápido

### Error "Bot system not available"
**Causa**: mt5_integration.py no está en el directorio
**Solución**: Verifica que `mt5_integration.py` esté en `c:\Users\Joshua\Desktop\proyectos\`

### Error "MT5 not connected"
**Causa**: Credenciales incorrectas o servidor wrong
**Solución**: 
- Verifica login y password en MT5
- Confirma nombre del servidor (ej: ICMarkets-Demo)
- Asegúrate que MT5 terminal esté ejecutándose

### El bot no genera señales
**Causa**: Requiere mínimo 50 candles para análisis
**Solución**: Espera 1-2 minutos para que se acumulen datos

### Trades no se ejecutan
**Causa**: Confianza baja o fuera de horas de trading (8AM-22PM)
**Solución**: Revisa análisis profesional → mira confianza %

---

## 💡 Tips para Mejores Resultados

1. **Comienza pequeño**: 0.01 lotes (volumen mínimo)
2. **Usa cuenta Demo**: Antes de dinero real
3. **Monitorea 1-2 horas**: Para entender el sistema
4. **Aumenta gradualmente**: Conforme veas ganancias
5. **Revisar logs**: Cada trade está registrado
6. **No desactives el bot**: Necesita ejecutar continuamente para análisis

---

## 📊 Métricas que Importan

El sistema rastrea:
- **Señales Generadas**: Total de análisis ejecutados
- **Trades Ejecutados**: Operaciones que pasaron validación
- **Win Rate**: % de trades ganadores (objetivo: >55%)
- **P&L Acumulado**: Ganancia total
- **Equity Curve**: Gráfico de capital (debe subir)

---

## 🎓 Después de 1 Hora

**Que esperar:**
- ✅ 100-200 señales analizadas
- ✅ 10-30 trades ejecutados
- ✅ 5-15 trades cerrados
- ✅ Ganancias visibles (si mercado favorable)

**Próximo paso:**
1. Aumenta volumen a 0.02 lotes (si ganancias positivas)
2. Continúa monitoreando
3. Ajusta confianza mínima si es necesario

---

## 🚀 Estado Actual

| Componente | Status | Detalles |
|-----------|--------|----------|
| Bot | ✅ | Automático y testeado |
| IA | ✅ | 8 factores + razonamiento |
| MT5 | ✅ | Conexión y órdenes listas |
| Dashboard | ✅ | Control en tiempo real |
| API | ✅ | 6 endpoints operativos |
| Documentación | ✅ | Guía completa incluida |

---

**¡Tu sistema está 100% listo para tradear! 🚀**

Para guía detallada: lee `BOT_INTEGRATION_SETUP.md`
Para status técnico: lee `BOT_INTEGRATION_STATUS.md`
