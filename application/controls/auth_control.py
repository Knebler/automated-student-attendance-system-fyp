from application.entities.user import User
from application.entities.base_entity import BaseEntity
from application.entities.platform_manager import PlatformManager
from application.entities.student import Student
from application.entities.lecturer import Lecturer
from application.entities.institution import Institution
from application.controls.institution_control import InstitutionControl
from datetime import datetime
import traceback

class AuthControl:
    """Control class for authentication business logic with multi-role support"""
    
    @staticmethod
    def authenticate_user(app, email, password, user_type='student'):
        """Authenticate user based on their role/type"""
        try:
            # This is a simplified version - in production, use proper password hashing
            # For now, we'll use Firebase for authentication
            
            # If Firebase isn't configured (disabled), return a friendly error
            firebase_auth = app.config.get('firebase_auth')
            if not firebase_auth:
                return {
                    'success': False,
                    'error': 'Authentication disabled - Firebase not configured',
                    'error_type': 'FIREBASE_DISABLED'
                }

            user_firebase = firebase_auth.sign_in_with_email_and_password(email, password)
            
            # Determine which table to check based on user_type
            user_info = AuthControl.get_user_by_email_and_type(app, email, user_type)
            
            if not user_info:
                return {
                    'success': False,
                    'error': f'{user_type.capitalize()} not found in system'
                }
            
            return {
                'success': True,
                'user': user_info,
                'user_type': user_type,
                'firebase_uid': user_firebase['localId'],
                'id_token': user_firebase['idToken'],
                'refresh_token': user_firebase['refreshToken']
            }
            
        except Exception as e:
            error_message = str(e)
            print(f"Authentication error: {error_message}")
            # Map common Firebase auth error codes/messages to friendly types
            err_type = 'UNKNOWN'
            friendly = error_message
            lower = error_message.lower()
            if 'invalid_password' in lower or 'invalid password' in lower:
                err_type = 'INVALID_CREDENTIALS'
                friendly = 'Incorrect password. Please try again.'
            elif 'email_not_found' in lower or 'email not found' in lower:
                err_type = 'INVALID_CREDENTIALS'
                friendly = 'No account found for this email.'

            return {
                'success': False,
                'error': friendly,
                'error_type': err_type
            }

    @staticmethod
    def verify_session(app, session_obj):
        """Verify an existing session and return user info.

        This is a lightweight helper: it checks for an id_token / user_id in session
        and attempts to load user details (User table) when present. Returns
        a dict { success: bool, user: dict }.
        """
        try:

            id_token = session_obj.get('id_token')
            uid = session_obj.get('user_id')

            # If no session present but Firebase is disabled, treat app as 'dev' mode
            if not uid or not id_token:
                if not app.config.get('firebase_auth'):
                    # Try to load a platform manager from the DB for dev sessions
                    try:
                        cursor = None
                        try:
                            cursor = BaseEntity.get_db_connection(app)
                            cursor.execute("SELECT platform_mgr_id, email, full_name, created_at FROM Platform_Managers LIMIT 1")
                            row = cursor.fetchone()
                            try:
                                cursor.close()
                            except Exception:
                                pass
                        except Exception:
                            # fallback to raw mysql connector
                            mysql = app.config.get('mysql')
                            row = None
                            if mysql:
                                cur = mysql.connection.cursor()
                                cur.execute("SELECT platform_mgr_id, email, full_name, created_at FROM Platform_Managers LIMIT 1")
                                row = cur.fetchone()
                                cur.close()

                        if row:
                            # map row -> user dict
                            return {
                                'success': True,
                                'user': {
                                    'user_type': 'platform_manager',
                                    'user_id': int(row[0]) if row[0] is not None else None,
                                    'email': row[1],
                                    'full_name': row[2]
                                }
                            }

                        # No platform manager present - return a generic dev user granting platform_manager access
                        return {
                            'success': True,
                            'user': {
                                'user_type': 'platform_manager',
                                'user_id': 0,
                                'email': 'dev@local'
                            }
                        }
                    except Exception:
                        # if anything goes wrong, be permissive in dev mode
                        return {'success': True, 'user': {'user_type': 'platform_manager', 'user_id': 0}}
                else:
                    return {'success': False, 'error': 'No session present'}

            # Prefer local user entry (users table) when present
            user = None
            try:
                user_obj = User.get_by_firebase_uid(app, uid)
                if user_obj:
                    user = user_obj if isinstance(user_obj, dict) else (user_obj.to_dict() if hasattr(user_obj, 'to_dict') else None)
            except Exception:
                user = None

            # fall back to session-stored user info
            if not user:
                user = session_obj.get('user')

            return {'success': True, 'user': user}

        except Exception as e:
            # Any error -> mark as not authenticated
            return {'success': False, 'error': str(e)}

    @staticmethod
    def register_user(app, email, password, name=None, role='student'):
        """Register a new user in Firebase and create a local User record.

        Returns {'success': True, 'firebase_uid': ..., 'id_token': ...} on success.
        """
        try:
            firebase_auth = app.config.get('firebase_auth')
            if not firebase_auth:
                return {
                    'success': False,
                    'error': 'Registration disabled - Firebase not configured',
                    'error_type': 'FIREBASE_DISABLED'
                }

            new_user = firebase_auth.create_user_with_email_and_password(email, password)
            uid = new_user.get('localId')
            id_token = new_user.get('idToken')

            # Persist minimal user in local Users table
            try:
                User.create(app, {
                    'firebase_uid': uid,
                    'email': email,
                    'name': name,
                    'role': role
                })
            except Exception:
                # best-effort - ignore if local create fails
                pass

            return {'success': True, 'firebase_uid': uid, 'id_token': id_token}
        except Exception as e:
            # Try to parse firebase error codes from the exception message
            msg = str(e)
            error_type = 'UNKNOWN'
            if 'EMAIL_EXISTS' in msg or 'email exists' in msg.lower():
                error_type = 'EMAIL_EXISTS'
                friendly = 'Email already registered'
            elif 'INVALID_EMAIL' in msg or 'invalid email' in msg.lower():
                error_type = 'INVALID_EMAIL'
                friendly = 'Provided email is invalid'
            elif 'WEAK_PASSWORD' in msg or 'password' in msg.lower():
                error_type = 'WEAK_PASSWORD'
                friendly = 'Password does not meet strength requirements'
            else:
                friendly = msg

            return {'success': False, 'error': friendly, 'error_type': error_type}
    
    @staticmethod
    def get_user_by_email_and_type(app, email, user_type):
        """Get user information based on type"""
        try:
            # Try BaseEntity cursor (SQLAlchemy) first, fallback to mysql connector
            cursor = None
            try:
                cursor = BaseEntity.get_db_connection(app)
                if user_type == 'student':
                    query = "SELECT * FROM Students WHERE email = %s"
                elif user_type == 'lecturer':
                    query = "SELECT * FROM Lecturers WHERE email = %s"
                elif user_type == 'platform_manager':
                    query = "SELECT * FROM Platform_Managers WHERE email = %s"
                elif user_type == 'institution_admin':
                    query = "SELECT * FROM Institution_Admins WHERE email = %s"
                else:
                    return None

                cursor.execute(query, (email,))
                result = cursor.fetchone()
                try:
                    cursor.close()
                except Exception:
                    pass
            except Exception:
                # fallback to raw mysql cursor
                mysql = app.config.get('mysql')
                if not mysql:
                    return None
                cursor = mysql.connection.cursor()
                if user_type == 'student':
                    query = "SELECT * FROM Students WHERE email = %s"
                elif user_type == 'lecturer':
                    query = "SELECT * FROM Lecturers WHERE email = %s"
                elif user_type == 'platform_manager':
                    query = "SELECT * FROM Platform_Managers WHERE email = %s"
                elif user_type == 'institution_admin':
                    query = "SELECT * FROM Institution_Admins WHERE email = %s"
                else:
                    return None

                cursor.execute(query, (email,))
                result = cursor.fetchone()
                cursor.close()
            
            if result:
                if user_type == 'student':
                    return {
                        'user_id': result[0],
                        'institution_id': result[1],
                        'student_code': result[2],
                        'email': result[3],
                        'full_name': result[5],
                        'enrollment_year': result[6],
                        'is_active': bool(result[7]),
                        'user_type': 'student'
                    }
                elif user_type == 'lecturer':
                    return {
                        'user_id': result[0],
                        'institution_id': result[1],
                        'email': result[2],
                        'full_name': result[4],
                        'department': result[5],
                        'is_active': bool(result[6]),
                        'user_type': 'lecturer'
                    }
                elif user_type == 'platform_manager':
                    return {
                        'user_id': result[0],
                        'email': result[1],
                        'full_name': result[3],
                        'created_at': result[4],
                        'user_type': 'platform_manager'
                    }
            
            return None
            
        except Exception as e:
            print(f"Error getting user by email and type: {e}")
            return None
    
    @staticmethod
    def register_institution(app, institution_data):
        """Register a new institution (for platform managers)"""
        try:
            # Insert into Unregistered_Users table first (use cursor fallback)
            cursor = None
            mysql = app.config.get('mysql')
            try:
                cursor = BaseEntity.get_db_connection(app)
            except Exception:
                cursor = None

            params = (
                institution_data.get('email'),
                institution_data.get('full_name'),
                institution_data.get('institution_name'),
                institution_data.get('institution_address'),
                institution_data.get('phone_number'),
                institution_data.get('message'),
                institution_data.get('selected_plan_id'),
                'pending'
            )

            query = """
            INSERT INTO Unregistered_Users 
            (email, full_name, institution_name, institution_address, 
             phone_number, message, selected_plan_id, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

            if cursor is not None:
                cursor.execute(query, params)
                unreg_user_id = getattr(cursor, 'lastrowid', None)
                try:
                    cursor.close()
                except Exception:
                    pass
                # commit using SQLAlchemy helper when available
                if mysql is None:
                    BaseEntity.commit_changes(app)
                else:
                    mysql.connection.commit()
            else:
                # as a last resort try raw mysql
                if not mysql:
                    raise RuntimeError('No database configured')
                cursor = mysql.connection.cursor()
                cursor.execute(query, params)
                unreg_user_id = cursor.lastrowid
                mysql.connection.commit()
                cursor.close()
            
            return {
                'success': True,
                'unreg_user_id': unreg_user_id,
                'message': 'Institution registration request submitted successfully. Awaiting approval.'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def approve_unregistered_user(app, unreg_user_id, reviewer_id=None, admin_password=None):
        """Approve a pending Unregistered_Users entry, create subscription, institution and institution admin.

        Returns { success: bool, message: str, admin_password: str?, institution_id: int? }
        """
        try:
            # Load the pending unregistered user
            cursor = BaseEntity.get_db_connection(app)
            cursor.execute("SELECT unreg_user_id, email, full_name, institution_name, institution_address, phone_number, selected_plan_id, status FROM Unregistered_Users WHERE unreg_user_id = %s", (unreg_user_id,))
            row = cursor.fetchone()
            if not row:
                return {'success': False, 'error': 'Registration request not found'}

            status = row[7]
            if status != 'pending':
                return {'success': False, 'error': f'Request is not pending (status={status})'}

            email = row[1]
            full_name = row[2]
            institution_name = row[3]
            institution_address = row[4]
            selected_plan = row[6]

            # 1) Create a Subscription record for this unregistered user
            from datetime import date, timedelta
            start_date = date.today()
            end_date = start_date + timedelta(days=365)

            sub_query = "INSERT INTO Subscriptions (unreg_user_id, plan_id, start_date, end_date, status) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(sub_query, (unreg_user_id, selected_plan, start_date, end_date, 'active'))
            subscription_id = getattr(cursor, 'lastrowid', None)
            # commit is handled below

            # 2) Create Institution with the subscription_id
            inst_data = {
                'name': institution_name,
                'address': institution_address,
                'website': None
            }
            # Use InstitutionControl which handles creation via entities
            ins_result = InstitutionControl.create_institution(app, inst_data, subscription_id)
            if not ins_result.get('success'):
                BaseEntity.rollback_changes(app)
                return {'success': False, 'error': 'Failed to create institution: ' + (ins_result.get('error') or '')}

            institution_id = ins_result.get('institution_id')

            # 3) Create Firebase user (if available) or proceed to create local admin
            firebase_auth = app.config.get('firebase_auth')
            created_firebase_uid = None
            used_password = admin_password
            if not used_password:
                # auto-generate a temporary password
                import secrets
                used_password = secrets.token_urlsafe(10)

            if firebase_auth:
                try:
                    # reuse register_user flow which creates firebase user and local Users table entry
                    reg_res = AuthControl.register_user(app, email, used_password, name=full_name, role='institution_admin')
                    if not reg_res.get('success'):
                        # attempt continued local creation but report firebase issue
                        created_firebase_uid = None
                    else:
                        created_firebase_uid = reg_res.get('firebase_uid')
                except Exception:
                    created_firebase_uid = None

            # 4) Insert into Institution_Admins local table
            import bcrypt
            pw_hash = bcrypt.hashpw(used_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            admin_query = "INSERT INTO Institution_Admins (email, password_hash, full_name, institution_id) VALUES (%s, %s, %s, %s)"
            cursor.execute(admin_query, (email, pw_hash, full_name, institution_id))

            # 5) Update Unregistered_Users status to approved
            update_q = "UPDATE Unregistered_Users SET status='approved', reviewed_by=%s, reviewed_at=NOW(), response_message=%s WHERE unreg_user_id = %s"
            resp_msg = f'Approved by reviewer {reviewer_id}' if reviewer_id else 'Approved by platform manager'
            cursor.execute(update_q, (reviewer_id, resp_msg, unreg_user_id))

            # Final commit
            try:
                BaseEntity.commit_changes(app)
            except Exception:
                try:
                    # In case underlying DB is mysql connector
                    mysql = app.config.get('mysql')
                    if mysql:
                        mysql.connection.commit()
                except Exception:
                    pass

            return {'success': True, 'message': 'Approved and account created', 'admin_password': used_password, 'institution_id': institution_id}

        except Exception as e:
            try:
                BaseEntity.rollback_changes(app)
            except Exception:
                pass
            return {'success': False, 'error': str(e)}


# Expose some auth helpers as dev actions when available
try:
    from application.boundaries.dev_actions import register_action

    register_action(
        'get_user_by_email_and_type',
        AuthControl.get_user_by_email_and_type,
        params=[
            {'name': 'email', 'label': 'Email', 'placeholder': 'email@example.com'},
            {'name': 'user_type', 'label': 'User type', 'placeholder': 'student | lecturer | platform_manager'}
        ],
        description='Lookup a user by email and type (dev only)'
    )

    register_action(
        'register_institution',
        AuthControl.register_institution,
        params=[{'name': 'institution_data', 'label': 'Institution JSON', 'placeholder': '{"email":"x","institution_name":"..."}'}],
        description='Submit an institution registration request (dev only)'
    )
except Exception:
    # dev_actions not available in non-dev environments
    pass