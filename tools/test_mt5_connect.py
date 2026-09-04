import requests, time
start = time.time()
try:
    r = requests.post('http://127.0.0.1:5000/api/mt5/connect', json={'login':'12345','password':'test','server':'Demo'}, timeout=35)
    print('status', r.status_code)
    print(r.json())
except Exception as e:
    print('error', e)
print('elapsed', time.time()-start)
