#!/usr/bin/env python3
"""
Security Module
CORS, rate limiting, input validation, encryption
"""

from flask import request
from functools import wraps
import re
import logging
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)

# Rate limiting in-memory store
request_counts = defaultdict(list)
RATE_LIMIT_REQUESTS = 100  # requests per window
RATE_LIMIT_WINDOW = 60     # seconds

class SecurityValidator:
    """Validador de seguridad para entradas"""
    
    @staticmethod
    def validate_email(email):
        """Validar formato de email"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_username(username):
        """Validar username"""
        if len(username) < 3 or len(username) > 32:
            return False
        pattern = r'^[a-zA-Z0-9_-]+$'
        return re.match(pattern, username) is not None
    
    @staticmethod
    def validate_password(password):
        """Validar contraseña"""
        if len(password) < 6:
            return False
        return True
    
    @staticmethod
    def sanitize_string(value, max_length=255):
        """Sanitizar string para prevenir injection"""
        if not isinstance(value, str):
            return ""
        # Remover caracteres peligrosos
        value = value.replace('\x00', '').replace('\r', '').replace('\n', '')
        return value[:max_length]
    
    @staticmethod
    def validate_symbol(symbol):
        """Validar símbolo de trading"""
        pattern = r'^[A-Z0-9]{2,10}$'
        return re.match(pattern, symbol) is not None
    
    @staticmethod
    def validate_number(value, min_val=None, max_val=None):
        """Validar número"""
        try:
            num = float(value)
            if min_val is not None and num < min_val:
                return False
            if max_val is not None and num > max_val:
                return False
            return True
        except (ValueError, TypeError):
            return False


def rate_limit(limit_per_minute=100):
    """Decorador para rate limiting"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Obtener cliente IP
            client_ip = request.remote_addr
            now = datetime.utcnow()
            
            # Limpiar requests antiguos
            request_counts[client_ip] = [
                req_time for req_time in request_counts[client_ip]
                if now - req_time < timedelta(seconds=60)
            ]
            
            # Verificar límite
            if len(request_counts[client_ip]) >= limit_per_minute:
                logger.warning(f"Rate limit exceeded for {client_ip}")
                return {'error': 'Rate limit exceeded'}, 429
            
            # Registrar request
            request_counts[client_ip].append(now)
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def setup_cors(app):
    """Configurar CORS seguro"""
    @app.after_request
    def set_cors_headers(response):
        # Solo permitir requests desde mismo origen en producción
        origin = request.headers.get('Origin', '')
        
        # Whitelist de orígenes permitidos
        allowed_origins = [
            'http://localhost:5000',
            'http://localhost:8080',
            'http://127.0.0.1:5000',
            'http://127.0.0.1:8080',
        ]
        
        if origin in allowed_origins or not origin:
            response.headers['Access-Control-Allow-Origin'] = origin or '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Max-Age'] = '3600'
        
        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        
        return response
    
    return app


def validate_request_json(required_fields=None):
    """Decorador para validar JSON de request"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            data = request.get_json(silent=True)
            
            if not data:
                return {'error': 'JSON requerido'}, 400
            
            if required_fields:
                missing = [field for field in required_fields if field not in data]
                if missing:
                    return {'error': f'Campos requeridos faltando: {", ".join(missing)}'}, 400
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


class SQLInjectionProtection:
    """Protección contra SQL injection"""
    
    SQL_KEYWORDS = [
        'DROP', 'DELETE', 'INSERT', 'UPDATE', 'EXEC', 'EXECUTE',
        'UNION', 'SELECT', 'ALTER', 'CREATE', 'REPLACE', 'TRUNCATE'
    ]
    
    @staticmethod
    def is_safe(value):
        """Verificar si string es seguro"""
        if not isinstance(value, str):
            return True
        
        upper_value = value.upper()
        for keyword in SQLInjectionProtection.SQL_KEYWORDS:
            if keyword in upper_value:
                return False
        
        return True


class CryptographyHelper:
    """Encriptación de datos sensibles"""
    
    @staticmethod
    def encrypt_card_number(card_number):
        """Encriptar número de tarjeta"""
        # NUNCA guardar número completo
        if len(card_number) >= 4:
            return '*' * (len(card_number) - 4) + card_number[-4:]
        return '*' * len(card_number)


def error_handler_json(error_code, message, status_code=400):
    """Crear respuesta de error JSON segura"""
    return {
        'success': False,
        'error': message,
        'error_code': error_code,
        'timestamp': datetime.utcnow().isoformat()
    }, status_code


# Log de seguridad
def log_security_event(event_type, user_id=None, details=None):
    """Registrar evento de seguridad"""
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'event_type': event_type,
        'user_id': user_id,
        'ip_address': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', ''),
        'details': details
    }
    logger.warning(f"SECURITY EVENT: {log_entry}")
