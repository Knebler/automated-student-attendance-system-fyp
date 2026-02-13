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
    
    # Exempt blueprints from CSRF
    try:
        from application.boundaries.platform_boundary import platform_bp
        from application.boundaries.student_boundary import student_bp
        from application.boundaries.main_boundary import main_bp
        from application.boundaries.lecturer_boundary import lecturer_bp
        csrf.exempt(platform_bp)
        csrf.exempt(student_bp)
        csrf.exempt(main_bp)
        csrf.exempt(lecturer_bp)
    except ImportError:
        print("⚠️ Some blueprints not found for CSRF exemption")

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
                        app.logger.info(f"✅ Scheduler: {updated_count} class(es) updated")
        except Exception as e:
            app.logger.error(f"❌ Scheduler error: {e}")
            import traceback
            app.logger.error(traceback.format_exc())
    
    def check_and_suspend_expired_subscriptions():
        """Background job to check for expired subscriptions and suspend institutions"""
        try:
            with app.app_context():
                from database.base import get_session
                from application.entities2.subscription import SubscriptionModel
                from database.models import Subscription, User
                from datetime import datetime
                
                with get_session() as db_session:
                    subscription_model = SubscriptionModel(db_session)
                    
                    # Query for subscriptions that are expired (end_date < now) but still active
                    now = datetime.now()
                    expired_active_subscriptions = (
                        db_session.query(Subscription)
                        .filter(
                            Subscription.end_date.isnot(None),
                            Subscription.end_date < now,
                            Subscription.is_active == True
                        )
                        .all()
                    )
                    
                    suspended_count = 0
                    for subscription in expired_active_subscriptions:
                        # Deactivate the subscription
                        subscription.is_active = False
                        
                        # Deactivate all users in the institution
                        if subscription.institution:
                            institution_users = (
                                db_session.query(User)
                                .filter(User.institution_id == subscription.institution.institution_id)
                                .all()
                            )
                            for user in institution_users:
                                user.is_active = False
                            
                            app.logger.info(
                                f"Suspended institution '{subscription.institution.name}' "
                                f"(ID: {subscription.institution.institution_id}) - "
                                f"Subscription expired on {subscription.end_date.strftime('%Y-%m-%d')}, "
                                f"{len(institution_users)} user(s) deactivated"
                            )
                        else:
                            app.logger.info(
                                f"Suspended subscription ID {subscription.subscription_id} - "
                                f"Expired on {subscription.end_date.strftime('%Y-%m-%d')}"
                            )
                        
                        suspended_count += 1
                    
                    if suspended_count > 0:
                        db_session.commit()
                        app.logger.info(f"Background scheduler: Suspended {suspended_count} expired subscription(s)")
                    
        except Exception as e:
            app.logger.error(f"Error in expired subscription check: {e}")
    
    # Schedule the job to run every 5 seconds (DEBUG MODE)
    scheduler.add_job(
        func=update_all_class_statuses,
        trigger="interval",
        seconds=5,
        id='update_class_statuses_job',
        name='Update class statuses and send notifications',
        replace_existing=True
    )
    
    # Schedule the job to check for expired subscriptions every hour
    scheduler.add_job(
        func=check_and_suspend_expired_subscriptions,
        trigger="interval",
        hours=1,
        id='check_expired_subscriptions_job',
        name='Check and suspend expired subscriptions',
        replace_existing=True
    )
    
    # Start the scheduler
    scheduler.start()
    app.logger.info("Background scheduler started - checking class statuses every 5 seconds (DEBUG MODE)")
    app.logger.info("Background scheduler started - checking expired subscriptions every hour")
    
    # Run an immediate check on startup
    try:
        update_all_class_statuses()
        app.logger.info("Initial class status check completed on startup")
    except Exception as e:
        app.logger.error(f"Error in initial class status check: {e}")
    
    # Run an immediate check for expired subscriptions on startup
    try:
        check_and_suspend_expired_subscriptions()
        app.logger.info("Initial expired subscription check completed on startup")
    except Exception as e:
        app.logger.error(f"Error in initial expired subscription check: {e}")
    
    # Shut down the scheduler when the app exits
    atexit.register(lambda: scheduler.shutdown())
    
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
    
    app.run(debug=True, host='0.0.0.0', port=app.config.get('PORT', 5000))