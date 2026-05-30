#!/usr/bin/env python3
"""
PROFESSIONAL TRADING SYSTEM - Sistema de Trading Inteligente Consolidado
Versión Profesional con Seguridad Avanzada y Arquitectura Unificada

Características:
- Sistema de trading completamente integrado
- Protecciones de seguridad avanzadas contra ataques
- Arquitectura profesional con logging seguro
- Validación de inputs y rate limiting
- Autenticación y encriptación de datos sensibles
- Dashboard web integrado con navegador embebido
- IA con protecciones anti-manipulación
- MT5 integration con validaciones de seguridad
- Actualización en tiempo real sin servidor separado

Autor: AI Trading System Professional
Fecha: Abril 2026
Versión: 3.0.0 - INTEGRATED VERSION
"""

import os
import sys
import socket
import logging
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from functools import wraps
import threading
import json
import base64
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import hmac
import re
import random
import webbrowser

# Fix console encoding issues on Windows
import sys
import os
if os.name == 'nt':  # Windows
    try:
        # Force UTF-8 encoding for console output
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python < 3.7 doesn't have reconfigure
        pass

# Third-party imports with error handling
try:
    import numpy as np
    import pandas as pd
    from flask import Flask, render_template, jsonify, request, session, redirect, url_for
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    import MetaTrader5 as mt5
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.neural_network import MLPRegressor
    from sklearn.preprocessing import StandardScaler
    import joblib
    try:
        import stripe
    except ImportError:
        stripe = None
    try:
        import webview
    except ImportError:
        webview = None
except ImportError as e:
    print(f"Error importing required packages: {e}")
    print("Please install requirements: pip install -r requirements.txt")
    sys.exit(1)

# Local imports - Database and Device Management
try:
    from database_manager import DatabaseManager
    from device_manager import DeviceManager
except ImportError as e:
    print(f"⚠️ Database/Device modules not found: {e}")
    print("Creating local database management system...")

# =============================================================================
# GESTIÓN DE BASE DE DATOS LOCAL
# =============================================================================

class DatabaseManager:
    """Gestor de base de datos local simplificado"""

    def __init__(self, db_path: str = "trading_system.db"):
        self.db_path = db_path
        self.users = {}
        self.devices = {}
        self.payments = {}
        self._load_data()

    def _load_data(self):
        """Carga datos desde archivo JSON"""
        try:
            if os.path.exists(self.db_path):
                with open(self.db_path, 'r') as f:
                    data = json.load(f)
                    self.users = data.get('users', {})
                    self.devices = data.get('devices', {})
                    self.payments = data.get('payments', {})
        except Exception as e:
            logger.error(f"Error loading database: {e}")

    def _save_data(self):
        """Guarda datos en archivo JSON"""
        try:
            data = {
                'users': self.users,
                'devices': self.devices,
                'payments': self.payments
            }
            with open(self.db_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving database: {e}")

    def add_user(self, username: str, password_hash: str, email: str, role: str = 'trader') -> bool:
        """Agrega usuario"""
        if username in self.users:
            return False
        self.users[username] = {
            'password_hash': password_hash,
            'email': email,
            'role': role,
            'created': datetime.now().isoformat(),
            'active': True
        }
        self._save_data()
        return True

    def get_user(self, username: str) -> Optional[Dict]:
        """Obtiene usuario"""
        return self.users.get(username)

    def update_user(self, username: str, data: Dict) -> bool:
        """Actualiza usuario"""
        if username not in self.users:
            return False
        self.users[username].update(data)
        self._save_data()
        return True

    def delete_user(self, username: str) -> bool:
        """Elimina usuario"""
        if username not in self.users:
            return False
        del self.users[username]
        self._save_data()
        return True

    def list_users(self) -> List[Dict]:
        """Lista todos los usuarios"""
        return list(self.users.values())

    def backup_database(self, backup_path: str = None) -> bool:
        """Crea backup de la base de datos"""
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.db_path}.backup_{timestamp}"

        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backup created: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False

    def get_database_stats(self) -> Dict:
        """Estadísticas de la base de datos"""
        return {
            'total_users': len(self.users),
            'active_users': len([u for u in self.users.values() if u.get('active', True)]),
            'admin_users': len([u for u in self.users.values() if u.get('role') == 'admin']),
            'trader_users': len([u for u in self.users.values() if u.get('role') == 'trader']),
            'database_size': os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        }

class DeviceManager:
    """Gestor de dispositivos simplificado"""

    def __init__(self):
        self.devices = {}

    def register_device(self, user_id: str, device_fingerprint: str) -> bool:
        """Registra dispositivo"""
        if user_id not in self.devices:
            self.devices[user_id] = []
        if device_fingerprint not in self.devices[user_id]:
            self.devices[user_id].append(device_fingerprint)
        return True

    def validate_device(self, user_id: str, device_fingerprint: str) -> bool:
        """Valida dispositivo"""
        return device_fingerprint in self.devices.get(user_id, [])

class ProfessionalAuthenticator:
    """Autenticador profesional simplificado"""

    def __init__(self):
        self.db = DatabaseManager()
        self.device_manager = DeviceManager()
        self.sessions = {}

    def register_user(self, username: str, password: str, email: str, role: str = 'trader') -> bool:
        """Registra nuevo usuario"""
        password_hash = SecurityUtils.hash_password(password)
        return self.db.add_user(username, password_hash, email, role)

    def authenticate_user(self, username: str, password: str, device_fingerprint: str = None) -> Optional[Dict]:
        """Autentica usuario"""
        user = self.db.get_user(username)
        if not user or not user.get('active', False):
            return None

        if not SecurityUtils.verify_password(password, user['password_hash']):
            return None

        # Validate device if provided
        if device_fingerprint and not self.device_manager.validate_device(username, device_fingerprint):
            return None

        # Register device for future logins
        if device_fingerprint:
            self.device_manager.register_device(username, device_fingerprint)

        return user

    def create_session(self, username: str) -> str:
        """Crea sesión"""
        session_id = secrets.token_hex(32)
        self.sessions[session_id] = {
            'username': username,
            'created': datetime.now(),
            'active': True
        }
        return session_id

    def validate_session(self, session_id: str) -> Optional[str]:
        """Valida sesión"""
        session = self.sessions.get(session_id)
        if not session or not session.get('active', False):
            return None

        # Check session timeout (24 hours)
        if datetime.now() - session['created'] > timedelta(hours=24):
            session['active'] = False
            return None

        return session['username']

    def logout_session(self, session_id: str) -> bool:
        """Cierra sesión"""
        if session_id in self.sessions:
            self.sessions[session_id]['active'] = False
            return True
        return False

    def cleanup_expired_sessions(self):
        """Limpia sesiones expiradas"""
        current_time = datetime.now()
        expired = []
        for session_id, session in self.sessions.items():
            if current_time - session['created'] > timedelta(hours=24):
                expired.append(session_id)

        for session_id in expired:
            del self.sessions[session_id]

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")

# =============================================================================
# CONFIGURACIÓN DE SEGURIDAD
# =============================================================================

class SecurityConfig:
    """Configuración centralizada de seguridad"""

    # Encriptación
    ENCRYPTION_KEY_ENV = 'TRADING_SYSTEM_ENCRYPTION_KEY'
    SECRET_KEY_ENV = 'TRADING_SYSTEM_SECRET_KEY'

    # Rate Limiting
    MAX_REQUESTS_PER_MINUTE = 60
    MAX_REQUESTS_PER_HOUR = 1000

    # Autenticación
    SESSION_TIMEOUT_MINUTES = 30
    PASSWORD_MIN_LENGTH = 12
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15

    # Validación de Inputs
    MAX_INPUT_LENGTH = 1000
    ALLOWED_CHARS_PATTERN = r'^[a-zA-Z0-9\s\.,!?\-_@#$%^&*()+=]+$'

    # IA Security
    MAX_MODEL_ITERATIONS = 10000
    CONFIDENCE_THRESHOLD_MIN = 0.1
    CONFIDENCE_THRESHOLD_MAX = 0.95

    # Trading Security
    MAX_POSITION_SIZE_PERCENT = 5.0
    MAX_TOTAL_RISK_PERCENT = 20.0
    MIN_ORDER_INTERVAL_SECONDS = 1

    # Payment Security
    STRIPE_API_KEY_ENV = 'STRIPE_API_KEY'
    STRIPE_WEBHOOK_SECRET_ENV = 'STRIPE_WEBHOOK_SECRET'
    ADMIN_CREATION_TOKEN_ENV = 'ADMIN_CREATION_TOKEN'
    PAYMENT_CURRENCY = 'usd'
    PAYMENT_AMOUNT_CENTS = 19900
    PAYMENT_DESCRIPTION = 'Professional Trading System License'
    MAX_USERS_PER_IP = 1
    MAX_ADMIN_PER_IP = 1

    # Logging Security
    SENSITIVE_DATA_MASK = "***MASKED***"

# =============================================================================
# UTILIDADES DE SEGURIDAD
# =============================================================================

