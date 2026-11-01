#!/usr/bin/env python3
"""
Database Models for Trading Platform
Users, subscriptions, trades, etc.
"""

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os

db = SQLAlchemy()

class User(db.Model):
    """Usuario de la plataforma de trading"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    username = db.Column(db.String(128), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Perfil
    full_name = db.Column(db.String(255))
    avatar_url = db.Column(db.String(512))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Suscripción
    subscription_plan = db.Column(db.String(50), default='FREE')  # FREE, PRO, PREMIUM
    subscription_expires = db.Column(db.DateTime)
    subscription_status = db.Column(db.String(50), default='active')  # active, canceled, expired
    
    # Billings
    stripe_customer_id = db.Column(db.String(255))
    stripe_subscription_id = db.Column(db.String(255))
    payment_method_last4 = db.Column(db.String(4))
    
    # Trading stats
    balance = db.Column(db.Float, default=10000.0)
    total_trades = db.Column(db.Integer, default=0)
    winning_trades = db.Column(db.Integer, default=0)
    
    # Active status
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    
    # Relations
    login_sessions = db.relationship('LoginSession', back_populates='user', cascade='all, delete-orphan')
    billing_history = db.relationship('BillingHistory', back_populates='user', cascade='all, delete-orphan')
    reset_tokens = db.relationship('PasswordResetToken', back_populates='user', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash y guardar contraseña"""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    def check_password(self, password):
        """Verificar contraseña"""
        return check_password_hash(self.password_hash, password)
    
    def has_active_subscription(self):
        """Verificar si tiene suscripción activa"""
        if self.subscription_plan == 'FREE':
            return True
        if not self.subscription_expires:
            return False
        return datetime.utcnow() < self.subscription_expires and self.subscription_status == 'active'
    
    def upgrade_subscription(self, plan, stripe_sub_id=None):
        """Mejorar plan de suscripción"""
        # Precios y duraciones
        plan_config = {
            'FREE': {'price': 0, 'duration_days': None},
            'PRO': {'price': 9.99, 'duration_days': 30},
            'PREMIUM': {'price': 19.99, 'duration_days': 30}
        }
        
        if plan not in plan_config:
            return False
        
        self.subscription_plan = plan
        self.stripe_subscription_id = stripe_sub_id
        
        config = plan_config[plan]
        if config['duration_days']:
            self.subscription_expires = datetime.utcnow() + timedelta(days=config['duration_days'])
        
        self.subscription_status = 'active'
        return True
    
    def cancel_subscription(self):
        """Cancelar suscripción"""
        self.subscription_status = 'canceled'
        self.subscription_plan = 'FREE'
    
    def to_dict(self, include_sensitive=False):
        """Convertir a diccionario"""
        data = {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'full_name': self.full_name,
            'avatar_url': self.avatar_url,
            'subscription_plan': self.subscription_plan,
            'subscription_expires': self.subscription_expires.isoformat() if self.subscription_expires else None,
            'subscription_status': self.subscription_status,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'balance': self.balance,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'win_rate': (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        }
        
        if include_sensitive:
            data['email'] = self.email
            data['payment_method_last4'] = self.payment_method_last4
        
        return data


class LoginSession(db.Model):
    """Sesión de login de usuario"""
    __tablename__ = 'login_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(512))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    user = db.relationship('User', back_populates='login_sessions')
    
    def is_valid(self):
        """Verificar si sesión es válida"""
        if not self.is_active:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True
    
    def update_activity(self):
        """Actualizar último acceso"""
        self.last_activity = datetime.utcnow()


class PasswordResetToken(db.Model):
    """Token de recuperación de contraseña"""
    __tablename__ = 'password_reset_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    
    user = db.relationship('User', back_populates='reset_tokens')
    
    def is_valid(self):
        """Verificar si el token de recuperación es válido"""
        if self.is_used:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True
        self.status = 'closed'
        self.closed_at = datetime.utcnow()
        
        if self.direction == 'BUY':
            self.profit_loss = (exit_price - self.entry_price) * self.quantity
        else:
            self.profit_loss = (self.entry_price - exit_price) * self.quantity
        
        self.profit_loss_pct = (self.profit_loss / (self.entry_price * self.quantity) * 100) if self.entry_price > 0 else 0
    
    def to_dict(self):
        """Convertir a diccionario"""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'direction': self.direction,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'quantity': self.quantity,
            'profit_loss': self.profit_loss,
            'profit_loss_pct': self.profit_loss_pct,
            'status': self.status,
            'opened_at': self.opened_at.isoformat(),
            'closed_at': self.closed_at.isoformat() if self.closed_at else None
        }


class BillingHistory(db.Model):
    """Historial de pagos"""
    __tablename__ = 'billing_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Billing info
    plan = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    
    # Payment info
    stripe_invoice_id = db.Column(db.String(255))
    stripe_charge_id = db.Column(db.String(255))
    status = db.Column(db.String(50), nullable=False)  # succeeded, pending, failed
    
    # Dates
    charged_at = db.Column(db.DateTime, default=datetime.utcnow)
    period_start = db.Column(db.DateTime)
    period_end = db.Column(db.DateTime)
    
    # Description
    description = db.Column(db.String(512))
    
    user = db.relationship('User', back_populates='billing_history')
    
    def to_dict(self):
        """Convertir a diccionario"""
        return {
            'id': self.id,
            'plan': self.plan,
            'amount': self.amount,
            'currency': self.currency,
            'status': self.status,
            'charged_at': self.charged_at.isoformat(),
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'description': self.description
        }


def init_db(app):
    """Inicializar base de datos y usuarios demo"""
    with app.app_context():
        db.create_all()
        if User.query.count() == 0:
            try:
                admin = User(
                    email='admin@example.com',
                    username='admin',
                    full_name='Administrador',
                    subscription_plan='PREMIUM',
                    subscription_status='active',
                    subscription_expires=datetime.utcnow() + timedelta(days=365)
                )
                admin.set_password('RyzA_jjITjuPQtV66Wwf0A')
                
                trader = User(
                    email='trader@example.com',
                    username='trader',
                    full_name='Trader Profesional',
                    subscription_plan='PRO',
                    subscription_status='active',
                    subscription_expires=datetime.utcnow() + timedelta(days=30)
                )
                trader.set_password('SecurePass123')
                
                demo = User(
                    email='demo@example.com',
                    username='demo',
                    full_name='Usuario Demo',
                    subscription_plan='FREE',
                    subscription_status='active'
                )
                demo.set_password('password123')
                
                db.session.add_all([admin, trader, demo])
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Error al crear usuarios iniciales: {e}")

        if os.environ.get('FLASK_ENV', '').lower() != 'production':
            now = datetime.utcnow()
            demo_profiles = (
                ('admin', 'admin@example.com', 'PREMIUM', 365),
                ('trader', 'trader@example.com', 'PRO', 30),
                ('demo', 'demo@example.com', 'FREE', None),
            )
            for username, email, plan, duration_days in demo_profiles:
                user = User.query.filter_by(username=username, email=email).first()
                if not user:
                    continue
                subscription_expired = (
                    duration_days is not None and
                    (not user.subscription_expires or user.subscription_expires <= now)
                )
                if (
                    user.subscription_plan != plan or
                    user.subscription_status != 'active' or
                    subscription_expired
                ):
                    user.subscription_plan = plan
                    user.subscription_status = 'active'
                    user.subscription_expires = (
                        now + timedelta(days=duration_days) if duration_days else None
                    )
            db.session.commit()
