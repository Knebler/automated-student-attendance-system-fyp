# attendance_control.py (updated to use ORM only)
from datetime import datetime, date, timedelta
from database.base import get_session
from application.entities2.classes import ClassModel
from application.entities2.attendance_record import AttendanceRecordModel
from application.entities2.course import CourseModel
from application.entities2.user import UserModel

class AttendanceControl:
    """Control class for attendance business logic using ORM"""
    
    @staticmethod
    def mark_attendance(app, class_id, student_id, status='present', 
                       marked_by='system', lecturer_id=None, notes=None):
        """Mark attendance for a student in a class"""
        try:
            with get_session() as db_session:
                attendance_model = AttendanceRecordModel(db_session)
                
                # Check if attendance already exists
                existing_record = attendance_model.get_one(
                    class_id=class_id, 
                    student_id=student_id
                )
                
                attendance_data = {
                    'class_id': class_id,
                    'student_id': student_id,
                    'status': status,
                    'marked_by': marked_by,
                    'lecturer_id': lecturer_id,
                    'notes': notes
                }
                
                if existing_record:
                    # Update existing record
                    attendance_model.update(existing_record.attendance_id, **attendance_data)
                    attendance_id = existing_record.attendance_id
                    message = f'Attendance updated to {status}'
                else:
                    # Create new record
                    new_record = attendance_model.create(**attendance_data)
                    attendance_id = new_record.attendance_id
                    message = f'Attendance marked as {status}'
                
                return {
                    'success': True,
                    'attendance_id': attendance_id,
                    'message': message
                }
                
        except Exception as e:
            app.logger.error(f"Error marking attendance: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_class_attendance(app, class_id):
        """Get attendance records for a specific class"""
        try:
            with get_session() as db_session:
                class_model = ClassModel(db_session)
                attendance_model = AttendanceRecordModel(db_session)
                user_model = UserModel(db_session)
                
                # Get class details
                class_obj = class_model.get_by_id(class_id)
                if not class_obj:
                    return {'success': False, 'error': 'Class not found'}
                
                # Get course details
                course_model = CourseModel(db_session)
                course = course_model.get_by_id(class_obj.course_id) if class_obj.course_id else None
                
                # Get attendance records
                attendance_records = attendance_model.get_all(class_id=class_id)
                
                # Prepare attendance records data
                formatted_records = []
                for record in attendance_records:
                    # Get student info
                    student = user_model.get_by_id(record.student_id) if record.student_id else None
                    
                    formatted_records.append({
                        'attendance_id': record.attendance_id,
                        'student_id': record.student_id,
                        'student_name': student.name if student else 'Unknown',
                        'status': record.status,
                        'marked_by': record.marked_by,
                        'lecturer_id': record.lecturer_id,
                        'notes': record.notes,
                        'recorded_at': record.recorded_at.isoformat() if record.recorded_at else None
                    })
                
                # Get lecturer info
                lecturer = user_model.get_by_id(class_obj.lecturer_id) if class_obj.lecturer_id else None
                
                return {
                    'success': True,
                    'class': {
                        'class_id': class_obj.class_id,
                        'course_id': class_obj.course_id,
                        'course_code': course.code if course else '',
                        'course_name': course.name if course else '',
                        'start_time': class_obj.start_time.isoformat() if class_obj.start_time else None,
                        'end_time': class_obj.end_time.isoformat() if class_obj.end_time else None,
                        'lecturer_id': class_obj.lecturer_id,
                        'lecturer_name': lecturer.name if lecturer else '',
                        'venue_id': class_obj.venue_id
                    },
                    'attendance_records': formatted_records
                }
                
        except Exception as e:
            app.logger.error(f"Error getting class attendance: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_student_attendance_summary(app, student_id, days=30):
        """Get attendance summary for a student"""
        try:
            with get_session() as db_session:
                attendance_model = AttendanceRecordModel(db_session)
                user_model = UserModel(db_session)
                class_model = ClassModel(db_session)
                course_model = CourseModel(db_session)
                
                # Get the student
                student = user_model.get_by_id(student_id)
                if not student:
                    return {'success': False, 'error': 'Student not found'}
                
                # Calculate date range
                end_date = date.today()
                start_date = end_date - timedelta(days=days)
                
                # Get attendance records for the student within date range
                # Note: This requires a more complex query to filter by date
                # For now, get all records and filter in Python
                all_records = attendance_model.get_all(student_id=student_id)
                
                # Filter by date (assuming Class has start_time)
                attendance_records = []
                for record in all_records:
                    class_obj = class_model.get_by_id(record.class_id)
                    if class_obj and class_obj.start_time:
                        class_date = class_obj.start_time.date()
                        if start_date <= class_date <= end_date:
                            attendance_records.append(record)
                
                # Calculate summary
                total_classes = len(attendance_records)
                present_count = sum(1 for record in attendance_records if record.status == 'present')
                absent_count = sum(1 for record in attendance_records if record.status == 'absent')
                late_count = sum(1 for record in attendance_records if record.status == 'late')
                excused_count = sum(1 for record in attendance_records if record.status == 'excused')
                
                attendance_rate = (present_count / total_classes * 100) if total_classes > 0 else 0
                
                # Prepare detailed records
                detailed_records = []
                for record in attendance_records:
                    class_obj = class_model.get_by_id(record.class_id)
                    if class_obj:
                        course = course_model.get_by_id(class_obj.course_id) if class_obj.course_id else None
                        lecturer = user_model.get_by_id(class_obj.lecturer_id) if class_obj.lecturer_id else None
                        
                        detailed_records.append({
                            'attendance_id': record.attendance_id,
                            'class_id': record.class_id,
                            'status': record.status,
                            'marked_by': record.marked_by,
                            'notes': record.notes,
                            'class_date': class_obj.start_time.date().isoformat() if class_obj.start_time else None,
                            'class_start': class_obj.start_time.isoformat() if class_obj.start_time else None,
                            'class_end': class_obj.end_time.isoformat() if class_obj.end_time else None,
                            'course_code': course.code if course else '',
                            'course_name': course.name if course else '',
                            'lecturer_name': lecturer.name if lecturer else ''
                        })
                
                return {
                    'success': True,
                    'student_info': {
                        'student_id': student.user_id,
                        'student_name': student.name,
                        'email': student.email
                    },
                    'summary': {
                        'total_classes': total_classes,
                        'present_count': present_count,
                        'absent_count': absent_count,
                        'late_count': late_count,
                        'excused_count': excused_count,
                        'attendance_rate': round(attendance_rate, 2)
                    },
                    'attendance_records': detailed_records,
                    'date_range': {
                        'start_date': start_date.isoformat(),
                        'end_date': end_date.isoformat(),
                        'days': days
                    }
                }
                
        except Exception as e:
            app.logger.error(f"Error getting student attendance summary: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_today_classes_attendance(app, lecturer_id=None):
        """Get attendance for all classes happening today"""
        try:
            with get_session() as db_session:
                class_model = ClassModel(db_session)
                
                # Get today's classes for the institution
                # This needs to be implemented in ClassModel
                # For now, return a placeholder
                today = date.today()
                
                return {
                    'success': True,
                    'message': 'Today\'s classes attendance feature coming soon',
                    'date': today.isoformat(),
                    'lecturer_id': lecturer_id
                }
                
        except Exception as e:
            app.logger.error(f"Error getting today's classes attendance: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def update_attendance_status(app, attendance_id, status, notes=None):
        """Update attendance status"""
        try:
            with get_session() as db_session:
                attendance_model = AttendanceRecordModel(db_session)
                
                update_data = {'status': status}
                if notes is not None:
                    update_data['notes'] = notes
                
                updated_record = attendance_model.update(attendance_id, **update_data)
                
                if updated_record:
                    return {
                        'success': True,
                        'message': f'Attendance updated to {status}',
                        'attendance': {
                            'attendance_id': updated_record.attendance_id,
                            'status': updated_record.status,
                            'notes': updated_record.notes
                        }
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Attendance record not found'
                    }
                
        except Exception as e:
            app.logger.error(f"Error updating attendance status: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_student_attendance_record(app, student_id, course_id=None, start_date=None, end_date=None):
        """Get detailed attendance records for a student with filters"""
        try:
            with get_session() as db_session:
                attendance_model = AttendanceRecordModel(db_session)
                user_model = UserModel(db_session)
                class_model = ClassModel(db_session)
                course_model = CourseModel(db_session)
                
                # Get the student
                student = user_model.get_by_id(student_id)
                if not student:
                    return {'success': False, 'error': 'Student not found'}
                
                # Get all attendance records for the student
                all_records = attendance_model.get_all(student_id=student_id)
                
                # Apply filters
                filtered_records = []
                for record in all_records:
                    class_obj = class_model.get_by_id(record.class_id)
                    if not class_obj:
                        continue
                    
                    # Filter by course
                    if course_id and class_obj.course_id != course_id:
                        continue
                    
                    # Filter by date
                    if class_obj.start_time:
                        class_date = class_obj.start_time.date()
                        if start_date and class_date < start_date:
                            continue
                        if end_date and class_date > end_date:
                            continue
                    
                    filtered_records.append(record)
                
                # Prepare detailed records
                detailed_records = []
                for record in filtered_records:
                    class_obj = class_model.get_by_id(record.class_id)
                    if class_obj:
                        course = course_model.get_by_id(class_obj.course_id) if class_obj.course_id else None
                        lecturer = user_model.get_by_id(class_obj.lecturer_id) if class_obj.lecturer_id else None
                        
                        detailed_records.append({
                            'attendance_id': record.attendance_id,
                            'class_id': record.class_id,
                            'status': record.status,
                            'marked_by': record.marked_by,
                            'notes': record.notes,
                            'recorded_at': record.recorded_at.isoformat() if record.recorded_at else None,
                            'class_date': class_obj.start_time.date().isoformat() if class_obj.start_time else None,
                            'class_start': class_obj.start_time.isoformat() if class_obj.start_time else None,
                            'class_end': class_obj.end_time.isoformat() if class_obj.end_time else None,
                            'course_id': class_obj.course_id,
                            'course_code': course.code if course else '',
                            'course_name': course.name if course else '',
                            'lecturer_name': lecturer.name if lecturer else ''
                        })
                
                return {
                    'success': True,
                    'student_info': {
                        'student_id': student.user_id,
                        'student_name': student.name,
                        'email': student.email
                    },
                    'attendance_records': detailed_records,
                    'filters_applied': {
                        'course_id': course_id,
                        'start_date': start_date.isoformat() if start_date else None,
                        'end_date': end_date.isoformat() if end_date else None
                    },
                    'count': len(detailed_records)
                }
                
        except Exception as e:
            app.logger.error(f"Error getting student attendance record: {e}")
            return {
                'success': False,
                'error': str(e)
            }