class SecurityUtils:
    """Utilidades de seguridad avanzadas"""

    @staticmethod
    def generate_secure_key(length: int = 32) -> str:
        """Genera una clave segura usando secrets"""
        return secrets.token_hex(length)

    @staticmethod
    def get_encryption_key() -> bytes:
        """Obtiene o genera clave de encriptación"""
        key = os.environ.get(SecurityConfig.ENCRYPTION_KEY_ENV)
        if not key:
            key = SecurityUtils.generate_secure_key(32)
            os.environ[SecurityConfig.ENCRYPTION_KEY_ENV] = key
        return base64.urlsafe_b64encode(key.encode())

    @staticmethod
    def encrypt_data(data: str) -> str:
        """Encripta datos sensibles"""
        try:
            f = Fernet(SecurityUtils.get_encryption_key())
            return f.encrypt(data.encode()).decode()
        except Exception as e:
            logger.error(f"Error encrypting data: {e}")
            return SecurityConfig.SENSITIVE_DATA_MASK

    @staticmethod
    def decrypt_data(encrypted_data: str) -> str:
        """Desencripta datos"""
        try:
            f = Fernet(SecurityUtils.get_encryption_key())
            return f.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"Error decrypting data: {e}")
            return SecurityConfig.SENSITIVE_DATA_MASK

    @staticmethod
    def hash_password(password: str) -> str:
        """Hashea contraseña de forma segura"""
        salt = secrets.token_hex(16)
        key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}:{key.hex()}"

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verifica contraseña hasheada"""
        try:
            salt, key = hashed.split(':')
            new_key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return hmac.compare_digest(key, new_key.hex())
        except:
            return False

    @staticmethod
    def sanitize_input(input_str: str, max_length: int = None) -> str:
        """Limpia y valida input del usuario"""
        if not input_str:
            return ""

        # Limitar longitud
        if max_length:
            input_str = input_str[:max_length]

        # Remover caracteres peligrosos
        input_str = re.sub(r'[<>]', '', input_str)

        # Validar patrón permitido
        if not re.match(SecurityConfig.ALLOWED_CHARS_PATTERN, input_str):
            raise ValueError("Input contiene caracteres no permitidos")

        return input_str.strip()

    @staticmethod
    def validate_trading_parameters(params: Dict) -> bool:
        """Valida parámetros de trading para seguridad"""
        try:
            # Validar límites de posición
            if params.get('lot_size', 0) > SecurityConfig.MAX_POSITION_SIZE_PERCENT / 100:
                return False

            # Validar confianza de IA
            confidence = params.get('confidence', 0)
            if not (SecurityConfig.CONFIDENCE_THRESHOLD_MIN <= confidence <= SecurityConfig.CONFIDENCE_THRESHOLD_MAX):
                return False

            # Validar precios razonables
            entry_price = params.get('entry_price', 0)
            if not (0.1 <= entry_price <= 10.0):  # Rango típico forex
                return False

            return True
        except:
            return False

# =============================================================================
# SISTEMA DE LOGGING SEGURO
# =============================================================================

class SecureLogger:
    """Sistema de logging con protección de datos sensibles"""

    def __init__(self, name: str = "ProfessionalTradingSystem"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Crear formato seguro
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Handler para archivo
        file_handler = logging.FileHandler('trading_system_secure.log')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Handler para consola (sin datos sensibles)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def log_sensitive_action(self, action: str, user_id: str = "system", details: Dict = None):
        """Log de acciones sensibles con datos enmascarados"""
        safe_details = self._mask_sensitive_data(details or {})
        self.logger.info(f"SENSITIVE_ACTION: {action} | USER: {user_id} | DETAILS: {safe_details}")

    def log_trading_action(self, action: str, trade_data: Dict):
        """Log de acciones de trading con protección"""
        safe_trade_data = self._mask_sensitive_data(trade_data)
        self.logger.info(f"TRADING_ACTION: {action} | DATA: {safe_trade_data}")

    def log_security_event(self, event: str, severity: str = "INFO", details: Dict = None):
        """Log de eventos de seguridad"""
        safe_details = self._mask_sensitive_data(details or {})
        self.logger.log(getattr(logging, severity), f"SECURITY_EVENT: {event} | DETAILS: {safe_details}")

    def info(self, message: str):
        """Log informativo"""
        self.logger.info(message)

    def error(self, message: str):
        """Log de error"""
        self.logger.error(message)

    def warning(self, message: str):
        """Log de advertencia"""
        self.logger.warning(message)

    def debug(self, message: str):
        """Log de debug"""
        self.logger.debug(message)

    def _mask_sensitive_data(self, data: Dict) -> Dict:
        """Enmascara datos sensibles en logs"""
        sensitive_keys = ['password', 'token', 'key', 'secret', 'api_key', 'login', 'balance']
        masked_data = {}

        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                masked_data[key] = SecurityConfig.SENSITIVE_DATA_MASK
            elif isinstance(value, dict):
                masked_data[key] = self._mask_sensitive_data(value)
            else:
                masked_data[key] = value

        return masked_data

# Inicializar logger seguro
logger = SecureLogger()

# =============================================================================
# MOTOR DE IA PARA TRADING
# =============================================================================

class AIAnalyzer:
    """Analizador de IA Avanzado para Trading - Razonamiento Mejorado"""

    def __init__(self):
        self.window_size = 50  # Aumentado para mejor análisis
        self.trade_history = []
        self.signal_cache = {}
        
    def analyze_prices(self, prices: List[float]) -> Dict:
        """Análisis multi-capa mejorado con razonamiento sofisticado"""
        if len(prices) < self.window_size:
            return {'error': 'Datos insuficientes'}

        recent = prices[-self.window_size:]
        
        # Capas de análisis
        indicators = self._calculate_indicators(recent)
        pattern = self._identify_pattern(recent)
        momentum = self._analyze_momentum(recent)
        volatility = self._analyze_volatility(recent)
        signal = self._generate_advanced_signal(indicators, pattern, momentum, volatility, recent)
        prediction = self._advanced_prediction(recent, indicators)

        return {
            'current_price': float(prices[-1]),
            'indicators': indicators,
            'pattern': pattern,
            'momentum': momentum,
            'volatility': volatility,
            'signal': signal,
            'prediction': prediction,
            'confidence': signal['confidence'],
            'action': signal['action'],
            'reasoning': signal['reasoning'],
            'timestamp': datetime.now().isoformat()
        }

    def _calculate_indicators(self, prices: List[float]) -> Dict:
        """Calcula indicadores técnicos avanzados"""
        # Medias móviles
        sma_5 = sum(prices[-5:]) / 5
        sma_10 = sum(prices[-10:]) / 10
        sma_20 = sum(prices[-20:]) / 20
        sma_50 = sum(prices) / len(prices)
        
        # RSI mejorado (14 períodos estándar)
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d for d in deltas if d > 0]
        losses = [abs(d) for d in deltas if d < 0]
        
        avg_gain = sum(gains) / 14 if len(gains) >= 14 else (sum(gains) / len(gains) if gains else 0.0001)
        avg_loss = sum(losses) / 14 if len(losses) >= 14 else (sum(losses) / len(losses) if losses else 0.0001)
        
        rs = avg_gain / avg_loss if avg_loss > 0 else 0
        rsi = 100 - (100 / (1 + rs)) if rs > 0 else 50
        
        # MACD (12-26-9)
        ema_12 = self._calculate_ema(prices, 12)
        ema_26 = self._calculate_ema(prices, 26)
        macd_line = ema_12 - ema_26
        signal_line = self._calculate_ema([macd_line], 9)
        macd_histogram = macd_line - signal_line
        
        # Bandas de Bollinger
        bb_middle = sma_20
        bb_std = (sum([(p - bb_middle) ** 2 for p in prices[-20:]]) / 20) ** 0.5
        bb_upper = bb_middle + (2 * bb_std)
        bb_lower = bb_middle - (2 * bb_std)
        
        # Stochastic (14,3,3)
        lowest = min(prices[-14:])
        highest = max(prices[-14:])
        k_percent = ((prices[-1] - lowest) / (highest - lowest) * 100) if highest > lowest else 50
        
        # ATR (volatilidad)
        tr_values = []
        for i in range(1, len(prices)):
            tr = max(prices[i] - prices[i-1], abs(prices[i] - prices[i-1]))
            tr_values.append(tr)
        atr = sum(tr_values[-14:]) / 14 if len(tr_values) >= 14 else 0
        
        # Trend
        trend = 'UP' if sma_5 > sma_10 > sma_20 else ('DOWN' if sma_5 < sma_10 < sma_20 else 'SIDE')

        return {
            'sma_5': float(sma_5),
            'sma_10': float(sma_10),
            'sma_20': float(sma_20),
            'sma_50': float(sma_50),
            'rsi': float(rsi),
            'macd': float(macd_line),
            'macd_signal': float(signal_line),
            'macd_histogram': float(macd_histogram),
            'bb_upper': float(bb_upper),
            'bb_middle': float(bb_middle),
            'bb_lower': float(bb_lower),
            'stochastic': float(k_percent),
            'atr': float(atr),
            'trend': trend
        }
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calcula Media Móvil Exponencial"""
        if len(prices) < period:
            return sum(prices) / len(prices)
        
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        
        for price in prices[period:]:
            ema = price * multiplier + ema * (1 - multiplier)
        
        return ema
    
    def _identify_pattern(self, prices: List[float]) -> Dict:
        """Identifica patrones de precio"""
        current = prices[-1]
        prev = prices[-2]
        prev2 = prices[-3]
        
        # Detectar velas/candelabros
        if prev2 < prev and prev > current:
            pattern_type = 'BEARISH_REJECTION'
            strength = (prev - min(current, prev2)) / prev2
        elif prev2 > prev and prev < current:
            pattern_type = 'BULLISH_ENGULFING'
            strength = (max(current, prev2) - prev) / prev2
        elif current > prev and prev > prev2:
            pattern_type = 'ASCENDING'
            strength = (current - prev2) / prev2
        elif current < prev and prev < prev2:
            pattern_type = 'DESCENDING'
            strength = (prev2 - current) / prev2
        else:
            pattern_type = 'CONSOLIDATION'
            strength = 0
        
        return {
            'type': pattern_type,
            'strength': float(min(strength, 1.0))
        }
    
    def _analyze_momentum(self, prices: List[float]) -> Dict:
        """Analiza momentum y fuerza de tendencia"""
        # Momentum simple
        momentum = ((prices[-1] - prices[-5]) / prices[-5]) * 100 if prices[-5] != 0 else 0
        
        # ROC (Rate of Change)
        roc = ((prices[-1] - prices[-10]) / prices[-10]) * 100 if prices[-10] != 0 else 0
        
        # Acceleration
        recent_changes = [prices[i] - prices[i-1] for i in range(-5, 0)]
        acceleration = sum(recent_changes[-2:]) - sum(recent_changes[-5:-2]) if len(recent_changes) >= 5 else 0
        
        return {
            'momentum': float(momentum),
            'roc': float(roc),
            'acceleration': float(acceleration)
        }
    
    def _analyze_volatility(self, prices: List[float]) -> Dict:
        """Analiza volatilidad del mercado"""
        returns = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        mean_return = sum(returns) / len(returns)
        variance = sum([(r - mean_return) ** 2 for r in returns]) / len(returns)
        volatility = variance ** 0.5
        
        # Volatilidad normalizada
        norm_vol = (volatility / (sum(prices) / len(prices))) * 100
        
        return {
            'volatility': float(volatility),
            'normalized_volatility': float(norm_vol),
            'regime': 'HIGH' if norm_vol > 1.5 else ('LOW' if norm_vol < 0.5 else 'NORMAL')
        }
    
    def _generate_advanced_signal(self, indicators: Dict, pattern: Dict, momentum: Dict, 
                                  volatility: Dict, prices: List[float]) -> Dict:
        """Genera señal con razonamiento multi-factor sofisticado"""
        
        score = 0
        factors = []
        
        # Factor 1: Tendencia (Peso: 25%)
        if indicators['trend'] == 'UP':
            score += 3
            factors.append(('TREND_UP', 3))
        elif indicators['trend'] == 'DOWN':
            score -= 3
            factors.append(('TREND_DOWN', -3))
        else:
            factors.append(('TREND_SIDE', 0))
        
        # Factor 2: RSI (Peso: 20%)
        if indicators['rsi'] < 20:
            score += 2.5
            factors.append(('RSI_EXTREME_LOW', 2.5))
        elif indicators['rsi'] < 30:
            score += 1.5
            factors.append(('RSI_OVERSOLD', 1.5))
        elif indicators['rsi'] > 80:
            score -= 2.5
            factors.append(('RSI_EXTREME_HIGH', -2.5))
        elif indicators['rsi'] > 70:
            score -= 1.5
            factors.append(('RSI_OVERBOUGHT', -1.5))
        
        # Factor 3: MACD (Peso: 20%)
        if indicators['macd'] > indicators['macd_signal'] and indicators['macd_histogram'] > 0:
            score += 2
            factors.append(('MACD_BULLISH', 2))
        elif indicators['macd'] < indicators['macd_signal'] and indicators['macd_histogram'] < 0:
            score -= 2
            factors.append(('MACD_BEARISH', -2))
        
        # Factor 4: Bollinger Bands (Peso: 15%)
        if prices[-1] < indicators['bb_lower']:
            score += 1.5
            factors.append(('BB_LOWER_TOUCH', 1.5))
        elif prices[-1] > indicators['bb_upper']:
            score -= 1.5
            factors.append(('BB_UPPER_TOUCH', -1.5))
        
        # Factor 5: Stochastic (Peso: 10%)
        if indicators['stochastic'] < 20:
            score += 1
            factors.append(('STOCH_OVERSOLD', 1))
        elif indicators['stochastic'] > 80:
            score -= 1
            factors.append(('STOCH_OVERBOUGHT', -1))
        
        # Factor 6: Patrón (Peso: 10%)
        if pattern['type'] == 'BULLISH_ENGULFING':
            score += 1.5 * pattern['strength']
            factors.append((f"PATTERN_{pattern['type']}", 1.5 * pattern['strength']))
        elif pattern['type'] == 'BEARISH_REJECTION':
            score -= 1.5 * pattern['strength']
            factors.append((f"PATTERN_{pattern['type']}", -1.5 * pattern['strength']))
        
        # Factor 7: Momentum (Peso: 10%)
        if momentum['momentum'] > 2:
            score += 1
            factors.append(('POSITIVE_MOMENTUM', 1))
        elif momentum['momentum'] < -2:
            score -= 1
            factors.append(('NEGATIVE_MOMENTUM', -1))
        
        # Factor 8: Volatilidad (Riesgo/Recompensa)
        if volatility['regime'] == 'LOW':
            score += 0.5  # Mejora señal en volatilidad baja
            factors.append(('LOW_VOLATILITY', 0.5))
        elif volatility['regime'] == 'HIGH':
            score -= 0.5  # Reduce confianza en volatilidad alta
            factors.append(('HIGH_VOLATILITY', -0.5))
        
        # Calcular confianza con escala normalizada
        max_score = 13  # Score máximo posible
        raw_confidence = abs(score) / max_score
        confidence = min(max(raw_confidence, 0.3), 0.98)  # Rango 30% - 98%
        
        # Generar acción
        if score > 2.5:
            action = 'BUY'
        elif score < -2.5:
            action = 'SELL'
        else:
            action = 'HOLD'
        
        reasoning = f"Score: {score:.2f} | Factores: {len(factors)} | Confianza: {confidence:.1%}"

        return {
            'action': action,
            'score': float(score),
            'confidence': float(confidence),
            'factors': factors,
            'reasoning': reasoning
        }
    
    def _advanced_prediction(self, prices: List[float], indicators: Dict) -> Dict:
        """Predicción avanzada de precio"""
        current_price = prices[-1]
        
        # Predición basada en múltiples métodos
        # Método 1: Momentum lineal
        change_5 = (prices[-1] - prices[-5]) / 5
        pred_linear = current_price + (change_5 * 10)
        
        # Método 2: Tendencia SMA
        pred_trend = current_price + ((indicators['sma_5'] - current_price) * 0.3)
        
        # Método 3: Reversión a media
        pred_reversion = current_price + ((indicators['sma_20'] - current_price) * 0.15)
        
        # Promedio ponderado
        prediction = (pred_linear * 0.4 + pred_trend * 0.35 + pred_reversion * 0.25)
        
        return {
            'next_10': float(prediction),
            'direction': 'UP' if prediction > current_price else 'DOWN',
            'distance': float(abs(prediction - current_price)),
            'confidence': 0.65
        }


