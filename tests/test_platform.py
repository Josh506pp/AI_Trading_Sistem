#!/usr/bin/env python3
"""
Test Suite for Trading Platform
Tests for authentication, subscription, security
"""

import sys
import os

# Add root and src to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import unittest
from datetime import datetime, timedelta
import importlib
from unittest.mock import patch

# Import app and modules
try:
    from src.app import app, db, User, LoginSession, BillingHistory
    from src.security import SecurityValidator, request_counts
except ImportError:
    from app import app, db, User, LoginSession, BillingHistory
    from security import SecurityValidator, request_counts

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

app_module = importlib.import_module('src.app')


class IsolatedDatabaseTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        cls._test_engine = create_engine(
            'sqlite://',
            connect_args={'check_same_thread': False},
            poolclass=StaticPool
        )
        with app.app_context():
            cls._original_engine = db.engines[None]
            db.engines[None] = cls._test_engine
            db.create_all()

    @classmethod
    def tearDownClass(cls):
        with app.app_context():
            db.session.remove()
            db.drop_all()
            db.engines[None] = cls._original_engine
        cls._test_engine.dispose()

    def setUp(self):
        self.app = app
        request_counts.clear()
        with self.app.app_context():
            db.session.remove()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.create_all()


class TestAuthentication(IsolatedDatabaseTestCase):
    """Tests para autenticación"""
    
    def setUp(self):
        super().setUp()
        self.client = self.app.test_client()

    def test_register_user_success(self):
        """Test registro exitoso"""
        response = self.client.post('/api/auth/register', json={
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'password123',
            'full_name': 'Test User'
        })
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['email'], 'test@example.com')
    
    def test_register_duplicate_email(self):
        """Test que no permite email duplicado"""
        # Primer registro
        self.client.post('/api/auth/register', json={
            'email': 'test@example.com',
            'username': 'user1',
            'password': 'password123'
        })
        
        # Segundo registro con mismo email
        response = self.client.post('/api/auth/register', json={
            'email': 'test@example.com',
            'username': 'user2',
            'password': 'password123'
        })
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['success'])
        self.assertIn('ya está registrado', data['error'])

    def test_registration_rejects_sql_injection_shaped_username(self):
        response = self.client.post('/api/auth/register', json={
            'email': 'attack@example.com',
            'username': "admin' OR '1'='1",
            'password': 'password123'
        })

        self.assertEqual(response.status_code, 400)
        with self.app.app_context():
            self.assertIsNone(User.query.filter_by(email='attack@example.com').first())

    def test_registration_requires_eight_character_password(self):
        response = self.client.post('/api/auth/register', json={
            'email': 'short@example.com',
            'username': 'shortpass',
            'password': '1234567'
        })

        self.assertEqual(response.status_code, 400)
        with self.app.app_context():
            self.assertIsNone(User.query.filter_by(email='short@example.com').first())

    def test_registration_rejects_sql_injection_shaped_username(self):
        response = self.client.post('/api/auth/register', json={
            'email': 'attack@example.com',
            'username': "admin' OR '1'='1",
            'password': 'password123'
        })

        self.assertEqual(response.status_code, 400)
        with self.app.app_context():
            self.assertIsNone(User.query.filter_by(email='attack@example.com').first())

    def test_login_success(self):
        """Test login exitoso"""
        # Registrar
        self.client.post('/api/auth/register', json={
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'password123'
        })
        
        # Login
        response = self.client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'password123'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
    
    def test_login_invalid_password(self):
        """Test login con contraseña incorrecta"""
        # Registrar
        self.client.post('/api/auth/register', json={
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'password123'
        })
        
        # Login con contraseña incorrecta
        response = self.client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'wrongpassword'
        })
        
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertFalse(data['success'])


