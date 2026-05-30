"""Aplicación principal de trading empaquetada.

Exporta la app de Flask y los servicios de background para usar con WSGI.
"""

from .app import app, start_background_services
