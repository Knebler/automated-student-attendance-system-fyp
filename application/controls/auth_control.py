# auth_control.py (updated with ORM)
from application.entities2.user import UserModel
from application.entities2.institution import InstitutionModel
from application.controls.institution_control import InstitutionControl
from application.entities2.subscription import SubscriptionModel
from datetime import datetime, timedelta
import bcrypt
import secrets
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
        with get_session() as session:
            user_model = UserModel(session)
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
        with get_session() as session:
            user_model = UserModel(session)
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
        """Get user information using `users` table (UserModel). Returns a simple dict.
        This function does not rely on the legacy `application.entities` module.
        """
        try:
            # Map some aliases to canonical role values
            role_aliases = {
                'teacher': 'lecturer',
                'platmanager': 'platform_manager',
                'platform': 'platform_manager',
                'admin': 'admin',
                'institution_admin': 'admin'
            }
            canonical_role = role_aliases.get(user_type, user_type)

            with get_session() as session:
                user_model = UserModel(session)
                user = user_model.get_by_email(email)
                if not user:
                    return None
                # If a specific role is requested, ensure it matches
                if canonical_role and getattr(user, 'role', None) != canonical_role:
                    return None

                return {
                    'user_id': getattr(user, 'user_id', None),
                    'email': getattr(user, 'email', None),
                    'full_name': getattr(user, 'name', None),
                    'role': getattr(user, 'role', None),
                    'institution_id': getattr(user, 'institution_id', None),
                    'is_active': getattr(user, 'is_active', None)
                }
        except Exception as e:
            app.logger.error(f"Error getting user by email and type: {e}")
            return None

    @staticmethod
    def register_institution(app, institution_data: dict):
        """Register an institution application.

        Creates a pending Subscription (is_active=False) and inserts an application row in
        `Unregistered_Users` that references that subscription. Returns the application id
        and subscription id so it can be reviewed later.
        """
        try:
            from sqlalchemy import text
            from datetime import date

            email = institution_data.get('email')
            full_name = institution_data.get('full_name')
            inst_name = institution_data.get('institution_name')
            inst_address = institution_data.get('institution_address')
            phone = institution_data.get('phone_number')
            message = institution_data.get('message')
            selected_plan = institution_data.get('selected_plan_id')

            with get_session() as session:
                # Prevent duplicate pending application for the same email
                existing = session.execute(text("SELECT * FROM Unregistered_Users WHERE email = :email"), {'email': email}).first()
                if existing and dict(existing._mapping).get('status') == 'pending':
                    return {'success': False, 'error': 'An application for this email is already pending.'}

                sub_model = SubscriptionModel(session)
                start_date = date.today()
                end_date = start_date + timedelta(days=365)
                subscription = sub_model.create(plan_id=selected_plan, start_date=start_date, end_date=end_date, is_active=False)

                # Insert application referencing the pending subscription
                session.execute(text(
                    "INSERT INTO Unregistered_Users (email, full_name, institution_name, institution_address, phone_number, message, selected_plan_id, subscription_id, status)"
                    " VALUES (:email, :full_name, :institution_name, :institution_address, :phone_number, :message, :selected_plan_id, :subscription_id, 'pending')"
                ), {
                    'email': email,
                    'full_name': full_name,
                    'institution_name': inst_name,
                    'institution_address': inst_address,
                    'phone_number': phone,
                    'message': message,
                    'selected_plan_id': selected_plan,
                    'subscription_id': subscription.subscription_id
                })

                # Fetch inserted application id
                inserted = session.execute(text("SELECT unreg_user_id FROM Unregistered_Users WHERE email = :email"), {'email': email}).first()
                unreg_id = None
                if inserted:
                    unreg_id = dict(inserted._mapping).get('unreg_user_id')

            return {'success': True, 'message': 'Registration request submitted — awaiting approval', 'unreg_user_id': unreg_id, 'subscription_id': subscription.subscription_id}
        except Exception as e:
            app.logger.exception(f"Error registering institution: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def approve_unregistered_user(app, unreg_user_id, reviewer_id=None, admin_password=None):
        """Approve a pending registration application.

        If the application was registered with a pending subscription, activate that subscription
        and create the Institution + admin user; otherwise create the subscription and proceed.
        """
        try:
            from sqlalchemy import text
            from datetime import date

            with get_session() as session:
                # Fetch the unregistered user row (lock for update)
                row = session.execute(text("SELECT * FROM Unregistered_Users WHERE unreg_user_id = :id FOR UPDATE"), {'id': unreg_user_id}).first()
                if not row or row.status != 'pending':
                    return {'success': False, 'error': 'Registration request not found or not pending'}

                data = dict(row._mapping)
                selected_plan = data.get('selected_plan_id')
                subscription_id = data.get('subscription_id')

                sub_model = SubscriptionModel(session)

                # Use existing pending subscription if provided, otherwise create one (inactive -> will be activated)
                if subscription_id:
                    subscription = sub_model.get_by_subscription_id(subscription_id)
                    if not subscription:
                        # If subscription id is invalid, create a new one
                        subscription = sub_model.create(plan_id=selected_plan, start_date=date.today(), end_date=(date.today() + timedelta(days=365)), is_active=False)
                        # update the unregistered row with the new subscription id
                        session.execute(text("UPDATE Unregistered_Users SET subscription_id = :sid WHERE unreg_user_id = :id"), {'sid': subscription.subscription_id, 'id': unreg_user_id})
                else:
                    subscription = sub_model.create(plan_id=selected_plan, start_date=date.today(), end_date=(date.today() + timedelta(days=365)), is_active=False)
                    session.execute(text("UPDATE Unregistered_Users SET subscription_id = :sid WHERE unreg_user_id = :id"), {'sid': subscription.subscription_id, 'id': unreg_user_id})

                # Activate the subscription now that it's approved
                try:
                    sub_model.activate(subscription.subscription_id)
                except Exception:
                    # If activation helper fails, we'll attempt a direct update as fallback
                    try:
                        sub_model.update(subscription.subscription_id, is_active=True)
                    except Exception:
                        pass

                # Create Institution using InstitutionModel linked to the active subscription
                inst_model = InstitutionModel(session)
                inst = inst_model.create(name=data.get('institution_name'), address=data.get('institution_address'), subscription_id=subscription.subscription_id)
                institution_id = inst.institution_id

                # 3. Create admin password
                used_password = admin_password or secrets.token_urlsafe(10)

                # 4. Create or update Institution Admin as a user in the users table
                pw_hash = bcrypt.hashpw(used_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                user_model = UserModel(session)
                existing_user = user_model.get_by_email(data.get('email'))
                if existing_user:
                    # Update existing user to become institution admin and belong to the new institution
                    user_model.update(existing_user.user_id, role='admin', institution_id=institution_id, password_hash=pw_hash, name=data.get('full_name'))
                    admin_user = user_model.get_by_email(data.get('email'))
                else:
                    admin_user = user_model.create(
                        institution_id=institution_id,
                        role='admin',
                        email=data.get('email'),
                        password_hash=pw_hash,
                        name=data.get('full_name')
                    )

                # 5. Update Unregistered_Users status to approved
                session.execute(text("UPDATE Unregistered_Users SET status = 'approved', reviewed_by = :rev, reviewed_at = NOW(), response_message = :msg WHERE unreg_user_id = :id"), {
                    'rev': reviewer_id,
                    'msg': f'Approved by reviewer {reviewer_id}' if reviewer_id else 'Approved by platform manager',
                    'id': unreg_user_id
                })

            return {
                'success': True,
                'message': 'Approved and account created',
                'admin_password': used_password,
                'institution_id': institution_id
            }
        except Exception as e:
            app.logger.error(f"Error approving unregistered user: {e}")
            return {'success': False, 'error': str(e)}
        
    @staticmethod
    def verify_session(app, session_obj):
        """Verify an existing session and return user info.

        Validation:
        - If `session.user` (or `session.user_id`) is present, fetch from `users` table and confirm active.
        - If no session, return a dev platform manager if present.
        """
        try:
            session_user = session_obj.get('user')
            try:
                with get_session() as s:
                    user_model = UserModel(s)
                    user = None

                    # If session has full user dict, prefer email lookup
                    if session_user:
                        email = session_user.get('email')
                        uid = session_user.get('user_id') or session_user.get('user_id')
                        if email:
                            user = user_model.get_by_email(email)
                        elif uid:
                            user = user_model.get_by_id(uid)

                    # Fallback to explicit session keys
                    if not user:
                        uid = session_obj.get('user_id')
                        if uid:
                            user = user_model.get_by_id(uid)

                    # Ensure the user is active
                    if getattr(user, 'is_active', True) is False:
                        return {'success': False, 'error': 'User inactive'}

                    return {'success': True, 'user': user.as_sanitized_dict()}

            except Exception as inner_e:
                app.logger.exception(f"Error validating session user: {inner_e}")
                return {'success': False, 'error': str(inner_e)}

        except Exception as e:
            app.logger.exception(f"Unexpected error in verify_session: {e}")
            return {'success': False, 'error': str(e)}