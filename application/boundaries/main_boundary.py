from flask import Blueprint, render_template, session, current_app, request, redirect, url_for, flash, jsonify
from application.controls.database_control import DatabaseControl
from application.controls.testimonial_control import TestimonialControl
from application.controls.platformissue_control import PlatformIssueControl
from application.controls.auth_control import AuthControl, requires_roles, requires_roles_api
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

@main_bp.route('/testimonial/form')
@requires_roles(['student', 'lecturer', 'admin'])
def testimonial_form():
    with get_session() as db_session:
        testimonial_model = TestimonialModel(db_session)
        user_model = UserModel(db_session)
        user_id = session.get('user_id')
        institution_id = session.get('institution_id')
        role = session.get('role')
        user_name = user_model.get_by_id(user_id).name if user_id else "Unknown"
        institution_name = InstitutionModel(db_session).get_by_id(institution_id).name if institution_id else "Unknown"

        return render_template(
            'unregistered/testimonial_submission.html',
            user_name=user_name,
            institution_name=institution_name,
            role=role
        )
@main_bp.route('/testimonial/form/submit', methods=['POST'])
@requires_roles(['student', 'lecturer', 'admin'])
def submit_testimonial():
    with get_session() as db_session:
        testimonial_model = TestimonialModel(db_session)
        user_id = session.get('user_id')
        feedback_details = request.form.get('feedback_details')
        rating = request.form.get('rating')
        institution_id = session.get('institution_id')
        
        # Generate summary from first 100 characters of feedback
        summary = feedback_details[:100] + '...' if len(feedback_details) > 100 else feedback_details
        
        # Analyze testimonial for sentiment and inappropriate content
        analysis = TestimonialControl.analyze_testimonial_sentiment(
            content=feedback_details,
            summary=summary
        )
        
        # Determine status based on analysis
        if not analysis['is_appropriate']:
            testimonial_status = 'rejected'
            flash(f'Your testimonial was automatically rejected: {analysis["reason"]}. Please revise and resubmit with appropriate content.', 'danger')
        else:
            testimonial_status = 'pending'
            flash('Thank you for your testimonial! It will be reviewed before being published.', 'success')
        
        # Create testimonial with determined status
        new_testimonial = Testimonial(
            user_id=user_id,
            institution_id=institution_id,
            summary=summary,
            content=feedback_details,
            rating=int(rating),
            status=testimonial_status,
            date_submitted=datetime.now()
        )
        db_session.add(new_testimonial)
        db_session.commit()
        
        return redirect(url_for('main.testimonials'))
    
@main_bp.route('/report-issue')
@requires_roles(['student', 'lecturer', 'admin'])
def report_issue_form():
    """Display form for reporting platform issues"""
    try:
        # Get user info for the form
        user_id = session.get('user_id')
        institution_id = session.get('institution_id')
        
        if not user_id or not institution_id:
            flash('You must be logged in to report an issue', 'danger')
            return redirect(url_for('auth.login'))
        
        with get_session() as db_session:
            user_model = UserModel(db_session)
            institution_model = InstitutionModel(db_session)
            
            user = user_model.get_by_id(user_id)
            institution = institution_model.get_by_id(institution_id)
            
            if not user or not institution:
                flash('User or institution not found', 'danger')
                return redirect(url_for('main.home'))
        
        # Get available categories
        categories = PlatformIssueControl.get_categories()
        
        return render_template(
            'components/report_issue_form.html',
            user_name=user.name if user else 'User',
            user_role=session.get('role'),
            institution_name=institution.name if institution else 'Institution',
            categories=categories
        )
        
    except Exception as e:
        flash(f'Error loading issue report form: {str(e)}', 'danger')
        return redirect(url_for('main.home'))

