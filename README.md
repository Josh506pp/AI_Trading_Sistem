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
- Horizonte predictivo por defecto de 10 minutos (dentro del límite de 15 minutos)
- Detección de patrones en movimientos
- Asistente de IA conversacional
- Alertas inteligentes por volatilidad
- Pesos adaptativos por modelo, calculados con hasta 240 ventanas walk-forward; el prior da 40% a regresión lineal y 20% a cada otro modelo. Las etiquetas usan exactamente el horizonte solicitado y la precisión solo cuenta señales alineadas
- La confianza representa acuerdo de modelos, no probabilidad de ganar; no se ingieren operaciones privadas de traders profesionales

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

## Despliegue remoto recomendado (Windows VPS)

Para abrir el dashboard desde cualquier equipo sin dejar tu computadora encendida, aloja la app y MetaTrader 5 en un Windows VPS. La app actual usa la API local del terminal MT5; esta primera configuración es de un solo servidor y una sola instancia, no una arquitectura escalable con varios servidores.

Elige Windows Server con al menos 4 vCPU, 8 GB de RAM y 60 GB de disco. Cuando tengas bróker, selecciona una ubicación cercana a su servidor de trading y verifica el ping desde MT5. Mantén el puerto RDP (3389) limitado a tu IP o a una VPN; publica solo HTTPS mediante un proxy inverso como Caddy.

1. Instala Python de 64 bits, Git y MetaTrader 5 en el VPS. Clona el repositorio e instala `requirements.txt`.
2. Crea un directorio persistente para datos, por ejemplo `C:\\AITrading\\data`, y configura `DATABASE_PATH=C:\\AITrading\\data\\trading_platform.db`. La base SQLite queda en el disco del VPS y no debe guardarse en una carpeta temporal ni dentro de una carpeta que se borre al actualizar la app.
3. Configura `FLASK_ENV=production` y un `FLASK_SECRET_KEY` aleatorio de al menos 32 caracteres. Configura también SMTP para recuperación de contraseñas. No guardes estas variables en Git ni las compartas en el chat.
4. Apunta un dominio al VPS y configura Caddy para reenviar ese dominio por HTTPS a `127.0.0.1:8000`. Ejecuta la app con `waitress-serve --listen=127.0.0.1:8000 src.app:app`; mantenla como servicio de Windows para que se reinicie tras fallos o reinicios.
5. Inicia MT5 en el VPS y valida primero cotizaciones y operaciones en una cuenta demo. Restringe el firewall, activa copias de seguridad de la base de datos y verifica `/login` desde un equipo externo.

Usa una sola instancia del servidor: el estado de las solicitudes automáticas demo se mantiene en memoria y se pierde si el proceso se reinicia. Esta app rechaza cuentas MT5 reales para el envío automático; la automatización real no está habilitada por el despliegue. PayPal permanece en sandbox hasta completar su configuración y la revisión del flujo de producción.

## Instalación Rápida

Esta instalación es solo para desarrollo y pruebas locales:

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

La actualización automática de mercado solo lee cotizaciones. La única vía de órdenes está protegida y requiere una solicitud explícita de un usuario PREMIUM; siempre rechaza cuentas reales y no garantiza ganancias.

#### Prueba manual aislada en MT5 demo
El ejecutor comparte el mismo motor protegido que el comando del dashboard y nunca admite cuentas reales. Por defecto solo valida la señal y hace `order_check`; requiere `--execute-demo-order` para enviar como máximo una orden por ejecución:

```powershell
python tools\run_demo_trade_test.py --symbol EURUSD
python tools\run_demo_trade_test.py --symbol XAUUSD --max-loss-usd 5 --experimental-raw-direction-demo-only --execute-demo-order
```

Solo usa EURUSD/XAUUSD, cuenta demo USD y permisos MT5 activos. Por defecto exige una señal confirmada; el arnés experimental puede usar dirección cruda solo con `--experimental-raw-direction-demo-only`, al menos 55% walk-forward con 8 muestras, 75% de acuerdo, coincidencia entre el pronóstico ponderado y los cuatro modelos, movimiento suficiente y velas M1 recientes. Los niveles SL de predicción usan por defecto 2.25× ATR. Una validación MT5 limitada comparó 2×, 2.25× y 2.5× en dos ventanas; 2.25× fue el mejor neto combinado de XAUUSD, pero el resultado cambia entre periodos y no demuestra mejora futura. El arnés limita la pérdida bruta estimada a USD 5 y rechaza operaciones que excedan ese tope con el lote mínimo. Antes de enviar, calcula el riesgo/beneficio con la cotización y PnL estimado de MT5, y requiere al menos 2:1. El TP dinámico sigue el pronóstico dentro de USD 5-15; si no cabe en los límites de pérdida, margen o ratio, no abre la operación. El monitor espera el TP/SL del servidor hasta 15 minutos y puede cerrar antes solo cuando el PnL bruto estimado alcanza USD 1, la volatilidad M1 reciente es al menos 1.5 veces su referencia y la señal fresca indica giro. Si vence el monitor, el TP y SL siguen activos en MT5. Las entradas experimentales no son señales validadas y no deben usarse en cuentas reales. Lote mínimo, spread, comisiones, deslizamiento y gaps pueden cambiar el resultado real; no se garantiza ganancia. Otra posición u orden pendiente bloquea el mismo símbolo.

