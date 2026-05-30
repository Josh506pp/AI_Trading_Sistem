#!/usr/bin/env python3
"""
PROFESSIONAL TRADING SYSTEM - Database Manager
Gestor de Base de Datos para Control de Clientes y Dispositivos
"""

import sqlite3
import json
import hashlib
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
import logging

class DatabaseManager:
    """Gestor de base de datos con control de clientes y dispositivos"""

    def __init__(self, db_path: str = "trading_system.db"):
        """Inicializar gestor de base de datos"""
        self.db_path = db_path
        self.logger = logging.getLogger("DatabaseManager")
        self._initialize_database()

    def _connect(self):
        """Crear conexión SQLite con timeout y soporte de subprocesos."""
        conn = sqlite3.connect(self.db_path, timeout=10, check_same_thread=False)
        # Habilitar WAL mode para mejor manejo de concurrencia
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=1000")
        return conn

    def _execute_with_retry(self, query: str, params: Tuple = (), max_retries: int = 3) -> Optional[List]:
        """Ejecutar consulta con reintentos automáticos para database locked"""
        for attempt in range(max_retries):
            try:
                conn = self._connect()
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                result = cursor.fetchall()
                conn.close()
                return result
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 0.1  # Exponential backoff: 0.1s, 0.2s, 0.4s
                    self.logger.warning(f"⚠️ DB locked, reintentando en {wait_time}s (intento {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    raise
        return []

    def _initialize_database(self):
        """Inicializar tablas de base de datos"""
        try:
            conn = self._connect()
            cursor = conn.cursor()

            # Tabla de clientes
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    subscription_type TEXT DEFAULT 'free',
                    payment_status TEXT DEFAULT 'pending',
                    payment_amount REAL DEFAULT 0,
                    payment_date TIMESTAMP,
                    payment_method TEXT,
                    stripe_customer_id TEXT UNIQUE,
                    is_active BOOLEAN DEFAULT 1,
                    last_login TIMESTAMP,
                    role TEXT DEFAULT 'trader'
                )
            ''')

            # Tabla de dispositivos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    device_fingerprint TEXT NOT NULL UNIQUE,
                    device_name TEXT,
                    device_type TEXT,
                    ip_address TEXT NOT NULL,
                    os TEXT,
                    browser TEXT,
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    is_primary BOOLEAN DEFAULT 0,
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                )
            ''')

            # Tabla de sesiones
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    device_id INTEGER NOT NULL,
                    session_token TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    last_activity TIMESTAMP,
                    ip_address TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (customer_id) REFERENCES customers(id),
                    FOREIGN KEY (device_id) REFERENCES devices(id)
                )
            ''')

            # Tabla de pagos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT DEFAULT 'USD',
                    status TEXT DEFAULT 'pending',
                    payment_method TEXT,
                    stripe_payment_id TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    receipt_url TEXT,
                    description TEXT,
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                )
            ''')

            # Tabla de auditoría
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER,
                    action TEXT NOT NULL,
                    details TEXT,
                    ip_address TEXT,
                    device_fingerprint TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT,
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                )
            ''')

            # Tabla de accesos denegados
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS blocked_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER,
                    ip_address TEXT,
                    device_fingerprint TEXT,
                    reason TEXT,
                    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                )
            ''')

            conn.commit()
            conn.close()
            self.logger.info("✅ Base de datos inicializada correctamente")
        except Exception as e:
            self.logger.error(f"❌ Error inicializando base de datos: {e}")
            raise

    def register_customer(self, username: str, email: str, password: str,
                         subscription_type: str = 'free') -> Tuple[bool, str]:
        """Registrar nuevo cliente"""
        try:
            password_hash = hashlib.sha256(password.encode()).hexdigest()

            conn = self._connect()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO customers (username, email, password_hash, subscription_type)
                VALUES (?, ?, ?, ?)
            ''', (username, email, password_hash, subscription_type))

            customer_id = cursor.lastrowid
            conn.commit()
            conn.close()

            self.logger.info(f"✅ Cliente registrado: {username}")
            self._log_audit(customer_id, "CUSTOMER_REGISTERED",
                           f"Nuevo cliente: {email}", "registered")
            return True, f"Cliente {username} registrado exitosamente"

        except sqlite3.IntegrityError as e:
            if "username" in str(e):
                return False, "El nombre de usuario ya existe"
            elif "email" in str(e):
                return False, "El correo ya está registrado"
            else:
                return False, "Error de registro"
        except Exception as e:
            self.logger.error(f"❌ Error registrando cliente: {e}")
            return False, str(e)

    def verify_customer_password(self, username: str, password: str) -> Tuple[bool, Optional[int], str]:
        """Verificar contraseña del cliente"""
        try:
            password_hash = hashlib.sha256(password.encode()).hexdigest()

            conn = self._connect()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, is_active FROM customers WHERE username = ? AND password_hash = ?
            ''', (username, password_hash))

            result = cursor.fetchone()
            conn.close()

            if result:
                customer_id, is_active = result
                if not is_active:
                    return False, None, "Cuenta desactivada"
                return True, customer_id, "Contraseña correcta"
            else:
                return False, None, "Usuario o contraseña incorrectos"

        except Exception as e:
            self.logger.error(f"❌ Error verificando contraseña: {e}")
            return False, None, str(e)

    def register_device(self, customer_id: int, device_fingerprint: str,
                       device_name: str, device_type: str, ip_address: str,
                       os: str = "", browser: str = "", is_primary: bool = False) -> Tuple[bool, int]:
        """Registrar dispositivo del cliente"""
        for attempt in range(3):
            try:
                conn = self._connect()
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT INTO devices (customer_id, device_fingerprint, device_name,
                                        device_type, ip_address, os, browser, is_primary)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (customer_id, device_fingerprint, device_name, device_type,
                      ip_address, os, browser, is_primary))

                device_id = cursor.lastrowid
                conn.commit()
                conn.close()

                self.logger.info(f"✅ Dispositivo registrado: {device_name} (ID: {device_id})")
                self._log_audit(customer_id, "DEVICE_REGISTERED",
                               f"Dispositivo: {device_name} - IP: {ip_address}", "success")
                return True, device_id

            except sqlite3.IntegrityError:
                # El dispositivo ya está registrado
                try:
                    conn = self._connect()
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT id FROM devices WHERE device_fingerprint = ?
                    ''', (device_fingerprint,))
                    result = cursor.fetchone()
                    conn.close()
                    if result:
                        return True, result[0]
                except:
                    pass
                return False, -1
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < 2:
                    wait_time = (2 ** attempt) * 0.1
                    self.logger.warning(f"⚠️ DB locked al registrar dispositivo, reintentando en {wait_time}s")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"❌ Error registrando dispositivo: {e}")
                    return False, -1
            except Exception as e:
                self.logger.error(f"❌ Error registrando dispositivo: {e}")
                return False, -1
        
        return False, -1

    def validate_device_access(self, customer_id: int, device_fingerprint: str,
                               ip_address: str) -> Tuple[bool, str]:
        """Validar acceso desde dispositivo - SOLO UN DISPOSITIVO ACTIVO A LA VEZ"""
        try:
            conn = self._connect()
            cursor = conn.cursor()

            # Verificar si el cliente tiene una sesión activa en OTRO dispositivo
            cursor.execute('''
                SELECT s.id, d.device_fingerprint, d.device_name, s.expires_at
                FROM sessions s
                JOIN devices d ON s.device_id = d.id
                WHERE s.customer_id = ? AND s.is_active = 1 AND s.expires_at > datetime('now')
            ''', (customer_id,))

            active_session = cursor.fetchone()

            if active_session:
                session_id, active_device_fp, device_name, expires_at = active_session

                # Si intenta acceder desde el MISMO dispositivo, permitir
                if active_device_fp == device_fingerprint:
                    conn.close()
                    return True, "Acceso permitido - dispositivo autorizado"

                # Si intenta acceder desde OTRO dispositivo, DENEGAR
                else:
                    conn.close()
                    self._log_blocked_attempt(customer_id, ip_address, device_fingerprint,
                                             f"Intento de acceso desde dispositivo no autorizado")
                    return False, f"❌ ACCESO DENEGADO: Ya estás en sesión en otro dispositivo ({device_name}). Cierra esa sesión primero."

            conn.close()
            return True, "Acceso permitido - sin sesiones activas"

        except Exception as e:
            self.logger.error(f"❌ Error validando acceso: {e}")
            return False, str(e)

    def create_session(self, customer_id: int, device_id: int, session_token: str,
                      ip_address: str, session_duration_hours: int = 24) -> Tuple[bool, str]:
        """Crear sesión para cliente"""
        for attempt in range(3):
            try:
                # Primero cerrar cualquier otra sesión activa
                conn = self._connect()
                cursor = conn.cursor()

                cursor.execute('''
                    UPDATE sessions SET is_active = 0
                    WHERE customer_id = ? AND is_active = 1
                ''', (customer_id,))

                # Crear nueva sesión
                expires_at = datetime.now() + timedelta(hours=session_duration_hours)

                cursor.execute('''
                    INSERT INTO sessions (customer_id, device_id, session_token,
                                         expires_at, ip_address, last_activity)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (customer_id, device_id, session_token, expires_at.isoformat(), ip_address, datetime.now().isoformat()))

                session_id = cursor.lastrowid

                # Actualizar último login del cliente
                cursor.execute('''
                    UPDATE customers SET last_login = datetime('now')
                    WHERE id = ?
                ''', (customer_id,))

                # Actualizar último uso del dispositivo
                cursor.execute('''
                    UPDATE devices SET last_used = datetime('now')
                    WHERE id = ?
                ''', (device_id,))

                conn.commit()
                conn.close()

                self.logger.info(f"✅ Sesión creada: Customer {customer_id} - Device {device_id}")
                self._log_audit(customer_id, "SESSION_CREATED",
                               f"Nueva sesión - Dispositivo: {device_id} - IP: {ip_address}", "success")
                return True, session_token
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < 2:
                    wait_time = (2 ** attempt) * 0.1
                    self.logger.warning(f"⚠️ DB locked creating session, retrying in {wait_time}s")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"❌ Error creando sesión: {e}")
                    return False, ""
            except Exception as e:
                self.logger.error(f"❌ Error creando sesión: {e}")
                return False, ""

        return False, ""

    def verify_session_token(self, session_token: str) -> Tuple[bool, Optional[int]]:
        """Verificar token de sesión válido"""
        try:
            conn = self._connect()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, customer_id FROM sessions
                WHERE session_token = ? AND is_active = 1
                AND expires_at > datetime('now')
            ''', (session_token,))

            result = cursor.fetchone()

            if result:
                session_id, customer_id = result
                # Actualizar última actividad
                cursor.execute('''
                    UPDATE sessions SET last_activity = datetime('now')
                    WHERE id = ?
                ''', (session_id,))
                conn.commit()
                conn.close()
                return True, customer_id
            else:
                conn.close()
                return False, None

        except Exception as e:
            self.logger.error(f"❌ Error verificando sesión: {e}")
            return False, None

    def logout_customer(self, customer_id: int) -> bool:
        """Cerrar sesión del cliente"""
        try:
            conn = self._connect()
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE sessions SET is_active = 0
                WHERE customer_id = ? AND is_active = 1
            ''', (customer_id,))

            conn.commit()
            conn.close()

            self.logger.info(f"✅ Sesión cerrada: Customer {customer_id}")
            self._log_audit(customer_id, "SESSION_CLOSED", "Sesión cerrada por logout", "success")
            return True

        except Exception as e:
            self.logger.error(f"❌ Error cerrando sesión: {e}")
            return False

    def record_payment(self, customer_id: int, amount: float, payment_method: str = "stripe",
                      stripe_payment_id: str = "") -> Tuple[bool, int]:
        """Registrar pago del cliente"""
        for attempt in range(3):
            try:
                conn = self._connect()
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT INTO payments (customer_id, amount, payment_method,
                                         stripe_payment_id, status)
                    VALUES (?, ?, ?, ?, ?)
                ''', (customer_id, amount, payment_method, stripe_payment_id, 'completed'))

                payment_id = cursor.lastrowid

                # Actualizar estado del cliente
                cursor.execute('''
                    UPDATE customers SET payment_status = 'completed',
                                       payment_amount = ?,
                                       payment_date = ?,
                                       subscription_type = 'premium'
                    WHERE id = ?
                ''', (amount, datetime.now().isoformat(), customer_id))

                conn.commit()
                conn.close()

                self.logger.info(f"✅ Pago registrado: Customer {customer_id} - ${amount}")
                self._log_audit(customer_id, "PAYMENT_RECEIVED",
                               f"Pago de ${amount} - Método: {payment_method}", "success")
                return True, payment_id
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < 2:
                    wait_time = (2 ** attempt) * 0.1
                    self.logger.warning(f"⚠️ DB locked recording payment, retrying in {wait_time}s")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"❌ Error registrando pago: {e}")
                    return False, -1
            except Exception as e:
                self.logger.error(f"❌ Error registrando pago: {e}")
                return False, -1

        return False, -1

    def get_customer_info(self, customer_identifier: Any) -> Optional[Dict]:
        """Obtener información del cliente por ID o username"""
        try:
            conn = self._connect()
            cursor = conn.cursor()

            if isinstance(customer_identifier, int):
                cursor.execute('''
                    SELECT id, username, email, created_at, subscription_type,
                           payment_status, is_active, last_login, role
                    FROM customers WHERE id = ?
                ''', (customer_identifier,))
            else:
                cursor.execute('''
                    SELECT id, username, email, created_at, subscription_type,
                           payment_status, is_active, last_login, role
                    FROM customers WHERE username = ?
                ''', (customer_identifier,))

            result = cursor.fetchone()
            conn.close()

            if result:
                return {
                    'id': result[0],
                    'username': result[1],
                    'email': result[2],
                    'created_at': result[3],
                    'subscription_type': result[4],
                    'payment_status': result[5],
                    'is_active': bool(result[6]),
                    'last_login': result[7],
                    'role': result[8]
                }
            return None

        except Exception as e:
            self.logger.error(f"❌ Error obteniendo info del cliente: {e}")
            return None

    def get_customer_by_email(self, email: str) -> Optional[Dict]:
        """Obtener información del cliente por correo electrónico"""
        try:
            conn = self._connect()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, username, email, created_at, subscription_type,
                       payment_status, is_active, last_login, role
                FROM customers WHERE email = ?
            ''', (email,))

            result = cursor.fetchone()
            conn.close()

            if result:
                return {
                    'id': result[0],
                    'username': result[1],
                    'email': result[2],
                    'created_at': result[3],
                    'subscription_type': result[4],
                    'payment_status': result[5],
                    'is_active': bool(result[6]),
                    'last_login': result[7],
                    'role': result[8]
                }
            return None

        except Exception as e:
            self.logger.error(f"❌ Error obteniendo cliente por email: {e}")
            return None

    def get_customer_devices(self, customer_id: int) -> List[Dict]:
        """Obtener todos los dispositivos del cliente"""
        try:
            conn = self._connect()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, device_name, device_type, ip_address, os,
                       registered_at, last_used, is_active, is_primary
                FROM devices WHERE customer_id = ? ORDER BY last_used DESC
            ''', (customer_id,))

            results = cursor.fetchall()
            conn.close()

            devices = []
            for row in results:
                devices.append({
                    'id': row[0],
                    'name': row[1],
                    'type': row[2],
                    'ip_address': row[3],
                    'os': row[4],
                    'registered_at': row[5],
                    'last_used': row[6],
                    'is_active': bool(row[7]),
                    'is_primary': bool(row[8])
                })

            return devices

        except Exception as e:
            self.logger.error(f"❌ Error obteniendo dispositivos: {e}")
            return []

    def get_customer_payments(self, customer_id: int, limit: int = 10) -> List[Dict]:
        """Obtener historial de pagos del cliente"""
        try:
            conn = self._connect()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, amount, currency, status, payment_method,
                       created_at, completed_at
                FROM payments WHERE customer_id = ?
                ORDER BY created_at DESC LIMIT ?
            ''', (customer_id, limit))

            results = cursor.fetchall()
            conn.close()

            payments = []
            for row in results:
                payments.append({
                    'id': row[0],
                    'amount': row[1],
                    'currency': row[2],
                    'status': row[3],
                    'payment_method': row[4],
                    'created_at': row[5],
                    'completed_at': row[6]
                })

            return payments

        except Exception as e:
            self.logger.error(f"❌ Error obteniendo pagos: {e}")
            return []

    def get_audit_log(self, customer_id: int = None, limit: int = 100) -> List[Dict]:
        """Obtener registro de auditoría"""
        try:
            conn = self._connect()
            cursor = conn.cursor()

            if customer_id:
                cursor.execute('''
                    SELECT id, customer_id, action, details, ip_address,
                           timestamp, status
                    FROM audit_log WHERE customer_id = ?
                    ORDER BY timestamp DESC LIMIT ?
                ''', (customer_id, limit))
            else:
                cursor.execute('''
                    SELECT id, customer_id, action, details, ip_address,
                           timestamp, status
                    FROM audit_log ORDER BY timestamp DESC LIMIT ?
                ''', (limit,))

            results = cursor.fetchall()
            conn.close()

            logs = []
            for row in results:
                logs.append({
                    'id': row[0],
                    'customer_id': row[1],
                    'action': row[2],
                    'details': row[3],
                    'ip_address': row[4],
                    'timestamp': row[5],
                    'status': row[6]
                })

            return logs

        except Exception as e:
            self.logger.error(f"❌ Error obteniendo audit log: {e}")
            return []

    def _log_audit(self, customer_id: int, action: str, details: str,
                  status: str = "pending", ip_address: str = ""):
        """Registrar acción en auditoría"""
        try:
            conn = self._connect()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO audit_log (customer_id, action, details, ip_address, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (customer_id, action, details, ip_address, status))

            conn.commit()
            conn.close()

        except Exception as e:
            self.logger.error(f"❌ Error registrando auditoría: {e}")

    def _log_blocked_attempt(self, customer_id: int, ip_address: str,
                            device_fingerprint: str, reason: str):
        """Registrar intento de acceso bloqueado"""
        try:
            conn = self._connect()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO blocked_attempts (customer_id, ip_address,
                                             device_fingerprint, reason)
                VALUES (?, ?, ?, ?)
            ''', (customer_id, ip_address, device_fingerprint, reason))

            conn.commit()
            conn.close()

            self.logger.warning(f"⚠️ Acceso bloqueado: {reason}")

        except Exception as e:
            self.logger.error(f"❌ Error registrando intento bloqueado: {e}")

    def get_all_customers(self, limit: int = 100) -> List[Dict]:
        """Obtener todos los clientes (para admin)"""
        try:
            conn = self._connect()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, username, email, subscription_type, payment_status,
                       is_active, created_at, last_login
                FROM customers ORDER BY created_at DESC LIMIT ?
            ''', (limit,))

            results = cursor.fetchall()
            conn.close()

            customers = []
            for row in results:
                customers.append({
                    'id': row[0],
                    'username': row[1],
                    'email': row[2],
                    'subscription_type': row[3],
                    'payment_status': row[4],
                    'is_active': bool(row[5]),
                    'created_at': row[6],
                    'last_login': row[7]
                })

            return customers

        except Exception as e:
            self.logger.error(f"❌ Error obteniendo clientes: {e}")
            return []

    def disable_customer(self, customer_id: int, reason: str = "") -> bool:
        """Desactivar cuenta del cliente"""
        try:
            conn = self._connect()
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE customers SET is_active = 0 WHERE id = ?
            ''', (customer_id,))

            cursor.execute('''
                UPDATE sessions SET is_active = 0 WHERE customer_id = ?
            ''', (customer_id,))

            conn.commit()
            conn.close()

            self.logger.info(f"✅ Cliente desactivado: {customer_id}")
            self._log_audit(customer_id, "ACCOUNT_DISABLED", reason, "success")
            return True

        except Exception as e:
            self.logger.error(f"❌ Error desactivando cliente: {e}")
            return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    db = DatabaseManager()
    print("✅ Base de datos inicializada")