class TestSubscription(IsolatedDatabaseTestCase):
    """Tests para suscripción"""
    
    def setUp(self):
        super().setUp()
        self.client = self.app.test_client()
        
        with self.app.app_context():
            # Crear usuario de test
            self.user = User(
                email='test@example.com',
                username='testuser',
                subscription_plan='FREE'
            )
            self.user.set_password('password123')
            db.session.add(self.user)
            db.session.commit()
            self.user_id = self.user.id
    
    def test_get_plans(self):
        """Test obtener planes disponibles"""
        response = self.client.get('/api/subscription/plans')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertIn('FREE', data['plans'])
        self.assertIn('PRO', data['plans'])
        self.assertIn('PREMIUM', data['plans'])
    
    def test_get_subscription_requires_login(self):
        """Test que obtener suscripción requiere login"""
        response = self.client.get('/api/subscription/current')
        self.assertEqual(response.status_code, 401)
    
    def test_upgrade_subscription_success(self):
        """Test mejorar plan"""
        # Login
        with self.app.test_client() as c:
            c.post('/api/auth/login', json={
                'email': 'test@example.com',
                'password': 'password123'
            })
            
            # Upgrade
            response = c.post('/api/subscription/upgrade', json={
                'plan': 'PRO'
            })
            
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data['success'])
            self.assertEqual(data['subscription']['plan'], 'PRO')

    def test_renew_and_cancel_subscription(self):
        """Test renovación y cancelación de suscripción"""
        with self.app.test_client() as c:
            c.post('/api/auth/login', json={
                'email': 'test@example.com',
                'password': 'password123'
            })
            
            # Upgrade first
            c.post('/api/subscription/upgrade', json={'plan': 'PRO'})
            
            # Renew
            renew_resp = c.post('/api/subscription/renew')
            self.assertEqual(renew_resp.status_code, 200)
            self.assertTrue(renew_resp.get_json()['success'])
            
            # Cancel
            cancel_resp = c.post('/api/subscription/cancel')
            self.assertEqual(cancel_resp.status_code, 200)
            self.assertEqual(cancel_resp.get_json()['subscription']['plan'], 'FREE')

    def test_plan_feature_restrictions(self):
        """Test que las restricciones de funciones según el plan funcionen"""
        with self.app.test_client() as c:
            c.post('/api/auth/login', json={
                'email': 'test@example.com',
                'password': 'password123'
            })
            
            # FREE user - advanced prediction should return 403
            resp = c.get('/api/advanced-prediction')
            self.assertEqual(resp.status_code, 403)
            self.assertTrue(resp.get_json().get('upgrade_required'))
            
            # Upgrade to PRO - advanced prediction allowed
            c.post('/api/subscription/upgrade', json={'plan': 'PRO'})
            resp_pro = c.get('/api/advanced-prediction')
            self.assertEqual(resp_pro.status_code, 200)
            
            # PRO user blocked from PREMIUM analysis
            resp_prem = c.get('/api/professional-analysis')
            self.assertEqual(resp_prem.status_code, 403)
            
            # Upgrade to PREMIUM - professional analysis allowed
            c.post('/api/subscription/upgrade', json={'plan': 'PREMIUM'})
            resp_prem2 = c.get('/api/professional-analysis')
            self.assertEqual(resp_prem2.status_code, 200)

    def test_free_plan_gets_cached_basic_analysis_but_no_chat_or_advanced_features(self):
        with self.client:
            login = self.client.post('/api/auth/login', json={
                'email': 'test@example.com',
                'password': 'password123'
            })
            self.assertEqual(login.status_code, 200)
            analysis_key = (
                self.user_id, app_module.TRADING_DATA['symbol'], 'FREE'
            )
            app_module._basic_analysis_cache.pop(analysis_key, None)

            with patch.object(
                app_module, 'analyze_signal', wraps=app_module.analyze_signal
            ) as calculate:
                first = self.client.get('/api/analysis')
                second = self.client.get('/api/analysis')

            self.assertEqual(first.status_code, 200)
            self.assertEqual(first.get_json()['analysis_cache']['cooldown_seconds'], 900)
            self.assertEqual(second.get_json()['analysis_cache']['status'], 'cached')
            self.assertEqual(calculate.call_count, 1)
            self.assertEqual(self.client.get('/api/advanced-prediction').status_code, 403)
            self.assertEqual(self.client.get('/api/predict').status_code, 403)
            self.assertEqual(self.client.get('/api/predict/levels').status_code, 403)
            self.assertEqual(self.client.get('/api/predict/signal').status_code, 403)
            self.assertEqual(self.client.post(
                '/api/chat', json={'message': 'analiza el mercado'}
            ).status_code, 403)
            self.assertEqual(self.client.post(
                '/api/chat/command', json={'command': '/status'}
            ).status_code, 403)
            self.assertEqual(self.client.get('/api/chat/history').status_code, 403)
            self.assertEqual(self.client.get('/api/news-alerts').status_code, 403)
            app_module._basic_analysis_cache.pop(analysis_key, None)

    def test_paid_basic_analysis_uses_five_minute_cooldown(self):
        symbol = app_module.TRADING_DATA['symbol']
        with self.app.app_context():
            user = db.session.get(User, self.user_id)
            user.upgrade_subscription('PRO')
            db.session.commit()

        cache_key = (self.user_id, symbol, 'PRO')
        app_module._basic_analysis_cache.pop(cache_key, None)
        client = self.app.test_client()
        client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'password123'
        })
        response = client.get('/api/analysis')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['analysis_cache']['cooldown_seconds'], 300)
        app_module._basic_analysis_cache.pop(cache_key, None)

    def test_pro_plan_can_use_chat(self):
        with self.client:
            login = self.client.post('/api/auth/login', json={
                'email': 'test@example.com',
                'password': 'password123'
            })
            self.assertEqual(login.status_code, 200)
            upgrade = self.client.post('/api/subscription/upgrade', json={'plan': 'PRO'})
            self.assertEqual(upgrade.status_code, 200)
            response = self.client.post('/api/chat', json={'message': 'precio'})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['success'])

    def test_premium_professional_analysis_is_cached_for_five_minutes(self):
        user_id = self.user_id
        symbol = app_module.TRADING_DATA['symbol']
        app_module._professional_analysis_cache.pop((user_id, symbol), None)
        with self.app.app_context():
            user = db.session.get(User, user_id)
            user.upgrade_subscription('PREMIUM')
            db.session.commit()

        with self.client:
            login = self.client.post('/api/auth/login', json={
                'email': 'test@example.com',
                'password': 'password123'
            })
            self.assertEqual(login.status_code, 200)
            with patch.object(
                app_module, 'analyze_signal', wraps=app_module.analyze_signal
            ) as calculate:
                first = self.client.get('/api/professional-analysis')
                second = self.client.get('/api/professional-analysis')

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.get_json()['analysis_cache']['cooldown_seconds'], 300)
        self.assertEqual(second.get_json()['analysis_cache']['status'], 'cached')
        self.assertEqual(calculate.call_count, 1)
        app_module._professional_analysis_cache.pop((user_id, symbol), None)

    def test_chat_history_is_isolated_between_users(self):
        with self.app.app_context():
            other_user = User(
                email='other@example.com',
                username='othertrader',
                subscription_plan='PRO',
                subscription_status='active',
                subscription_expires=datetime.utcnow() + timedelta(days=30)
            )
            other_user.set_password('password123')
            db.session.add(other_user)
            db.session.commit()
            other_user_id = other_user.id

        app_module.CHAT_HISTORY_BY_USER.pop(self.user_id, None)
        app_module.CHAT_HISTORY_BY_USER.pop(other_user_id, None)
        first_client = self.app.test_client()
        second_client = self.app.test_client()
        first_client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'password123'
        })
        first_client.post('/api/subscription/upgrade', json={'plan': 'PRO'})
        second_client.post('/api/auth/login', json={
            'email': 'other@example.com',
            'password': 'password123'
        })

        first_response = first_client.post('/api/chat', json={'message': 'mi nota privada'})
        second_history = second_client.get('/api/chat/history').get_json()['history']

        self.assertEqual(first_response.status_code, 200)
        self.assertNotIn('mi nota privada', str(second_history))
        app_module.CHAT_HISTORY_BY_USER.pop(self.user_id, None)
        app_module.CHAT_HISTORY_BY_USER.pop(other_user_id, None)


