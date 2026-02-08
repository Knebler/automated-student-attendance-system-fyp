from flask import Blueprint, json, render_template, session, redirect, url_for, flash, current_app, request, jsonify
import secrets
import bcrypt
from application.controls.auth_control import AuthControl, authenticate_user, requires_roles
from application.controls.attendance_control import AttendanceControl
from application.entities2.institution import InstitutionModel
from application.entities2.user import UserModel
from application.entities2.subscription import SubscriptionModel
from application.entities2.subscription_plans import SubscriptionPlanModel
from database.base import get_session
from application.boundaries.dev_actions import register_action
import stripe

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
@requires_roles('student' or 'lecturer' or 'admin' or 'platform_manager')
def auth():
    """Main dashboard route"""
    return render_template('dashboard.html')

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
    preselected_plan_id = request.args.get('selected_plan_id') or request.form.get('selected_plan_id')
    preselected_role = 'institution_admin'

    # Get database session outside the try block so it's available in except
    db_session = None
    try:
        with get_session() as db_session:
            # Get institutions
            inst_model = InstitutionModel(db_session)
            institutions_objs = inst_model.get_all()
            institutions = [{'institution_id': inst.institution_id, 'name': inst.name} 
                          for inst in institutions_objs if getattr(inst, 'is_active', True)]

            # FIXED: Use SubscriptionPlanModel instead of SubscriptionModel
            plan_model = SubscriptionPlanModel(db_session)
            plans = plan_model.get_active_plans()
            
            # Adjust field names based on your SubscriptionPlan model
            subscription_plans = [
                {
                    'plan_id': p.plan_id, 
                    'name': p.name, 
                    'price': getattr(p, 'price_per_cycle', None),
                    'billing_cycle': getattr(p, 'billing_cycle', None)
                } 
                for p in plans
            ]
    except Exception as e:
        # Don't try to use db_session in except block - it might not be initialized
        current_app.logger.warning(f"Could not load institutions or subscription plans: {e}")
        institutions = []
        subscription_plans = []
        # No need to access db_session here

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'student')

        # Institution Admins: collect registration data and redirect to payment
        if role == 'institution_admin':
            institution_name = request.form.get('institution_name')
            if not institution_name:
                flash('Educational Institute name is required for Institution Admin registration.', 'warning')
                return render_template('auth/register.html', institutions=institutions, subscription_plans=subscription_plans, preselected_plan_id=preselected_plan_id, preselected_role=preselected_role)
            
            # Store registration data in session for payment page
            registration_data = {
                'name': name,
                'email': email,
                'password': password,
                'role': role,
                'institution_name': institution_name,
                'institution_address': (request.form.get('institution_address') or '').strip(),
                'detailed_address': (request.form.get('detailed_address') or '').strip(),
                'selected_plan_id': request.form.get('selected_plan_id') or None
            }
            
            # This uses Flask's session object (not the database session)
            session['registration_data'] = registration_data
            
            # Redirect to payment page
            return redirect(url_for('auth.payment'))
        
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
                    # Get a new database session for user creation
                    with get_session() as user_db_session:
                        user_model = UserModel(user_db_session)
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
@requires_roles('student' or 'lecturer' or 'admin'or 'platform_manager')
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

@auth_bp.route('/payment', methods=['GET'])
def payment():
    """Show payment page with registration summary"""
    # Get registration data from session
    registration_data = session.get('registration_data')
    if not registration_data:
        flash('Please complete registration first', 'warning')
        return redirect(url_for('auth.register'))
    
    try:
        with get_session() as db_session:
            # Get subscription plan details
            if registration_data.get('selected_plan_id'):
                plan_model = SubscriptionPlanModel(db_session)
                selected_plan = plan_model.get_by_id(registration_data['selected_plan_id'])
            else:
                selected_plan = None
            
            # Convert registration data to JSON for hidden field
            registration_data_json = json.dumps(registration_data)
            
            return render_template(
                'auth/payment.html',
                registration_data=registration_data,
                registration_data_json=registration_data_json,
                selected_plan=selected_plan,
                stripe_public_key=current_app.config.get('STRIPE_PUBLIC_KEY')
            )
    except Exception as e:
        current_app.logger.error(f"Error loading payment page: {e}")
        flash('Error loading payment information', 'danger')
        return redirect(url_for('auth.register'))

