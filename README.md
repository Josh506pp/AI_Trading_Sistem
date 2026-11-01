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
3. Los precios se actualizan cada cinco segundos

Para validar planes en desarrollo local, los perfiles de prueba son `demo` (FREE), `trader` (PRO) y `admin` (PREMIUM). Sus suscripciones de prueba se reactivan al iniciar la app; esta renovación automática no se aplica con `FLASK_ENV=production`.

### Funcionalidades

#### Gráfico de Precios
- Ver gráfico con colores dinámicos (dorado subida, morado bajada)
- Cambiar símbolo: EURUSD, XAUUSD, BTCUSD, etc.
- Ver la cotización actual de la divisa seleccionada, sincronizada con el último punto del gráfico
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

# Suite de tests
python tests/test_platform.py
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
│   └── test_platform.py       # Suite de tests
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
- Las estimaciones no incluyen costos de operación ni garantizan ganancias

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
