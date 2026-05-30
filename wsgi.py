"""
WSGI entry point for production deployment.
Compatible with Heroku, Docker, and other WSGI servers.
"""
import os
import sys
import logging

# Configure Python path for production imports
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import Flask app and services
try:
    from src import app, start_background_services
    
    # Start background services when module is imported (for production servers)
    start_background_services()
    
    # Set production settings
    app.config['ENV'] = 'production'
    app.config['DEBUG'] = False
    
    logger = logging.getLogger(__name__)
    logger.info('✅ Trading System application loaded successfully')
    
except Exception as e:
    logger = logging.getLogger(__name__)
    logger.error(f'❌ Failed to load application: {str(e)}', exc_info=True)
    raise

if __name__ == '__main__':
    # Use Waitress for local production-style execution
    try:
        from waitress import serve
        port = int(os.environ.get('PORT', 8080))
        serve(app, host='0.0.0.0', port=port)
    except ImportError:
        port = int(os.environ.get('PORT', 8080))
        app.run(host='0.0.0.0', port=port, debug=False)
