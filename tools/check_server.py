import requests, sys
try:
    r = requests.get('http://127.0.0.1:5000/api/status', timeout=5)
    print('status', r.status_code)
    d = r.json()
    print('symbol', d.get('symbol'), 'price', d.get('price'), 'sim', d.get('simulation_mode'))
except Exception as e:
    print('error', e)
    sys.exit(1)
