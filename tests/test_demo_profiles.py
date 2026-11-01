import importlib
import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from flask import Flask

from src.models import User, db, init_db

app_module = importlib.import_module('src.app')


class TestDemoProfiles(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
            SQLALCHEMY_TRACK_MODIFICATIONS=False
        )
        db.init_app(self.app)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_expired_demo_plan_is_restored_for_local_feature_testing(self):
        with patch.dict(os.environ, {'FLASK_ENV': 'development'}):
            init_db(self.app)
            with self.app.app_context():
                trader = User.query.filter_by(username='trader').one()
                trader.subscription_plan = 'FREE'
                trader.subscription_status = 'expired'
                trader.subscription_expires = datetime.utcnow() - timedelta(days=1)
                db.session.commit()

            init_db(self.app)

        with self.app.app_context():
            trader = User.query.filter_by(username='trader').one()
            self.assertEqual(trader.subscription_plan, 'PRO')
            self.assertTrue(trader.has_active_subscription())
            self.assertGreater(trader.subscription_expires, datetime.utcnow())

    def test_login_page_reports_database_unavailable(self):
        with patch.object(app_module, 'DB_AVAILABLE', False):
            response = app_module.app.test_client().get('/login')

        self.assertEqual(response.status_code, 503)
        self.assertIn('Autenticación no disponible', response.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
