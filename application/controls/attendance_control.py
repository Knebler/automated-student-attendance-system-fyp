from application.entities.attendance import Attendance
from application.entities.session import Session
from application.entities.student import Student
from application.entities.course import Course
from datetime import datetime, date, timedelta

class AttendanceControl:
    """Control class for attendance business logic"""
    
    @staticmethod
    def mark_attendance(app, session_id, student_id, status='present', 
                       marked_by='system', lecturer_id=None, 
                       captured_image_path=None, notes=None):
        """Mark attendance for a student in a session"""
        try:
            attendance_data = {
                'session_id': session_id,
                'student_id': student_id,
                'status': status,
                'marked_by': marked_by,
                'lecturer_id': lecturer_id,
                'captured_image_path': captured_image_path,
                'attendance_time': datetime.now().time(),
                'notes': notes
            }
            
            attendance_id = Attendance.mark_attendance(app, attendance_data)
            
            return {
                'success': True,
                'attendance_id': attendance_id,
                'message': f'Attendance marked as {status}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_session_attendance(app, session_id):
        """Get attendance records for a specific session"""
        try:
            # Get session details
            session_query = "SELECT * FROM Sessions WHERE session_id = %s"
            session_result = Attendance.execute_query(app, session_query, (session_id,), fetch_one=True)
            
            if not session_result:
                return {'success': False, 'error': 'Session not found'}
            
            # Get attendance records
            attendance_query = """
            SELECT ar.*, s.full_name, s.student_code
            FROM Attendance_Records ar
            JOIN Students s ON ar.student_id = s.student_id
            WHERE ar.session_id = %s
            """
            
            attendance_results = Attendance.execute_query(app, attendance_query, (session_id,), fetch_all=True)
            
            attendance_records = []
            for result in attendance_results:
                attendance_records.append({
                    'attendance_id': result[0],
                    'student_id': result[2],
                    'student_name': result[9],
                    'student_code': result[10],
                    'status': result[3],
                    'marked_by': result[4],
                    'attendance_time': str(result[7]) if result[7] else None,
                    'notes': result[8]
                })
            
            # Get course details
            course_id = session_result[1]
            course_query = "SELECT course_code, course_name FROM Courses WHERE course_id = %s"
            course_result = Attendance.execute_query(app, course_query, (course_id,), fetch_one=True)
            
            return {
                'success': True,
                'session': {
                    'session_id': session_result[0],
                    'course_code': course_result[0] if course_result else '',
                    'course_name': course_result[1] if course_result else '',
                    'session_date': session_result[5].isoformat() if session_result[5] else None,
                    'session_topic': session_result[6]
                },
                'attendance_records': attendance_records
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_student_attendance_summary(app, student_id, days=30):
        """Get attendance summary for a student"""
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            query = """
            SELECT 
                COUNT(*) as total_sessions,
                COUNT(CASE WHEN ar.status = 'present' THEN 1 END) as present_count,
                COUNT(CASE WHEN ar.status = 'absent' THEN 1 END) as absent_count,
                COUNT(CASE WHEN ar.status = 'late' THEN 1 END) as late_count,
                COUNT(CASE WHEN ar.status = 'excused' THEN 1 END) as excused_count
            FROM Sessions s
            LEFT JOIN Attendance_Records ar ON s.session_id = ar.session_id AND ar.student_id = %s
            WHERE s.session_date BETWEEN %s AND %s
            AND EXISTS (
                SELECT 1 FROM Enrollments e 
                WHERE e.student_id = %s AND e.course_id = s.course_id AND e.status = 'active'
            )
            """
            
            result = Attendance.execute_query(app, query, (student_id, start_date, end_date, student_id), fetch_one=True)
            
            if result and result[0] > 0:
                total_sessions = result[0]
                attendance_rate = (result[1] / total_sessions * 100) if total_sessions > 0 else 0
                
                return {
                    'success': True,
                    'summary': {
                        'total_sessions': total_sessions,
                        'present_count': result[1],
                        'absent_count': result[2],
                        'late_count': result[3],
                        'excused_count': result[4],
                        'attendance_rate': round(attendance_rate, 2)
                    }
                }
            else:
                return {
                    'success': True,
                    'summary': {
                        'total_sessions': 0,
                        'present_count': 0,
                        'absent_count': 0,
                        'late_count': 0,
                        'excused_count': 0,
                        'attendance_rate': 0
                    }
                }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }