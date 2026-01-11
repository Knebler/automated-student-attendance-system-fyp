from flask import Flask, app
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
import pyrebase
from application import create_app
import os
import ssl
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session

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
    
    # Test connection immediately
    try:
        with app.app_context():
            print("Testing database connection...")
            
            # Simple connection test
            result = db.session.execute(text('SELECT 1'))
            print("Basic connection test passed")
            
            # Test SSL if enabled
            if ssl_enabled:
                try:
                    result = db.session.execute(text('SHOW STATUS LIKE "Ssl_cipher"'))
                    ssl_status = result.fetchone()
                    if ssl_status and ssl_status[1]:
                        print(f"SSL active. Cipher: {ssl_status[1]}")
                    else:
                        print("Connected but SSL cipher not detected")
                except Exception as ssl_err:
                    print(f"Could not check SSL status: {ssl_err}")
            
            # Get database info
            result = db.session.execute(text('SELECT DATABASE(), VERSION()'))
            db_info = result.fetchone()
            print(f"Connected to: {db_info[0]}")
            print(f"MySQL Version: {db_info[1]}")
            
    except Exception as e:
        print(f"Database connection failed: {e}")
        
        # Try alternative connection method
        print("\nAttempting alternative connection method...")
        try:
            # Create a custom engine with explicit SSL
            engine = create_engine(
                database_uri,
                connect_args=connect_args,
                pool_size=10,
                pool_recycle=300
            )
            
            # Test the custom engine
            with engine.connect() as conn:
                result = conn.execute(text('SELECT 1'))
                print("Alternative connection method works!")
                
                # Replace Flask-SQLAlchemy's engine with our custom one
                db.engine.dispose()  # Dispose old engine
                db.engine = engine
                db.session.bind = engine
                
                print("Replaced SQLAlchemy engine with custom SSL-enabled engine")
                
        except Exception as alt_err:
            print(f"Alternative connection also failed: {alt_err}")
            
            # Last resort: create a minimal working connection
            print("\nCreating minimal test connection...")
            try:
                import pymysql
                
                connection = pymysql.connect(
                    host=app.config['MYSQL_HOST'],
                    user=app.config['MYSQL_USER'],
                    password=app.config['MYSQL_PASSWORD'],
                    database=app.config['MYSQL_DB'],
                    port=app.config.get('MYSQL_PORT', 3306),
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor,
                    ssl={'ca': ssl_ca_path} if ssl_enabled and os.path.exists(ssl_ca_path) else None
                )
                
                print("Minimal PyMySQL connection works!")
                connection.close()
                
            except Exception as pymysql_err:
                print(f"Even minimal connection failed: {pymysql_err}")
        
        # Don't raise error - let the app start anyway
        print("\nContinuing with app startup despite connection issues...")
    
    # Initialize CSRF protection for forms
    csrf = CSRFProtect()
    csrf.init_app(app)
    
    # Configure Firebase
    firebase_config = {
        "apiKey": app.config['FIREBASE_API_KEY'],
        "authDomain": app.config['FIREBASE_AUTH_DOMAIN'],
        "projectId": app.config['FIREBASE_PROJECT_ID'],
        "storageBucket": app.config['FIREBASE_STORAGE_BUCKET'],
        "messagingSenderId": app.config['FIREBASE_MESSAGING_SENDER_ID'],
        "appId": app.config['FIREBASE_APP_ID'],
        "databaseURL": app.config.get('FIREBASE_DATABASE_URL', '')
    }
    
    firebase = pyrebase.initialize_app(firebase_config)
    auth = firebase.auth()
    
    # Store extensions in app config
    app.config['db'] = db  # SQLAlchemy instance
    app.config['firebase_auth'] = auth
    app.config['firebase_app'] = firebase

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
    create_app(app)
    
    return app

if __name__ == '__main__':
    app = create_flask_app('dev')
    app.run(debug=True, host='0.0.0.0', port=5000)