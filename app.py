from flask import Flask, app
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
import os
import ssl
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from datetime import timedelta

from database.models import Base

def create_flask_app(config_name='default'):
    """Factory function to create Flask application"""
    app = Flask(__name__)
    
    # Load configuration
    from config import config_by_name
    app.config.from_object(config_by_name[config_name])
    
    # Get SSL configuration
    ssl_ca_path = app.config.get('MYSQL_SSL_CA', './combined-ca-certificates.pem')
    ssl_enabled = app.config.get('MYSQL_SSL_ENABLED', True)
    
    # Build SQLAlchemy URI with URL-encoded password
    encoded_password = quote_plus(app.config['MYSQL_PASSWORD'])
    
    # Create the base database URI (without SSL parameters in the URI string)
    database_uri = (
        f"mysql+pymysql://{app.config['MYSQL_USER']}:{encoded_password}"
        f"@{app.config['MYSQL_HOST']}:{app.config['MYSQL_PORT']}/{app.config['MYSQL_DB']}"
        f"?charset=utf8mb4"
    )
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Configure SSL for SQLAlchemy
    connect_args = {}
    if ssl_enabled:
        print(f"Configuring SSL with certificate: {ssl_ca_path}")
        
        if os.path.exists(ssl_ca_path):
            # Method 1: Use SSL context (most reliable)
            ssl_context = ssl.create_default_context(cafile=ssl_ca_path)
            ssl_context.verify_mode = ssl.CERT_REQUIRED
            connect_args = {
                'ssl': ssl_context
            }
            print("Using SSL context with certificate verification")
        else:
            # Method 2: Use dictionary SSL parameters
            connect_args = {
                'ssl': {
                    'ca': ssl_ca_path,
                    'check_hostname': True,
                    'verify_mode': ssl.CERT_REQUIRED
                }
            }
            print("Certificate not found, using dictionary SSL config")
    else:
        print("SSL disabled")
    
    # Configure SQLAlchemy engine with SSL
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': connect_args,
        'pool_size': app.config.get('SQLALCHEMY_POOL_SIZE', 10),
        'max_overflow': app.config.get('SQLALCHEMY_MAX_OVERFLOW', 20),
        'pool_recycle': app.config.get('SQLALCHEMY_POOL_RECYCLE', 300),
        'pool_timeout': app.config.get('SQLALCHEMY_POOL_TIMEOUT', 30),
        'echo': app.config.get('DEBUG', False),
        'pool_pre_ping': True  # Verify connections before using them
    }
    
    # Initialize SQLAlchemy
    db = SQLAlchemy(app, metadata=Base.metadata)
    
    # Initialize CSRF protection for forms
    csrf = CSRFProtect()
    csrf.init_app(app)
    
    # Store extensions in app config
    app.config['db'] = db  # SQLAlchemy instance

    # Add facial recognition config
    app.config['FACIAL_DATA_DIR'] = './AttendanceAI/data/'
    app.config['FACIAL_RECOGNITION_THRESHOLD'] = 70

    # Initialize facial recognition control
    from application.controls.facial_recognition_control import FacialRecognitionControl
    fr_control = FacialRecognitionControl()
    fr_control.initialize(app)  # Optional: initialize on startup
    app.config['facial_recognition'] = fr_control

    # Register the facial recognition blueprint
    from application.boundaries.facial_recognition_boundary import facial_recognition_bp
    app.register_blueprint(facial_recognition_bp, url_prefix='/api/facial-recognition')
    
    # Initialize application with BCE structure
    from application import create_app
    create_app(app)
    
    return app

if __name__ == '__main__':
    app = create_flask_app('dev')
    app.run(debug=True, host='0.0.0.0', port=5000)