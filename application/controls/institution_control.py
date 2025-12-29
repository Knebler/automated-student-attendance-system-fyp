from application.entities.institution import Institution
from application.entities.course import Course
from application.entities.lecturer import Lecturer
from application.entities.student import Student
from application.entities.subscription import Subscription
from application.entities.base_entity import BaseEntity
from datetime import datetime

class InstitutionControl:
    """Control class for institution management"""
    
    @staticmethod
    def create_institution(app, institution_data, subscription_id):
        """Create a new institution with subscription"""
        try:
            # Create institution
            institution_id = Institution.create(app, {
                'name': institution_data.get('name'),
                'address': institution_data.get('address'),
                'website': institution_data.get('website'),
                'subscription_id': subscription_id,
                'is_active': True
            })
            
            return {
                'success': True,
                'institution_id': institution_id,
                'message': 'Institution created successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def get_institution_stats(app, institution_id):
        """Get statistics for an institution"""
        try:
            # Count active students
            student_row = BaseEntity.execute_query(
                app,
                "SELECT COUNT(*) FROM Students WHERE institution_id = :institution_id AND is_active = TRUE",
                {'institution_id': institution_id},
                fetch_one=True
            )
            student_count = student_row[0] if student_row and student_row[0] is not None else 0

            # Count active lecturers
            lecturer_row = BaseEntity.execute_query(
                app,
                "SELECT COUNT(*) FROM Lecturers WHERE institution_id = :institution_id AND is_active = TRUE",
                {'institution_id': institution_id},
                fetch_one=True
            )
            lecturer_count = lecturer_row[0] if lecturer_row and lecturer_row[0] is not None else 0

            # Count active courses
            course_row = BaseEntity.execute_query(
                app,
                "SELECT COUNT(*) FROM Courses WHERE institution_id = :institution_id AND is_active = TRUE",
                {'institution_id': institution_id},
                fetch_one=True
            )
            course_count = course_row[0] if course_row and course_row[0] is not None else 0

            # Get recent attendance rate
            result = BaseEntity.execute_query(
                app,
                '''
                SELECT 
                    COUNT(DISTINCT s.session_id) as total_sessions,
                    COUNT(CASE WHEN ar.status = 'present' THEN 1 END) as present_count
                FROM Sessions s
                JOIN Courses c ON s.course_id = c.course_id
                LEFT JOIN Attendance_Records ar ON s.session_id = ar.session_id
                WHERE c.institution_id = %s 
                AND s.session_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                ''',
                (institution_id,),
                fetch_one=True
            )

            total_sessions = result[0] if result and result[0] else 1
            attendance_rate = (result[1] / total_sessions * 100) if total_sessions > 0 and result and result[1] else 0

            return {
                'success': True,
                'stats': {
                    'student_count': student_count,
                    'lecturer_count': lecturer_count,
                    'course_count': course_count,
                    'attendance_rate': round(attendance_rate, 2),
                    'last_updated': datetime.now().isoformat()
                }
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_institution_user_details(app, institution_id):
        """Retrieve institution details by ID"""
        try:
            student_data = BaseEntity.execute_query(
                app,
                "SELECT full_name, student_id, is_active FROM students WHERE institution_id = :institution_id",
                {'institution_id': institution_id},
                fetch_all=True
            )
            print("Student data:", student_data)
            lecturer_data = BaseEntity.execute_query(
                app,
                "SELECT full_name, lecturer_id, is_active FROM lecturers WHERE institution_id = :institution_id",
                {'institution_id': institution_id},
                fetch_all=True
            )
            admin_data = BaseEntity.execute_query(
                app,
                "SELECT full_name, inst_admin_id FROM institution_admins WHERE institution_id = :institution_id",
                {'institution_id': institution_id},
                fetch_all=True
            )
            return {
                'success': True,
                'users': [
                    *[{
                        'name': row[0],
                        'id': row[1],
                        'is_active': row[2],
                        'role': 'student',
                    } for row in student_data],
                    *[{
                        'name': row[0],
                        'id': row[1],
                        'is_active': row[2],
                        'role': 'lecturer',
                    } for row in lecturer_data],
                    *[{
                        'name': row[0],
                        'id': row[1],
                        'is_active': True,  # Admins are always active
                        'role': 'admin',
                    } for row in admin_data]
                ]
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# Expose useful dev actions for institution management
try:
    from application.boundaries.dev_actions import register_action

    register_action(
        'create_institution',
        InstitutionControl.create_institution,
        params=[
            {'name': 'institution_data', 'label': 'Institution JSON', 'placeholder': '{"name":"My Inst","address":"..."}'},
            {'name': 'subscription_id', 'label': 'Subscription ID', 'placeholder': 'Plan id or subscription id'}
        ],
        description='Create a new institution with subscription (dev only)'
    )

    register_action(
        'get_institution_stats',
        InstitutionControl.get_institution_stats,
        params=[{'name': 'institution_id', 'label': 'Institution ID', 'placeholder': 'e.g. 1'}],
        description='Get basic stats for an institution (dev only)'
    )
except Exception:
    pass