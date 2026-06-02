# AI Trading System

AI Trading System es un sistema de trading algorítmico local con panel web integrado, simulación de precios en tiempo real y soporte opcional para MetaTrader 5.

## Visión general

Este proyecto ofrece una aplicación Flask de escritorio que permite ejecutar un dashboard local, analizar datos de precios, alternar el modo de trading automático y conectar una cuenta MT5 si está disponible.

## Características principales

- Dashboard accesible en `/` y `/dashboard`.
- Gráfico de precios en tiempo real con historial de valores.
- Controles de trading manuales: comprar, vender y cerrar posiciones.
- Alternador de modo automático para el bot de trading.
- Integración opcional con MetaTrader 5 para trading real.
- Análisis técnico basado en RSI, MACD, bandas de Bollinger y aprendizaje de patrones.
- API REST local para estado, órdenes, predicciones y configuración.
- Chat interno para enviar comandos y registrar conversaciones.
- Soporte de funcionamiento en modo simulación cuando MT5 no está disponible.

## Requisitos

- Python 3.10 o superior.
- Dependencias instaladas con `pip install -r requirements.txt`.
- Opcional: MetaTrader 5 y `terminal64.exe` para trading real.
- Entorno virtual recomendado.

## Instalación

1. Crear y activar el entorno virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Instalar dependencias:

```powershell
pip install -r requirements.txt
```

## Ejecución

Iniciar la aplicación:

```powershell
python src/app.py
```

También se puede usar el launcher incluido:

```powershell
.\Launch_Trading_System.bat
# o
.\LAUNCH_TRADING_SYSTEM.py
```

Luego abrir el navegador en `http://127.0.0.1:5000`.

## Uso del dashboard

El panel permite:

- Ver precio actual y tendencia histórica.
- Iniciar o detener el bot de trading.
- Alternar el modo de predicción.
- Conectar y verificar la conexión MT5.
- Enviar órdenes de compra, venta y cierre de posiciones.
- Revisar mensajes de chat y comandos del sistema.

## Empaquetado como ejecutable

Para generar un ejecutable en Windows:

```powershell
python package_executable.py
```

O con el script de empaquetado:

```powershell
.\build_executable.bat
```

El ejecutable resultante se crea en `release/dist/TradingSystem`.

## Integración con MetaTrader 5

1. Configurar credenciales en un archivo local o mediante variables de entorno.
2. Desde el dashboard, usar el formulario de MT5 para conectar la cuenta.
3. Si se habilita el modo real, `MT5_PATH` debe apuntar al ejecutable de MetaTrader 5.

## Seguridad y uso responsable

- No incluir credenciales ni datos sensibles en el repositorio público.
- Este software es una herramienta de análisis y no garantiza resultados financieros.
- No debe usarse en producción sin pruebas exhaustivas.
- El uso de MetaTrader 5 está sujeto a los términos de MetaQuotes.

## Contribución

1. Crear una rama con nombre descriptivo.
2. Realizar cambios en `src/` y, cuando sea posible, agregar pruebas.
3. Abrir una solicitud de extracción con una descripción clara del alcance.

## Archivos clave

- `src/app.py`: servidor Flask, lógica de trading y dashboard embebido.
- `src/mt5_config.py`: configuración opcional de MetaTrader 5.
- `package_executable.py`: script de empaquetado.
- `requirements.txt`: dependencias del proyecto.
- `release/dist/TradingSystem`: ejecutable generado.

## Licencia

El proyecto se distribuye bajo MIT License con términos adicionales de exención de responsabilidad y uso de trading.

---

# English version

AI Trading System is a local algorithmic trading system with an integrated web panel, real-time price simulation, and optional MetaTrader 5 support.

## Overview

This project provides a desktop Flask application that runs a local dashboard, analyzes price data, toggles automatic trading mode, and connects to a MT5 account when available.

## Main features

- Dashboard available at `/` and `/dashboard`.
- Real-time price chart with historical values.
- Manual trading controls: buy, sell, and close positions.
- Auto trading bot toggle.
- Optional MetaTrader 5 integration for real trading.
- Technical analysis based on RSI, MACD, Bollinger Bands, and pattern learning.
- Local REST API for status, orders, predictions, and configuration.
- Internal chat for sending commands and recording conversations.
- Simulation mode support when MT5 is not available.

## Requirements

- Python 3.10 or higher.
- Dependencies installed with `pip install -r requirements.txt`.
- Optional: MetaTrader 5 and `terminal64.exe` for real trading.
- Virtual environment recommended.

## Installation

1. Create and activate the virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

## Run

Start the application:

```powershell
python src/app.py
```

You can also use the included launcher:

```powershell
.\Launch_Trading_System.bat
# or
.\LAUNCH_TRADING_SYSTEM.py
```

Then open the browser at `http://127.0.0.1:5000`.

## Dashboard usage

The panel allows you to:

- See current price and historical trends.
- Start or stop the trading bot.
- Toggle prediction mode.
- Connect and verify MT5 connection.
- Send buy, sell, and close position orders.
- Review chat messages and system commands.

## Packaging as executable

To generate a Windows executable:

```powershell
python package_executable.py
```

Or with the packaging script:

```powershell
.\build_executable.bat
```

The resulting executable is created in `release/dist/TradingSystem`.

## MetaTrader 5 integration

1. Configure credentials in a local file or via environment variables.
2. Use the MT5 connection form from the dashboard.
3. If real mode is enabled, `MT5_PATH` must point to the MetaTrader 5 executable.

## Security and responsible use

- Do not include credentials or sensitive data in the public repository.
- This software is an analysis tool and does not guarantee financial results.
- It should not be used in production without exhaustive testing.
- Use of MetaTrader 5 is subject to MetaQuotes terms.

## Contribution

1. Create a branch with a descriptive name.
2. Make changes in `src/` and add tests when possible.
3. Open a pull request with a clear scope description.

## Key files

- `src/app.py`: Flask server, trading logic and embedded dashboard.
- `src/mt5_config.py`: optional MetaTrader 5 configuration.
- `package_executable.py`: packaging script.
- `requirements.txt`: project dependencies.
- `release/dist/TradingSystem`: generated executable.

## License

The project is distributed under the MIT License with additional trading disclaimer terms.
