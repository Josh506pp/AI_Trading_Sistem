import shutil
import os
src = os.path.join('release','dist','TradingSystem')
out = os.path.join('release','TradingSystem-release')
if not os.path.exists(src):
    raise SystemExit('Source not found: ' + src)
shutil.make_archive(out,'zip',src)
print('ZIP creado:', out + '.zip')
