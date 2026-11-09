#!/usr/bin/env python3
"""
Test Suite for Trading Platform
Tests for authentication, subscription, security
"""

import sys
import os
import smtplib

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
    from src.app import (
        app, db, User, LoginSession, BillingHistory, PasswordResetToken,
        PaymentTransaction, PaymentWebhookEvent
    )
    from src.security import SecurityValidator, request_counts
except ImportError:
    from app import (
        app, db, User, LoginSession, BillingHistory, PasswordResetToken,
        PaymentTransaction, PaymentWebhookEvent
    )
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

    def grant_test_subscription(self, user_id, plan):
        amount = 9.99 if plan == 'PRO' else 19.99
        with self.app.app_context():
            user = db.session.get(User, user_id)
            user.upgrade_subscription(plan)
            db.session.add(PaymentTransaction(
                user_id=user_id,
                provider='paypal',
                provider_reference=f'test-{user_id}-{plan}-{datetime.utcnow().timestamp()}',
                plan=plan,
                amount=amount,
                currency='USD',
                status='active'
            ))
            db.session.commit()


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

    def test_login_page_does_not_expose_default_demo_credentials(self):
        response = self.client.get('/login')
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('RyzA_', body)
        self.assertNotIn('SecurePass123', body)
        self.assertNotIn('password123', body)

    def test_authenticated_routes_reject_missing_and_invalid_session_tokens(self):
        self.client.post('/api/auth/register', json={
            'email': 'session@example.com',
            'username': 'sessionuser',
            'password': 'password123'
        })
        with self.client.session_transaction() as state:
            state.pop('session_token', None)
        self.assertEqual(self.client.get('/api/auth/me').status_code, 401)

        self.client.post('/api/auth/login', json={
            'email': 'session@example.com',
            'password': 'password123'
        })
        with self.client.session_transaction() as state:
            state['session_token'] = 'not-an-active-database-session'
        self.assertEqual(self.client.get('/api/auth/me').status_code, 401)

    def test_logout_revokes_database_session_token(self):
        self.client.post('/api/auth/register', json={
            'email': 'logout@example.com',
            'username': 'logoutuser',
            'password': 'password123'
        })
        with self.client.session_transaction() as state:
            token = state['session_token']

        response = self.client.post('/api/auth/logout')

        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            login_session = LoginSession.query.filter_by(
                session_token=token
            ).one()
            self.assertFalse(login_session.is_active)
        self.assertEqual(self.client.get('/api/auth/me').status_code, 401)

    def test_seeded_legacy_accounts_are_disabled_and_their_sessions_revoked(self):
        with self.app.app_context():
            seeded = User(
                email='admin@example.com',
                username='admin',
                subscription_plan='PREMIUM',
                subscription_status='active'
            )
            seeded.set_password('old_shared_password')
            db.session.add(seeded)
            db.session.commit()
            db.session.add(LoginSession(
                user_id=seeded.id,
                session_token='legacy-seeded-session',
                expires_at=datetime.utcnow() + timedelta(days=10),
                is_active=True
            ))
            db.session.commit()

        app_module.init_db(self.app)

        with self.app.app_context():
            seeded = User.query.filter_by(
                username='admin',
                email='admin@example.com'
            ).one()
            active_sessions = LoginSession.query.filter_by(
                user_id=seeded.id,
                is_active=True
            ).count()
            self.assertFalse(seeded.is_active)
            self.assertEqual(active_sessions, 0)

    def test_flask_secret_key_is_ephemeral_in_dev_and_required_in_production(self):
        first = app_module.resolve_flask_secret_key({'FLASK_ENV': 'development'})
        second = app_module.resolve_flask_secret_key({'FLASK_ENV': 'development'})

        self.assertNotEqual(first, second)
        with self.assertRaises(RuntimeError):
            app_module.resolve_flask_secret_key({'FLASK_ENV': 'production'})
        with self.assertRaises(RuntimeError):
            app_module.resolve_flask_secret_key({
                'FLASK_ENV': 'production',
                'FLASK_SECRET_KEY': 'short'
            })
        configured = 'x' * 48
        self.assertEqual(
            app_module.resolve_flask_secret_key({
                'FLASK_ENV': 'production',
                'FLASK_SECRET_KEY': configured
            }),
            configured
        )

    def test_empty_database_initialization_does_not_seed_shared_accounts(self):
        with patch.dict(os.environ, {'FLASK_ENV': 'production'}):
            app_module.init_db(self.app)

        with self.app.app_context():
            self.assertEqual(User.query.count(), 0)

    def test_initialization_disables_legacy_shared_accounts_and_revokes_sessions(self):
        with self.app.app_context():
            legacy = User(
                email='admin@example.com',
                username='admin',
                subscription_plan='PREMIUM'
            )
            legacy.set_password('legacy-password-123')
            customer = User(
                email='customer@example.com',
                username='customer',
                subscription_plan='FREE'
            )
            customer.set_password('customer-password-123')
            db.session.add_all((legacy, customer))
            db.session.commit()
            legacy_id = legacy.id
            customer_id = customer.id
            db.session.add(LoginSession(
                user_id=legacy_id,
                session_token='legacy-demo-session',
                expires_at=datetime.utcnow() + timedelta(days=1),
                is_active=True
            ))
            db.session.commit()

        app_module.init_db(self.app)

        with self.app.app_context():
            self.assertFalse(db.session.get(User, legacy_id).is_active)
            self.assertTrue(db.session.get(User, customer_id).is_active)
            self.assertEqual(
                LoginSession.query.filter_by(
                    user_id=legacy_id,
                    is_active=True
                ).count(),
                0
            )

    def test_production_secret_must_be_unique_configured_and_long_enough(self):
        first = app_module.resolve_flask_secret_key({'FLASK_ENV': 'development'})
        second = app_module.resolve_flask_secret_key({'FLASK_ENV': 'development'})
        self.assertNotEqual(first, second)
        with self.assertRaises(RuntimeError):
            app_module.resolve_flask_secret_key({'FLASK_ENV': 'production'})
        with self.assertRaises(RuntimeError):
            app_module.resolve_flask_secret_key({
                'FLASK_ENV': 'production',
                'FLASK_SECRET_KEY': 'short'
            })
        configured = 'secure-production-key-' * 3
        self.assertEqual(
            app_module.resolve_flask_secret_key({
                'FLASK_ENV': 'production',
                'FLASK_SECRET_KEY': configured
            }),
            configured
        )

    def test_initialization_revokes_only_legacy_shared_demo_accounts(self):
        with self.app.app_context():
            legacy = User(
                email='admin@example.com',
                username='admin',
                subscription_plan='PREMIUM'
            )
            legacy.set_password('legacy-password-123')
            ordinary = User(
                email='customer@example.com',
                username='customer',
                subscription_plan='FREE'
            )
            ordinary.set_password('customer-password-123')
            db.session.add_all([legacy, ordinary])
            db.session.commit()
            legacy_id = legacy.id
            ordinary_id = ordinary.id
            db.session.add(LoginSession(
                user_id=legacy_id,
                session_token='legacy-active-session',
                expires_at=datetime.utcnow() + timedelta(days=1),
                is_active=True
            ))
            db.session.commit()

        app_module.init_db(self.app)

        with self.app.app_context():
            legacy = db.session.get(User, legacy_id)
            ordinary = db.session.get(User, ordinary_id)
            self.assertFalse(legacy.is_active)
            self.assertTrue(ordinary.is_active)
            self.assertEqual(
                LoginSession.query.filter_by(
                    user_id=legacy_id,
                    is_active=True
                ).count(),
                0
            )

    def test_secret_key_resolution_rejects_missing_or_short_production_secret(self):
        self.assertNotEqual(
            app_module.resolve_flask_secret_key({'FLASK_ENV': 'development'}),
            app_module.resolve_flask_secret_key({'FLASK_ENV': 'development'})
        )
        for secret in ('', 'short'):
            with self.assertRaises(RuntimeError):
                app_module.resolve_flask_secret_key({
                    'FLASK_ENV': 'production',
                    'FLASK_SECRET_KEY': secret
                })
        long_secret = 'x' * 48
        self.assertEqual(
            app_module.resolve_flask_secret_key({
                'FLASK_ENV': 'production',
                'FLASK_SECRET_KEY': long_secret
            }),
            long_secret
        )

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
        """Paid plans cannot be assigned without provider checkout."""
        with self.app.test_client() as c:
            c.post('/api/auth/login', json={
                'email': 'test@example.com',
                'password': 'password123'
            })
            response = c.post('/api/subscription/upgrade', json={
                'plan': 'PRO'
            })
            self.assertEqual(response.status_code, 410)
            self.assertIn('checkout', response.get_json()['error'].lower())
            with self.app.app_context():
                user = db.session.get(User, self.user_id)
                self.assertEqual(user.subscription_plan, 'FREE')

    def test_paypal_checkout_requires_login(self):
        response = self.app.test_client().post(
            '/api/subscription/checkout',
            json={'plan': 'PRO'}
        )

        self.assertEqual(response.status_code, 401)

    def test_paypal_checkout_disabled_until_sandbox_credentials_are_configured(self):
        self.client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'password123'
        })
        with patch.object(app_module.paypal_payments, 'is_configured', return_value=False):
            response = self.client.post(
                '/api/subscription/checkout',
                json={'plan': 'PRO'}
            )

        self.assertEqual(response.status_code, 503)
        with self.app.app_context():
            self.assertEqual(db.session.get(User, self.user_id).subscription_plan, 'FREE')
            self.assertEqual(PaymentTransaction.query.count(), 0)

    def test_paypal_checkout_creates_pending_transaction_but_not_entitlement(self):
        self.client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'password123'
        })
        provider_response = {
            'id': 'I-SANDBOX123',
            'links': [{
                'rel': 'approve',
                'href': 'https://www.sandbox.paypal.com/checkoutnow?token=I-SANDBOX123'
            }]
        }
        with patch.object(app_module.paypal_payments, 'is_configured', return_value=True), \
                patch.object(
                    app_module.paypal_payments,
                    'create_subscription',
                    return_value=provider_response
                ):
            response = self.client.post(
                '/api/subscription/checkout',
                json={'plan': 'PRO'}
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()['approval_url'], provider_response['links'][0]['href'])
        with self.app.app_context():
            user = db.session.get(User, self.user_id)
            transaction = PaymentTransaction.query.one()
            self.assertEqual(user.subscription_plan, 'FREE')
            self.assertEqual(transaction.provider, 'paypal')
            self.assertEqual(transaction.provider_reference, 'I-SANDBOX123')
            self.assertEqual(transaction.status, 'pending')

    def test_paypal_checkout_rejects_non_paypal_approval_url(self):
        self.client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'password123'
        })
        with patch.object(app_module.paypal_payments, 'is_configured', return_value=True), \
                patch.object(
                    app_module.paypal_payments,
                    'create_subscription',
                    return_value={
                        'id': 'I-SANDBOX123',
                        'links': [{'rel': 'approve', 'href': 'https://evil.example/checkout'}]
                    }
                ):
            response = self.client.post(
                '/api/subscription/checkout',
                json={'plan': 'PRO'}
            )

        self.assertEqual(response.status_code, 502)
        with self.app.app_context():
            self.assertEqual(PaymentTransaction.query.count(), 0)
            self.assertEqual(db.session.get(User, self.user_id).subscription_plan, 'FREE')

    def test_paypal_return_activates_only_a_paid_matching_subscription(self):
        with self.app.app_context():
            db.session.add(PaymentTransaction(
                user_id=self.user_id,
                provider='paypal',
                provider_reference='I-PAID',
                plan='PRO',
                amount=9.99,
                currency='USD',
                status='pending'
            ))
            db.session.commit()
        self.client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'password123'
        })
        provider_subscription = {
            'id': 'I-PAID',
            'status': 'ACTIVE',
            'plan_id': 'P-PRO',
            'custom_id': f'trading-platform:user:{self.user_id}:plan:PRO',
            'billing_info': {
                'last_payment': {
                    'amount': {'value': '9.99', 'currency_code': 'USD'}
                }
            }
        }
        plan_details = {
            'id': 'P-PRO',
            'billing_cycles': [{
                'tenure_type': 'REGULAR',
                'frequency': {'interval_unit': 'MONTH', 'interval_count': 1},
                'pricing_scheme': {
                    'fixed_price': {'value': '9.99', 'currency_code': 'USD'}
                }
            }]
        }
        with patch.object(app_module.paypal_payments, 'plan_id', return_value='P-PRO'), \
                patch.object(
                    app_module.paypal_payments,
                    'get_subscription',
                    return_value=provider_subscription
                ), patch.object(
                    app_module.paypal_payments,
                    'get_plan_details',
                    return_value=plan_details
                ):
            response = self.client.get('/billing/paypal/return?subscription_id=I-PAID')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], '/dashboard?payment=success')
        with self.app.app_context():
            user = db.session.get(User, self.user_id)
            transaction = PaymentTransaction.query.filter_by(
                provider_reference='I-PAID'
            ).one()
            self.assertEqual(user.subscription_plan, 'PRO')
            self.assertEqual(transaction.status, 'active')
            self.assertTrue(app_module.has_verified_paid_subscription(user))
            self.assertEqual(BillingHistory.query.count(), 1)

    def test_paypal_return_rejects_unpaid_or_wrong_price_subscription(self):
        with self.app.app_context():
            db.session.add(PaymentTransaction(
                user_id=self.user_id,
                provider='paypal',
                provider_reference='I-UNPAID',
                plan='PRO',
                amount=9.99,
                currency='USD',
                status='pending'
            ))
            db.session.commit()
        self.client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'password123'
        })
        provider_subscription = {
            'id': 'I-UNPAID',
            'status': 'ACTIVE',
            'plan_id': 'P-PRO',
            'custom_id': f'trading-platform:user:{self.user_id}:plan:PRO',
            'billing_info': {
                'last_payment': {
                    'amount': {'value': '0.01', 'currency_code': 'USD'}
                }
            }
        }
        plan_details = {
            'id': 'P-PRO',
            'billing_cycles': [{
                'tenure_type': 'REGULAR',
                'frequency': {'interval_unit': 'MONTH', 'interval_count': 1},
                'pricing_scheme': {
                    'fixed_price': {'value': '9.99', 'currency_code': 'USD'}
                }
            }]
        }
        with patch.object(app_module.paypal_payments, 'plan_id', return_value='P-PRO'), \
                patch.object(
                    app_module.paypal_payments,
                    'get_subscription',
                    return_value=provider_subscription
                ), patch.object(
                    app_module.paypal_payments,
                    'get_plan_details',
                    return_value=plan_details
                ):
            response = self.client.get('/billing/paypal/return?subscription_id=I-UNPAID')

        self.assertEqual(response.headers['Location'], '/dashboard?payment=pending')
        with self.app.app_context():
            user = db.session.get(User, self.user_id)
            self.assertEqual(user.subscription_plan, 'FREE')
            transaction = PaymentTransaction.query.filter_by(
                provider_reference='I-UNPAID'
            ).one()
            self.assertEqual(transaction.status, 'pending')
            self.assertEqual(BillingHistory.query.count(), 0)

    def test_paypal_webhook_rejects_unverified_event(self):
        with patch.object(app_module.paypal_payments, 'verify_webhook', return_value=False):
            response = self.client.post(
                '/api/payments/paypal/webhook',
                json={'id': 'WH-FAKE', 'event_type': 'BILLING.SUBSCRIPTION.ACTIVATED'}
            )

        self.assertEqual(response.status_code, 400)
        with self.app.app_context():
            self.assertEqual(PaymentWebhookEvent.query.count(), 0)

    def test_paypal_webhook_activates_a_matching_paid_subscription_once(self):
        with self.app.app_context():
            db.session.add(PaymentTransaction(
                user_id=self.user_id,
                provider='paypal',
                provider_reference='I-WEBHOOK',
                plan='PRO',
                amount=9.99,
                currency='USD',
                status='pending'
            ))
            db.session.commit()
        event = {
            'id': 'WH-UNIQUE-1',
            'event_type': 'BILLING.SUBSCRIPTION.ACTIVATED',
            'resource': {'id': 'I-WEBHOOK'},
            'create_time': datetime.utcnow().isoformat() + 'Z'
        }
        subscription = {
            'id': 'I-WEBHOOK',
            'status': 'ACTIVE',
            'plan_id': 'P-PRO',
            'custom_id': f'trading-platform:user:{self.user_id}:plan:PRO',
            'billing_info': {
                'last_payment': {
                    'id': 'PAYMENT-1',
                    'time': datetime.utcnow().isoformat() + 'Z',
                    'amount': {'value': '9.99', 'currency_code': 'USD'}
                },
                'next_billing_time': (
                    datetime.utcnow() + timedelta(days=30)
                ).isoformat() + 'Z'
            }
        }
        plan = {
            'id': 'P-PRO',
            'billing_cycles': [{
                'tenure_type': 'REGULAR',
                'frequency': {'interval_unit': 'MONTH', 'interval_count': 1},
                'pricing_scheme': {
                    'fixed_price': {'value': '9.99', 'currency_code': 'USD'}
                }
            }]
        }
        with patch.object(app_module.paypal_payments, 'verify_webhook', return_value=True), \
                patch.object(app_module.paypal_payments, 'plan_id', return_value='P-PRO'), \
                patch.object(app_module.paypal_payments, 'get_subscription', return_value=subscription), \
                patch.object(app_module.paypal_payments, 'get_plan_details', return_value=plan):
            first = self.client.post('/api/payments/paypal/webhook', json=event)
            duplicate = self.client.post('/api/payments/paypal/webhook', json=event)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(duplicate.status_code, 200)
        self.assertTrue(duplicate.get_json()['duplicate'])
        with self.app.app_context():
            user = db.session.get(User, self.user_id)
            transaction = PaymentTransaction.query.filter_by(
                provider_reference='I-WEBHOOK'
            ).one()
            self.assertEqual(user.subscription_plan, 'PRO')
            self.assertEqual(transaction.status, 'active')
            self.assertEqual(PaymentWebhookEvent.query.count(), 1)
            self.assertEqual(BillingHistory.query.count(), 1)

    def test_paypal_cancel_calls_provider_then_removes_paid_entitlement(self):
        self.grant_test_subscription(self.user_id, 'PRO')
        with self.app.app_context():
            transaction = PaymentTransaction.query.filter_by(
                user_id=self.user_id,
                provider='paypal'
            ).one()
            provider_reference = transaction.provider_reference
        self.client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'password123'
        })
        with patch.object(app_module.paypal_payments, 'cancel_subscription') as cancel:
            response = self.client.post('/api/subscription/cancel')

        self.assertEqual(response.status_code, 200)
        cancel.assert_called_once_with(
            provider_reference,
            'Cancellation requested by subscriber'
        )
        with self.app.app_context():
            user = db.session.get(User, self.user_id)
            transaction = PaymentTransaction.query.filter_by(
                provider_reference=provider_reference
            ).one()
            self.assertEqual(user.subscription_plan, 'FREE')
            self.assertEqual(transaction.status, 'cancelled')

    def test_paypal_webhook_activates_and_deduplicates_verified_event(self):
        with self.app.app_context():
            db.session.add(PaymentTransaction(
                user_id=self.user_id,
                provider='paypal',
                provider_reference='I-WEBHOOK',
                plan='PRO',
                amount=9.99,
                currency='USD',
                status='pending'
            ))
            db.session.commit()
        event = {
            'id': 'WH-UNIQUE-1',
            'event_type': 'BILLING.SUBSCRIPTION.ACTIVATED',
            'resource': {'id': 'I-WEBHOOK'},
            'create_time': datetime.utcnow().isoformat() + 'Z'
        }
        provider_subscription = {
            'id': 'I-WEBHOOK',
            'status': 'ACTIVE',
            'plan_id': 'P-PRO',
            'custom_id': f'trading-platform:user:{self.user_id}:plan:PRO',
            'billing_info': {
                'last_payment': {
                    'id': 'PAYMENT-1',
                    'time': datetime.utcnow().isoformat() + 'Z',
                    'amount': {'value': '9.99', 'currency_code': 'USD'}
                }
            }
        }
        plan_details = {
            'id': 'P-PRO',
            'billing_cycles': [{
                'tenure_type': 'REGULAR',
                'frequency': {'interval_unit': 'MONTH', 'interval_count': 1},
                'pricing_scheme': {
                    'fixed_price': {'value': '9.99', 'currency_code': 'USD'}
                }
            }]
        }
        with patch.object(app_module.paypal_payments, 'verify_webhook', return_value=True), \
                patch.object(app_module.paypal_payments, 'plan_id', return_value='P-PRO'), \
                patch.object(
                    app_module.paypal_payments,
                    'get_subscription',
                    return_value=provider_subscription
                ), patch.object(
                    app_module.paypal_payments,
                    'get_plan_details',
                    return_value=plan_details
                ):
            first = self.client.post('/api/payments/paypal/webhook', json=event)
            second = self.client.post('/api/payments/paypal/webhook', json=event)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.get_json()['duplicate'])
        with self.app.app_context():
            user = db.session.get(User, self.user_id)
            transaction = PaymentTransaction.query.filter_by(
                provider_reference='I-WEBHOOK'
            ).one()
            self.assertEqual(user.subscription_plan, 'PRO')
            self.assertEqual(transaction.status, 'active')
            self.assertEqual(PaymentWebhookEvent.query.count(), 1)
            self.assertEqual(BillingHistory.query.count(), 1)

    def test_paypal_subscription_cancellation_calls_provider_and_revokes_plan(self):
        self.grant_test_subscription(self.user_id, 'PRO')
        with self.app.app_context():
            transaction = PaymentTransaction.query.filter_by(
                user_id=self.user_id,
                provider='paypal'
            ).one()
            provider_reference = transaction.provider_reference
        self.client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'password123'
        })

        with patch.object(app_module.paypal_payments, 'cancel_subscription') as cancel:
            response = self.client.post('/api/subscription/cancel')

        self.assertEqual(response.status_code, 200)
        cancel.assert_called_once_with(
            provider_reference,
            'Cancellation requested by subscriber'
        )
        with self.app.app_context():
            user = db.session.get(User, self.user_id)
            transaction = PaymentTransaction.query.filter_by(
                provider_reference=provider_reference
            ).one()
            self.assertEqual(user.subscription_plan, 'FREE')
            self.assertEqual(transaction.status, 'cancelled')

    def test_paypal_subscription_cancel_calls_provider_before_revoking_local_access(self):
        self.grant_test_subscription(self.user_id, 'PRO')
        with self.app.app_context():
            transaction = PaymentTransaction.query.filter_by(
                user_id=self.user_id,
                provider='paypal'
            ).one()
        client = self.app.test_client()
        client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'password123'
        })
        with patch.object(app_module.paypal_payments, 'cancel_subscription') as cancel:
            response = client.post('/api/subscription/cancel')

        self.assertEqual(response.status_code, 200)
        cancel.assert_called_once_with(
            transaction.provider_reference,
            'Cancellation requested by subscriber'
        )
        with self.app.app_context():
            user = db.session.get(User, self.user_id)
            updated = PaymentTransaction.query.get(transaction.id)
            self.assertEqual(user.subscription_plan, 'FREE')
            self.assertEqual(updated.status, 'cancelled')

    def test_legacy_paid_plan_without_provider_payment_has_no_paid_entitlement(self):
        with self.app.app_context():
            user = db.session.get(User, self.user_id)
            user.upgrade_subscription('PRO')
            db.session.commit()
        self.client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'password123'
        })

        prediction = self.client.get('/api/advanced-prediction')
        subscription = self.client.get('/api/subscription/current').get_json()['subscription']

        self.assertEqual(prediction.status_code, 403)
        self.assertEqual(subscription['plan'], 'FREE')
        self.assertEqual(subscription['status'], 'payment_required')

    def test_renew_and_cancel_subscription(self):
        """Renewal cannot fabricate payment; FREE account cannot cancel."""
        with self.app.test_client() as c:
            c.post('/api/auth/login', json={
                'email': 'test@example.com',
                'password': 'password123'
            })
            renew_resp = c.post('/api/subscription/renew')
            self.assertEqual(renew_resp.status_code, 410)
            cancel_resp = c.post('/api/subscription/cancel')
            self.assertEqual(cancel_resp.status_code, 400)

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
            
            self.grant_test_subscription(self.user_id, 'PRO')
            resp_pro = c.get('/api/advanced-prediction')
            self.assertEqual(resp_pro.status_code, 200)
            
            # PRO user blocked from PREMIUM analysis
            resp_prem = c.get('/api/professional-analysis')
            self.assertEqual(resp_prem.status_code, 403)
            
            self.grant_test_subscription(self.user_id, 'PREMIUM')
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
        self.grant_test_subscription(self.user_id, 'PRO')

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
            self.grant_test_subscription(self.user_id, 'PRO')
            response = self.client.post('/api/chat', json={'message': 'precio'})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['success'])

    def test_demo_trade_chat_command_requires_premium(self):
        self.client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'password123'
        })
        self.grant_test_subscription(self.user_id, 'PRO')
        with patch.object(app_module, 'start_demo_chat_trade_job') as start_job:
            response = self.client.post('/api/chat/command', json={
                'command': '/trade auto demo XAUUSD'
            })

        self.assertEqual(response.status_code, 403)
        self.assertFalse(start_job.called)

    def test_premium_demo_trade_chat_command_starts_one_job(self):
        self.client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'password123'
        })
        self.grant_test_subscription(self.user_id, 'PREMIUM')
        with patch.object(
            app_module, 'start_demo_chat_trade_job', return_value='demo-job-123'
        ) as start_job:
            response = self.client.post('/api/chat/command', json={
                'command': '/trade auto demo XAUUSD'
            })

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.get_json()['job_id'], 'demo-job-123')
        self.assertEqual(response.get_json()['status'], 'queued')
        start_job.assert_called_once_with(self.user_id, 'XAUUSD')

    def test_demo_trade_chat_command_rejects_bad_symbol(self):
        self.client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'password123'
        })
        self.grant_test_subscription(self.user_id, 'PREMIUM')
        with patch.object(app_module, 'start_demo_chat_trade_job') as start_job:
            response = self.client.post('/api/chat/command', json={
                'command': '/trade auto demo BTCUSD'
            })

        self.assertEqual(response.status_code, 400)
        self.assertFalse(start_job.called)

    def test_demo_trade_job_status_is_private_to_requesting_user(self):
        with self.app.app_context():
            other_user = User(
                email='other-demo@example.com',
                username='other_demo',
                subscription_plan='PREMIUM',
                subscription_status='active',
                subscription_expires=datetime.utcnow() + timedelta(days=30)
            )
            other_user.set_password('password123')
            db.session.add(other_user)
            db.session.commit()
            other_user_id = other_user.id
        job_id = 'private-demo-job'
        with app_module._demo_chat_trade_jobs_lock:
            app_module.DEMO_CHAT_TRADE_JOBS[job_id] = {
                'job_id': job_id,
                'user_id': self.user_id,
                'symbol': 'XAUUSD',
                'status': 'completed',
                'message': 'done'
            }

        try:
            self.client.post('/api/auth/login', json={
                'email': 'test@example.com',
                'password': 'password123'
            })
            self.grant_test_subscription(self.user_id, 'PREMIUM')
            self.grant_test_subscription(other_user_id, 'PREMIUM')
            owner_response = self.client.get(f'/api/chat/demo-trade/{job_id}')
            other_client = self.app.test_client()
            other_client.post('/api/auth/login', json={
                'email': 'other-demo@example.com',
                'password': 'password123'
            })
            other_response = other_client.get(f'/api/chat/demo-trade/{job_id}')

            self.assertEqual(owner_response.status_code, 200)
            self.assertEqual(other_response.status_code, 404)
        finally:
            with app_module._demo_chat_trade_jobs_lock:
                app_module.DEMO_CHAT_TRADE_JOBS.pop(job_id, None)

    def test_dashboard_exposes_premium_demo_trade_command(self):
        from src.app import DASHBOARD_HTML

        self.assertIn('/trade auto demo XAUUSD', DASHBOARD_HTML)
        self.assertIn('function pollDemoTradeJob(jobId)', DASHBOARD_HTML)
        self.assertIn("fetch(isCommand ? '/api/chat/command' : '/api/chat'", DASHBOARD_HTML)

    def test_premium_professional_analysis_is_cached_for_five_minutes(self):
        user_id = self.user_id
        symbol = app_module.TRADING_DATA['symbol']
        app_module._professional_analysis_cache.pop((user_id, symbol), None)
        self.grant_test_subscription(user_id, 'PREMIUM')

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
        self.grant_test_subscription(other_user_id, 'PRO')
        app_module.CHAT_HISTORY_BY_USER.pop(self.user_id, None)
        app_module.CHAT_HISTORY_BY_USER.pop(other_user_id, None)
        first_client = self.app.test_client()
        second_client = self.app.test_client()
        first_client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'password123'
        })
        self.grant_test_subscription(self.user_id, 'PRO')
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
            self.user_id = self.user.id
            
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
        """Recovery codes are delivered out of band and never returned in API JSON."""
        self.client.post('/api/auth/login', json={
            'email': 'user@example.com',
            'password': 'oldpassword123'
        })
        with patch.object(app_module, '_password_reset_email_settings', return_value={
            'host': 'smtp.example.test',
            'port': 587,
            'sender': 'no-reply@example.com',
            'username': 'smtp-user',
            'password': 'smtp-secret',
            'use_ssl': False,
            'use_starttls': True
        }), patch.object(app_module, '_send_password_reset_email') as send_email:
            forgot_resp = self.client.post(
                '/api/auth/forgot-password',
                json={'email': 'user@example.com'}
            )

        self.assertEqual(forgot_resp.status_code, 202)
        data = forgot_resp.get_json()
        self.assertNotIn('reset_token', data)
        send_email.assert_called_once()
        token = send_email.call_args.args[1]
        with self.app.app_context():
            reset_record = PasswordResetToken.query.one()
            self.assertNotEqual(reset_record.token, token)
            self.assertEqual(
                reset_record.token,
                app_module._password_reset_token_digest(token)
            )
        
        reset_resp = self.client.post('/api/auth/reset-password', json={'token': token, 'new_password': 'resetpass123'})
        self.assertEqual(reset_resp.status_code, 200)
        self.assertTrue(reset_resp.get_json()['success'])
        with self.app.app_context():
            user = db.session.get(User, self.user_id)
            self.assertTrue(all(reset_token.is_used for reset_token in user.reset_tokens))
        self.assertEqual(self.client.get('/api/auth/me').status_code, 401)

    def test_password_recovery_requires_mail_configuration(self):
        with patch.object(
            app_module,
            '_password_reset_email_settings',
            side_effect=app_module.PasswordResetDeliveryError('SMTP missing')
        ):
            response = self.client.post(
                '/api/auth/forgot-password',
                json={'email': 'user@example.com'}
            )

        self.assertEqual(response.status_code, 503)
        self.assertNotIn('reset_token', response.get_json())

    def test_password_recovery_delivery_failure_does_not_expose_account_existence(self):
        with patch.object(app_module, '_password_reset_email_settings', return_value={
            'host': 'smtp.example.test',
            'port': 587,
            'sender': 'no-reply@example.com',
            'username': 'smtp-user',
            'password': 'smtp-secret',
            'use_ssl': False,
            'use_starttls': True
        }), patch.object(
            app_module,
            '_send_password_reset_email',
            side_effect=smtplib.SMTPException('mail server unavailable')
        ):
            response = self.client.post(
                '/api/auth/forgot-password',
                json={'email': 'user@example.com'}
            )

        self.assertEqual(response.status_code, 202)
        self.assertNotIn('reset_token', response.get_json())
        with self.app.app_context():
            token = PasswordResetToken.query.one()
            self.assertTrue(token.is_used)


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
            user.upgrade_subscription('PRO')
            
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
