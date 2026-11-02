# Asistente de Trading Inteligente

Una plataforma web moderna de análisis técnico y predicciones automáticas de mercado financiero con sistema de autenticación, gestión de suscripciones y predicciones impulsadas por IA.

## Descripcion

Asistente de Trading Inteligente es una aplicación Flask de análisis de mercado en tiempo real que proporciona:
- Gráficos interactivos con datos de precios en vivo
- Análisis técnico automático (RSI, MACD, Bandas de Bollinger, ATR)
- Predicciones de precios con IA
- Sistema de autenticación y suscripciones
- Dashboard moderno con tema dorado/morado
- API REST completa para integración

## Características Principales

### Análisis de Mercado Tiempo Real
- Gráfico de precios en canvas nativo, sin dependencia de CDN
- Datos en vivo desde yfinance (12+ símbolos)
- Análisis técnico: RSI, MACD, Bandas de Bollinger, Estocástico, ATR
- Predicciones con consenso técnico y filtro mínimo de riesgo/beneficio 2:1
- Niveles de soporte/resistencia automáticos
- Monitoreo de volatilidad en tiempo real

### Sistema de IA
- Análisis de señales usando múltiples indicadores
- Predicciones combinadas con puntuación de confianza
- Detección de patrones en movimientos
- Asistente de IA conversacional
- Alertas inteligentes por volatilidad

### Sistema de Suscripciones
- **FREE**: 3 predicciones/día
- **PRO**: 20 predicciones/día + análisis avanzado
- **PREMIUM**: Predicciones ilimitadas
- Gestión de billings y histórico
- Upgrade/Downgrade dinámico

### Seguridad
- Autenticación por token con sesiones
- Validación contra inyección SQL
- Rate limiting por IP (10-100 req/min)
- Encriptación de datos sensibles
- CORS y headers de seguridad

### Interfaz Moderna
- Dark mode con tema dorado/morado
- Responsive y optimizado para móviles
- Dashboard intuitivo con actualizaciones en tiempo real
- Secciones bien organizadas

## Requisitos

- Python 3.8+
- Dependencias en `requirements.txt`
- Navegador moderno (Chrome, Firefox, Safari, Edge)

## Instalación Rápida

```bash
# 1. Clonar repositorio
git clone https://github.com/tu-usuario/trading-platform.git
cd trading-platform

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Iniciar servidor
python src/app.py

# 5. Abrir navegador
# http://localhost:5000/dashboard
```

## Uso