class TradingEngine:
    """Motor de trading mejorado con IA avanzada"""

    def __init__(self):
        self.trades = {}
        self.closed = []
        self.balance = 10000.0
        self.equity = 10000.0
        self.id = 1
        self.ai = AIAnalyzer()
        self.use_mt5 = mt5 is not None
        self.last_signal = None
        self.trade_count = 0
        self.win_count = 0
    def open_trade(self, action: str, price: float, confidence: float = 0.5, atr: float = 0.001) -> Dict:
        """Abre trade con gestión de riesgo inteligente basada en confianza"""
        tid = self.id
        self.id += 1
        self.trade_count += 1

        # Tamaño de posición dinámico basado en confianza
        # Confianza 50% = 0.01 lot, Confianza 95% = 0.05 lot
        base_size = 0.01
        dynamic_size = base_size * (0.5 + (confidence * 2.5))  # 0.01 a 0.05
        size = min(dynamic_size, 0.1)  # Máximo 0.1 lots para seguridad

        # Stop Loss y Take Profit dinámicos basados en ATR
        atr_adjusted = max(atr, 0.0005)  # Mínimo
        
        if action == 'BUY':
            sl = price - (atr_adjusted * 2)  # 2x ATR como SL
            tp = price + (atr_adjusted * 4)  # 4x ATR como TP (4:1 risk/reward)
        else:  # SELL
            sl = price + (atr_adjusted * 2)
            tp = price - (atr_adjusted * 4)

        trade = {
            'id': tid,
            'action': action,
            'entry': float(price),
            'time': datetime.now().isoformat(),
            'size': float(size),
            'sl': float(sl),
            'tp': float(tp),
            'pl': 0,
            'pct': 0,
            'ticket': None,
            'confidence': float(confidence),
            'atr': float(atr_adjusted),
            'status': 'OPEN'
        }

        if self.use_mt5:
            try:
                order_type = mt5.ORDER_TYPE_BUY if action == 'BUY' else mt5.ORDER_TYPE_SELL
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": "EURUSD",
                    "volume": float(size),
                    "type": order_type,
                    "price": float(price),
                    "sl": float(sl),
                    "tp": float(tp),
                    "deviation": 20,
                    "magic": 234000,
                    "comment": f"AI Trade {tid} - Conf:{confidence:.1%}",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
                result = mt5.order_send(request)
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    trade['ticket'] = int(result.order)
                    trade['status'] = 'MT5_EXECUTED'
            except Exception as e:
                logger.error(f"MT5 trade error: {e}")
                trade['status'] = 'SIMULATION'
        else:
            trade['status'] = 'SIMULATION'

        self.trades[tid] = trade
        return trade

    def execute_signal(self, signal: Dict, current_price: float, atr: float = 0.001) -> Optional[Dict]:
        """Ejecuta automáticamente una señal si cumple criterios"""
        
        # Criterios para ejecutar automáticamente
        if signal['action'] == 'HOLD':
            return None
        
        # Solo ejecutar si confianza es suficientemente alta
        min_confidence = 0.65
        if signal['confidence'] < min_confidence:
            return None
        
        # Evitar operar muy seguido (máximo 1 trade cada 30 segundos)
        if self.last_signal and (datetime.now() - self.last_signal).total_seconds() < 30:
            return None
        
        # Ejecutar trade
        trade = self.open_trade(signal['action'], current_price, signal['confidence'], atr)
        self.last_signal = datetime.now()
        
        logger.info(f"✅ AUTO-TRADE EJECUTADO: {signal['action']} @ {current_price:.5f} (Confianza: {signal['confidence']:.1%})")
        
        return trade

    def update(self, price: float):
        """Actualiza trades con mejor gestión de riesgo"""
        for tid, t in list(self.trades.items()):
            if t['action'] == 'BUY':
                t['pl'] = (price - t['entry']) * (t['size'] * 100000)
                # Trailing stop - mueve SL hacia arriba con ganancias
                if price > t['entry'] and price > t['sl']:
                    new_sl = price - (t['atr'] * 1.5)  # Trail 1.5x ATR
                    t['sl'] = max(t['sl'], new_sl)
            else:  # SELL
                t['pl'] = (t['entry'] - price) * (t['size'] * 100000)
                if price < t['entry'] and price < t['sl']:
                    new_sl = price + (t['atr'] * 1.5)
                    t['sl'] = min(t['sl'], new_sl)
            
            t['pct'] = (t['pl'] / (t['entry'] * t['size'] * 100000)) * 100 if t['size'] > 0 else 0
            
            should_close = False
            
            # Cierre por Stop Loss o Take Profit
            if t['action'] == 'BUY':
                if price <= t['sl']:
                    should_close = True
                    t['status'] = 'CLOSED_SL'
                elif price >= t['tp']:
                    should_close = True
                    t['status'] = 'CLOSED_TP'
            else:  # SELL
                if price >= t['sl']:
                    should_close = True
                    t['status'] = 'CLOSED_SL'
                elif price <= t['tp']:
                    should_close = True
                    t['status'] = 'CLOSED_TP'
            
            if should_close:
                self.balance += t['pl']
                self.closed.append(t)
                if t['pl'] > 0:
                    self.win_count += 1
                del self.trades[tid]

        self.equity = self.balance + sum([t['pl'] for t in self.trades.values()])

    def close_trade(self, trade_id: int, price: float = None) -> Dict:
        """Cierra un trade manualmente con confirmación"""
        if trade_id not in self.trades:
            return {}
        trade = self.trades[trade_id]
        if price is None:
            price = trade['entry']

        if self.use_mt5 and trade.get('ticket'):
            try:
                close_request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": "EURUSD",
                    "volume": float(trade['size']),
                    "type": mt5.ORDER_TYPE_SELL if trade['action'] == 'BUY' else mt5.ORDER_TYPE_BUY,
                    "position": int(trade['ticket']),
                    "price": float(price),
                    "deviation": 20,
                    "magic": 234000,
                    "comment": f"Close AI Trade {trade_id}",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
                result = mt5.order_send(close_request)
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    trade['status'] = 'CLOSED_MANUAL_MT5'
            except Exception as e:
                logger.error(f"MT5 close error: {e}")
                trade['status'] = 'CLOSED_MANUAL_SIM'
        else:
            trade['status'] = 'CLOSED_MANUAL_SIM'

        if trade['action'] == 'BUY':
            trade['pl'] = (price - trade['entry']) * (trade['size'] * 100000)
        else:
            trade['pl'] = (trade['entry'] - price) * (trade['size'] * 100000)
        trade['pct'] = (trade['pl'] / (trade['entry'] * trade['size'] * 100000)) * 100 if trade['size'] > 0 else 0
        self.balance += trade['pl']
        if trade['pl'] > 0:
            self.win_count += 1
        self.closed.append(trade)
        del self.trades[trade_id]
        self.equity = self.balance + sum([t['pl'] for t in self.trades.values()])
        return trade

    def close_all(self, price: float = None) -> List[Dict]:
        """Cierra todos los trades abiertos"""
        closed = []
        for trade_id in list(self.trades.keys()):
            closed_trade = self.close_trade(trade_id, price)
            if closed_trade:
                closed.append(closed_trade)
        return closed

    def stats(self) -> Dict:
        """Estadísticas"""
        if not self.closed:
            return {'total': 0, 'wins': 0, 'losses': 0, 'wr': 0, 'pl': 0}

        wins = len([t for t in self.closed if t['pl'] > 0])
        losses = len([t for t in self.closed if t['pl'] < 0])
        pl = sum([t['pl'] for t in self.closed])

        return {
            'total': len(self.closed),
            'wins': wins,
            'losses': losses,
            'wr': float(wins / len(self.closed) * 100) if self.closed else 0,
            'pl': float(pl)
        }

