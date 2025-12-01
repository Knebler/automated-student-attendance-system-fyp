from application.entities.institution import Institution
from application.entities.course import Course
from application.entities.lecturer import Lecturer
from application.entities.student import Student
from application.entities.subscription import Subscription
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
            cursor = app.config['mysql'].connection.cursor()
            
            # Count active students
            cursor.execute("SELECT COUNT(*) FROM Students WHERE institution_id = %s AND is_active = TRUE", 
                         (institution_id,))
            student_count = cursor.fetchone()[0]
            
            # Count active lecturers
            cursor.execute("SELECT COUNT(*) FROM Lecturers WHERE institution_id = %s AND is_active = TRUE", 
                         (institution_id,))
            lecturer_count = cursor.fetchone()[0]
            
            # Count active courses
            cursor.execute("SELECT COUNT(*) FROM Courses WHERE institution_id = %s AND is_active = TRUE", 
                         (institution_id,))
            course_count = cursor.fetchone()[0]
            
            # Get recent attendance rate
            cursor.execute("""
            SELECT 
                COUNT(DISTINCT s.session_id) as total_sessions,
                COUNT(CASE WHEN ar.status = 'present' THEN 1 END) as present_count
            FROM Sessions s
            JOIN Courses c ON s.course_id = c.course_id
            LEFT JOIN Attendance_Records ar ON s.session_id = ar.session_id
            WHERE c.institution_id = %s 
            AND s.session_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            """, (institution_id,))
            
            result = cursor.fetchone()
            total_sessions = result[0] if result[0] else 1
            attendance_rate = (result[1] / total_sessions * 100) if total_sessions > 0 else 0
            
            cursor.close()
            
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