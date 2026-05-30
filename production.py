"""Production server entrypoint using Waitress."""
import os
import logging

from wsgi import app

try:
    from waitress import serve
except ImportError:
    raise RuntimeError('Waitress is required for production execution. Install it with pip install waitress.')

logging.basicConfig(
    level=os.environ.get('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    host = os.environ.get('HOST', '0.0.0.0')
    logger.info(f'Starting production server on {host}:{port}')
    serve(app, host=host, port=port)