@auth_bp.route('/process_payment', methods=['POST'])
def process_payment():
    """Process payment and complete registration (mock version without real Stripe calls)"""
    try:
        # Get registration data from form
        registration_data_json = request.form.get('registration_data')
        if not registration_data_json:
            flash('Invalid registration data', 'danger')
            return redirect(url_for('auth.register'))
        
        registration_data = json.loads(registration_data_json)
        
        # Mock payment method validation (skip actual validation in dev mode)
        payment_method_id = request.form.get('payment_method_id')
        
        if not payment_method_id:
            # In development, allow bypassing real payment validation
            # For production, you'd want to keep this check
            if current_app.config.get('ENV') == 'development':
                # Generate a mock payment method ID
                import secrets
                payment_method_id = f'pm_mock_{secrets.token_hex(8)}'
            else:
                flash('Payment information is required', 'danger')
                return redirect(url_for('auth.payment'))
        
        # Get subscription plan
        with get_session() as db_session:
            plan_model = SubscriptionPlanModel(db_session)
            selected_plan = plan_model.get_by_id(registration_data.get('selected_plan_id'))
        
            if not selected_plan:
                flash('Invalid subscription plan', 'danger')
                return redirect(url_for('auth.register'))
            
            # Generate mock Stripe IDs (no actual API calls)
            import secrets
            import time
            
            # Mock Stripe customer ID
            stripe_customer_id = f'cus_mock_{secrets.token_hex(12)}'
            
            # Mock Stripe subscription ID
            timestamp = int(time.time())
            random_hex = secrets.token_hex(6)
            stripe_subscription_id = f'sub_mock_{timestamp}_{random_hex}'
            
            # Update registration data with mock Stripe info
            registration_data['stripe_customer_id'] = stripe_customer_id
            registration_data['stripe_subscription_id'] = stripe_subscription_id
            registration_data['mock_payment'] = True  # Flag to indicate mock payment
            
            # Store payment details for record (optional)
            registration_data['payment_details'] = {
                'amount': selected_plan.price_per_cycle,
                'currency': 'usd',
                'billing_cycle': selected_plan.billing_cycle,
                'plan_name': selected_plan.name,
                'payment_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'transaction_id': f'txn_mock_{secrets.token_hex(8)}'
            }
            
        # Store updated registration data in session for the final registration step
        session['registration_data'] = registration_data
            
        # Show confirmation page before final registration
        flash('Payment processed successfully (mock mode). Ready to complete registration.', 'success')
        return redirect(url_for('auth.complete_registration'))
            
    except Exception as e:
        current_app.logger.error(f"Payment processing error: {e}")
        flash('An error occurred while processing payment', 'danger')
        return redirect(url_for('auth.payment'))

@auth_bp.route('/complete_registration', methods=['GET', 'POST'])
def complete_registration():
    """Final step to complete registration with payment confirmation"""
    registration_data = session.get('registration_data')
    if not registration_data:
        flash('Please complete payment first', 'warning')
        return redirect(url_for('auth.register'))

    # Now call the existing registration logic with Stripe info
    institution_data = {
        'email': registration_data['email'],
        'full_name': registration_data['name'],
        'institution_name': registration_data['institution_name'],
        'institution_address': registration_data.get('detailed_address') or registration_data.get('institution_address', ''),
        'selected_plan_id': registration_data.get('selected_plan_id'),
        'stripe_subscription_id': registration_data.get('stripe_subscription_id'),
        'stripe_customer_id': registration_data.get('stripe_customer_id')
    }
    
    result = AuthControl.register_institution(current_app, institution_data)
    
    if result.get('success'):
        # Clear registration data from session
        session.pop('registration_data', None)
        
        flash(result.get('message') or 'Registration completed successfully! Your account is pending approval.', 'success')
        return redirect(url_for('main.home'))
    else:
        flash(result.get('error') or 'Failed to complete registration', 'danger')
        return redirect(url_for('auth.register'))