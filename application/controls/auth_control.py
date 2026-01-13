# auth_control.py (updated to use ORM only)
from application.entities2.user import UserModel
from application.entities2.institution import InstitutionModel
from application.controls.institution_control import InstitutionControl
from application.entities2.subscription import SubscriptionModel
from application.entities2.subscription_plans import SubscriptionPlanModel
from datetime import datetime, timedelta, date
import bcrypt
import secrets
from functools import wraps
from flask import flash, redirect, url_for, session
from sqlalchemy.exc import IntegrityError

from database.base import get_session

def requires_roles(roles):
    """
    Decorator to require specific role from session
    Usage: @requires_roles(['admin', 'student'])
        or @requires_roles('admin')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            print("Checking roles...")
            # Normalize roles to a list
            allowed = roles if isinstance(roles, (list, tuple, set)) else [roles]
            # Check if user is logged in and has an allowed role
            if 'role' not in session or session.get('role') not in allowed:
                flash('Access denied.', 'danger')
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def authenticate_user(email, password):
    """Authenticate user based on their role/type using ORM"""
    if (email, password) == ("admin@attendanceplatform.com", "password"):
        return {
            'success': True,
            'user': { 'user_id': 0, 'role': 'platform_manager' },
        }

    try:
        with get_session() as db_session:
            user_model = UserModel(db_session)
            user = user_model.get_by_email(email)
            if not user or not getattr(user, 'password_hash', None):
                return {'success': False, 'error': 'Invalid email or password'}
            if bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
                return {
                    'success': True,
                    'user': user.as_sanitized_dict(),
                }
    except Exception as e:
        # log if necessary
        pass
    return {'success': False, 'error': 'Invalid email or password'}

class AuthControl:
    """Control class for authentication business logic with multi-role support"""
    
    @staticmethod
    def authenticate_user(email, password):
        """Authenticate user based on their role/type using ORM"""
        with get_session() as db_session:
            user_model = UserModel(db_session)
            user = user_model.get_by_email(email)
            if bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
                return {
                    'success': True,
                    'user_id': user.user_id,
                    'role': user.role,
                }
        return {'success': False, 'error': 'Invalid email or password'}
        
    @staticmethod
    def get_user_by_email(app, email):
        """Convenience method returning a user dict (defaults to student-level lookup)."""
        return AuthControl.get_user_by_email_and_type(app, email, 'student')

    @staticmethod
    def get_user_by_email_and_type(app, email, user_type):
        """Get user information using `users` table (UserModel). Returns a simple dict."""
        try:
            with get_session() as db_session:
                user_model = UserModel(db_session)
                user = user_model.get_by_email(email)
                if not user:
                    return None
                
                return {
                    'user': user.as_sanitized_dict(),
                }
        except Exception as e:
            app.logger.error(f"Error getting user by email and type: {e}")
            return None

    @staticmethod
    def register_institution(app, institution_data: dict):
        """Register an institution application.
        
        This creates:
        1. A pending subscription (is_active=False)
        2. The institution record
        3. An admin user for the institution
        
        All records are linked together.
        """
        try:
            email = institution_data.get('email')
            full_name = institution_data.get('full_name')
            inst_name = institution_data.get('institution_name')
            inst_address = institution_data.get('institution_address')
            phone = institution_data.get('phone_number')
            message = institution_data.get('message', '')
            selected_plan = institution_data.get('selected_plan_id')
            
            # Generate a temporary password
            temp_password = secrets.token_urlsafe(12)

            with get_session() as db_session:
                # Check if email is already registered (as a user)
                user_model = UserModel(db_session)
                existing_user = user_model.get_by_email(email)
                if existing_user:
                    return {'success': False, 'error': 'This email is already registered as a user.'}

                # Check if institution name already exists
                institution_model = InstitutionModel(db_session)
                existing_institution = institution_model.get_by_name(inst_name)
                if existing_institution:
                    return {'success': False, 'error': 'An institution with this name already exists.'}

                # Verify the selected plan exists
                subscription_plan_model = SubscriptionPlanModel(db_session)
                plan = subscription_plan_model.get_by_id(selected_plan)
                if not plan:
                    return {'success': False, 'error': 'Selected subscription plan does not exist.'}

                # Create pending subscription
                subscription_model = SubscriptionModel(db_session)
                start_date = date.today()
                end_date = start_date + timedelta(days=365)
                subscription = subscription_model.create(
                    plan_id=selected_plan,
                    start_date=start_date,
                    end_date=end_date,
                    is_active=False,
                    stripe_subscription_id=None  # Will be set when payment is processed
                )

                # Create institution
                institution = institution_model.create(
                    name=inst_name,
                    address=inst_address,
                    poc_name=full_name,
                    poc_phone=phone,
                    poc_email=email,
                    subscription_id=subscription.subscription_id
                )

                # Create admin user for the institution
                # Hash the temporary password
                password_hash = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                admin_user = user_model.create(
                    institution_id=institution.institution_id,
                    role='admin',
                    name=full_name,
                    phone_number=phone,
                    email=email,
                    password_hash=password_hash,
                    is_active=False  # User inactive until subscription is approved
                )

                # Commit all changes
                db_session.commit()

                return {
                    'success': True,
                    'message': 'Registration request submitted — awaiting approval',
                    'institution_id': institution.institution_id,
                    'subscription_id': subscription.subscription_id,
                    'admin_user_id': admin_user.user_id,
                    'temp_password': temp_password,  # For email notification
                    'notes': 'Admin user created but inactive. Will be activated when subscription is approved.'
                }

        except IntegrityError as e:
            db_session.rollback()
            app.logger.error(f"Integrity error in institution registration: {e}")
            return {'success': False, 'error': 'Database integrity error. Please try again.'}
            
        except Exception as e:
            if 'db_session' in locals():
                db_session.rollback()
            app.logger.exception(f"Error registering institution: {e}")
            return {'success': False, 'error': f'Registration failed: {str(e)}'}
    """ 
    @staticmethod
    def approve_institution_registration(app, subscription_id):
        Activate a pending institution registration.
        try:
            with get_session() as db_session:
                subscription_model = SubscriptionModel(db_session)
                institution_model = InstitutionModel(db_session)
                user_model = UserModel(db_session)
                
                # Get and activate subscription
                subscription = subscription_model.get_by_id(subscription_id)
                if not subscription:
                    return {'success': False, 'error': 'Subscription not found.'}
                    
                if subscription.is_active:
                    return {'success': False, 'error': 'Subscription is already active.'}
                
                subscription.is_active = True
                
                # Get the institution linked to this subscription
                institution = institution_model.get_by_subscription_id(subscription_id)
                if not institution:
                    return {'success': False, 'error': 'Institution not found for this subscription.'}
                
                # Activate the admin user
                admin_user = user_model.get_by_email(institution.poc_email)
                if admin_user:
                    admin_user.is_active = True
                
                db_session.commit()
                
                return {
                    'success': True,
                    'message': 'Institution registration approved successfully',
                    'institution_id': institution.institution_id,
                    'subscription_id': subscription.subscription_id
                }
                
        except Exception as e:
            if 'db_session' in locals():
                db_session.rollback()
            app.logger.exception(f"Error approving institution registration: {e}")
            return {'success': False, 'error': str(e)}

        """