### Acceso a la Plataforma
1. Abre [http://localhost:5000/dashboard](http://localhost:5000/dashboard)
2. La plataforma carga automáticamente en modo demostración
3. La app consulta MT5 cada segundo si hay una terminal conectada; Yahoo Finance se sondea cada cinco segundos y entrega barras de un minuto que pueden retrasarse. Fuera del horario se conserva y marca el último precio.

#### Cotización MT5 opcional (Windows)
Para recibir ticks del bróker en lugar de las barras retrasadas de Yahoo:
1. Instala y abre MetaTrader 5, inicia sesión en una cuenta demo o del bróker y habilita los símbolos en Market Watch.
2. Instala el puente oficial en el mismo entorno Python: `pip install MetaTrader5`.
3. Reinicia la aplicación. Intentará leer cotizaciones y velas de MT5; si el terminal, la sesión o el símbolo no están disponibles, usará Yahoo Finance como respaldo.

La integración normal de la app lee cotizaciones y velas, pero no opera cuentas ni garantiza ganancias por operación ni un mínimo de USD 1.

#### Prueba manual aislada en MT5 demo
El ejecutor de prueba no forma parte del servidor web y nunca admite cuentas reales. Por defecto solo valida la señal y hace `order_check`; requiere `--execute-demo-order` para enviar como máximo una orden por ejecución:

```powershell
python tools\run_demo_trade_test.py --symbol EURUSD
python tools\run_demo_trade_test.py --symbol XAUUSD --target-profit-usd 1 --max-loss-usd 5.12 --experimental-raw-direction-demo-only --execute-demo-order
```

Solo usa EURUSD/XAUUSD, cuenta demo USD y permisos MT5 activos. Por defecto exige una señal confirmada y limita tanto el objetivo bruto como la pérdida estimada al stop a USD 1; los topes pueden cambiarse explícitamente para una prueba. La opción `--experimental-raw-direction-demo-only` puede usar la dirección cruda aunque el filtro habitual marque ESPERA; está aislada del servidor y requiere al menos 75% de acuerdo entre modelos, coincidencia de la dirección ponderada con los cuatro votos componentes, movimiento suficiente, SL/TP direccionales y velas M1 recientes. No exige el ratio riesgo/beneficio normal; estas entradas no son señales validadas y no deben usarse en cuentas reales. El TP se ajusta al precio negociable más cercano que alcance el objetivo bruto solicitado; el lote mínimo puede hacer que lo supere. Spread, comisiones, deslizamiento y gaps pueden cambiar el resultado real. Otra posición u orden pendiente bloquea el mismo símbolo.

Para validar planes en desarrollo local, los perfiles de prueba son `demo` (FREE), `trader` (PRO) y `admin` (PREMIUM). Sus suscripciones de prueba se reactivan al iniciar la app; esta renovación automática no se aplica con `FLASK_ENV=production`.

Los usuarios se registran desde `/register`; las contraseñas se guardan con hash y las consultas de la app usan SQLAlchemy ORM parametrizado. El plan FREE recibe análisis técnico básico cada 15 minutos, sin chat con IA, noticias PRO ni predicciones. PRO habilita chat y predicción avanzada cada cinco minutos; PREMIUM mantiene el análisis profesional cada cinco minutos y la predicción avanzada cada dos minutos.

### Funcionalidades

#### Gráfico de Precios
- Ver gráfico con colores dinámicos (dorado subida, morado bajada)
- Cambiar símbolo: EURUSD, XAUUSD, BTCUSD, etc.
- Indicadores estimados de presión compradora/vendedora, volumen relativo y zona de precio con mayor volumen
- Ver la cotización actual de la divisa seleccionada, sincronizada con el último punto del gráfico
- Consultar la hora del último tick y detectar cuando el proveedor no entrega datos recientes
- Niveles de entrada, stop-loss y objetivo cuando hay una señal confirmada
- Ver símbolo y precio del punto al pasar el cursor sobre el gráfico

#### Análisis de IA
- **Señal**: COMPRA/VENTA/ESPERA
- **Confianza**: 0-100%
- **Patrón**: Identifica patrones técnicos
- **Volatilidad**: Nivel actual

#### Predicción Avanzada
- Calcular predicción multi-indicador
- Ver score de confianza
- Obtener niveles S/R
- Rango esperado

#### Noticias y Alertas
- Alertas de volatilidad automáticas
- Noticias del mercado
- Índice de volatilidad en vivo

#### Asistente de IA
- Hacer preguntas al asistente
- Análisis conversacionales
- Comandos: `/status`, `/predict`, etc.

- `GET /api/status` - Estado del sistema
- `GET /api/symbols` - Símbolos disponibles
- `POST /api/symbol` - Cambiar símbolo activo
- `POST /api/auth/register` - Registrar usuario
- `POST /api/auth/login` - Login
- `GET /api/predict` - Predicción simple
- `POST /api/advanced-prediction` - Predicción avanzada
- `GET /api/subscription/plans` - Planes disponibles
- `POST /api/subscription/upgrade` - Upgrade de plan
- `POST /api/chat` - Enviar mensaje al asistente

## Testing

```bash
# Verificar integridad del sistema
python verify_system.py

# Test del API
python test_api.py

# Test del dashboard
python test_dashboard.py

# Suite automatizada completa
python -m unittest discover -s tests -v
```

## Estructura del Proyecto

```
proyectos/
├── src/
│   ├── app.py                 # Flask app principal (2900+ líneas)
│   ├── models.py              # SQLAlchemy ORM (4 modelos)
│   ├── market_data.py         # Proveedor yfinance
│   ├── security.py            # Validación y rate limiting
│   ├── prediction_system.py   # Motor de predicciones IA
│   └── market_symbols.py      # Configuración de símbolos
├── tests/
│   ├── test_platform.py       # Autenticación, seguridad y suscripciones
│   ├── test_market_data.py    # Datos de mercado y liquidez
│   ├── test_dashboard_chart.py
│   └── test_prediction_quality.py
├── requirements.txt           # Dependencias
├── verify_system.py          # Script de verificación
└── README.md                 # Documentación
```

## Cambios Recientes (v1.0)

**Limpieza de código completa**
- Eliminado automatización de bots
- Removido código MT5 (300+ líneas)
- Limpieza de deployment files (Heroku, Docker, OmniRoute)

**Dashboard reorganizado**
- Gráfico de precios al inicio
- Predicciones destacadas
- Análisis de IA integrado
- Alertas y noticias en sección propia

**Colores actualizados**
- Dorado (#D4AF37) para precios en alza
- Morado (#8B5CF6) para precios en baja
- Tema consistente en toda la plataforma

**Mejoras de gráfico**
- Renderizado en canvas nativo, sin depender de librerías externas bloqueadas por CSP
- Manejo de datos faltantes sin inventar precios de demostración
- Actualizaciones cada cinco segundos

**Filtro de operaciones**
- Requiere consenso entre modelos e indicadores técnicos alineados
- Solo muestra operaciones con riesgo/beneficio estimado de al menos 2:1
- Limita el horizonte de predicción a 15 velas de un minuto (máximo 15 minutos)
- Aplica cooldown del análisis avanzado de 5 minutos en PRO y 2 minutos en PREMIUM; los endpoints básicos usan su caché breve
- Solo permite una dirección si el backtest reciente tiene al menos 55% de aciertos con 8 o más muestras
- El consenso del modelo y el backtest son referencias históricas, no probabilidades ni garantías de resultados
- Las estimaciones no incluyen costos de operación ni garantizan ganancias
- La presión de compra/venta se estima de las velas OHLCV; no revela las posiciones ni órdenes de participantes institucionales

## Contribuir y pruebas

La suite automatizada activa se ejecuta con:

```bash
python -m unittest discover -s tests -v
```

Los archivos `tests/diagnostic_*.py` son comprobaciones manuales de integraciones opcionales/legacy y no forman parte del descubrimiento de unittest.

## Seguridad

- No incluir credenciales en el repositorio público
- Este software es una herramienta de análisis
- No garantiza resultados financieros
- Usar en modo simulación para pruebas

## Licencia

MIT License - Ver [LICENSE.md](LICENSE.md)

## Autor

Desarrollado para traders inteligentes

---

**Última actualización**: Septiembre 2026  
**Estado**: Producción (v1.0)
