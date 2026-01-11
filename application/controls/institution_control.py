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
    
    @staticmethod
    def get_user_counts(app, institution_id):
        """Get user counts by role for an institution"""
        try:
            # Count students
            student_count_row = BaseEntity.execute_query(
                app,
                "SELECT COUNT(*) FROM Students WHERE institution_id = :institution_id",
                {'institution_id': institution_id},
                fetch_one=True
            )
            student_count = student_count_row[0] if student_count_row and student_count_row[0] is not None else 0

            # Count lecturers
            lecturer_count_row = BaseEntity.execute_query(
                app,
                "SELECT COUNT(*) FROM Lecturers WHERE institution_id = :institution_id",
                {'institution_id': institution_id},
                fetch_one=True
            )
            lecturer_count = lecturer_count_row[0] if lecturer_count_row and lecturer_count_row[0] is not None else 0

            # Count admins
            admin_count_row = BaseEntity.execute_query(
                app,
                "SELECT COUNT(*) FROM Institution_Admins WHERE institution_id = :institution_id",
                {'institution_id': institution_id},
                fetch_one=True
            )
            admin_count = admin_count_row[0] if admin_count_row and admin_count_row[0] is not None else 0

            # Count active suspensions (inactive users)
            suspended_count_row = BaseEntity.execute_query(
                app,
                """SELECT 
                    (SELECT COUNT(*) FROM Students WHERE institution_id = :institution_id AND is_active = FALSE) +
                    (SELECT COUNT(*) FROM Lecturers WHERE institution_id = :institution_id AND is_active = FALSE)
                    as suspended_count""",
                {'institution_id': institution_id},
                fetch_one=True
            )
            suspended_count = suspended_count_row[0] if suspended_count_row and suspended_count_row[0] is not None else 0

            total_count = student_count + lecturer_count + admin_count

            return {
                'success': True,
                'counts': {
                    'total_users': total_count,
                    'students': student_count,
                    'lecturers': lecturer_count,
                    'admins': admin_count,
                    'suspended': suspended_count
                }
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def suspend_user(app, user_id, institution_id, role):
        try:
            if role == 'student':
                BaseEntity.execute_query(
                    app,
                    "UPDATE Students SET is_active = FALSE WHERE student_id = :user_id AND institution_id = :institution_id",
                    {'user_id': user_id, 'institution_id': institution_id}
                )
            elif role == 'lecturer':
                BaseEntity.execute_query(
                    app,
                    "UPDATE Lecturers SET is_active = FALSE WHERE lecturer_id = :user_id AND institution_id = :institution_id",
                    {'user_id': user_id, 'institution_id': institution_id}
                )
            else:
                return {
                    'success': False,
                    'error': 'Invalid role specified'
                }
            return {
                'success': True,
                'message': 'User suspended successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def unsuspend_user(app, user_id, institution_id, role):
        try:
            if role == 'student':
                BaseEntity.execute_query(
                    app,
                    "UPDATE Students SET is_active = TRUE WHERE student_id = :user_id AND institution_id = :institution_id",
                    {'user_id': user_id, 'institution_id': institution_id}
                )
            elif role == 'lecturer':
                BaseEntity.execute_query(
                    app,
                    "UPDATE Lecturers SET is_active = TRUE WHERE lecturer_id = :user_id AND institution_id = :institution_id",
                    {'user_id': user_id, 'institution_id': institution_id}
                )
            else:
                return {
                    'success': False,
                    'error': 'Invalid role specified'
                }
            return {
                'success': True,
                'message': 'User unsuspended successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def delete_user(app, user_id, institution_id, role):
        try:
            if role == 'student':
                BaseEntity.execute_query(
                    app,
                    "DELETE FROM Students WHERE student_id = :user_id AND institution_id = :institution_id",
                    {'user_id': user_id, 'institution_id': institution_id}
                )
            elif role == 'lecturer':
                BaseEntity.execute_query(
                    app,
                    "DELETE FROM Lecturers WHERE lecturer_id = :user_id AND institution_id = :institution_id",
                    {'user_id': user_id, 'institution_id': institution_id}
                )
            else:
                return {
                    'success': False,
                    'error': 'Invalid role specified'
                }
            return {
                'success': True,
                'message': 'User deleted successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
            
    @staticmethod
    def view_user(app, user_id, institution_id, role):
        try:
            if role == 'student':
                to_pull = [
                    "student_id", "institution_id", "student_code", "age",
                    "gender", "phone_number", "email", "full_name",
                    "enrollment_year", "is_active",
                ]
                user_row = BaseEntity.execute_query(
                    app,
                    f"SELECT {', '.join(to_pull)} FROM Students WHERE student_id = :user_id AND institution_id = :institution_id",
                    {'user_id': user_id, 'institution_id': institution_id},
                    fetch_one=True
                )
                user_details = {k: v for k, v in zip(to_pull, user_row)}
                user_details['id'] = user_details.pop('student_id')
                user_details['role'] = 'student'
                user_details['created_year'] = user_details.pop('enrollment_year')

                to_pull = [
                    'course_id', 'course_name', 'course_code', 'start_date', 'end_date'
                ]
                course_rows = BaseEntity.execute_query(
                    app,
                    f"SELECT {', '.join(to_pull)} FROM Course_Students JOIN Courses USING (course_id) WHERE student_id = :user_id",
                    {'user_id': user_id},
                    fetch_all=True
                )
                user_details['courses'] = [
                    {k: v for k, v in zip(to_pull, course_row)}
                    for course_row in course_rows
                ]
                course_rows = BaseEntity.execute_query(
                    app,
                    f"""
                    SELECT {', '.join(to_pull)}
                    FROM Courses c
                    WHERE c.institution_id = :institution_id
                    AND c.is_active = TRUE
                    AND NOT EXISTS (
                        SELECT 1
                        FROM Course_Students cl
                        WHERE cl.course_id = c.course_id
                            AND cl.student_id = :user_id
                    );
                    """,
                    {'institution_id': institution_id, 'user_id': user_id},
                    fetch_all=True
                )
                user_details['possible_courses'] = [
                    {k: v for k, v in zip(to_pull, course_row)}
                    for course_row in course_rows
                ]
            elif role == 'lecturer':
                to_pull = [
                    "lecturer_id", "institution_id", "age", "gender",
                    "phone_number", "email", "full_name", "department",
                    "is_active", "year_joined",
                ]
                user_row = BaseEntity.execute_query(
                    app,
                    f"SELECT {', '.join(to_pull)} FROM Lecturers WHERE lecturer_id = :user_id AND institution_id = :institution_id",
                    {'user_id': user_id, 'institution_id': institution_id},
                    fetch_one=True
                )
                user_details = {k: v for k, v in zip(to_pull, user_row)}
                user_details['id'] = user_details.pop('lecturer_id')
                user_details['role'] = 'lecturer'
                user_details['created_year'] = user_details.pop('year_joined')

                to_pull = [
                    'course_id', 'course_name', 'course_code', 'start_date', 'end_date'
                ]
                course_rows = BaseEntity.execute_query(
                    app,
                    f"SELECT {', '.join(to_pull)} FROM Course_Lecturers JOIN Courses USING (course_id) WHERE lecturer_id = :user_id",
                    {'user_id': user_id},
                    fetch_all=True
                )
                user_details['courses'] = [
                    {k: v for k, v in zip(to_pull, course_row)}
                    for course_row in course_rows
                ]
                course_rows = BaseEntity.execute_query(
                    app,
                    f"""
                    SELECT {', '.join(to_pull)}
                    FROM Courses c
                    WHERE c.institution_id = :institution_id
                    AND c.is_active = TRUE
                    AND NOT EXISTS (
                        SELECT 1
                        FROM Course_Lecturers cl
                        WHERE cl.course_id = c.course_id
                            AND cl.lecturer_id = :user_id
                    );
                    """,
                    {'institution_id': institution_id, 'user_id': user_id},
                    fetch_all=True
                )
                user_details['possible_courses'] = [
                    {k: v for k, v in zip(to_pull, course_row)}
                    for course_row in course_rows
                ]
            else:
                return {
                    'success': False,
                    'error': 'Invalid role specified'
                }
            if not user_row:
                return {
                    'success': False,
                    'error': 'User not found'
                }
            return {
                'success': True,
                'user_details': user_details,
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def remove_user_from_course(app, user_id, course_id, role):
        try:
            if role == 'student':
                BaseEntity.execute_query(
                    app,
                    "DELETE FROM Course_Students WHERE student_id = :user_id AND course_id = :course_id",
                    {'user_id': user_id, 'course_id': course_id}
                )
            elif role == 'lecturer':
                print(user_id, course_id)
                BaseEntity.execute_query(
                    app,
                    "DELETE FROM Course_Lecturers WHERE lecturer_id = :user_id AND course_id = :course_id",
                    {'user_id': user_id, 'course_id': course_id}
                )
            else:
                return {
                    'success': False,
                    'error': 'Invalid role specified'
                }
            return {
                'success': True,
                'message': 'User removed from course successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def add_user_to_course(app, user_id, course_id, role):
        try:
            if role == 'student':
                BaseEntity.execute_query(
                    app,
                    "INSERT INTO Course_Students (student_id, course_id) VALUES (:user_id, :course_id)",
                    {'user_id': user_id, 'course_id': course_id}
                )
            elif role == 'lecturer':
                BaseEntity.execute_query(
                    app,
                    "INSERT INTO Course_Lecturers (lecturer_id, course_id) VALUES (:user_id, :course_id)",
                    {'user_id': user_id, 'course_id': course_id}
                )
            else:
                return {
                    'success': False,
                    'error': 'Invalid role specified'
                }
            return {
                'success': True,
                'message': 'User added to course successfully'
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

    