class TestUserManagement(IsolatedDatabaseTestCase):
    """Tests para perfil, contraseñas y recuperación"""
    
    def setUp(self):
        super().setUp()
        self.client = self.app.test_client()
        
        with self.app.app_context():
            self.user = User(
                email='user@example.com',
                username='profileuser',
                full_name='Original Name'
            )
            self.user.set_password('oldpassword123')
            db.session.add(self.user)
            db.session.commit()
            
    def test_update_profile(self):
        """Test actualizar perfil de usuario"""
        with self.app.test_client() as c:
            c.post('/api/auth/login', json={'email': 'user@example.com', 'password': 'oldpassword123'})
            resp = c.put('/api/user/profile', json={'full_name': 'Nuevo Nombre'})
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.get_json()['user']['full_name'], 'Nuevo Nombre')

    def test_change_password(self):
        """Test cambiar contraseña"""
        with self.app.test_client() as c:
            c.post('/api/auth/login', json={'email': 'user@example.com', 'password': 'oldpassword123'})
            resp = c.post('/api/user/password', json={'current_password': 'oldpassword123', 'new_password': 'newpassword123'})
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.get_json()['success'])

    def test_forgot_and_reset_password(self):
        """Test flujo completo de olvido y restablecimiento de contraseña"""
        forgot_resp = self.client.post('/api/auth/forgot-password', json={'email': 'user@example.com'})
        self.assertEqual(forgot_resp.status_code, 200)
        data = forgot_resp.get_json()
        token = data.get('reset_token')
        self.assertIsNotNone(token)
        
        reset_resp = self.client.post('/api/auth/reset-password', json={'token': token, 'new_password': 'resetpass123'})
        self.assertEqual(reset_resp.status_code, 200)
        self.assertTrue(reset_resp.get_json()['success'])


