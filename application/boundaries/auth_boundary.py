from flask import Blueprint, render_template, session, redirect, url_for, flash, current_app, request
import secrets
import bcrypt
from application.controls.auth_control import AuthControl, authenticate_user, requires_roles
from application.controls.attendance_control import AttendanceControl
from application.entities2.institution import InstitutionModel
from application.entities2.user import UserModel
from application.entities2.subscription import SubscriptionModel
from database.base import get_session
from application.boundaries.dev_actions import register_action

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
@requires_roles('student', 'lecturer', 'admin', 'platform_manager')
def auth():
    """Main dashboard route"""
    return render_template('dashboard.html')

@auth_bp.route('/profile')
@requires_roles('student', 'lecturer', 'admin', 'platform_manager')
def profile():
    """User profile route"""
    return render_template('components/profile.html')


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
    """User registration"""
    institutions = []
    subscription_plans = []
    # Allow pre-selecting a plan and role via query params (used by subscription CTA links)
    # Accept preselected values from either GET query (when arriving from CTA) or from POST form (in case of validation errors)
    preselected_plan_id = request.args.get('selected_plan_id') or request.form.get('selected_plan_id')
    preselected_role = 'institution_admin'

    try:
        with get_session() as session:
            inst_model = InstitutionModel(session)
            institutions_objs = inst_model.get_all()
            institutions = [{'institution_id': inst.institution_id, 'name': inst.name} for inst in institutions_objs if getattr(inst, 'is_active', True)]

            # Load subscription plans for institution admin registration selection
            sub_model = SubscriptionModel(session)
            plans = sub_model.get_all()
            subscription_plans = [{'plan_id': p.plan_id, 'name': p.name, 'price': getattr(p, 'price_per_cycle', None), 'billing_cycle': getattr(p, 'billing_cycle', None)} for p in plans if getattr(p, 'is_active', True)]
    except Exception as e:
        current_app.logger.warning(f"Could not load institutions or subscription plans: {e}")
        institutions = []
        subscription_plans = []


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
                return render_template('auth/register.html', institutions=institutions, subscription_plans=subscription_plans, preselected_plan_id=preselected_plan_id, preselected_role=preselected_role)
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
            # For other roles, create a local user account (registration)
            institution_id = request.form.get('institution_id') or None
            if role in ['student', 'lecturer'] and not institution_id:
                flash('Please select an institution for your account', 'warning')
                return render_template('auth/register.html', institutions=institutions, subscription_plans=subscription_plans, preselected_plan_id=preselected_plan_id, preselected_role=preselected_role)
            try:
                # Validate registration
                reg_res = AuthControl.register_user(current_app, email, password, name=name, role=role)
            except Exception as e:
                current_app.logger.exception('Registration exception')
                flash('Internal error while attempting to register. Try again later.', 'danger')
                return render_template('auth/register.html', institutions=institutions, subscription_plans=subscription_plans, preselected_plan_id=preselected_plan_id, preselected_role=preselected_role)

            if reg_res.get('success'):
                # Optionally create a local DB record for student/lecturer using new User model
                try:
                    pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    with get_session() as session:
                        user_model = UserModel(session)
                        user_model.create(
                            institution_id=int(institution_id) if institution_id else None,
                            role=role if role in ['student', 'lecturer'] else 'student',
                            email=email,
                            password_hash=pw_hash,
                            name=name
                        )
                except Exception as e:
                    current_app.logger.warning(f"Local user creation failed: {e}")
                flash('Registration successful. Please log in.', 'success')
                return redirect(url_for('auth.login'))
            else:
                flash(reg_res.get('error') or 'Registration failed', 'danger')
                return render_template('auth/register.html', institutions=institutions, subscription_plans=subscription_plans, preselected_plan_id=preselected_plan_id, preselected_role=preselected_role)

    return render_template('auth/register.html', institutions=institutions, subscription_plans=subscription_plans, preselected_plan_id=preselected_plan_id, preselected_role=preselected_role)


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('main.home'))

@auth_bp.route('/attendance-history')
@requires_roles('student', 'lecturer', 'admin', 'platform_manager')
def attendance_history():
    """Attendance history route"""
    return render_template('attendance_history.html')

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
