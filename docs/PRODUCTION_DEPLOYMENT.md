# Despliegue a Producción

Este proyecto ya está preparado para producción con servidor WSGI y contenedor Docker.

## Pasos recomendados

1. Copia el archivo de ejemplo de entorno:
   ```bash
   copy .env.example .env
   ```
2. Configura tus credenciales MT5 y la clave secreta en `.env`.
3. Ejecuta el servidor de producción con Waitress:
   ```bash
   python production.py
   ```
4. Si usas Docker:
   ```bash
   docker build -t trading-system:prod .
   docker run -p 8080:8080 --env-file .env trading-system:prod
   ```

## Opciones de despliegue

- `python production.py` — recommended for Windows/host deployments
- `waitress-serve --listen=0.0.0.0:8080 wsgi:app` — WSGI production server
- `docker build` / `docker run` — container deployment
- `gunicorn --workers=1 wsgi:app` — Linux deploy (si no usas MT5 en el contenedor)

## Notas importantes

- `MetaTrader5` puede requerir un entorno Windows compatible. El contenedor Docker Linux puede funcionar para el modo simulado, pero la conexión MT5 real se recomienda en Windows.
- Usa `FLASK_SECRET_KEY` distinto y seguro en producción.
- Si usas `gunicorn`, limita a un solo worker para evitar duplicar el hilo de análisis en segundo plano:
  ```bash
  gunicorn --workers=1 wsgi:app
  ```

## Empaquetado como ejecutable

Este repositorio puede empaquetarse como aplicación ejecutable en Windows usando PyInstaller.

### Uso rápido

```bash
python copy_and_package.py
```

O con el script de Windows:

```bat
build_executable.bat
```

### Resultado

- La carpeta de release se crea en `release/`
- El ejecutable empaquetado queda en `release/dist/TradingSystem`
- Ejecuta `release\dist\TradingSystem\TradingSystem.exe`

> Nota: si usas MT5 real en producción, el ejecutable debe correr en un host Windows con MetaTrader 5 instalado.

## Ejecución en producción con Docker Compose

```bash
docker compose up --build -d
```

## Verificación

- Abre `http://127.0.0.1:8080`
- Revisa el estado del bot y la conexión MT5
- Usa los endpoints `/api/mt5/connect` y `/api/professional-analysis`
