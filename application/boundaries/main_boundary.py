from flask import Blueprint, render_template, current_app, request, redirect, url_for, flash
from application.controls.database_control import DatabaseControl
from application.controls.testimonial_control import TestimonialControl
from application.controls.auth_control import AuthControl, requires_roles
from application.boundaries.dev_actions import register_action
import datetime

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
    """Public Testimonials page with real data - showing only latest 3 testimonials"""
    # Get approved testimonials for display - limit to 3 latest
    result = TestimonialControl.get_public_testimonials(
        current_app,
        limit=3,  # Show only 3 testimonials
        min_rating=4  # Only show testimonials with 4+ stars
    )
    
    # Get testimonial statistics
    stats_result = TestimonialControl.get_testimonial_stats(current_app)
    
    # Prepare data for template
    testimonials_data = []
    if result['success']:
        testimonials_data = result['testimonials'][:3]  # Ensure only 3
        
        # Ensure each testimonial has an ID for routing
        for testimonial in testimonials_data:
            if 'testimonial_id' not in testimonial:
                testimonial['testimonial_id'] = 1  # Default fallback ID
                
        # If we have fewer than 3 testimonials, we'll use fallback for the rest
        if len(testimonials_data) < 3:
            additional_needed = 3 - len(testimonials_data)
            
            # Sample hardcoded testimonials as fallback
            fallback_testimonials = [
                {
                    'testimonial_id': 1,
                    'title': 'Excellent Attendance System',
                    'description': 'This platform has completely transformed how we track attendance. The facial recognition feature is incredibly accurate and saves us so much time.',
                    'user_name': 'Dr. Sarah Johnson',
                    'display_name': 'Dr. Sarah J.',
                    'rating': 5,
                    'author_role': 'Dean of Students',
                    'author_organization': 'University of Technology'
                },
                {
                    'testimonial_id': 2,
                    'title': 'Great for Large Classes',
                    'description': 'Managing attendance for 200+ students was a nightmare before. Now it\'s automated and efficient. Highly recommended!',
                    'user_name': 'Michael Chen',
                    'display_name': 'Michael C.',
                    'rating': 4,
                    'author_role': 'IT Director',
                    'author_organization': 'Global Business School'
                },
                {
                    'testimonial_id': 3,
                    'title': 'Very Reliable',
                    'description': 'The system rarely has any downtime and the reporting features are comprehensive. It has made administrative tasks much easier.',
                    'user_name': 'Robert Williams',
                    'display_name': 'Robert W.',
                    'rating': 5,
                    'author_role': 'Principal',
                    'author_organization': 'Metropolitan High School'
                }
            ]
            
            # Add only the number of fallback testimonials needed
            testimonials_data.extend(fallback_testimonials[:additional_needed])
    
    else:
        # If no data from database, use fallback testimonials
        testimonials_data = [
            {
                'testimonial_id': 1,
                'title': 'Excellent Attendance System',
                'description': 'This platform has completely transformed how we track attendance. The facial recognition feature is incredibly accurate and saves us so much time.',
                'user_name': 'Dr. Sarah Johnson',
                'display_name': 'Dr. Sarah J.',
                'rating': 5,
                'author_role': 'Dean of Students',
                'author_organization': 'University of Technology'
            },
            {
                'testimonial_id': 2,
                'title': 'Great for Large Classes',
                'description': 'Managing attendance for 200+ students was a nightmare before. Now it\'s automated and efficient. Highly recommended!',
                'user_name': 'Michael Chen',
                'display_name': 'Michael C.',
                'rating': 4,
                'author_role': 'IT Director',
                'author_organization': 'Global Business School'
            },
            {
                'testimonial_id': 3,
                'title': 'Very Reliable',
                'description': 'The system rarely has any downtime and the reporting features are comprehensive. It has made administrative tasks much easier.',
                'user_name': 'Robert Williams',
                'display_name': 'Robert W.',
                'rating': 5,
                'author_role': 'Principal',
                'author_organization': 'Metropolitan High School'
            }
        ]
    
    # Prepare stats for template
    stats = {}
    if stats_result['success']:
        stats = stats_result['stats']
    
    template_stats = {
        'institutions': stats.get('total_count', 0) or 500,
        'satisfaction': 98,
        'users': stats.get('total_count', 0) * 500 or 250000,  # Estimate users
        'attendance_increase': 23
    }
    
    return render_template(
        'unregistered/testimonials.html',
        testimonials=testimonials_data,
        stats=template_stats
    )

@main_bp.route('/testimonials/<int:testimonial_id>')
def testimonial_detail(testimonial_id):
    """Detailed testimonial page"""
    # Get the specific testimonial
    result = TestimonialControl.get_testimonial_by_id(current_app, testimonial_id)
    
    if not result['success']:
        flash('Testimonial not found', 'error')
        return redirect(url_for('main.testimonials'))
    
    testimonial = result['testimonial']
    
    # Get related testimonials (same institution or similar rating)
    related_result = TestimonialControl.get_public_testimonials(
        current_app,
        institution_id=testimonial.get('institution_id'),
        limit=3
    )
    
    related_testimonials = []
    if related_result['success']:
        # Filter out the current testimonial
        related_testimonials = [
            t for t in related_result['testimonials'] 
            if t.get('testimonial_id') != testimonial_id
        ][:3]
    
    # Sample related testimonials as fallback
    if not related_testimonials:
        related_testimonials = [
            {
                'title': 'Excellent Attendance System',
                'description': 'This platform has completely transformed how we track attendance. The facial recognition feature is incredibly accurate and saves us so much time.',
                'user_name': 'Dr. Sarah Johnson',
                'display_name': 'Dr. Sarah J.',
                'rating': 5
            },
            {
                'title': 'Great for Large Classes',
                'description': 'Managing attendance for 200+ students was a nightmare before. Now it\'s automated and efficient. Highly recommended!',
                'user_name': 'Michael Chen',
                'display_name': 'Michael C.',
                'rating': 4
            },
            {
                'title': 'Very Reliable',
                'description': 'The system rarely has any downtime and the reporting features are comprehensive. It has made administrative tasks much easier.',
                'user_name': 'Robert Williams',
                'display_name': 'Robert W.',
                'rating': 5
            }
        ]
    
    # Prepare detailed testimonial data for template
    detailed_testimonial = {
        'title': testimonial.get('title', 'How AttendAI Transformed Our Attendance Tracking'),
        'description': testimonial.get('description', ''),
        'user_name': testimonial.get('user_name', 'Test User'),
        'author_role': 'Director of Human Resources',  # Could store this in user profile
        'author_organization': testimonial.get('author_organization', 'HelloWorld University'),
        'rating': testimonial.get('rating', 5),
        'date_submitted': testimonial.get('date_submitted', datetime.datetime.now().strftime('%B %d, %Y'))
    }
    
    # Prepare results data
    results_data = [
        {'value': '85%', 'label': 'Reduction in administrative time'},
        {'value': '99.7%', 'label': 'Attendance accuracy rate'},
        {'value': '23%', 'label': 'Increase in overall attendance'},
        {'value': '4.8/5', 'label': 'Faculty satisfaction score'}
    ]
    
    return render_template(
        'unregistered/testimonialdetails.html',
        testimonial=detailed_testimonial,
        related_testimonials=related_testimonials,
        results=results_data
    )

@main_bp.route('/submit-testimonial', methods=['GET', 'POST'])
def submit_testimonial():
    """Page for submitting a new testimonial"""
    from flask import session as flask_session  # Import Flask session separately to avoid confusion
    
    if request.method == 'POST':
        # Get user info from verified session
        user = auth_result['user']
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