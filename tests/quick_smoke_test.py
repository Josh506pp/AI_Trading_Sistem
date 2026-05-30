"""Quick smoke test using Flask test client to verify key endpoints."""
import json
import os
import sys

# Ensure project root is on sys.path so `src` package imports correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src import app

endpoints = [
    '/api/status',
    '/api/predict',
    '/api/predict/levels',
    '/api/predict/signal',
    '/api/professional-analysis'
]

with app.test_client() as client:
    results = {}
    for ep in endpoints:
        try:
            resp = client.get(ep)
            status = resp.status_code
            try:
                data = resp.get_json()
            except Exception:
                data = resp.data.decode('utf-8')[:400]
            results[ep] = {'status': status, 'json': data}
        except Exception as e:
            results[ep] = {'error': str(e)}

    # Print summary
    print(json.dumps(results, indent=2, ensure_ascii=False))
