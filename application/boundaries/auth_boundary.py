from flask import Blueprint, render_template, session, redirect, url_for, flash, current_app, request
import secrets
import bcrypt
from application.controls.auth_control import AuthControl, authenticate_user
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
    user_id = user.get('firebase_uid') or session.get('user_id')
    
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

        try:
            auth_result = authenticate_user(email, password)
        except Exception as e:
            current_app.logger.exception('Login exception')
            flash('Internal error while attempting to authenticate. Try again later.', 'danger')
            return render_template('auth/login.html')

        if auth_result.get('success'):
            # store minimal session state
            user = auth_result.get('user')
            session['user_id'] = user['user_id']
            session['role'] = user['role']
            session['institution_id'] = user.get('institution_id')
            role = user['role']
            flash('Logged in successfully', 'success')
            # Redirect users to the role-specific dashboard
            # platform_manager -> platform dashboard
            if role == 'platform_manager':
                return redirect(url_for('platform.platform_dashboard'))
            # institution_admin -> institution admin dashboard
            elif role == 'admin':
                return redirect(url_for('institution.institution_dashboard'))
            # lecturer -> lecturer dashboard (separate scope)
            elif role == 'lecturer':
                return redirect(url_for('institution_lecturer.lecturer_dashboard'))
            # Dont even trust your db enum, check for student
            elif role == 'student':
                return redirect(url_for('student.dashboard'))
            else:
                flash('Unknown user role: ' + role, 'danger')
                session.clear()
                return redirect(url_for('main.home')) 
        flash(auth_result.get('error', 'Login failed'), 'danger')
    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration (creates Firebase user + local profile)."""
    # load active institutions for the registration form (for student/lecturer selection)
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
            # require institution name
            if not institution_name:
                flash('Educational Institute name is required for Institution Admin registration.', 'warning')
                return render_template('auth/register.html', institutions=institutions)

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

        else:
            # For other roles, create a Firebase user account (registration)
            institution_id = request.form.get('institution_id') or None
            if role in ['student', 'lecturer'] and not institution_id:
                flash('Please select an institution for your account', 'warning')
                return render_template('auth/register.html', institutions=institutions)
            try:
                reg_res = AuthControl.register_user(current_app, email, password, name=name, role=role)
            except Exception as e:
                current_app.logger.exception('Registration exception')
                flash('Internal error while attempting to register. Try again later.', 'danger')
                return render_template('auth/register.html', institutions=institutions)

            if reg_res.get('success'):
                # Optionally create a local DB record for student/lecturer
                try:
                    pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
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
    
    user_id = auth_result['user']['firebase_uid']
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