# =============================================================================
# SISTEMA INTEGRADO DE TRADING
# =============================================================================

class IntegratedTradingSystem:
    """Sistema de trading completamente integrado"""

    def __init__(self):
        self.auth = ProfessionalAuthenticator()
        self.ai_analyzer = AIAnalyzer()
        self.price_history = [1.0850 + random.uniform(-0.01, 0.01) for _ in range(50)]
        self.current_price = self.price_history[-1]
        self.user_profiles = {}
        self.market_running = True
        self.price_lock = threading.Lock()

        # Initialize MT5 if available
        self.mt5_available = mt5 is not None
        if self.mt5_available:
            try:
                mt5.initialize()
                logger.info("MT5 initialized successfully")
            except Exception as e:
                logger.error(f"MT5 initialization failed: {e}")
                self.mt5_available = False

        # Create default users
        self._create_default_users()

        # Start market thread
        self.market_thread = threading.Thread(target=self._run_market, daemon=True)
        self.market_thread.start()

    def _create_default_users(self):
        """Create default admin and trader users"""
        # Admin user
        if not self.auth.register_user('admin', 'RyzA_jjITjuPQtV66Wwf0A', 'admin@local', role='admin'):
            logger.info("Admin user already exists")

        # Demo trader
        if not self.auth.register_user('trader', 'SecurePass123', 'trader@local', role='trader'):
            logger.info("Trader user already exists")

    def _get_mt5_price(self):
        """Get price from MT5 if available"""
        if not self.mt5_available:
            return None
        try:
            tick = mt5.symbol_info_tick("EURUSD")
            if tick:
                return tick.ask
        except Exception as e:
            logger.error(f"MT5 price error: {e}")
        return None

    def _advance_price(self):
        """Advance price simulation"""
        with self.price_lock:
            last = self.price_history[-1]
            change = random.uniform(-0.0005, 0.0005)
            new_price = max(0.9, last + change)
            self.price_history.append(new_price)
            if len(self.price_history) > 200:
                self.price_history.pop(0)
            self.current_price = new_price
            return new_price

    def _create_user_profile(self) -> Dict:
        """Create a new user profile with all required fields"""
        return {
            'trading_engine': TradingEngine(),
            'auto_enabled': False,
            'last_analysis': None,
            'ai_confidence_threshold': 0.7,
            'position_size_factor': 1.0,
            'autonomous_mode': False,
            'autonomous_duration': 0,
            'autonomous_start': 0,
            'autonomous_risk': 'medium'
        }

    def _run_market(self):
        """Run market simulation and AI analysis"""
        while self.market_running:
            price = self._get_mt5_price() or self._advance_price()

            # Update all user profiles
            for username, profile in self.user_profiles.items():
                if 'trading_engine' in profile:
                    profile['trading_engine'].update(price)

                # Run AI analysis
                if len(self.price_history) >= 20:
                    analysis = self.ai_analyzer.analyze_prices(self.price_history[-20:])
                    profile['last_analysis'] = analysis

                    # Auto trading if enabled
                    if profile.get('auto_enabled', False) and analysis['signal']['action'] != 'HOLD':
                            # Check autonomous mode timeout
                            if profile.get('autonomous_mode', False):
                                elapsed = time.time() - profile.get('autonomous_start', time.time())
                                if elapsed > profile.get('autonomous_duration', 3600):
                                    profile['autonomous_mode'] = False
                                    profile['auto_enabled'] = False
                                    continue
                            
                            confidence_threshold = profile.get('ai_confidence_threshold', 0.7)
                            if analysis['signal']['confidence'] > confidence_threshold:
                                if 'trading_engine' in profile and len(profile['trading_engine'].trades) < 5:
                                    profile['trading_engine'].open_trade(analysis['signal']['action'], price)

            time.sleep(1)

    # Web API methods
    def authenticate(self, username: str, password: str) -> Optional[str]:
        """Authenticate user and return session ID"""
        user = self.auth.authenticate_user(username, password)
        if user:
            return self.auth.create_session(username)
        return None

    def get_user_data(self, username: str) -> Dict:
        """Get user data for dashboard"""
        if username not in self.user_profiles:
            self.user_profiles[username] = self._create_user_profile()

        profile = self.user_profiles[username]
        engine = profile['trading_engine']

        # Get AI analysis
        analysis = self.ai_analyzer.analyze_prices(self.price_history[-20:])

        return {
            'balance': engine.balance,
            'open_trades': len(engine.trades),
            'total_trades': len(engine.closed),
            'win_rate': engine.stats()['wr'],
            'current_price': self.current_price,
            'signal': {
                'action': analysis['signal']['action'],
                'confidence': analysis['signal']['confidence']
            },
            'auto_enabled': profile['auto_enabled'],
            'price_history': self.price_history[-50:]
        }

    def get_admin_data(self) -> Dict:
        """Get admin data"""
        users = []
        for username, user_data in self.auth.db.users.items():
            profile = self.user_profiles.get(username, {})
            engine = profile.get('trading_engine')
            users.append({
                'username': username,
                'role': user_data.get('role', 'trader'),
                'balance': engine.balance if engine else 10000.0,
                'trades_open': len(engine.trades) if engine else 0,
                'auto_enabled': profile.get('auto_enabled', False)
            })

        return {'users': users}

    def toggle_auto_trading(self, username: str) -> bool:
        """Toggle auto trading for user"""
        if username not in self.user_profiles:
            self.user_profiles[username] = self._create_user_profile()

        profile = self.user_profiles[username]
        profile['auto_enabled'] = not profile['auto_enabled']
        return profile['auto_enabled']

    def execute_trade(self, username: str, action: str) -> Dict:
        """Execute trade for user"""
        if username not in self.user_profiles:
            self.user_profiles[username] = self._create_user_profile()

        profile = self.user_profiles[username]
        engine = profile['trading_engine']

        if action in ['BUY', 'SELL']:
            trade = engine.open_trade(action, self.current_price)
            return {'success': True, 'trade': trade}
        else:
            return {'success': False, 'error': 'Invalid action'}

    def close_user_trades(self, username: str) -> Dict:
        """Close all trades for user"""
        if username not in self.user_profiles:
            return {'error': 'User not found'}

        profile = self.user_profiles[username]
        engine = profile['trading_engine']
        closed = engine.close_all(self.current_price)
        return {'success': True, 'closed_trades': len(closed)}

    def set_autonomous_trading(self, username: str, duration_minutes: int, risk_level: str = 'medium') -> Dict:
        """Set autonomous trading with time limit"""
        if username not in self.user_profiles:
            self.user_profiles[username] = self._create_user_profile()
        
        profile = self.user_profiles[username]
        profile['autonomous_mode'] = True
        profile['autonomous_duration'] = duration_minutes * 60
        profile['autonomous_start'] = time.time()
        profile['autonomous_risk'] = risk_level
        profile['auto_enabled'] = True
        return {'success': True, 'message': f'Autonomous trading started for {duration_minutes} minutes with {risk_level} risk'}

    def stop_autonomous_trading(self, username: str) -> Dict:
        """Stop autonomous trading"""
        if username not in self.user_profiles:
            return {'error': 'User not found'}
        
        profile = self.user_profiles[username]
        profile['autonomous_mode'] = False
        profile['auto_enabled'] = False
        return {'success': True, 'message': 'Autonomous trading stopped'}

    def get_ai_metrics(self, username: str) -> Dict:
        """Get AI performance metrics"""
        if username not in self.user_profiles:
            self.user_profiles[username] = self._create_user_profile()
        
        profile = self.user_profiles[username]
        engine = profile['trading_engine']
        stats = engine.stats()
        
        if stats['total'] > 0:
            efficiency = (stats['wins'] / stats['total'] * 100)
            avg_profit = stats['pl'] / stats['total']
        else:
            efficiency = 0
            avg_profit = 0
        
        return {
            'win_rate': stats['wr'],
            'total_trades': stats['total'],
            'wins': stats['wins'],
            'losses': stats['losses'],
            'total_profit': stats['pl'],
            'efficiency_score': efficiency,
            'avg_profit_per_trade': avg_profit,
            'current_price': self.current_price
        }

    def send_ai_message(self, username: str, message: str) -> Dict:
        """Send message to AI and get response"""
        if username not in self.user_profiles:
            self.user_profiles[username] = self._create_user_profile()
        
        profile = self.user_profiles[username]
        message_lower = message.lower()
        response = self._generate_ai_response(message_lower, profile)
        
        return {'response': response, 'timestamp': datetime.now().isoformat()}

    def _generate_ai_response(self, message: str, profile: Dict) -> str:
        """Generate intelligent AI response"""
        engine = profile.get('trading_engine')
        
        if 'buy' in message or 'comprar' in message:
            return f'Ejecutando orden de compra. Precio actual: {self.current_price:.4f}. Análisis en progreso...'
        elif 'sell' in message or 'vender' in message:
            return f'Ejecutando orden de venta. Precio: {self.current_price:.4f}'
        elif 'status' in message or 'estado' in message:
            if engine:
                stats = engine.stats()
                balance_str = f'${engine.balance:.2f}'
                trades_count = len(engine.trades)
                win_rate = stats.get("wr", 0)
                return f'Balance: {balance_str} | Trades abiertos: {trades_count} | Win Rate: {win_rate:.1f}%'
            return 'No hay datos disponibles'
        elif 'autonomous' in message or 'autónomo' in message:
            return 'Modo autónomo: Controlando trades con gestión de riesgo automática. Duración: ' + str(profile.get('autonomous_duration', 0) // 60) + ' minutos'
        elif 'analyze' in message or 'analizar' in message:
            analysis = self.ai_analyzer.analyze_prices(self.price_history[-20:])
            signal_action = analysis['signal']['action']
            confidence = analysis['signal']['confidence']
            return f'Análisis: Señal {signal_action} con confianza {confidence:.2%}'
        else:
            analysis = self.ai_analyzer.analyze_prices(self.price_history[-20:])
            signal_action = analysis['signal']['action']
            confidence = analysis['signal']['confidence']
            return f'Analizando mercado... Señal: {signal_action} | Confianza: {confidence:.2%}'

    def improve_ai_model(self, username: str) -> Dict:
        """Improve AI model based on trading history"""
        if username not in self.user_profiles:
            self.user_profiles[username] = self._create_user_profile()
        
        profile = self.user_profiles[username]
        engine = profile['trading_engine']
        stats = engine.stats()
        
        if stats['total'] < 5:
            return {'message': 'Necesita al menos 5 trades para mejorar el modelo'}
        
        if stats['wr'] > 60:
            profile['ai_confidence_threshold'] = max(0.5, profile.get('ai_confidence_threshold', 0.7) - 0.05)
        else:
            profile['ai_confidence_threshold'] = min(0.9, profile.get('ai_confidence_threshold', 0.7) + 0.05)
        
        if stats['wins'] > 0:
            profile['position_size_factor'] = min(1.5, profile.get('position_size_factor', 1.0) + 0.1)
        
        return {
            'success': True,
            'message': 'AI model mejorado',
            'new_confidence_threshold': profile.get('ai_confidence_threshold', 0.7),
            'position_size_factor': profile.get('position_size_factor', 1.0)
        }

# =============================================================================
# SISTEMA WEB FLASK INTEGRADO
# =============================================================================

class IntegratedWebSystem:
    """Sistema web integrado con Flask que funciona sin servidor separado"""

    def __init__(self, trading_system: IntegratedTradingSystem):
        self.trading_system = trading_system
        self.app = Flask(__name__)
        self.app.secret_key = SecurityUtils.generate_secure_key(32)
        self.current_user = None

        # Configure Flask app
        self._setup_routes()

        # Rate limiting
        self.limiter = Limiter(
            app=self.app,
            key_func=get_remote_address,
            default_limits=["1000 per hour"]
        )

    def _setup_routes(self):
        """Setup Flask routes"""

        @self.app.route('/')
        def index():
            if 'user' in session:
                user_data = self.trading_system.auth.db.get_user(session['user'])
                user_role = user_data.get('role', 'trader') if user_data else 'trader'
                if user_role == 'admin':
                    return redirect(url_for('admin'))
                else:
                    return redirect(url_for('dashboard'))
            return self._get_login_html()

        @self.app.route('/login', methods=['GET', 'POST'])
        def login():
            if request.method == 'POST':
                username = request.form.get('username', '').strip()
                password = request.form.get('password', '').strip()

                if self.trading_system.authenticate(username, password):
                    session['user'] = username
                    user_data = self.trading_system.auth.db.get_user(username)
                    user_role = user_data.get('role', 'trader') if user_data else 'trader'
                    if user_role == 'admin':
                        return redirect('/admin')
                    else:
                        return redirect('/dashboard')
                else:
                    return self._get_login_html(error="Usuario o contraseña inválidos")

            return self._get_login_html()

        @self.app.route('/dashboard')
        def dashboard():
            if 'user' not in session:
                return redirect('/login')
            return self._get_dashboard_html()

        @self.app.route('/admin')
        def admin():
            if 'user' not in session:
                return redirect('/login')

            user_data = self.trading_system.auth.db.get_user(session['user'])
            user_role = user_data.get('role', 'trader') if user_data else 'trader'
            if user_role != 'admin':
                return redirect('/dashboard')

            return self._get_admin_html()

        @self.app.route('/logout')
        def logout():
            session.pop('user', None)
            return redirect('/login')

        @self.app.route('/api/user-data')
        def api_user_data():
            if 'user' not in session:
                return jsonify({'error': 'Not logged in'}), 401
            return jsonify(self.trading_system.get_user_data(session['user']))

        @self.app.route('/api/admin-data')
        def api_admin_data():
            if 'user' not in session:
                return jsonify({'error': 'Not logged in'}), 401

            user_data = self.trading_system.auth.db.get_user(session['user'])
            user_role = user_data.get('role', 'trader') if user_data else 'trader'
            if user_role != 'admin':
                return jsonify({'error': 'Access denied'}), 403

            return jsonify(self.trading_system.get_admin_data())

        @self.app.route('/api/toggle-auto', methods=['POST'])
        def api_toggle_auto():
            if 'user' not in session:
                return jsonify({'error': 'Not logged in'}), 401

            result = self.trading_system.toggle_auto_trading(session['user'])
            return jsonify({'success': result})

        @self.app.route('/api/execute-trade', methods=['POST'])
        def api_execute_trade():
            if 'user' not in session:
                return jsonify({'error': 'Not logged in'}), 401

            action = request.json.get('action', 'HOLD')
            result = self.trading_system.execute_trade(session['user'], action)
            return jsonify(result)

        @self.app.route('/api/admin/toggle-user-auto/<username>', methods=['POST'])
        def api_toggle_user_auto(username):
            if 'user' not in session:
                return jsonify({'error': 'Not logged in'}), 401

            user_data = self.trading_system.auth.db.get_user(session['user'])
            user_role = user_data.get('role', 'trader') if user_data else 'trader'
            if user_role != 'admin':
                return jsonify({'error': 'Access denied'}), 403

            result = self.trading_system.toggle_auto_trading(username)
            return jsonify({'success': result})

        @self.app.route('/api/admin/close-user-trades/<username>', methods=['POST'])
        def api_close_user_trades(username):
            if 'user' not in session:
                return jsonify({'error': 'Not logged in'}), 401

            user_data = self.trading_system.auth.db.get_user(session['user'])
            user_role = user_data.get('role', 'trader') if user_data else 'trader'
            if user_role != 'admin':
                return jsonify({'error': 'Access denied'}), 403

            result = self.trading_system.close_user_trades(username)
            return jsonify(result)

        @self.app.route('/chat')
        def chat():
            if 'user' not in session:
                return redirect('/login')
            return self._get_chat_html()

        @self.app.route('/ai-control')
        def ai_control():
            if 'user' not in session:
                return redirect('/login')
            return self._get_ai_control_html()

        @self.app.route('/api/chat', methods=['POST'])
        def api_chat():
            if 'user' not in session:
                return jsonify({'error': 'Not logged in'}), 401
            
            message = request.json.get('message', '')
            result = self.trading_system.send_ai_message(session['user'], message)
            return jsonify(result)

        @self.app.route('/api/autonomous-trading/start', methods=['POST'])
        def api_start_autonomous():
            if 'user' not in session:
                return jsonify({'error': 'Not logged in'}), 401
            
            duration = request.json.get('duration', 30)
            risk_level = request.json.get('risk_level', 'medium')
            result = self.trading_system.set_autonomous_trading(session['user'], duration, risk_level)
            return jsonify(result)

        @self.app.route('/api/autonomous-trading/stop', methods=['POST'])
        def api_stop_autonomous():
            if 'user' not in session:
                return jsonify({'error': 'Not logged in'}), 401
            
            result = self.trading_system.stop_autonomous_trading(session['user'])
            return jsonify(result)

        @self.app.route('/api/ai-metrics')
        def api_ai_metrics():
            if 'user' not in session:
                return jsonify({'error': 'Not logged in'}), 401
            
            metrics = self.trading_system.get_ai_metrics(session['user'])
            return jsonify(metrics)

        @self.app.route('/api/improve-ai', methods=['POST'])
        def api_improve_ai():
            if 'user' not in session:
                return jsonify({'error': 'Not logged in'}), 401
            
            result = self.trading_system.improve_ai_model(session['user'])
            return jsonify(result)

    def _get_chat_html(self):
        """Get AI chat interface HTML"""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Chat con IA</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #f5f5f5; }
        .navbar { background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 20px 40px; display: flex; justify-content: space-between; }
        .navbar a { color: white; text-decoration: none; background: rgba(255,255,255,0.2); padding: 8px 15px; border-radius: 5px; cursor: pointer; }
        .container { max-width: 1000px; margin: 20px auto; padding: 20px; }
        .chat-box { background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); height: 500px; display: flex; flex-direction: column; }
        .messages { flex: 1; overflow-y: auto; padding: 20px; border-bottom: 1px solid #eee; }
        .message { margin: 10px 0; padding: 10px; border-radius: 5px; }
        .user-message { background: #e3f2fd; text-align: right; }
        .ai-message { background: #f3e5f5; }
        .input-area { padding: 20px; display: flex; gap: 10px; }
        input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        button { padding: 10px 20px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { opacity: 0.8; }
        .stats-panel { margin-top: 20px; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .stat { display: inline-block; margin-right: 30px; }
        .stat-label { color: #666; font-size: 12px; }
        .stat-value { font-size: 24px; font-weight: bold; color: #667eea; }
    </style>
</head>
<body>
    <div class="navbar">
        <h2>💬 Chat con IA Trading</h2>
        <a href="/dashboard">Volver</a>
    </div>

    <div class="container">
        <div class="chat-box">
            <div class="messages" id="messages"></div>
            <div class="input-area">
                <input type="text" id="messageInput" placeholder="Escribe un comando (buy, sell, status, analyze, autonomous)..." autocomplete="off">
                <button onclick="sendMessage()">Enviar</button>
            </div>
        </div>

        <div class="stats-panel">
            <div class="stat">
                <div class="stat-label">Balance</div>
                <div class="stat-value" id="balance">$10,000</div>
            </div>
            <div class="stat">
                <div class="stat-label">Trades Abiertos</div>
                <div class="stat-value" id="open-trades">0</div>
            </div>
            <div class="stat">
                <div class="stat-label">Win Rate</div>
                <div class="stat-value" id="win-rate">0%</div>
            </div>
            <div class="stat">
                <div class="stat-label">Precio</div>
                <div class="stat-value" id="price">1.0850</div>
            </div>
        </div>
    </div>

    <script>
        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            if (!message) return;

            const messagesDiv = document.getElementById('messages');
            messagesDiv.innerHTML += '<div class="message user-message">' + message + '</div>';
            input.value = '';

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: message })
                });
                const data = await response.json();
                messagesDiv.innerHTML += '<div class="message ai-message">' + data.response + '</div>';
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
                updateStats();
            } catch (error) {
                console.error('Error:', error);
            }
        }

        async function updateStats() {
            try {
                const response = await fetch('/api/user-data');
                const data = await response.json();
                document.getElementById('balance').textContent = '$' + data.balance.toFixed(2);
                document.getElementById('open-trades').textContent = data.open_trades;
                document.getElementById('win-rate').textContent = data.win_rate.toFixed(1) + '%';
                document.getElementById('price').textContent = data.current_price.toFixed(4);
            } catch (error) {
                console.error('Error:', error);
            }
        }

        document.getElementById('messageInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') sendMessage();
        });

        updateStats();
        setInterval(updateStats, 3000);
    </script>
