from application.entities.base_entity import BaseEntity
from application.entities2.user import UserModel
from application.entities.platform_manager import PlatformManager
from application.entities.student import Student
from application.entities.lecturer import Lecturer
from application.entities.institution_admin import InstitutionAdmin
from application.entities.unregistered_user import UnregisteredUser
from application.entities.subscription import Subscription
from application.controls.institution_control import InstitutionControl
from datetime import datetime, timedelta
import traceback
import bcrypt
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import flash, redirect, url_for, session



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
            # Check if user is logged in
            if 'role' not in session or session.get('role') not in roles:
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
        } # Currently shall hardcode the password but idea is only 1 platform manager account

    with get_session() as session:
        user_model = UserModel(session)
        user = user_model.get_by_email(email)
        if bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            return {
                'success': True,
                'user': user.as_sanitized_dict(),
            }
    return {'success': False, 'error': 'Invalid email or password'}

class AuthControl:
    """Control class for authentication business logic with multi-role support"""
    @staticmethod
    def verify_password(password, password_hash):
        """Verify password against bcrypt hash"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    @staticmethod
    def authenticate_user(app, email, password, user_type='student'):
        """Authenticate user based on their role/type using ORM"""
        try:
            # Get user info using ORM
            user_info = AuthControl.get_user_by_email_and_type(app, email, user_type)
            
            if not user_info:
                return {
                    'success': False,
                    'error': f'{user_type.capitalize()} not found in system',
                    'error_type': 'USER_NOT_FOUND'
                }
            
            # Verify password (password_hash should be in user_info)
            password_hash = user_info.get('password_hash')
            if not password_hash or not AuthControl.verify_password(password, password_hash):
                return {
                    'success': False,
                    'error': 'Incorrect password. Please try again.',
                    'error_type': 'INVALID_CREDENTIALS'
                }
            
            return {
                'success': True,
                'user': user_info,
                'user_type': user_type,
                'user_id': user_info.get('user_id')
            }
            
        except Exception as e:
            error_message = str(e)
            app.logger.error(f"Authentication error: {error_message}")
            
            return {
                'success': False,
                'error': 'Authentication failed. Please try again.',
                'error_type': 'UNKNOWN'
            }
    
    @staticmethod
    def get_user_by_email_and_type(app, email, user_type):
        """Get user information based on type using SQLAlchemy ORM"""
        try:
            # Map user_type to entity class
            entity_map = {
                'student': Student,
                'lecturer': Lecturer,
                'teacher': Lecturer,
                'platform_manager': PlatformManager,
                'platform': PlatformManager,
                'platmanager': PlatformManager,
                'institution_admin': InstitutionAdmin,
                'admin': InstitutionAdmin
            }
            
            entity_class = entity_map.get(user_type)
            if not entity_class:
                return None
            
            # Get the actual SQLAlchemy model class
            model_class = entity_class.get_model()
            
            # Use BaseEntity to query with filters
            filters = {'email': email}
            results = BaseEntity.get_all(app, model_class, filters=filters)
            
            if not results:
                return None
            
            result = results[0]  # Get first result
            
            # Convert result to dictionary based on user type
            user_dict = {
                'email': result.email,
                'full_name': result.full_name,
                'user_type': user_type if user_type != 'teacher' else 'lecturer',
                'password_hash': result.password_hash  # Keep this for verification
            }
            
            # Add type-specific fields
            if user_type == 'student':
                user_dict.update({
                    'user_id': result.student_id,
                    'institution_id': result.institution_id,
                    'student_code': result.student_code,
                    'enrollment_year': result.enrollment_year,
                    'is_active': result.is_active
                })
            elif user_type in ['lecturer', 'teacher']:
                user_dict.update({
                    'user_id': result.lecturer_id,
                    'institution_id': result.institution_id,
                    'department': result.department,
                    'is_active': result.is_active
                })
            elif user_type in ['platform_manager', 'platform', 'platmanager']:
                user_dict.update({
                    'user_id': result.platform_mgr_id,
                    'created_at': result.created_at
                })
            elif user_type in ['institution_admin', 'admin']:
                user_dict.update({
                    'user_id': result.inst_admin_id,
                    'institution_id': result.institution_id,
                    'created_at': result.created_at
                })
            
            return user_dict
            
        except Exception as e:
            app.logger.error(f"Error getting user by email and type: {e}")
            return None
    
    @staticmethod
    def verify_session(app, session_obj):
        """Verify an existing session and return user info."""
        try:
            # Prefer explicit user object in session (set during login)
            user = session_obj.get('user')
            if user:
                return {'success': True, 'user': user}

            # Fallback: try session user_id + role
            user_id = session_obj.get('user_id')
            role = session_obj.get('role') or session_obj.get('user_type')
            if user_id and role:
                return {'success': True, 'user': {'user_id': user_id, 'role': role}}

            # Dev fallback for convenience
            if app.config.get('DEBUG', False):
                try:
                    pm_model = PlatformManager.get_model()
                    session = BaseEntity.get_db_session(app)
                    platform_manager = session.query(pm_model).first()

                    if platform_manager:
                        return {
                            'success': True,
                            'user': {
                                'user_type': 'platform_manager',
                                'user_id': platform_manager.platform_mgr_id,
                                'email': platform_manager.email,
                                'full_name': platform_manager.full_name
                            }
                        }

                    return {
                        'success': True,
                        'user': {
                            'user_type': 'platform_manager',
                            'user_id': 0,
                            'email': 'dev@local'
                        }
                    }
                except Exception:
                    return {'success': True, 'user': {'user_type': 'platform_manager', 'user_id': 0}}

            return {'success': False, 'error': 'No session present'}
        except Exception as e:
            # Any error -> mark as not authenticated
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def register_user(app, email, password, name=None, role='student'):
        """Register a new user (creates local record only)"""
        try:
            # Check if user already exists
            existing_user = AuthControl.get_user_by_email_and_type(app, email, role)
            if existing_user:
                return {
                    'success': False,
                    'error': 'Email already registered',
                    'error_type': 'EMAIL_EXISTS'
                }
            
            # Hash password
            pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Generate token for immediate login
            # Note: user_id will be set after creation
            temp_user_id = 0  # Will be updated
            
            # The actual user creation happens in auth_boundary.py
            # This function just validates and returns success
            return {
                'success': True,
                'message': 'User registration validated',
                'password_hash': pw_hash
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': 'REGISTRATION_ERROR'
            }
    
    @staticmethod
    def register_institution(app, institution_data):
        """Register a new institution using ORM"""
        try:
            # Create UnregisteredUser using ORM
            unregistered_user = BaseEntity.create(
                app=app,
                model_class=UnregisteredUser.get_model(),  # Get the actual model class
                data={
                    'email': institution_data.get('email'),
                    'full_name': institution_data.get('full_name'),
                    'institution_name': institution_data.get('institution_name'),
                    'institution_address': institution_data.get('institution_address'),
                    'phone_number': institution_data.get('phone_number'),
                    'message': institution_data.get('message'),
                    'selected_plan_id': institution_data.get('selected_plan_id'),
                    'status': 'pending'
                }
            )
            
            return {
                'success': True,
                'unreg_user_id': unregistered_user.unreg_user_id,
                'message': 'Institution registration request submitted successfully. Awaiting approval.'
            }
            
        except Exception as e:
            app.logger.error(f"Error registering institution: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def approve_unregistered_user(app, unreg_user_id, reviewer_id=None, admin_password=None):
        """Approve a pending Unregistered_Users entry using ORM"""
        try:
            # 1. Get the unregistered user
            unreg_user_model = UnregisteredUser.get_model()
            session = BaseEntity.get_db_session(app)
            unreg_user = session.query(unreg_user_model).get(unreg_user_id)
            
            if not unreg_user or unreg_user.status != 'pending':
                return {
                    'success': False,
                    'error': 'Registration request not found or not pending'
                }
            
            # 2. Create Subscription
            from datetime import date
            start_date = date.today()
            end_date = start_date + timedelta(days=365)
            
            subscription = BaseEntity.create(
                app=app,
                model_class=Subscription.get_model(),  # Get the actual model class
                data={
                    'unreg_user_id': unreg_user_id,
                    'plan_id': unreg_user.selected_plan_id,
                    'start_date': start_date,
                    'end_date': end_date,
                    'status': 'active'
                }
            )
            
            # 3. Create Institution
            inst_data = {
                'name': unreg_user.institution_name,
                'address': unreg_user.institution_address,
                'website': None,
                'subscription_id': subscription.subscription_id
            }
            
            ins_result = InstitutionControl.create_institution(app, inst_data, subscription.subscription_id)
            if not ins_result.get('success'):
                BaseEntity.rollback_changes(app)
                return {
                    'success': False,
                    'error': f"Failed to create institution: {ins_result.get('error')}"
                }
            
            institution_id = ins_result.get('institution_id')
            
            # 4. Create Institution Admin password
            used_password = admin_password or secrets.token_urlsafe(10)
            
            # 5. Create Institution Admin
            pw_hash = bcrypt.hashpw(used_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            admin_model = InstitutionAdmin.get_model()
            admin = BaseEntity.create(
                app=app,
                model_class=admin_model,  # Use the actual model class
                data={
                    'email': unreg_user.email,
                    'password_hash': pw_hash,
                    'full_name': unreg_user.full_name,
                    'institution_id': institution_id
                }
            )
            
            # 6. Update Unregistered User status
            unreg_user.status = 'approved'
            unreg_user.reviewed_by = reviewer_id
            unreg_user.reviewed_at = datetime.now()
            unreg_user.response_message = f'Approved by reviewer {reviewer_id}' if reviewer_id else 'Approved by platform manager'
            
            BaseEntity.commit_changes(app)
            
            return {
                'success': True, 
                'message': 'Approved and account created', 
                'admin_password': used_password, 
                'institution_id': institution_id
            }
            
        except Exception as e:
            BaseEntity.rollback_changes(app)
            app.logger.error(f"Error approving unregistered user: {e}")
            return {
                'success': False,
                'error': str(e)
            }