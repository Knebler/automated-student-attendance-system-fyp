from flask import Blueprint, render_template, session, current_app, request, redirect, url_for, flash
from application.controls.database_control import DatabaseControl
from application.controls.testimonial_control import TestimonialControl
from application.controls.auth_control import AuthControl, requires_roles
from application.boundaries.dev_actions import register_action
import datetime
from flask import Blueprint, render_template, request, session, current_app, flash, redirect, url_for, abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from application.controls.attendance_control import AttendanceControl
from application.controls.auth_control import requires_roles
from application.entities2 import ClassModel, UserModel, InstitutionModel, SubscriptionModel, CourseModel, AttendanceRecordModel, CourseUserModel, VenueModel, TestimonialModel
from database.base import get_session
from database.models import *
from datetime import date, datetime, timedelta
from collections import defaultdict

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    """Home page route"""
    return render_template('index.html')

@main_bp.route('/about')
def about():
    """About page route (public/unregistered)"""
    return render_template('unregistered/aboutus.html')

@main_bp.route('/faq')
def faq():
    """Public FAQ page"""
    return render_template('unregistered/faq.html')

@main_bp.route('/features')
def features():
    """Public Features page"""
    return render_template('unregistered/features.html')

@main_bp.route('/subscriptions')
def subscriptions():
    """Public Subscription summary page"""
    return render_template('unregistered/subscriptionsummary.html')

@main_bp.route('/testimonials')
def testimonials():
    with get_session() as db_session:
        testimonial_model = TestimonialModel(db_session)
        testimonial_detail = testimonial_model.testimonials()
    return render_template('unregistered/testimonials.html', testimonials=testimonial_detail)

@main_bp.route('/testimonials/<int:testimonial_id>')
def testimonial_detail(testimonial_id):
    with get_session() as db_session:
        testimonial_model = TestimonialModel(db_session)
        testimonial = testimonial_model.get_by_id(testimonial_id)
        if not testimonial or testimonial.status != 'approved':
            abort(404)
        user_model = UserModel(db_session)
        user = user_model.get_by_id(testimonial.user_id)
        institution_model = InstitutionModel(db_session)
        institution = institution_model.get_by_id(user.institution_id) if user else None
        
        testimonial_info = {
            "id": testimonial.testimonial_id,
            "summary": testimonial.summary,
            "content": testimonial.content,
            "rating": testimonial.rating,
            "date_submitted": testimonial.date_submitted.strftime("%d %b %Y"),
            "user_name": user.name if user else "Unknown",
            "user_role": user.role if user else "Unknown",
            "institution_name": institution.name if institution else "Unknown"
        }
        
        # Get random related testimonials
        related_testimonials = testimonial_model.get_random_testimonials(
            exclude_id=testimonial_id, 
            limit=3
        )
    
    return render_template(
        'unregistered/testimonialdetails.html', 
        testimonial=testimonial_info,
        related_testimonials=related_testimonials
    )

@main_bp.route('/submit-testimonial', methods=['GET', 'POST'])
@requires_roles('student' or 'lecturer' or 'admin' or 'platform_manager')
def submit_testimonial():
    """Page for submitting a new testimonial"""
    if request.method == 'POST':
        # Get user info from verified session
        user = session.get('user')
        user_id = user.get('user_id')
        institution_id = user.get('institution_id')
        
        # Get form data
        title = request.form.get('title')
        description = request.form.get('description')
        rating = request.form.get('rating', type=int)
        
        # Validate required fields
        if not all([title, description, rating]):
            flash('Please fill in all required fields', 'error')
            return redirect(url_for('main.submit_testimonial'))
        
        # Validate rating range
        if rating < 1 or rating > 5:
            flash('Rating must be between 1 and 5', 'error')
            return redirect(url_for('main.submit_testimonial'))
        
        # Create testimonial
        result = TestimonialControl.create_testimonial(
            current_app,
            user_id=user_id,
            institution_id=institution_id,
            title=title,
            description=description,
            rating=rating,
            status='pending'  # Needs admin approval
        )
        
        if result['success']:
            flash('Thank you for your testimonial! It has been submitted for review.', 'success')
            return redirect(url_for('main.testimonials'))
        else:
            flash(f'Error submitting testimonial: {result.get("error", "Unknown error")}', 'error')
            return redirect(url_for('main.submit_testimonial'))
    
    # GET request - show form
    return render_template('unregistered/submit_testimonial.html')

@main_bp.route('/testimonial-stats')
def testimonial_stats():
    """API endpoint to get testimonial statistics (could be used for AJAX)"""
    result = TestimonialControl.get_testimonial_stats(current_app)
    
    if result['success']:
        return {
            'success': True,
            'stats': result['stats'],
            'timestamp': datetime.datetime.now().isoformat()
        }
    else:
        return {
            'success': False,
            'error': result.get('error', 'Unknown error'),
            'timestamp': datetime.datetime.now().isoformat()
        }, 500

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
        'timestamp': datetime.datetime.now().isoformat()
    }

# register a dev action for initializing the DB (callable will be invoked with app)
register_action(
    'init_database',
    DatabaseControl.initialize_database,
    params=[],
    description='Create tables and sample data'
)

# register a dev action for managing testimonials
register_action(
    'approve_testimonials',
    lambda app: TestimonialControl.update_testimonial_status(
        app, 
        testimonial_id=1, 
        new_status='approved'
    ),
    params=[],
    description='Approve pending testimonials'
)