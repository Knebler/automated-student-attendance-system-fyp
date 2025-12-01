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
            
            return {
                'success': False,
                'error': error_message,
                'error_type': 'INVALID_CREDENTIALS' if any(
                    err in error_message for err in ['INVALID_PASSWORD', 'EMAIL_NOT_FOUND']
                ) else 'UNKNOWN'
            }
    
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