import os, struct, platform
try:
    import MetaTrader5 as mt5
except Exception as e:
    print('MetaTrader5 import error:', e)
    raise SystemExit(1)

mt5_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"
print('Python executable:', platform.python_implementation(), platform.python_version())
print('Pointer size (bits):', struct.calcsize('P')*8)
print('MT5 path exists:', os.path.exists(mt5_path))
try:
    mt5.shutdown()
except Exception:
    pass
ok = mt5.initialize(mt5_path)
print('initialize returned:', ok)
print('mt5.last_error():', mt5.last_error())
if ok:
    try:
        print('mt5.version():', mt5.version())
    finally:
        mt5.shutdown()
