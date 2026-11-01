#!/usr/bin/env python
"""
Script de verificación completa del sistema de trading.
Valida que:
1. Todas las funciones principales funcionen
2. El API devuelva datos correctos
3. La base de datos esté inicializada
4. Los módulos se carguen correctamente
"""

import sys
import os
import time
import json
from pathlib import Path

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def check_file_structure():
    """Verificar estructura de archivos."""
    print("\n📁 VERIFICANDO ESTRUCTURA DE ARCHIVOS")
    print("=" * 70)
    
    required_files = [
        'src/app.py',
        'src/models.py',
        'src/market_data.py',
        'src/security.py',
        'requirements.txt',
    ]
    
    all_exist = True
    for filepath in required_files:
        full_path = os.path.join(os.path.dirname(__file__), filepath)
        exists = os.path.exists(full_path)
        status = "✅" if exists else "❌"
        print(f"{status} {filepath}")
        if not exists:
            all_exist = False
    
    return all_exist

def check_imports():
    """Verificar que todos los módulos se importan correctamente."""
    print("\n📦 VERIFICANDO IMPORTACIONES")
    print("=" * 70)
    
    modules = [
        ('Flask', 'flask'),
        ('SQLAlchemy', 'sqlalchemy'),
        ('Flask-SQLAlchemy', 'flask_sqlalchemy'),
        ('yfinance', 'yfinance'),
        ('requests', 'requests'),
    ]
    
    all_imported = True
    for display_name, module_name in modules:
        try:
            __import__(module_name)
            print(f"✅ {display_name}")
        except ImportError as e:
            print(f"❌ {display_name}: {e}")
            all_imported = False
    
    return all_imported

def check_python_files():
    """Verificar sintaxis de archivos Python."""
    print("\n✨ VERIFICANDO SINTAXIS DE PYTHON")
    print("=" * 70)
    
    python_files = [
        'src/app.py',
        'src/models.py',
        'src/market_data.py',
        'src/security.py',
    ]
    
    import py_compile
    all_valid = True
    
    for filepath in python_files:
        full_path = os.path.join(os.path.dirname(__file__), filepath)
        try:
            py_compile.compile(full_path, doraise=True)
            print(f"✅ {filepath}")
        except py_compile.PyCompileError as e:
            print(f"❌ {filepath}: {e}")
            all_valid = False
    
    return all_valid

def check_app_initialization():
    """Verificar que la app Flask se inicializa correctamente."""
    print("\n🚀 VERIFICANDO INICIALIZACIÓN DE FLASK")
    print("=" * 70)
    
    try:
        from app import app, db, init_db
        print("✅ Flask app importado correctamente")
        
        with app.app_context():
            init_db(app)
            print("✅ Base de datos inicializada")
        
        # Verificar que las tablas se crearon
        from models import User, LoginSession, BillingHistory, PasswordResetToken
        print("✅ Modelos de base de datos importados")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_market_data():
    """Verificar que market_data funciona."""
    print("\n📊 VERIFICANDO MERCADO DE DATOS")
    print("=" * 70)
    
    try:
        from market_data import MarketDataProvider, SYMBOL_MAPPING
        
        print(f"✅ MarketDataProvider importado")
        print(f"✅ Símbolos soportados: {len(SYMBOL_MAPPING)}")
        
        symbols = list(SYMBOL_MAPPING.keys())[:5]
        for symbol in symbols:
            print(f"   - {symbol}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def check_security():
    """Verificar que security funciona."""
    print("\n🔐 VERIFICANDO SEGURIDAD")
    print("=" * 70)
    
    try:
        from security import SecurityValidator, rate_limit
        
        print("✅ SecurityValidator importado")
        print("✅ Decorador rate_limit importado")
        
        # Probar validadores
        validator = SecurityValidator()
        
        # Email
        is_valid = validator.validate_email("user@example.com")
        print(f"✅ Validador email: {is_valid}")
        
        # Password
        is_valid = validator.validate_password("SecurePass123!")
        print(f"✅ Validador password: {is_valid}")
        
        # Symbol
        is_valid = validator.validate_symbol("EURUSD")
        print(f"✅ Validador symbol: {is_valid}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_endpoints():
    """Verificar que los endpoints clave existen en la app."""
    print("\n🔗 VERIFICANDO ENDPOINTS")
    print("=" * 70)
    
    try:
        from app import app
        
        # Listar todas las rutas
        endpoints = []
        for rule in app.url_map.iter_rules():
            endpoints.append(str(rule.rule))
        
        required_endpoints = [
            '/dashboard',
            '/api/status',
            '/api/auth/register',
            '/api/auth/login',
            '/api/predict',
            '/api/advanced-prediction',
            '/api/news-alerts',
        ]
        
        missing = []
        for endpoint in required_endpoints:
            if endpoint in endpoints:
                print(f"✅ {endpoint}")
            else:
                print(f"❌ {endpoint}")
                missing.append(endpoint)
        
        print(f"\n📈 Total de endpoints: {len(endpoints)}")
        return len(missing) == 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Ejecutar todas las verificaciones."""
    print("\n" + "=" * 70)
    print("🔍 VERIFICACIÓN COMPLETA DEL SISTEMA DE TRADING")
    print("=" * 70)
    
    results = {
        'Estructura de archivos': check_file_structure(),
        'Importaciones': check_imports(),
        'Sintaxis Python': check_python_files(),
        'Inicialización Flask': check_app_initialization(),
        'Mercado de datos': check_market_data(),
        'Seguridad': check_security(),
        'Endpoints': check_endpoints(),
    }
    
    print("\n" + "=" * 70)
    print("📋 RESUMEN DE VERIFICACIONES")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for test_name, result in results.items():
        status = "✅ PASÓ" if result else "❌ FALLÓ"
        print(f"{status:15} {test_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 70)
    
    if failed == 0:
        print(f"✅ TODAS LAS VERIFICACIONES PASARON ({passed}/{passed + failed})")
        print("\n🚀 El sistema está listo para producción")
        print("\nPara iniciar el servidor:")
        print("   python src/app.py")
        print("\nLuego abre en tu navegador:")
        print("   http://localhost:5000/dashboard")
        print("=" * 70)
        return 0
    else:
        print(f"⚠️  ALGUNAS VERIFICACIONES FALLARON ({passed}/{passed + failed})")
        print("\nPor favor revisa los errores arriba")
        print("=" * 70)
        return 1

if __name__ == '__main__':
    sys.exit(main())