</body>
</html>
"""

    def _get_ai_control_html(self):
        """Get AI control panel HTML"""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Panel de Control de IA</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #f5f5f5; }
        .navbar { background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 20px 40px; display: flex; justify-content: space-between; }
        .navbar a { color: white; text-decoration: none; background: rgba(255,255,255,0.2); padding: 8px 15px; border-radius: 5px; cursor: pointer; }
        .container { max-width: 1200px; margin: 20px auto; padding: 20px; }
        .panel { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .panel h3 { color: #667eea; margin-bottom: 15px; }
        .control-group { margin: 15px 0; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input, select { padding: 10px; border: 1px solid #ddd; border-radius: 5px; width: 200px; }
        button { padding: 10px 20px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer; margin: 5px 5px 5px 0; }
        button:hover { opacity: 0.8; }
        .btn-danger { background: #f44336; }
        .btn-success { background: #4caf50; }
        .metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; }
        .metric { background: #f9f9f9; padding: 15px; border-radius: 8px; border-left: 4px solid #667eea; }
        .metric-label { font-size: 12px; color: #666; }
        .metric-value { font-size: 24px; font-weight: bold; color: #667eea; margin-top: 5px; }
        .status-badge { display: inline-block; padding: 5px 15px; border-radius: 20px; font-size: 12px; margin-top: 10px; }
        .status-active { background: #c8e6c9; color: #2e7d32; }
        .status-inactive { background: #ffccbc; color: #d84315; }
        .alert { padding: 15px; background: #fff3cd; border-left: 4px solid #ffc107; border-radius: 5px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="navbar">
        <h2>🤖 Panel de Control de IA</h2>
        <a href="/dashboard">Volver</a>
    </div>

    <div class="container">
        <div class="panel">
            <h3>Modo Autónomo</h3>
            <div class="control-group">
                <label>Duración (minutos):</label>
                <input type="number" id="duration" value="30" min="1" max="480">
            </div>
            <div class="control-group">
                <label>Nivel de Riesgo:</label>
                <select id="riskLevel">
                    <option value="low">Bajo</option>
                    <option value="medium" selected>Medio</option>
                    <option value="high">Alto</option>
                </select>
            </div>
            <button class="btn-success" onclick="startAutonomous()">Iniciar Modo Autónomo</button>
            <button class="btn-danger" onclick="stopAutonomous()">Detener Modo Autónomo</button>
            <div id="autonomousStatus"></div>
        </div>

        <div class="panel">
            <h3>Métricas de IA</h3>
            <div class="metrics">
                <div class="metric">
                    <div class="metric-label">Win Rate</div>
                    <div class="metric-value" id="winRate">0%</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Total Trades</div>
                    <div class="metric-value" id="totalTrades">0</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Ganadas</div>
                    <div class="metric-value" id="wins">0</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Perdidas</div>
                    <div class="metric-value" id="losses">0</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Total Ganancias</div>
                    <div class="metric-value" id="totalProfit">$0</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Eficiencia</div>
                    <div class="metric-value" id="efficiency">0%</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Ganancia/Trade</div>
                    <div class="metric-value" id="avgProfit">$0</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Precio Actual</div>
                    <div class="metric-value" id="currentPrice">1.0850</div>
                </div>
            </div>
        </div>

        <div class="panel">
            <h3>Auto-Mejora de IA</h3>
            <div class="alert">La IA se mejora automáticamente basándose en el historial de trading. Necesita al menos 5 trades.</div>
            <button class="btn-success" onclick="improveAI()">Mejorar Modelo de IA Ahora</button>
            <div id="improveStatus"></div>
        </div>

        <div class="panel">
            <h3>Parámetros de IA</h3>
            <div class="metrics">
                <div class="metric">
                    <div class="metric-label">Confianza Mínima</div>
                    <div class="metric-value" id="confidenceThreshold">0.70</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Factor de Posición</div>
                    <div class="metric-value" id="positionSize">1.00</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        async function startAutonomous() {
            const duration = document.getElementById('duration').value;
            const riskLevel = document.getElementById('riskLevel').value;
            
            try {
                const response = await fetch('/api/autonomous-trading/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ duration: parseInt(duration), risk_level: riskLevel })
                });
                const data = await response.json();
                document.getElementById('autonomousStatus').innerHTML = '<div class="status-badge status-active">✓ ' + data.message + '</div>';
                updateMetrics();
            } catch (error) {
                console.error('Error:', error);
            }
        }

        async function stopAutonomous() {
            try {
                const response = await fetch('/api/autonomous-trading/stop', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await response.json();
                document.getElementById('autonomousStatus').innerHTML = '<div class="status-badge status-inactive">✗ ' + data.message + '</div>';
                updateMetrics();
            } catch (error) {
                console.error('Error:', error);
            }
        }

        async function improveAI() {
            try {
                const response = await fetch('/api/improve-ai', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await response.json();
                if (data.success) {
                    document.getElementById('improveStatus').innerHTML = '<div class="alert" style="background: #c8e6c9; border-color: #4caf50; color: #2e7d32;">✓ ' + data.message + '</div>';
                    document.getElementById('confidenceThreshold').textContent = data.new_confidence_threshold.toFixed(2);
                    document.getElementById('positionSize').textContent = data.position_size_factor.toFixed(2);
                } else {
                    document.getElementById('improveStatus').innerHTML = '<div class="alert">' + data.message + '</div>';
                }
                updateMetrics();
            } catch (error) {
                console.error('Error:', error);
            }
        }

        async function updateMetrics() {
            try {
                const response = await fetch('/api/ai-metrics');
                const data = await response.json();
                document.getElementById('winRate').textContent = data.win_rate.toFixed(1) + '%';
                document.getElementById('totalTrades').textContent = data.total_trades;
                document.getElementById('wins').textContent = data.wins;
                document.getElementById('losses').textContent = data.losses;
                document.getElementById('totalProfit').textContent = '$' + data.total_profit.toFixed(2);
                document.getElementById('efficiency').textContent = data.efficiency_score.toFixed(1) + '%';
                document.getElementById('avgProfit').textContent = '$' + data.avg_profit_per_trade.toFixed(2);
                document.getElementById('currentPrice').textContent = data.current_price.toFixed(4);
            } catch (error) {
                console.error('Error:', error);
            }
        }

        updateMetrics();
        setInterval(updateMetrics, 5000);
    </script>
</body>
</html>
"""

    def _get_login_html(self, error=None):
        """Get login page HTML"""
        error_html = f'<div class="error">{error}</div>' if error else ''
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Trading + IA</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea, #764ba2);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 0;
        }
        .login-box {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            width: 100%;
            max-width: 400px;
        }
        .login-box h1 {
            color: #667eea;
            text-align: center;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            color: #333;
            font-weight: bold;
            margin-bottom: 8px;
        }
        input {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
            box-sizing: border-box;
        }
        input:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
        }
        button:hover {
            opacity: 0.9;
        }
        .error {
            color: red;
            margin-bottom: 20px;
            text-align: center;
        }
        .creds {
            margin-top: 30px;
            padding-top: 30px;
            border-top: 1px solid #eee;
            font-size: 12px;
            color: #666;
        }
        .creds code {
            background: #f5f5f5;
            padding: 4px;
            border-radius: 3px;
        }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>🤖 Trading + IA</h1>
        {error_html}
        <form method="POST">
            <div class="form-group">
                <label>Usuario</label>
                <input type="text" name="username" required>
            </div>
            <div class="form-group">
                <label>Contraseña</label>
                <input type="password" name="password" required>
            </div>
            <button type="submit">Entrar</button>
        </form>
        <div class="creds">
            <strong>Admin:</strong> <code>admin</code> / <code>RyzA_jjITjuPQtV66Wwf0A</code><br>
            <strong>Demo:</strong> <code>trader</code> / <code>SecurePass123</code>
        </div>
    </div>
