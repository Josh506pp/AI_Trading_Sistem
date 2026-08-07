import os
import tempfile
import unittest
from importlib import util
from unittest import mock


APP_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src', 'app.py')
spec = util.spec_from_file_location('app_module', APP_PATH)
app_module = util.module_from_spec(spec)
spec.loader.exec_module(app_module)


class TestMT5PathDetection(unittest.TestCase):
    def test_detects_terminal_in_nested_program_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            mt5_dir = os.path.join(tmp_dir, 'Program Files', 'MetaTrader 5')
            os.makedirs(mt5_dir, exist_ok=True)
            target_path = os.path.join(mt5_dir, 'terminal64.exe')
            with open(target_path, 'w', encoding='utf-8'):
                pass

            with mock.patch.dict(os.environ, {'PROGRAMFILES': os.path.join(tmp_dir, 'Program Files')}, clear=False):
                detected = app_module.find_mt5_terminal_path()

            self.assertEqual(detected, target_path)

    def test_status_keeps_connected_with_cached_account_info(self):
        app_module.MT5_CONNECTED = True
        app_module.MT5_ACCOUNT_INFO = type('Info', (), {'login': 123456, 'server': 'Demo', 'balance': 1000.0, 'equity': 1000.0, 'profit': 0.0, 'currency': 'USD'})()

        with mock.patch.object(app_module, 'MT5_AVAILABLE', True), \
             mock.patch.object(app_module, 'mt5') as mt5_mock:
            mt5_mock.account_info.side_effect = RuntimeError('temporary issue')
            status = app_module.mt5_status()

        self.assertTrue(status['connected'])
        self.assertEqual(status['login'], '123456')

    def test_resolves_directory_to_terminal_executable(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            mt5_dir = os.path.join(tmp_dir, 'MetaTrader 5')
            os.makedirs(mt5_dir, exist_ok=True)
            terminal_path = os.path.join(mt5_dir, 'terminal64.exe')
            with open(terminal_path, 'w', encoding='utf-8'):
                pass

            normalized = app_module.resolve_mt5_terminal_path(mt5_dir)

        self.assertEqual(normalized, terminal_path)


if __name__ == '__main__':
    unittest.main()
