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
            session['user_type'] = auth_result.get('user_type', user_type)
            session['user'] = auth_result.get('user')
            flash('Logged in successfully', 'success')
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

        result = AuthControl.register_user(current_app, email, password, name=name, role=role)
        if result.get('success'):
            session['user_id'] = result.get('firebase_uid')
            session['id_token'] = result.get('id_token')
            session['user_type'] = role
            session['user'] = {'email': email, 'name': name, 'role': role}
            flash('Registration successful — you are now logged in', 'success')
            return redirect(url_for('dashboard.dashboard'))

        # Show friendly error messages from AuthControl.register_user
        if not result.get('success'):
            err = result.get('error') or 'Registration failed'
            if result.get('error_type') == 'EMAIL_EXISTS':
                flash('That email is already registered. Try logging in instead.', 'warning')
            elif result.get('error_type') == 'WEAK_PASSWORD':
                flash('The password is too weak. Use a stronger password.', 'warning')
            else:
                flash(err, 'danger')

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


        # Dev-exposable auth actions (register + authenticate)
        register_action(
            'register_user',
            AuthControl.register_user,
            params=[
                {'name': 'email', 'label': 'Email', 'placeholder': 'email@example.com'},
                {'name': 'password', 'label': 'Password', 'placeholder': 'min 6 chars'},
                {'name': 'name', 'label': 'Full name', 'placeholder': 'Optional display name'},
                {'name': 'role', 'label': 'Role', 'placeholder': 'student | lecturer | platform_manager'}
            ],
            description='Create a Firebase user and a local user record (dev use only)'
        )

        register_action(
            'authenticate_user',
            AuthControl.authenticate_user,
            params=[
                {'name': 'email', 'label': 'Email', 'placeholder': 'email@example.com'},
                {'name': 'password', 'label': 'Password', 'placeholder': 'password'},
                {'name': 'user_type', 'label': 'User type', 'placeholder': 'student | lecturer | platform_manager'}
            ],
            description='Authenticate a user via Firebase (dev only)'
        )