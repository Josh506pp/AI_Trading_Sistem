# AI Trading System

Un sistema de trading experimental con dashboard web, simulador y soporte para integración con MetaTrader 5 (MT5). Este repositorio incluye código para ejecutar localmente, empaquetar como ejecutable y extender la lógica de trading.

Contenido rápido
-----------------
- Inicio rápido: ejecutar la demo local y abrir el dashboard
- Empaquetado: crear un .exe con PyInstaller (Windows)
- MT5: conectar cuenta desde la UI y opcionalmente guardar credenciales

Requisitos
----------
- Python 3.10+ (recomendado 3.11 / 3.14)
- Dependencias: instalar con `pip install -r requirements.txt`
- (Opcional) MetaTrader 5 y terminal64.exe para trading real

Instalación y ejecución (dev)
----------------------------
1. Crear/activar entorno virtual (recomendado):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1    # PowerShell
# o en cmd: .\.venv\Scripts\activate.bat
```

2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. Ejecutar la aplicación (abrirá el dashboard en el navegador):

```bash
python src/app.py
```

O usar el launcher proporcionado:

```powershell
# Windows
.\Launch_Trading_System.bat
# o
.\LAUNCH_TRADING_SYSTEM.py
```

Dashboard
---------
La interfaz web se sirve desde `src/app.py` (ruta `/` o `/dashboard`). Provee:
- Gráfico de precios en tiempo real
- Control de bot (start/stop)
- Conexión y estado MT5
- Chat / comandos de control

Empaquetado a ejecutable (Windows)
---------------------------------
Usamos PyInstaller vía script incluido. Resultado en `release/dist/TradingSystem`.

```powershell
# Empaqueta y genera el ejecutable (puede tardar varios minutos)
.\build_executable.bat
# o
python package_executable.py
```

MT5 — configuración y uso
-------------------------
1. Puedes configurar credenciales en `.env` o conectarlas desde la UI.
2. Desde el dashboard usa el modal de MT5 para conectar; al conectarse la UI pregunta si quieres guardar en `src/mt5_config.py`.
3. Si quieres usar trading real, instala MetaTrader 5 y provee `MT5_PATH` apuntando a `terminal64.exe`.

Archivos clave
-------------
- `src/app.py` — servidor Flask + dashboard HTML embebido
- `package_executable.py` / `build_executable.bat` — scripts de empaquetado
- `requirements.txt` — dependencias Python
- `src/mt5_config.py` — (opcional) credenciales MT5 guardadas

Buenas prácticas
----------------
- No incluyas credenciales en el repo público. Usa `.env` o `mt5_config.py` local.
- Añade tests para cualquier cambio crítico en `src/`.
- Revisa `release/` antes de distribuir.

Problemas comunes
-----------------
- Gráfico parpadea o se recrea: actualizar el dashboard (ya corregido para actualizar datos sin recrear Chart.js).
- Error al empujar a GitHub: configurar `git remote add origin <repo>` y push.
- MT5: si `mt5` no está instalado, la app funciona en modo simulación.

Contribuir
----------
1. Crear un branch con nombre descriptivo
2. Hacer cambios y añadir tests si aplica
3. Abrir PR con descripción clara del cambio

Licencia
--------
Revisa `LICENSE.md` en la raíz. Si quieres que cambie a MIT u otra licencia, dime cuál y lo actualizo.

Contacto
-------
Si quieres que haga un README en inglés, o que añada secciones específicas (ej. CI, badges, deploy), dime y lo genero.

---

`README.md` actualizado por el asistente — dime si quieres que añada una tabla de comandos o instrucciones paso a paso para empaquetar en Windows con firmas.