En el chat PREMIUM del dashboard también se puede solicitar una operación individual con `/trade auto demo XAUUSD` o `/trade auto demo EURUSD`. La solicitud se procesa en segundo plano, informa su estado en el chat y usa los mismos límites/monitor del arnés; el servidor bloquea cuentas reales, posiciones ya abiertas y solicitudes simultáneas. No es un bot recurrente ni garantiza que se abra una operación o se alcance ganancia.

Los usuarios se registran desde `/register`. No hay cuentas ni contraseñas demo compartidas; al iniciar, las cuentas heredadas `admin`, `trader` y `demo` con sus emails de ejemplo se desactivan y sus sesiones se revocan.

#### Pagos PayPal para Costa Rica (sandbox)
La app puede iniciar suscripciones recurrentes PayPal Checkout en USD, adecuada para probar compradores en Costa Rica. Los planes se activan solo tras verificar con PayPal la suscripción y el último pago; el webhook también verifica su firma en la API de PayPal y deduplica eventos. Los cobros sandbox no son dinero real.

1. Crea una aplicación sandbox y planes mensuales PRO (`USD 9.99`) y PREMIUM (`USD 19.99`) en PayPal Developer.
2. Registra el webhook HTTPS `POST /api/payments/paypal/webhook` para `BILLING.SUBSCRIPTION.ACTIVATED`, `BILLING.SUBSCRIPTION.CANCELLED`, `BILLING.SUBSCRIPTION.EXPIRED`, `BILLING.SUBSCRIPTION.SUSPENDED` y `PAYMENT.SALE.COMPLETED`.
3. Copia las variables placeholder de `.env.payments.example` a tu `.env` local (ignorado por Git). Genera también `FLASK_SECRET_KEY` con `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Configura `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_WEBHOOK_ID`, `PAYPAL_PRO_PLAN_ID`, `PAYPAL_PREMIUM_PLAN_ID` y `PAYPAL_PUBLIC_BASE_URL` (URL pública HTTPS accesible por el navegador y PayPal).
4. Configura `FLASK_SECRET_KEY` y SMTP: `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`, `SMTP_USERNAME`, `SMTP_PASSWORD`, y opcionalmente `SMTP_USE_SSL`/`SMTP_STARTTLS`.
5. Si faltan credenciales PayPal, el checkout responde 503 y no concede planes. No se manejan datos de tarjeta en la app; el comprador los ingresa en PayPal.

PayPal mantiene suscripciones y realiza renovaciones recurrentes. La cancelación de la app se envía al proveedor; `POST /api/subscription/upgrade` y `/renew` ya no pueden inventar pagos ni otorgar acceso. El modo de producción queda deshabilitado intencionalmente hasta una revisión separada de operaciones, impuestos y webhook.

#### Seguridad de cuentas
Configura un `FLASK_SECRET_KEY` aleatorio y SMTP antes de producción. La recuperación de contraseña envía un token de un solo uso por correo; el API no lo devuelve y en la base se guarda su hash. La sesión requiere un token activo en la base y se revoca al cerrar sesión o al cambiar/restablecer contraseña. El SQL de la aplicación usa consultas ORM parametrizadas; no construyas consultas interpolando entrada del usuario.

Los usuarios se registran desde `/register`; las contraseñas se guardan con hash y las consultas de la app usan SQLAlchemy ORM parametrizado. El plan FREE recibe análisis técnico básico cada 15 minutos, sin chat con IA, noticias PRO ni predicciones. PRO habilita chat y predicción avanzada cada cinco minutos; PREMIUM mantiene el análisis profesional cada cinco minutos y la predicción avanzada cada dos minutos.

### Funcionalidades

#### Gráfico de Precios
- Ver gráfico con colores dinámicos (dorado subida, morado bajada)
- Con MT5 conectado, mostrar velas OHLC M1 reales y sincronizar el cierre/quote con el modo de gráfico del símbolo (BID o LAST)
- Velas alcistas verdes y bajistas rojas; al pasar el cursor se muestran hora UTC y valores O/H/L/C
- Usar gráfico de línea como respaldo cuando la fuente no entrega velas OHLC
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
- `POST /api/chat/command` - Ejecutar comandos del chat; el trade automático demo requiere PREMIUM
- `GET /api/chat/demo-trade/<job_id>` - Consultar el estado de una solicitud demo propia

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
- Usa horizonte de 10 velas de un minuto; el máximo soportado por endpoint es 15 minutos
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
