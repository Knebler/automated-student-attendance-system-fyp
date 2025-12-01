from flask import Blueprint, render_template, current_app
from application.controls.database_control import DatabaseControl
import datetime

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    """Home page route"""
    return render_template('index.html')

@main_bp.route('/about')
def about():
    """About page route"""
    return render_template('about.html')

@main_bp.route('/init-db')
def init_database():
    """Initialize database tables (for development only)"""
    result = DatabaseControl.initialize_database(current_app)
    
    if result['success']:
        return f"Database initialized: {result['tables_created']}"
    else:
        return f"Database initialization failed: {result['error']}", 500

@main_bp.route('/health')
def health_check():
    """Health check endpoint"""
    db_result = DatabaseControl.check_database_connection(current_app)
    
    return {
        'status': 'ok' if db_result['success'] else 'error',
        'database': db_result['message'],
        'timestamp': datetime.now().isoformat()
    }