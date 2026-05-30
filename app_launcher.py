#!/usr/bin/env python3
"""Lanzador local para ejecutar la aplicación de trading como una app normal."""
import webbrowser
from src.app import run_flask_app

if __name__ == '__main__':
    try:
        webbrowser.open('http://127.0.0.1:5000')
    except Exception:
        pass
    run_flask_app()
