from flask import Blueprint, render_template, session, redirect, url_for, flash, current_app, request
from application.controls.auth_control import AuthControl
from application.controls.attendance_control import AttendanceControl
from application.boundaries.dev_actions import register_action

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def auth():
    """Main dashboard route"""
    # Check authentication
    auth_result = AuthControl.verify_session(current_app, session)
    
    if not auth_result['success']:
        flash('Please login to access the dashboard', 'warning')
        return redirect(url_for('auth.login'))
    
    # Get user from session
    user = auth_result.get('user', {})
    user_id = user.get('firebase_uid') or session.get('user_id')
    
    # Get attendance summary
    attendance_summary = {}
    if user_id:
        attendance_result = AttendanceControl.get_user_attendance_summary(current_app, user_id, days=30)
        if attendance_result['success']:
            attendance_summary = attendance_result['summary']
    
    return render_template('dashboard.html',
                         user=user,
                         attendance_summary=attendance_summary)

@auth_bp.route('/profile')
def profile():
    """User profile route"""
    auth_result = AuthControl.verify_session(current_app, session)
    
    if not auth_result['success']:
        flash('Please login to view profile', 'warning')
        return redirect(url_for('auth.login'))
    
    return render_template('profile.html', user=auth_result['user'])


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login route (GET shows form, POST authenticates)"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user_type = request.form.get('role') or request.form.get('user_type') or 'student'

        try:
            auth_result = AuthControl.authenticate_user(current_app, email, password, user_type=user_type)
        except Exception as e:
            current_app.logger.exception('Login exception')
            flash('Internal error while attempting to authenticate. Try again later.', 'danger')
            return render_template('auth/login.html')

        if auth_result.get('success'):
            # store minimal session state
            session['user_id'] = auth_result.get('firebase_uid')
            session['id_token'] = auth_result.get('id_token')
            resolved_type = auth_result.get('user_type', user_type)
            session['user_type'] = resolved_type
            session['user'] = auth_result.get('user')
            flash('Logged in successfully', 'success')

            # Redirect users to the role-specific dashboard
            # platform_manager -> platform dashboard
            if resolved_type in ['platform_manager', 'platform', 'platmanager']:
                return redirect(url_for('platform.platform_dashboard'))

            # institution_admin -> institution admin dashboard
            if resolved_type in ['institution_admin', 'admin']:
                return redirect(url_for('institution.institution_dashboard'))

            # lecturer -> lecturer dashboard (separate scope)
            if resolved_type in ['lecturer', 'teacher']:
                return redirect(url_for('institution_lecturer.lecturer_dashboard'))

            # all other users (students, default) -> main dashboard
            return redirect(url_for('dashboard.dashboard'))

        flash(auth_result.get('error', 'Login failed'), 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration (creates Firebase user + local profile)."""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'student')

        # Only institution admins are allowed to register via this form
        if role != 'institution_admin':
            flash('Registration is restricted to Institution Admins only.', 'warning')
            return render_template('auth/register.html')

        institution_name = request.form.get('institution_name')
        # require institution name
        if not institution_name:
            flash('Educational Institute name is required for Institution Admin registration.', 'warning')
            return render_template('auth/register.html')

        # Build payload for institution registration (creates a pending/unregistered entry)
        institution_data = {
            'email': email,
            'full_name': name,
            'institution_name': institution_name,
            'institution_address': request.form.get('institution_address') or '',
            'phone_number': request.form.get('phone_number') or '',
            'message': request.form.get('message') or '',
            'selected_plan_id': request.form.get('selected_plan_id') or None
        }

        result = AuthControl.register_institution(current_app, institution_data)
        if result.get('success'):
            flash(result.get('message') or 'Registration request submitted — awaiting approval', 'success')
            return redirect(url_for('main.home'))
        else:
            flash(result.get('error') or 'Failed to submit registration request', 'danger')

    return render_template('auth/register.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('main.home'))

@auth_bp.route('/attendance-history')
def attendance_history():
    """Attendance history route"""
    auth_result = AuthControl.verify_session(current_app, session)
    
    if not auth_result['success']:
        flash('Please login to view attendance history', 'warning')
        return redirect(url_for('auth.login'))
    
    user_id = auth_result['user']['firebase_uid']
    attendance_result = AttendanceControl.get_user_attendance_summary(current_app, user_id, days=90)
    
    if attendance_result['success']:
        return render_template('attendance_history.html',
                             user=auth_result['user'],
                             summary=attendance_result['summary'],
                             records=attendance_result['records'])
    else:
        flash('Failed to load attendance history', 'danger')
        return redirect(url_for('dashboard.dashboard'))


# Register dev actions for auth helpers
try:
    register_action(
        'register_user',
        AuthControl.register_user,
        params=[
            {'name': 'email', 'label': 'Email', 'placeholder': 'email@example.com'},
            {'name': 'password', 'label': 'Password', 'placeholder': 'min 6 chars'},
            {'name': 'name', 'label': 'Full name', 'placeholder': 'Optional display name'},
            {'name': 'role', 'label': 'Role', 'placeholder': 'student | lecturer | institution_admin | platform_manager'}
        ],
        description='Create a Firebase user and a local user record (dev use only)'
    )

    register_action(
        'authenticate_user',
        AuthControl.authenticate_user,
        params=[
            {'name': 'email', 'label': 'Email', 'placeholder': 'email@example.com'},
            {'name': 'password', 'label': 'Password', 'placeholder': 'password'},
            {'name': 'user_type', 'label': 'User type', 'placeholder': 'student | lecturer | institution_admin | platform_manager'}
        ],
        description='Authenticate a user via Firebase (dev only)'
    )
except Exception:
    pass


