from flask import Flask, app
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
import os
import ssl
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from datetime import timedelta
import stripe
from application import create_app
from application.boundaries.platform_boundary import platform_bp
from application.boundaries.student_boundary import student_bp
from application.boundaries.main_boundary import main_bp
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

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

    #Initialize Stripe keys
    stripe.api_key = app.config.get('STRIPE_SECRET_KEY')
    
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
    create_app(app)
    csrf.exempt(platform_bp)
    csrf.exempt(student_bp)
    csrf.exempt(main_bp)

    # Initialize and start the background scheduler for class notifications
    scheduler = BackgroundScheduler()
    
    def update_all_class_statuses():
        """Background job to update class statuses and send notifications"""
        try:
            with app.app_context():
                from database.base import get_session
                from application.entities2.classes import ClassModel
                
                with get_session() as db_session:
                    class_model = ClassModel(db_session)
                    updated_count = class_model.update_class_statuses()
                    if updated_count > 0:
                        app.logger.info(f"Background scheduler: Updated {updated_count} class(es) and sent notifications")
        except Exception as e:
            app.logger.error(f"Error in background class status update: {e}")
    
    # Schedule the job to run every 2 minutes
    scheduler.add_job(
        func=update_all_class_statuses,
        trigger="interval",
        minutes=2,
        id='update_class_statuses_job',
        name='Update class statuses and send notifications',
        replace_existing=True
    )
    
    # Start the scheduler
    scheduler.start()
    app.logger.info("Background scheduler started - checking class statuses every 2 minutes")
    
    # Run an immediate check on startup
    try:
        update_all_class_statuses()
        app.logger.info("Initial class status check completed on startup")
    except Exception as e:
        app.logger.error(f"Error in initial class status check: {e}")
    
    # Shut down the scheduler when the app exits
    atexit.register(lambda: scheduler.shutdown())

    return app

if __name__ == '__main__':
    app = create_flask_app('dev')
    app.run(debug=True, host='0.0.0.0', port=app.config.get('PORT', 5000))