from application.entities.attendance_record import AttendanceRecord
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
            
            # Check if attendance already exists
            existing_record = AttendanceRecord.get_model().get_by_session_and_student(app, session_id, student_id)
            
            if existing_record:
                # Update existing record
                updated_record = AttendanceRecord.update_attendance(app, existing_record.attendance_id, attendance_data)
                attendance_id = updated_record.attendance_id if updated_record else None
                message = f'Attendance updated to {status}'
            else:
                # Create new record
                new_record = AttendanceRecord.mark_attendance(app, attendance_data)
                attendance_id = new_record.attendance_id if new_record else None
                message = f'Attendance marked as {status}'
            
            if attendance_id:
                return {
                    'success': True,
                    'attendance_id': attendance_id,
                    'message': message
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to mark attendance'
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
            # Get session details using Session model
            session_model = Session.get_model()
            session = session_model.query.get(session_id)
            
            if not session:
                return {'success': False, 'error': 'Session not found'}
            
            # Get attendance records using AttendanceRecord model
            attendance_records = AttendanceRecord.get_model().get_by_session(app, session_id)
            
            # Prepare attendance records data
            formatted_records = []
            for record in attendance_records:
                # Get student info
                student = record.student if hasattr(record, 'student') else None
                student_name = student.full_name if student else 'Unknown'
                student_code = student.student_code if student else 'Unknown'
                
                formatted_records.append({
                    'attendance_id': record.attendance_id,
                    'student_id': record.student_id,
                    'student_name': student_name,
                    'student_code': student_code,
                    'status': record.status,
                    'marked_by': record.marked_by,
                    'lecturer_id': record.lecturer_id,
                    'attendance_time': str(record.attendance_time) if record.attendance_time else None,
                    'notes': record.notes,
                    'recorded_at': record.recorded_at.isoformat() if record.recorded_at else None
                })
            
            # Get course details
            course_model = Course.get_model() if hasattr(Course, 'get_model') else None
            course = None
            if course_model and hasattr(session, 'course_id'):
                course = course_model.query.get(session.course_id)
            
            return {
                'success': True,
                'session': {
                    'session_id': session.session_id,
                    'course_id': session.course_id,
                    'course_code': course.course_code if course else '',
                    'course_name': course.course_name if course else '',
                    'session_date': session.session_date.isoformat() if session.session_date else None,
                    'session_topic': session.session_topic,
                    'status': session.status,
                    'venue_id': session.venue_id,
                    'slot_id': session.slot_id,
                    'lecturer_id': session.lecturer_id
                },
                'attendance_records': formatted_records
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
            
            # Get all sessions within date range where student is enrolled
            session_model = Session.get_model()
            student_model = Student.get_model()
            
            # Get the student
            student = student_model.query.get(student_id)
            if not student:
                return {
                    'success': False,
                    'error': 'Student not found'
                }
            
            # Get attendance records for the student within date range
            attendance_records = AttendanceRecord.get_by_student(app, student_id, start_date, end_date)
            
            # Calculate summary
            total_sessions = len(attendance_records)
            present_count = sum(1 for record in attendance_records if record.status == 'present')
            absent_count = sum(1 for record in attendance_records if record.status == 'absent')
            late_count = sum(1 for record in attendance_records if record.status == 'late')
            excused_count = sum(1 for record in attendance_records if record.status == 'excused')
            
            attendance_rate = (present_count / total_sessions * 100) if total_sessions > 0 else 0
            
            # Prepare detailed records
            detailed_records = []
            for record in attendance_records:
                # Get session info
                session = record.session if hasattr(record, 'session') else None
                session_date = session.session_date if session else None
                session_topic = session.session_topic if session else None
                
                # Get course info if available
                course_info = {}
                if session and hasattr(session, 'course'):
                    course = session.course
                    course_info = {
                        'course_code': course.course_code,
                        'course_name': course.course_name
                    }
                
                detailed_records.append({
                    'attendance_id': record.attendance_id,
                    'session_id': record.session_id,
                    'status': record.status,
                    'marked_by': record.marked_by,
                    'attendance_time': str(record.attendance_time) if record.attendance_time else None,
                    'session_date': session_date.isoformat() if session_date else None,
                    'session_topic': session_topic,
                    **course_info
                })
            
            return {
                'success': True,
                'student_info': {
                    'student_id': student.student_id,
                    'student_code': student.student_code,
                    'full_name': student.full_name,
                    'email': student.email
                },
                'summary': {
                    'total_sessions': total_sessions,
                    'present_count': present_count,
                    'absent_count': absent_count,
                    'late_count': late_count,
                    'excused_count': excused_count,
                    'attendance_rate': round(attendance_rate, 2)
                },
                'attendance_records': detailed_records
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_today_sessions_attendance(app, lecturer_id=None):
        """Get attendance for all sessions happening today"""
        try:
            # Get today's sessions
            today_sessions = Session.get_today_sessions(app, lecturer_id)
            
            result = []
            for session in today_sessions:
                # Get attendance for this session
                attendance_data = AttendanceControl.get_session_attendance(app, session.session_id)
                
                if attendance_data['success']:
                    result.append(attendance_data)
                else:
                    result.append({
                        'session_id': session.session_id,
                        'error': attendance_data.get('error', 'Failed to get attendance')
                    })
            
            return {
                'success': True,
                'sessions': result
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def get_all_sessions_attendance(app, lecturer_id=None, course_id=None, start_date=None, end_date=None):
        """Get attendance for all sessions in the system (or filtered by date/course/lecturer).

        By default this returns all sessions that have taken place up to today (end_date default).
        Each session's attendance payload is collected by calling get_session_attendance.
        """
        try:
            # Get all sessions (default end_date to today so we get historical sessions)
            all_sessions = Session.get_all_sessions(app, lecturer_id=lecturer_id, course_id=course_id, start_date=start_date, end_date=end_date)

            result = []
            for session_obj in all_sessions:
                # For each session, fetch the attendance payload via existing helper
                attendance_data = AttendanceControl.get_session_attendance(app, session_obj.session_id)

                if attendance_data.get('success'):
                    result.append(attendance_data)
                else:
                    result.append({'session_id': session_obj.session_id, 'error': attendance_data.get('error', 'Failed to get attendance')})

            return {
                'success': True,
                'sessions': result
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def update_attendance_status(app, attendance_id, status, notes=None):
        """Update attendance status"""
        try:
            update_data = {'status': status}
            if notes is not None:
                update_data['notes'] = notes
            
            updated_record = AttendanceRecord.update_attendance(app, attendance_id, update_data)
            
            if updated_record:
                return {
                    'success': True,
                    'message': f'Attendance updated to {status}',
                    'attendance': updated_record.to_dict()
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to update attendance'
                }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# Register dev actions for querying attendance (do this after functions are defined)
try:
    from application.boundaries.dev_actions import register_action

    register_action(
        'mark_attendance',
        AttendanceControl.mark_attendance,
        params=[
            {'name': 'session_id', 'label': 'Session ID', 'placeholder': 'e.g. 123'},
            {'name': 'student_id', 'label': 'Student ID', 'placeholder': 'e.g. 456'},
            {'name': 'status', 'label': 'Status', 'placeholder': 'present, absent, late, excused'},
            {'name': 'marked_by', 'label': 'Marked By', 'placeholder': 'system or lecturer'},
            {'name': 'lecturer_id', 'label': 'Lecturer ID', 'placeholder': 'Optional'},
            {'name': 'notes', 'label': 'Notes', 'placeholder': 'Optional notes'}
        ],
        description='Mark attendance for a student in a session'
    )

    register_action(
        'get_session_attendance',
        AttendanceControl.get_session_attendance,
        params=[{'name': 'session_id', 'label': 'Session ID', 'placeholder': 'e.g. 123'}],
        description='Get attendance records for a session'
    )

    register_action(
        'get_student_attendance_summary',
        AttendanceControl.get_student_attendance_summary,
        params=[
            {'name': 'student_id', 'label': 'Student ID', 'placeholder': 'e.g. 456'},
            {'name': 'days', 'label': 'Days', 'placeholder': 'Number of days to summarize (default 30)'}
        ],
        description='Get attendance summary for a student'
    )

    register_action(
        'get_today_sessions_attendance',
        AttendanceControl.get_today_sessions_attendance,
        params=[
            {'name': 'lecturer_id', 'label': 'Lecturer ID', 'placeholder': 'Optional'}
        ],
        description='Get attendance for all sessions happening today'
    )

    register_action(
        'update_attendance_status',
        AttendanceControl.update_attendance_status,
        params=[
            {'name': 'attendance_id', 'label': 'Attendance ID', 'placeholder': 'e.g. 789'},
            {'name': 'status', 'label': 'Status', 'placeholder': 'present, absent, late, excused'},
            {'name': 'notes', 'label': 'Notes', 'placeholder': 'Optional notes'}
        ],
        description='Update attendance status'
    )

except Exception:
    pass