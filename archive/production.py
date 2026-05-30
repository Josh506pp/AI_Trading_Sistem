import os
from waitress import serve
from wsgi import app

if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '8080'))
    threads = int(os.environ.get('WEB_CONCURRENCY', '4'))
    serve(app, host=host, port=port, threads=threads)
