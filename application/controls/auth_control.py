from application.entities.user import User
from application.entities.platform_manager import PlatformManager
from application.entities.student import Student
from application.entities.lecturer import Lecturer
from application.entities.institution import Institution
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
            
            firebase_auth = app.config['firebase_auth']
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

            if not uid or not id_token:
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
            firebase_auth = app.config['firebase_auth']
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
            cursor = app.config['mysql'].connection.cursor()
            
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
            # Insert into Unregistered_Users table first
            cursor = app.config['mysql'].connection.cursor()
            
            cursor.execute("""
            INSERT INTO Unregistered_Users 
            (email, full_name, institution_name, institution_address, 
             phone_number, message, selected_plan_id, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                institution_data.get('email'),
                institution_data.get('full_name'),
                institution_data.get('institution_name'),
                institution_data.get('institution_address'),
                institution_data.get('phone_number'),
                institution_data.get('message'),
                institution_data.get('selected_plan_id'),
                'pending'
            ))
            
            unreg_user_id = cursor.lastrowid
            
            app.config['mysql'].connection.commit()
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