class TestSecurity(unittest.TestCase):
    """Tests para seguridad"""
    
    def test_email_validation(self):
        """Test validación de email"""
        self.assertTrue(SecurityValidator.validate_email('test@example.com'))
        self.assertFalse(SecurityValidator.validate_email('invalid'))
        self.assertFalse(SecurityValidator.validate_email('test@'))
    
    def test_username_validation(self):
        """Test validación de username"""
        self.assertTrue(SecurityValidator.validate_username('validuser'))
        self.assertTrue(SecurityValidator.validate_username('user_123'))
        self.assertFalse(SecurityValidator.validate_username('ab'))  # muy corto
        self.assertFalse(SecurityValidator.validate_username('user@email'))  # carácter inválido
    
    def test_password_validation(self):
        """Test validación de contraseña"""
        self.assertTrue(SecurityValidator.validate_password('password123'))
        self.assertFalse(SecurityValidator.validate_password('short'))  # muy corta
        self.assertFalse(SecurityValidator.validate_password('1234567'))
        self.assertFalse(SecurityValidator.validate_password(None))
    
    def test_symbol_validation(self):
        """Test validación de símbolo"""
        self.assertTrue(SecurityValidator.validate_symbol('EURUSD'))
        self.assertTrue(SecurityValidator.validate_symbol('BTC'))
        self.assertTrue(SecurityValidator.validate_symbol('US30'))
        self.assertFalse(SecurityValidator.validate_symbol('INVALID!'))
        self.assertFalse(SecurityValidator.validate_symbol('1234567890'))
        self.assertFalse(SecurityValidator.validate_symbol('123'))
        self.assertFalse(SecurityValidator.validate_symbol(None))
        self.assertFalse(SecurityValidator.validate_symbol('123'))
        self.assertFalse(SecurityValidator.validate_symbol(None))
    
    def test_sanitize_string(self):
        """Test sanitización de strings"""
        dirty = "test\x00\r\nvalue"
        clean = SecurityValidator.sanitize_string(dirty)
        self.assertNotIn('\x00', clean)
        self.assertNotIn('\r', clean)
        self.assertNotIn('\n', clean)


class TestUserModel(IsolatedDatabaseTestCase):
    """Tests para modelo User"""
    
    def setUp(self):
        super().setUp()
    
    def test_password_hashing(self):
        """Test que contraseña se hashea"""
        with self.app.app_context():
            user = User(email='test@example.com', username='testuser')
            user.set_password('password123')
            
            # No debe ser igual al texto plano
            self.assertNotEqual(user.password_hash, 'password123')
            
            # Debe verificarse correctamente
            self.assertTrue(user.check_password('password123'))
            self.assertFalse(user.check_password('wrongpassword'))
    
    def test_subscription_upgrade(self):
        """Test mejorar suscripción"""
        with self.app.app_context():
            user = User(
                email='test@example.com',
                username='testuser',
                subscription_plan='FREE'
            )
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            
            # Mejorar a PRO
            user.upgrade_subscription('PRO', 'sub_123')
            
            self.assertEqual(user.subscription_plan, 'PRO')
            self.assertEqual(user.subscription_status, 'active')
            self.assertIsNotNone(user.subscription_expires)
    
    def test_has_active_subscription(self):
        """Test verificar suscripción activa"""
        with self.app.app_context():
            # Free tier siempre activa
            free_user = User(
                email='free@example.com',
                username='freeuser',
                subscription_plan='FREE'
            )
            self.assertTrue(free_user.has_active_subscription())
            
            # Plan expirado
            expired_user = User(
                email='expired@example.com',
                username='expireduser',
                subscription_plan='PRO',
                subscription_expires=datetime.utcnow() - timedelta(days=1),
                subscription_status='active'
            )
            self.assertFalse(expired_user.has_active_subscription())


def run_tests():
    """Ejecutar tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Agregar tests
    suite.addTests(loader.loadTestsFromTestCase(TestAuthentication))
    suite.addTests(loader.loadTestsFromTestCase(TestSubscription))
    suite.addTests(loader.loadTestsFromTestCase(TestUserManagement))
    suite.addTests(loader.loadTestsFromTestCase(TestSecurity))
    suite.addTests(loader.loadTestsFromTestCase(TestUserModel))
    
    # Ejecutar
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