@main_bp.route('/report-issue/submit', methods=['POST'])
@requires_roles_api(['student', 'lecturer', 'admin'])
def submit_issue_report():
    """Handle submission of platform issue reports"""
    try:
        user_id = session.get('user_id')
        institution_id = session.get('institution_id')
        
        if not user_id or not institution_id:
            return jsonify({'success': False, 'error': 'You must be logged in to report an issue'}), 401
        
        # Get form data
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'bug')
        
        # Validate inputs
        if not description:
            flash('Issue description is required', 'danger')
            return redirect(url_for('main.report_issue_form'))
        
        # Validate category
        if not PlatformIssueControl.validate_category(category):
            flash('Invalid issue category selected', 'danger')
            return redirect(url_for('main.report_issue_form'))
        
        # Analyze content for appropriateness
        analysis = PlatformIssueControl.analyze_issue_content(description, category)
        
        if not analysis['is_appropriate']:
            flash(f'Your issue report contains inappropriate content: {analysis["reason"]}. Please revise your report.', 'danger')
            return redirect(url_for('main.report_issue_form'))
        
        # Create the issue
        result = PlatformIssueControl.create_issue(
            app=current_app,
            user_id=user_id,
            institution_id=institution_id,
            description=description,
            category=category
        )
        
        if result['success']:
            flash('Issue reported successfully! Our team will review it soon.', 'success')
            # Optionally redirect to a confirmation page or user's issue history
            return redirect(url_for('main.my_reports'))
        else:
            flash(f'Failed to submit issue: {result["error"]}', 'danger')
            return redirect(url_for('main.report_issue_form'))
            
    except Exception as e:
        flash(f'Error submitting issue report: {str(e)}', 'danger')
        return redirect(url_for('main.report_issue_form'))

@main_bp.route('/my-reports')
@requires_roles(['student', 'lecturer', 'admin'])
def my_reports():
    """Display user's submitted issue reports"""
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            flash('You must be logged in to view your reports', 'danger')
            return redirect(url_for('auth.login'))
        
        result = PlatformIssueControl.get_issues_by_user(
            user_id=user_id,
            include_deleted=False
        )
        
        if not result['success']:
            flash(f'Error loading your reports: {result["error"]}', 'danger')
            return redirect(url_for('main.home'))
        
        # Get categories for filter display
        categories = PlatformIssueControl.get_categories()
        
        return render_template(
            'components/my_reports.html',
            issues=result['issues'],
            total_count=result['count'],
            categories=categories
        )
        
    except Exception as e:
        flash(f'Error loading your reports: {str(e)}', 'danger')
        return redirect(url_for('main.home'))

@main_bp.route('/api/report-issue', methods=['POST'])
@requires_roles_api(['student', 'lecturer', 'admin'])
def api_report_issue():
    """API endpoint for submitting issue reports (for AJAX)"""
    try:
        user_id = session.get('user_id')
        institution_id = session.get('institution_id')
        
        if not user_id or not institution_id:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        # Get JSON data
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        description = data.get('description', '').strip()
        category = data.get('category', 'bug')
        
        # Validate inputs
        if not description:
            return jsonify({'success': False, 'error': 'Issue description is required'}), 400
        
        if not PlatformIssueControl.validate_category(category):
            return jsonify({'success': False, 'error': 'Invalid issue category'}), 400
        
        # Analyze content
        analysis = PlatformIssueControl.analyze_issue_content(description, category)
        
        if not analysis['is_appropriate']:
            return jsonify({
                'success': False, 
                'error': f'Content validation failed: {analysis["reason"]}',
                'validation_details': analysis
            }), 400
        
        # Create the issue
        result = PlatformIssueControl.create_issue(
            app=current_app,
            user_id=user_id,
            institution_id=institution_id,
            description=description,
            category=category
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Issue reported successfully',
                'issue_id': result['issue_id']
            }), 201
        else:
            return jsonify({'success': False, 'error': result['error']}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/api/validate-issue', methods=['POST'])
@requires_roles_api(['student', 'lecturer', 'admin'])
def api_validate_issue():
    """API endpoint for validating issue content before submission"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        description = data.get('description', '').strip()
        category = data.get('category', 'bug')
        
        # Analyze content
        analysis = PlatformIssueControl.analyze_issue_content(description, category)
        
        return jsonify({
            'success': True,
            'validation': analysis
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/api/my-reports')
@requires_roles_api(['student', 'lecturer', 'admin'])
def api_my_reports():
    """API endpoint for getting user's reports"""
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        result = PlatformIssueControl.get_issues_by_user(
            user_id=user_id,
            include_deleted=False
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'issues': result['issues'],
                'count': result['count']
            })
        else:
            return jsonify({'success': False, 'error': result['error']}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
        
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