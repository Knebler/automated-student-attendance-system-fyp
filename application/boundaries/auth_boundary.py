from flask import Blueprint, render_template, session, redirect, url_for, flash, current_app, request
import secrets
import bcrypt
from application.controls.auth_control import AuthControl
from application.controls.attendance_control import AttendanceControl
from application.entities.institution import Institution
from application.entities.student import Student
from application.entities.lecturer import Lecturer
from application.entities.base_entity import BaseEntity
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
    user_id = user.get('user_id')
    
    # Get attendance summary
    attendance_summary = {}
    if user_id:
        attendance_result = AttendanceControl.get_all_sessions_attendance(current_app, user_id, days=30)
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
    
    return render_template('components/profile.html', user=auth_result['user'])


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login route (GET shows form, POST authenticates)"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user_type = request.form.get('role') or 'student'

        try:
            auth_result = AuthControl.authenticate_user(current_app, email, password, user_type=user_type)
        except Exception:
            current_app.logger.exception('Login exception')
            flash('Internal error while attempting to authenticate. Try again later.', 'danger')
            return render_template('auth/login.html')

        if not auth_result.get('success'):
            flash(auth_result.get('error', 'Login failed'), 'danger')
            return render_template('auth/login.html')

        # Success — rely on AuthControl returned fields
        user = auth_result.get('user', {}) or {}
        user.pop('password_hash', None)
        session['user'] = user
        session['user_id'] = auth_result.get('user_id') or user.get('user_id')
        resolved_type = auth_result.get('user_type') or user.get('user_type') or user.get('role') or user_type
        session['role'] = resolved_type

        flash('Logged in successfully', 'success')

        # Redirect users to the role-specific dashboard
        if resolved_type in ['platform_manager', 'platform', 'platmanager']:
            return redirect(url_for('platform.platform_dashboard'))

        if resolved_type in ['institution_admin', 'admin']:
            return redirect(url_for('institution.institution_dashboard'))

        if resolved_type in ['lecturer', 'teacher']:
            return redirect(url_for('institution_lecturer.lecturer_dashboard'))

        # all other users (students, default) -> main dashboard
        return redirect(url_for('student.dashboard'))

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration (creates local profile only)."""
    # load active institutions for the registration form
    institutions_raw = BaseEntity.execute_query(current_app, "SELECT institution_id, name FROM Institutions WHERE is_active = TRUE", fetch_all=True)
    institutions = [{'institution_id': r[0], 'name': r[1]} for r in institutions_raw] if institutions_raw else []

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'student')

        # Institution Admins: create a pending registration request
        if role == 'institution_admin':
            institution_name = request.form.get('institution_name')
            if not institution_name:
                flash('Educational Institute name is required for Institution Admin registration.', 'warning')
                return render_template('auth/register.html', institutions=institutions)

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

        else:
            # For other roles, validate registration
            institution_id = request.form.get('institution_id') or None
            if role in ['student', 'lecturer'] and not institution_id:
                flash('Please select an institution for your account', 'warning')
                return render_template('auth/register.html', institutions=institutions)
            
            try:
                # Validate registration
                reg_res = AuthControl.register_user(current_app, email, password, name=name, role=role)
            except Exception as e:
                current_app.logger.exception('Registration exception')
                flash('Internal error while attempting to register. Try again later.', 'danger')
                return render_template('auth/register.html', institutions=institutions)

            if reg_res.get('success'):
                try:
                    # Use the hashed password from registration validation
                    pw_hash = reg_res.get('password_hash')
                    if role == 'student':
                        model = Student.get_model()
                        # Generate a student_code (simple fallback)
                        student_code = f"S{secrets.token_hex(3)}"
                        student = BaseEntity.create(current_app, model, {
                            'institution_id': int(institution_id) if institution_id else None,
                            'student_code': student_code,
                            'email': email,
                            'password_hash': pw_hash,
                            'full_name': name
                        })
                    elif role == 'lecturer':
                        model = Lecturer.get_model()
                        lecturer = BaseEntity.create(current_app, model, {
                            'institution_id': int(institution_id) if institution_id else None,
                            'email': email,
                            'password_hash': pw_hash,
                            'full_name': name
                        })
                except Exception as e:
                    current_app.logger.warning(f"Local {role} creation failed: {e}")

                flash('Registration successful. Please log in.', 'success')
                return redirect(url_for('auth.login'))
            else:
                flash(reg_res.get('error') or 'Registration failed', 'danger')
                return render_template('auth/register.html', institutions=institutions)

    return render_template('auth/register.html', institutions=institutions)


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
    
    user_id = auth_result['user'].get('user_id')
    attendance_result = AttendanceControl.get_user_attendance_summary(current_app, user_id, days=90)
    
    if attendance_result['success']:
        return render_template('attendance_history.html',
                             user=auth_result['user'],
                             summary=attendance_result['summary'],
                             records=attendance_result['records'])
    else:
        flash('Failed to load attendance history', 'danger')
        return redirect(url_for('student.dashboard'))


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
        description='Create a local user record (dev use only)'
    )

    register_action(
        'authenticate_user',
        AuthControl.authenticate_user,
        params=[
            {'name': 'email', 'label': 'Email', 'placeholder': 'email@example.com'},
            {'name': 'password', 'label': 'Password', 'placeholder': 'password'},
            {'name': 'user_type', 'label': 'User type', 'placeholder': 'student | lecturer | institution_admin | platform_manager'}
        ],
        description='Authenticate a user (dev only)'
    )
except Exception:
    pass