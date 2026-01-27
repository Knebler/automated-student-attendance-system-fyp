"""
Flask Application with Integrated Facial Recognition AI
========================================================
This app.py includes all the necessary endpoints for the
attendance_client.py facial recognition system.

Run with: python app.py

The facial recognition client can then connect to:
- http://localhost:5000/api/health
- http://localhost:5000/api/sessions
- http://localhost:5000/api/students/training-data
- etc.
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
import os
import ssl
from urllib.parse import quote_plus
from datetime import timedelta
import stripe
from application import create_app

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

    # Initialize Stripe keys
    stripe.api_key = app.config.get('STRIPE_SECRET_KEY')
    
    # Store extensions in app config
    app.config['db'] = db  # SQLAlchemy instance

    # Add facial recognition config
    app.config['FACIAL_DATA_DIR'] = './AttendanceAI/data/'
    app.config['FACIAL_RECOGNITION_THRESHOLD'] = 70

    # Initialize facial recognition control (existing)
    try:
        from application.controls.facial_recognition_control import FacialRecognitionControl
        fr_control = FacialRecognitionControl()
        fr_control.initialize(app)
        app.config['facial_recognition'] = fr_control
    except ImportError:
        print("⚠️ FacialRecognitionControl not found, skipping...")

    # Register the facial recognition blueprint (existing)
    try:
        from application.boundaries.facial_recognition_boundary import facial_recognition_bp
        app.register_blueprint(facial_recognition_bp, url_prefix='/api/facial-recognition')
    except ImportError:
        print("⚠️ facial_recognition_bp not found, skipping...")
    
    # ============================================================
    # REGISTER ATTENDANCE AI API BLUEPRINT
    # This provides all endpoints needed by attendance_client.py
    # ============================================================
    from attendance_ai_blueprint import attendance_ai_bp
    
    # Register at /api (this is what attendance_client.py expects)
    app.register_blueprint(attendance_ai_bp, url_prefix='/api')
    
    # Exempt AI API endpoints from CSRF (they're called by Python client)
    csrf.exempt(attendance_ai_bp)
    
    print("")
    print("=" * 70)
    print("🎓 ATTENDANCE AI API INTEGRATED")
    print("=" * 70)
    print("Available endpoints for attendance_client.py:")
    print("")
    print("  System:")
    print("    GET  /api/health                  - Health check")
    print("    GET  /api/recognition/status      - Recognition status")
    print("    POST /api/recognition/start       - Start recognition client")
    print("    POST /api/recognition/stop        - Stop recognition client")
    print("")
    print("  Sessions:")
    print("    GET  /api/sessions                - Get today's sessions")
    print("    GET  /api/classes                 - Get today's classes")
    print("")
    print("  Students:")
    print("    GET  /api/students                - Get all students")
    print("    GET  /api/students/training-data  - Get KNN training data")
    print("    POST /api/students/import         - Import students with photos")
    print("    GET  /api/class/<id>/students     - Get enrolled students")
    print("")
    print("  Attendance:")
    print("    POST /api/attendance/mark         - Mark attendance")
    print("    POST /api/attendance/unmark       - Unmark (left early)")
    print("    GET  /api/attendance/class/<id>   - Get class attendance")
    print("")
    print("  Debug:")
    print("    GET  /api/debug/facial-data       - Check facial data in DB")
    print("    GET  /api/recognition/check-script - Check client script")
    print("=" * 70)
    print("")
    
    # Initialize application with BCE structure
    create_app(app)
    
    return app


# ============================================================
# STARTUP CHECK FOR ATTENDANCE CLIENT
# ============================================================
def check_attendance_client():
    """Check if attendance_client.py is available"""
    possible_locations = [
        './attendance_client.py',
        './AttendanceAI/attendance_client.py',
        '../attendance_client.py',
    ]
    
    for path in possible_locations:
        if os.path.exists(path):
            print(f"✅ attendance_client.py found: {os.path.abspath(path)}")
            return True
    
    print("⚠️  attendance_client.py NOT FOUND")
    print("   Place attendance_client.py in one of these locations:")
    for path in possible_locations:
        print(f"   - {os.path.abspath(path)}")
    
    return False


def ensure_tables_exist(app):
    """Ensure required tables exist in database"""
    with app.app_context():
        db = app.config.get('db')
        if db:
            try:
                # Create facial_data table if not exists
                db.session.execute(db.text("""
                    CREATE TABLE IF NOT EXISTS facial_data (
                        facial_data_id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        face_encoding LONGBLOB NOT NULL,
                        sample_count INT DEFAULT 1,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE,
                        INDEX idx_facial_user (user_id),
                        INDEX idx_facial_active (is_active)
                    )
                """))
                db.session.commit()
                print("✅ facial_data table ready")
            except Exception as e:
                print(f"⚠️ Table check: {e}")


if __name__ == '__main__':
    print("")
    print("=" * 70)
    print("🚀 STARTING FLASK APP WITH ATTENDANCE AI")
    print("=" * 70)
    
    # Check for attendance client
    check_attendance_client()
    
    # Create app
    app = create_flask_app('dev')
    
    # Ensure tables exist
    ensure_tables_exist(app)
    
    print("")
    print("=" * 70)
    print("🌐 SERVER STARTING")
    print("=" * 70)
    print("")
    print("  Dashboard:     http://localhost:5000")
    print("  AI API:        http://localhost:5000/api/health")
    print("")
    print("  To start facial recognition:")
    print("    Option 1: POST http://localhost:5000/api/recognition/start")
    print("    Option 2: python attendance_client.py")
    print("")
    print("=" * 70)
    print("")
    
    app.run(debug=True, host='0.0.0.0', port=5000)