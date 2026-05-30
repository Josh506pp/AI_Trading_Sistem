import os
import re
import sys

root = os.path.dirname(os.path.abspath(__file__))
app_path = os.path.join(root, 'app.py')
bundle_path = os.path.join(root, 'start_bundle.py')

with open(app_path, 'r', encoding='utf-8') as f:
    text = f.read()

start_marker = 'try:'
import_marker = 'from mt5_config import ('
end_marker = "USE_REAL_ACCOUNT = False"

start_idx = text.find("try:\n    from mt5_config import (")
if start_idx == -1:
    start_idx = text.find("try:\r\n    from mt5_config import (")

if start_idx == -1:
    sys.exit('No se encontró el bloque de importación de mt5_config para reemplazar')

end_idx = text.find(end_marker, start_idx)
if end_idx == -1:
    sys.exit('No se encontró la línea final de USE_REAL_ACCOUNT en el bloque')

end_idx = text.find('\n', end_idx)
if end_idx == -1:
    sys.exit('No se pudo determinar el fin de la línea de USE_REAL_ACCOUNT')

block_end = end_idx + 1
replacement = """# Configuración MT5 inline (se puede editar aquí directamente)
MT5_LOGIN = None
MT5_PASSWORD = None
MT5_SERVER = None
MT5_PATH = None
TRADING_SYMBOL = 'EURUSD'
DEFAULT_VOLUME = 0.01
USE_REAL_ACCOUNT = False

"""

text = text[:start_idx] + replacement + text[block_end:]

with open(bundle_path, 'w', encoding='utf-8') as f:
    f.write(text)

print('Generado', bundle_path)