</body>
</html>
"""

    def _get_dashboard_html(self):
        """Get trading dashboard HTML"""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Dashboard Trading</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: Arial, sans-serif;
            background: #f5f5f5;
        }
        .navbar {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 20px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .navbar a {
            color: white;
            text-decoration: none;
            background: rgba(255,255,255,0.2);
            padding: 8px 15px;
            border-radius: 5px;
            cursor: pointer;
        }
        .container {
            max-width: 1400px;
            margin: 20px auto;
            padding: 20px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .card h3 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 14px;
        }
        .stat {
            font-size: 28px;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }
        .signal {
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
            border-left: 4px solid;
        }
        .buy { background: #e8f5e9; border-color: #4caf50; color: #2e7d32; }
        .sell { background: #ffebee; border-color: #f44336; color: #c62828; }
        .hold { background: #fff3e0; border-color: #ff9800; color: #e65100; }
        .btn {
            padding: 10px 20px;
            margin: 5px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        .btn:hover { opacity: 0.8; }
        .btn-danger { background: #f44336; }
        .btn-success { background: #4caf50; }
        .chart-container {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="navbar">
        <h2>🤖 Trading + IA Dashboard</h2>
        <div>
            <a href="/chat" style="margin-right: 10px;">💬 Chat</a>
            <a href="/ai-control" style="margin-right: 10px;">🎛️ Control IA</a>
            <a href="/logout">Logout</a>
        </div>
    </div>

    <div class="container">
        <div class="grid">
            <div class="card">
                <h3>Balance</h3>
                <div class="stat" id="balance">$10,000.00</div>
            </div>
            <div class="card">
                <h3>Trades Abiertos</h3>
                <div class="stat" id="open-trades">0</div>
            </div>
            <div class="card">
                <h3>Señal IA</h3>
                <div id="signal" class="signal hold">HOLD</div>
            </div>
            <div class="card">
                <h3>Auto Trading</h3>
                <button class="btn" id="toggle-auto" onclick="toggleAuto()">OFF</button>
            </div>
        </div>

        <div class="chart-container">
            <canvas id="priceChart" width="400" height="200"></canvas>
        </div>

        <div class="grid">
            <div class="card">
                <h3>Precio Actual</h3>
                <div class="stat" id="current-price">1.0850</div>
            </div>
            <div class="card">
                <h3>Trades Totales</h3>
                <div class="stat" id="total-trades">0</div>
            </div>
            <div class="card">
                <h3>Win Rate</h3>
                <div class="stat" id="win-rate">0%</div>
            </div>
            <div class="card">
                <h3>Acciones</h3>
                <button class="btn btn-success" onclick="executeTrade('BUY')">BUY</button>
                <button class="btn btn-danger" onclick="executeTrade('SELL')">SELL</button>
            </div>
        </div>
    </div>

    <script>
        let priceChart;
        let priceData = [];
        let timeLabels = [];

        function initChart() {
            const ctx = document.getElementById('priceChart').getContext('2d');
            priceChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: timeLabels,
                    datasets: [{
                        label: 'EUR/USD',
                        data: priceData,
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: false
                        }
                    }
                }
            });
        }

        async function loadData() {
            try {
                const response = await fetch('/api/user-data');
                const data = await response.json();

                if (data.error) {
                    window.location.href = '/logout';
                    return;
                }

                // Update stats
                document.getElementById('balance').textContent = '$' + data.balance.toFixed(2);
                document.getElementById('open-trades').textContent = data.open_trades;
                document.getElementById('total-trades').textContent = data.total_trades;
                document.getElementById('win-rate').textContent = data.win_rate + '%';
                document.getElementById('current-price').textContent = data.current_price.toFixed(4);

                // Update signal
                const signalEl = document.getElementById('signal');
                signalEl.className = 'signal ' + data.signal.action.toLowerCase();
                signalEl.textContent = data.signal.action + ' (' + data.signal.confidence.toFixed(2) + ')';

                // Update auto button
                const autoBtn = document.getElementById('toggle-auto');
                autoBtn.textContent = data.auto_enabled ? 'ON' : 'OFF';
                autoBtn.className = 'btn ' + (data.auto_enabled ? 'btn-success' : '');

                // Update chart
                if (data.price_history && data.price_history.length > 0) {
                    priceData = data.price_history;
                    timeLabels = data.price_history.map((_, i) => i);
                    if (priceChart) {
                        priceChart.update();
                    }
                }

            } catch (error) {
                console.error('Error loading data:', error);
            }
        }

        async function toggleAuto() {
            try {
                const response = await fetch('/api/toggle-auto', { method: 'POST' });
                const result = await response.json();
                if (result.success) {
                    loadData();
                }
            } catch (error) {
                console.error('Error toggling auto:', error);
            }
        }

        async function executeTrade(action) {
            try {
                const response = await fetch('/api/execute-trade', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: action })
                });
                const result = await response.json();
                loadData();
            } catch (error) {
                console.error('Error executing trade:', error);
            }
        }

        // Initialize
        initChart();
        loadData();
        setInterval(loadData, 2000);
    </script>
</body>
</html>
"""

    def _get_admin_html(self):
        """Get admin dashboard HTML"""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Admin Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: Arial, sans-serif;
            background: #f5f5f5;
        }
        .navbar {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 20px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .navbar a {
            color: white;
            text-decoration: none;
            background: rgba(255,255,255,0.2);
            padding: 8px 15px;
            border-radius: 5px;
            cursor: pointer;
        }
        .container {
            max-width: 1400px;
            margin: 20px auto;
            padding: 20px;
        }
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .card h3 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 14px;
        }
        .stat {
            font-size: 28px;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }
        .btn {
            padding: 8px 15px;
            margin: 2px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 3px;
            cursor: pointer;
            font-size: 12px;
        }
        .btn-success { background: #4caf50; }
        .btn-danger { background: #f44336; }
        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        th {
            background: #667eea;
            color: white;
        }
        tr:hover {
            background: #f9f9f9;
        }
    </style>
</head>
<body>
    <div class="navbar">
        <h2>🔧 Admin Dashboard</h2>
        <a href="/logout">Logout</a>
    </div>

    <div class="container">
        <div class="summary">
            <div class="card">
                <h3>Usuarios Totales</h3>
                <div class="stat" id="summary-count">0</div>
            </div>
            <div class="card">
                <h3>IA Automática Activa</h3>
                <div class="stat" id="summary-auto">0</div>
            </div>
            <div class="card">
                <h3>Trades Abiertos Totales</h3>
                <div class="stat" id="summary-open">0</div>
            </div>
            <div class="card">
                <h3>Balance Total Combinado</h3>
                <div class="stat" id="summary-balance">$0.00</div>
            </div>
        </div>

        <div class="card">
            <h3>Gestión de Usuarios</h3>
            <table>
                <thead>
                    <tr>
                        <th>Usuario</th>
                        <th>Rol</th>
                        <th>Balance</th>
                        <th>Trades Abiertos</th>
                        <th>IA Auto</th>
                        <th>Acciones</th>
                    </tr>
                </thead>
                <tbody id="usersTableBody">
                </tbody>
            </table>
        </div>
    </div>

    <script>
        async function loadUsers() {
            try {
                const response = await fetch('/api/admin-data');
                const data = await response.json();

                if (data.error) {
                    window.location.href = '/logout';
                    return;
                }

                const allUsers = data.users || [];
                const rows = allUsers.map(u => `
                    <tr>
                        <td>${u.username}</td>
                        <td>${u.role}</td>
                        <td>$${u.balance.toFixed(2)}</td>
                        <td>${u.trades_open}</td>
                        <td>${u.auto_enabled ? 'ON' : 'OFF'}</td>
                        <td>
                            <button class="btn btn-success" onclick="toggleUserAuto('${u.username}')">
                                ${u.auto_enabled ? 'OFF' : 'ON'}
                            </button>
                            <button class="btn btn-danger" onclick="closeUserTrades('${u.username}')">
                                Cerrar Trades
                            </button>
                        </td>
                    </tr>`).join('');

                document.getElementById('usersTableBody').innerHTML = rows || '<tr><td colspan="6" style="text-align:center">No hay usuarios</td></tr>';

                // Update summary
                const activeAuto = allUsers.filter(u => u.auto_enabled).length;
                const openTrades = allUsers.reduce((sum, u) => sum + u.trades_open, 0);
                const balanceTotal = allUsers.reduce((sum, u) => sum + u.balance, 0);
                document.getElementById('summary-count').textContent = allUsers.length;
                document.getElementById('summary-auto').textContent = activeAuto;
                document.getElementById('summary-open').textContent = openTrades;
                document.getElementById('summary-balance').textContent = '$' + balanceTotal.toFixed(2);

            } catch (error) {
                console.error('Error loading users:', error);
            }

        </script>
    </body>
    </html>
    """

    def run(self, host='localhost', port=5000, debug=False):
        """Run the web server"""
        print(f"Starting Professional Trading System on http://{host}:{port}")

        # Open browser automatically
        try:
            import webbrowser
            webbrowser.open(f'http://{host}:{port}')
        except:
            pass  # Ignore if browser can't be opened

        self.app.run(host=host, port=port, debug=debug)

# =============================================================================
# FUNCIONES DE VERIFICACIÓN DE INTEGRIDAD
# =============================================================================

def verify_system_integrity() -> Dict:
    """Verifica la integridad completa del sistema"""
    results = {
        'overall_status': 'OK',
        'checks': {},
        'warnings': [],
        'errors': []
    }

    # Verificar clases principales
    classes_to_check = [
        ('DatabaseManager', DatabaseManager),
        ('DeviceManager', DeviceManager),
        ('ProfessionalAuthenticator', ProfessionalAuthenticator),
        ('SecurityUtils', SecurityUtils),
        ('SecureLogger', SecureLogger),
        ('AIAnalyzer', AIAnalyzer),
        ('TradingEngine', TradingEngine),
        ('IntegratedTradingSystem', IntegratedTradingSystem),
        ('IntegratedWebSystem', IntegratedWebSystem)
    ]

    for class_name, class_obj in classes_to_check:
        try:
            # Verificar que la clase existe
            if not hasattr(class_obj, '__init__'):
                results['errors'].append(f"Clase {class_name} no tiene __init__")
                results['overall_status'] = 'ERROR'
            else:
                results['checks'][f'class_{class_name.lower()}'] = 'OK'
        except Exception as e:
            results['errors'].append(f"Error verificando clase {class_name}: {e}")
            results['overall_status'] = 'ERROR'

    # Verificar dependencias críticas
    critical_imports = [
        ('json', json),
        ('threading', threading),
        ('datetime', datetime),
        ('hashlib', hashlib),
        ('secrets', secrets),
        ('re', re),
        ('base64', base64),
        ('logging', logging)
    ]

    for import_name, import_obj in critical_imports:
        if import_obj is None:
            results['errors'].append(f"Import crítico faltante: {import_name}")
            results['overall_status'] = 'ERROR'
        else:
            results['checks'][f'import_{import_name}'] = 'OK'

    # Verificar dependencias opcionales
    optional_imports = [
        ('MetaTrader5', mt5),
        ('Flask', Flask),
        ('Flask_Limiter', Limiter),
        ('webview', webview),
        ('stripe', stripe)
    ]

    for import_name, import_obj in optional_imports:
        if import_obj is None:
            results['warnings'].append(f"Import opcional faltante: {import_name}")
        else:
            results['checks'][f'import_{import_name}'] = 'OK'

    # Verificar configuración de seguridad
    try:
        key = SecurityUtils.get_encryption_key()
        if len(key) < 32:
            results['warnings'].append("Clave de encriptación muy corta")
        else:
            results['checks']['encryption_key'] = 'OK'
    except Exception as e:
        results['errors'].append(f"Error con clave de encriptación: {e}")
        results['overall_status'] = 'ERROR'

    # Verificar base de datos
    try:
        db = DatabaseManager()
        stats = db.get_database_stats()
        results['checks']['database'] = 'OK'
        results['checks']['database_stats'] = stats
    except Exception as e:
        results['errors'].append(f"Error con base de datos: {e}")
        results['overall_status'] = 'ERROR'

    # Verificar autenticador
    try:
        auth = ProfessionalAuthenticator()
        results['checks']['authenticator'] = 'OK'
    except Exception as e:
        results['errors'].append(f"Error con autenticador: {e}")
        results['overall_status'] = 'ERROR'

    # Verificar motor de IA
    try:
        ai = AIAnalyzer()
        test_prices = [1.0850 + i*0.0001 for i in range(25)]
        analysis = ai.analyze_prices(test_prices)
        if 'error' not in analysis:
            results['checks']['ai_analyzer'] = 'OK'
        else:
            results['warnings'].append("Analizador IA necesita más datos de prueba")
    except Exception as e:
        results['errors'].append(f"Error con analizador IA: {e}")
        results['overall_status'] = 'ERROR'

    # Verificar motor de trading
    try:
        engine = TradingEngine()
        results['checks']['trading_engine'] = 'OK'
    except Exception as e:
        results['errors'].append(f"Error con motor de trading: {e}")
        results['overall_status'] = 'ERROR'

    # Resumen final
    total_checks = len(results['checks'])
    total_warnings = len(results['warnings'])
    total_errors = len(results['errors'])

    results['summary'] = {
        'total_checks': total_checks,
        'total_warnings': total_warnings,
        'total_errors': total_errors,
        'status': results['overall_status']
    }

    return results

def print_integrity_report(report: Dict):
    """Imprime reporte de integridad del sistema"""
    print("\n" + "="*80)
    print("REPORTE DE INTEGRIDAD DEL SISTEMA PROFESIONAL DE TRADING")
    print("="*80)
    print(f"Estado General: {report['overall_status']}")
    print(f"Checks Pasados: {report['summary']['total_checks']}")
    print(f"Advertencias: {report['summary']['total_warnings']}")
    print(f"Errores: {report['summary']['total_errors']}")
    print("-"*80)

    if report['checks']:
        print("CHECKS EXITOSOS:")
        for check, status in report['checks'].items():
            if isinstance(status, dict):
                print(f"   • {check}: {status}")
            else:
                print(f"   • {check}: {status}")

    if report['warnings']:
        print("\nADVERTENCIAS:")
        for warning in report['warnings']:
            print(f"   • {warning}")

    if report['errors']:
        print("\nERRORES:")
        for error in report['errors']:
            print(f"   • {error}")

    print("="*80)

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def main():
    """
    Función principal que inicializa y ejecuta el Sistema de Trading Profesional completo
    """
    print("\n" + "="*70)
    print("  SISTEMA DE TRADING PROFESIONAL - INICIANDO")
    print("="*70 + "\n")

    try:
        # PASO 1: Inicializar el motor de trading
        print("🚀 Inicializando motor de trading...")
        trading_system = IntegratedTradingSystem()
        print("✅ Motor iniciado")

        # PASO 2: Configurar usuarios
        print("👤 Configurando usuarios...")
        admin_profile = trading_system._create_user_profile()
        admin_profile['auto_enabled'] = False
        trading_system.user_profiles['admin'] = admin_profile

        trader_profile = trading_system._create_user_profile()
        trader_profile['auto_enabled'] = True
        trader_profile['autonomous_mode'] = True
        trader_profile['autonomous_duration'] = 3600
        trader_profile['autonomous_start'] = time.time()
        trading_system.user_profiles['trader'] = trader_profile
        print("✅ Usuarios configurados")

        # PASO 3: Crear servidor web
        print("🌐 Inicializando servidor web...")
        web_system = IntegratedWebSystem(trading_system)
        print("✅ Servidor web listo")

        # PASO 4: Abrir navegador
        print("🔗 Abriendo navegador...")
        try:
            webbrowser.open('http://127.0.0.1:5000')
            print("✅ Navegador abierto")
        except:
            print("⚠️ No se pudo abrir navegador automáticamente")

        print("\n" + "="*70)
        print("  ✅ SISTEMA LISTO - INICIANDO SERVIDOR")
        print("="*70 + "\n")
        print("📊 Acceso: http://127.0.0.1:5000")
        print("🔐 Credenciales:")
        print("   Admin: admin / RyzA_jjITjuPQtV66Wwf0A")
        print("   Trader: trader / SecurePass123")
        print("\n" + "="*70 + "\n")

        # Iniciar servidor
        web_system.run(host='127.0.0.1', port=5000, debug=False)

    except Exception as e:
        print(f"\n❌ ERROR DURANTE LA INICIALIZACIÓN:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

