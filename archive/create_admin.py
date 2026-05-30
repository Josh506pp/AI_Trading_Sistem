#!/usr/bin/env python3
"""
CREATE ADMIN USER - Sistema de Acceso Administrativo
Crea un usuario administrador con acceso completo al sistema
"""

import sqlite3
import hashlib
import secrets
from datetime import datetime
from database_manager import DatabaseManager
from device_manager import DeviceManager, DeviceFingerprint

def hash_password(password: str) -> str:
    """Generar hash SHA256 de contraseña"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_admin_user(db_path: str = "trading_system.db"):
    """Crear usuario administrador con credenciales seguras"""
    
    print("=" * 70)
    print(" 🔐 CREADOR DE USUARIO ADMINISTRADOR")
    print("=" * 70)
    print()
    
    # Inicializar gestor de BD
    db = DatabaseManager(db_path)
    
    # Credenciales del admin
    admin_username = "admin"
    admin_email = "admin@tradingsystem.pro"
    admin_password = secrets.token_urlsafe(16)  # Contraseña segura aleatoria
    
    print("📝 Configurando usuario administrador...")
    print()
    
    try:
        # Conectar a BD
        conn = sqlite3.connect(db_path, timeout=10, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        cursor = conn.cursor()
        
        # Verificar si admin ya existe
        cursor.execute("SELECT id FROM customers WHERE username = ? OR email = ?", 
                      (admin_username, admin_email))
        existing = cursor.fetchone()
        
        if existing:
            print("⚠️  Usuario admin ya existe. Actualizando credenciales...")
            admin_id = existing[0]
            
            # Actualizar contraseña
            password_hash = hash_password(admin_password)
            cursor.execute(
                "UPDATE customers SET password_hash = ?, updated_at = ? WHERE id = ?",
                (password_hash, datetime.now().isoformat(), admin_id)
            )
            conn.commit()
            print("✅ Contraseña actualizada")
            
        else:
            print("✨ Creando nuevo usuario administrador...")
            
            # Crear admin
            password_hash = hash_password(admin_password)
            cursor.execute('''
                INSERT INTO customers 
                (username, email, password_hash, subscription_type, 
                 payment_status, is_active, role, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                admin_username,
                admin_email,
                password_hash,
                'premium',  # Subscripción premium
                'completed',  # Pago completado
                1,  # Activo
                'admin',  # Rol admin
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            conn.commit()
            
            # Obtener ID del admin
            cursor.execute("SELECT id FROM customers WHERE username = ?", (admin_username,))
            admin_id = cursor.fetchone()[0]
            print(f"✅ Usuario administrador creado (ID: {admin_id})")
        
        conn.close()
        
        # Mostrar credenciales
        print()
        print("=" * 70)
        print(" 🎯 CREDENCIALES DE ADMINISTRADOR")
        print("=" * 70)
        print()
        print(f"👤 Usuario:      {admin_username}")
        print(f"📧 Email:        {admin_email}")
        print(f"🔑 Contraseña:   {admin_password}")
        print()
        print("=" * 70)
        print()
        
        # Información adicional
        print("📌 INFORMACIÓN IMPORTANTE:")
        print()
        print("✅ Acceso: Sistema Completo")
        print("✅ Rol: Administrador")
        print("✅ Subscripción: Premium")
        print("✅ Estado: Activo")
        print()
        print("🛡️  PERMISOS:")
        print("  • Ver todos los clientes")
        print("  • Administrar usuarios")
        print("  • Ver auditoría completa")
        print("  • Acceso a métricas del sistema")
        print("  • Configuración de plataforma")
        print("  • Múltiples dispositivos simultáneos (sin restricción)")
        print()
        
        # Instrucciones de login
        print("🚀 CÓMO INICIAR SESIÓN:")
        print()
        print("1. Ejecuta: python professional_trading_system.py")
        print(f"2. Username: {admin_username}")
        print(f"3. Password: {admin_password}")
        print()
        print("O accede vía:")
        print("  • http://localhost:5000/login")
        print()
        
        print("⚠️  SEGURIDAD:")
        print("  • Guarda estas credenciales en un lugar seguro")
        print("  • Cambiar contraseña después del primer login")
        print("  • No compartir credenciales con otros usuarios")
        print()
        
        # Mostrar resumen del sistema
        print("=" * 70)
        print(" 📊 RESUMEN DEL SISTEMA")
        print("=" * 70)
        print()
        
        cursor = conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Contar usuarios
        cursor.execute("SELECT COUNT(*) FROM customers")
        user_count = cursor.fetchone()[0]
        
        # Contar dispositivos
        cursor.execute("SELECT COUNT(*) FROM devices")
        device_count = cursor.fetchone()[0]
        
        # Contar sesiones
        cursor.execute("SELECT COUNT(*) FROM sessions WHERE is_active = 1")
        active_sessions = cursor.fetchone()[0]
        
        # Contar pagos
        cursor.execute("SELECT SUM(amount) FROM payments WHERE status = 'completed'")
        total_payments = cursor.fetchone()[0] or 0
        
        # Contar logs de auditoría
        cursor.execute("SELECT COUNT(*) FROM audit_log")
        audit_logs = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"👥 Usuarios totales:        {user_count}")
        print(f"🖥️  Dispositivos registrados: {device_count}")
        print(f"📱 Sesiones activas:        {active_sessions}")
        print(f"💰 Ingresos por pagos:      ${total_payments:.2f}")
        print(f"📋 Eventos de auditoría:    {audit_logs}")
        print()
        print("=" * 70)
        print()
        
        return {
            'success': True,
            'admin_id': admin_id,
            'username': admin_username,
            'email': admin_email,
            'password': admin_password
        }
        
    except Exception as e:
        print(f"❌ Error creando usuario admin: {e}")
        return {'success': False, 'error': str(e)}

if __name__ == "__main__":
    result = create_admin_user()
    
    if result['success']:
        print("✨ ¡Usuario administrador configurado exitosamente!")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")
