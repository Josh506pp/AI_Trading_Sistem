import importlib
import os
import tempfile
import unittest
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

    def test_database_path_can_use_a_persistent_host_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            configured_path = os.path.join(directory, 'persistent', 'trading.db')
            resolved_path = app_module.resolve_database_path(
                {'DATABASE_PATH': configured_path},
                'default.db'
            )

        self.assertEqual(resolved_path, os.path.abspath(configured_path))

    def test_database_initialization_does_not_seed_shared_demo_accounts(self):
        init_db(self.app)
        with self.app.app_context():
            self.assertEqual(
                User.query.filter(
                    User.username.in_(('admin', 'trader', 'demo'))
                ).count(),
                0
            )

    def test_login_page_reports_database_unavailable(self):
        with patch.object(app_module, 'DB_AVAILABLE', False):
            response = app_module.app.test_client().get('/login')

        self.assertEqual(response.status_code, 503)
        self.assertIn('Autenticación no disponible', response.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
