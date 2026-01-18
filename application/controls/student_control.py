from application.entities2.classes import ClassModel
from application.entities2.semester import SemesterModel
from application.entities2.attendance_record import AttendanceRecordModel
from application.entities2.attendance_appeal import AttendanceAppealModel
from application.entities2.user import UserModel
from application.entities2.course import CourseModel
from datetime import datetime, date, timedelta
from database.base import get_session
from database.models import AttendanceAppealStatusEnum, AttendanceRecord
from sqlalchemy import or_, func
import math

class StudentControl:
    """Control class for student business logic"""
    
    @staticmethod
    def get_student_dashboard(user_id):
        """Get student dashboard data"""
        try:
            with get_session() as db_session:
                user_model = UserModel(db_session)
                semester_model = SemesterModel(db_session)
                class_model = ClassModel(db_session)
                
                # Get basic student info
                student = user_model.get_by_id(user_id)
                if not student:
                    return {'error': 'Student not found', 'success': False}
                
                # Get current semester info
                term_info = semester_model.get_current_semester_info()
                term_info["student_id"] = user_id
                term_info["cutoff"] = 90  # 90% attendance cutoff
                
                # Calculate attendance overview
                term_stats = semester_model.student_dashboard_term_attendance(user_id)
                
                # Extract counts from term_stats
                p = term_stats.get("present", 0)
                a = term_stats.get("absent", 0)
                l = term_stats.get("late", 0)
                e = term_stats.get("excused", 0)
                unmarked = term_stats.get("unmarked", 0)
                
                marked = p + a + l + e
                total = marked + unmarked
                
                # Calculate percentages
                present_percent = ((p + l + e) / marked * 100) if marked > 0 else 0
                absent_percent = (a / marked * 100) if marked > 0 else 0
                
                return {
                    'success': True,
                    'student': {
                        'name': student.name,
                        'email': student.email,
                        'institution_id': student.institution_id
                    },
                    'term_info': term_info,
                    'overview': {
                        'present_percent': round(present_percent, 1),
                        'absent_percent': round(absent_percent, 1),
                        'present': p + l + e,
                        'absent': a,
                        'late': l,
                        'excused': e,
                        'unmarked': unmarked,
                        'total': total,
                        'marked': marked
                    }
                }
                
        except Exception as e:
            return {'error': f'Error loading dashboard: {str(e)}', 'success': False}
    
    @staticmethod
    def get_student_profile(user_id):
        """Get student profile data"""
        try:
            with get_session() as db_session:
                user_model = UserModel(db_session)
                student = user_model.get_by_id(user_id)
                
                if not student:
                    return {'error': 'Student not found', 'success': False}
                
                # Get enrollment data
                class_model = ClassModel(db_session)
                course_model = CourseModel(db_session)
                
                # Get current courses
                courses = course_model.get_by_user_id(user_id)
                
                return {
                    'success': True,
                    'student': student.as_sanitized_dict(),
                    'courses': [{
                        'course_id': course.course_id,
                        'code': course.code,
                        'name': course.name,
                        'description': course.description,
                        'credits': course.credits
                    } for course in courses]
                }
                
        except Exception as e:
            return {'error': f'Error loading profile: {str(e)}', 'success': False}
    
    @staticmethod
    def get_student_attendance(user_id):
        """Get student attendance overview with monthly breakdown"""
        try:
            with get_session() as db_session:
                good_attendance_cutoff = 0.9
                class_model = ClassModel(db_session)
                semester_model = SemesterModel(db_session)
                
                # Get current semester info
                term_info = semester_model.get_current_semester_info()
                term_info["student_id"] = user_id
                term_info["cutoff"] = good_attendance_cutoff * 100
                
                # Analyze monthly report
                def analyse_report(report):
                    y, m = report["year"], report["month"]
                    p, a, l, e = report["p"], report["a"], report["l"], report["e"]
                    total = report["total_classes"]
                    present_count = p + l + e
                    present_percent = (present_count / total * 100) if total > 0 else 0
                    
                    return {
                        "month": date(int(y), int(m), 1).strftime("%B %Y"),
                        "present": p,
                        "absent": a,
                        "late": l,
                        "excused": e,
                        "present_percent": round(present_percent, 1),
                        "absent_percent": round((a / total * 100) if total > 0 else 0, 1),
                        "total_classes": total,
                        "is_good": present_percent >= (good_attendance_cutoff * 100)
                    }
                
                # Get monthly attendance data
                monthly_data = class_model.student_attendance_monthly(user_id, 4)
                monthly_report = [analyse_report(report) for report in monthly_data]
                
                # Get term statistics
                term_stats = semester_model.student_dashboard_term_attendance(user_id)
                p = term_stats.get("present", 0)
                a = term_stats.get("absent", 0)
                l = term_stats.get("late", 0)
                e = term_stats.get("excused", 0)
                unmarked = term_stats.get("unmarked", 0)
                
                marked = p + a + l + e
                total = marked + unmarked
                
                # Calculate percentages
                present_percent = ((p + l + e) / marked * 100) if marked > 0 else 0
                absent_percent = (a / marked * 100) if marked > 0 else 0
                
                # Get absent/late records
                absent_late_records = class_model.student_attendance_absent_late(user_id)
                
                return {
                    'success': True,
                    'term_info': term_info,
                    'monthly_report': monthly_report,
                    'overview': {
                        'present_percent': round(present_percent, 1),
                        'absent_percent': round(absent_percent, 1),
                        'present': p + l + e,
                        'absent': a,
                        'late': l,
                        'excused': e,
                        'total': total,
                        'marked': marked
                    },
                    'classes': absent_late_records
                }
                
        except Exception as e:
            return {'error': f'Error loading attendance data: {str(e)}', 'success': False}
    
    @staticmethod
    def get_attendance_history(user_id):
        """Get student attendance history"""
        try:
            with get_session() as db_session:
                attendance_model = AttendanceRecordModel(db_session)
                user_model = UserModel(db_session)
                
                # Get student info
                student = user_model.get_by_id(user_id)
                if not student:
                    return {'error': 'Student not found', 'success': False}
                
                # Get attendance records
                attendance_records = attendance_model.get_by_student(user_id)
                
                # Format records for display
                formatted_records = []
                for record in attendance_records:
                    # Get class details
                    with get_session() as inner_session:
                        from database.models import Class, Course
                        class_details = inner_session.query(Class, Course).join(
                            Course, Class.course_id == Course.course_id
                        ).filter(Class.class_id == record.class_id).first()
                        
                        if class_details:
                            class_obj, course = class_details
                            formatted_records.append({
                                'date': class_obj.start_time.strftime("%Y-%m-%d"),
                                'time': class_obj.start_time.strftime("%H:%M"),
                                'course_code': course.code,
                                'course_name': course.name,
                                'status': record.status,
                                'marked_by': record.marked_by,
                                'recorded_at': record.recorded_at.strftime("%Y-%m-%d %H:%M") if record.recorded_at else None,
                                'notes': record.notes
                            })
                
                # Calculate summary
                total_classes = len(formatted_records)
                present_count = sum(1 for r in formatted_records if r['status'] in ['present', 'late'])
                attendance_percentage = (present_count / total_classes * 100) if total_classes > 0 else 0
                
                return {
                    'success': True,
                    'student': student.as_sanitized_dict(),
                    'summary': {
                        'total_classes': total_classes,
                        'present_count': present_count,
                        'attendance_percentage': round(attendance_percentage, 1)
                    },
                    'records': formatted_records
                }
                
        except Exception as e:
            return {'error': f'Error loading attendance history: {str(e)}', 'success': False}
    
    @staticmethod
    def get_student_appeals(user_id, module_filter='', status_filter='', date_filter=''):
        """Get student appeals with filtering options"""
        try:
            with get_session() as db_session:
                appeal_model = AttendanceAppealModel(db_session)
                class_model = ClassModel(db_session)
                
                # Get all appeals for the student
                all_appeals = appeal_model.student_appeals(student_id=user_id)
                
                # Apply filters
                filtered_appeals = []
                for appeal in all_appeals:
                    # Module filter
                    if module_filter and appeal.get("course_code") != module_filter:
                        continue
                    
                    # Status filter
                    if status_filter and appeal.get("status") != status_filter:
                        continue
                    
                    # Date filter
                    if date_filter:
                        appeal_date = appeal.get("class_date", "")
                        if isinstance(appeal_date, str):
                            # Compare date strings
                            if appeal_date != date_filter:
                                continue
                        elif hasattr(appeal_date, 'strftime'):
                            # Compare datetime objects
                            if appeal_date.strftime("%Y-%m-%d") != date_filter:
                                continue
                    
                    filtered_appeals.append(appeal)
                
                # Get absent/late records for potential appeals
                absent_late = class_model.student_attendance_absent_late(user_id)
                
                # Prepare filter options
                modules = set()
                for appeal in all_appeals:
                    module = appeal.get("course_code")
                    if module:
                        modules.add(module)
                
                return {
                    'success': True,
                    'filters': {
                        'modules': sorted(list(modules)),
                        'statuses': [status.value for status in AttendanceAppealStatusEnum],
                    },
                    'appeals': filtered_appeals,
                    'absent_late': absent_late
                }
                
        except Exception as e:
            return {'error': f'Error loading appeals: {str(e)}', 'success': False}
    
    @staticmethod
    def can_appeal_record(user_id, attendance_record_id):
        """Check if student can appeal a specific record"""
        try:
            with get_session() as db_session:
                attendance_model = AttendanceRecordModel(db_session)
                appeal_model = AttendanceAppealModel(db_session)
                
                # Check if record exists
                record = attendance_model.get_by_id(attendance_record_id)
                if not record:
                    return {
                        'success': False,
                        'can_appeal': False,
                        'message': 'Attendance record not found'
                    }
                
                # Check if record belongs to student
                if record.student_id != user_id:
                    return {
                        'success': False,
                        'can_appeal': False,
                        'message': 'You are not authorized to appeal this record'
                    }
                
                # Check if appeal already exists
                existing_appeal = appeal_model.get_one(attendance_id=attendance_record_id)
                if existing_appeal:
                    return {
                        'success': False,
                        'can_appeal': False,
                        'message': 'An appeal for this attendance record already exists'
                    }
                
                # Check if status is appealable (absent or late)
                if record.status not in ['absent', 'late']:
                    return {
                        'success': False,
                        'can_appeal': False,
                        'message': 'Only absent or late records can be appealed'
                    }
                
                return {
                    'success': True,
                    'can_appeal': True,
                    'message': 'Record can be appealed'
                }
                
        except Exception as e:
            return {
                'success': False,
                'can_appeal': False,
                'message': f'Error checking appeal eligibility: {str(e)}'
            }
    
    @staticmethod
    def get_appeal_form_data(user_id, attendance_record_id):
        """Get data for appeal form"""
        try:
            with get_session() as db_session:
                attendance_model = AttendanceRecordModel(db_session)
                
                # Verify student can appeal this record
                can_appeal = StudentControl.can_appeal_record(user_id, attendance_record_id)
                if not can_appeal.get('can_appeal'):
                    return {
                        'success': False,
                        'error': can_appeal.get('message')
                    }
                
                # Get attendance record details
                record_details = attendance_model.student_get_attendance_for_appeal(attendance_record_id)
                
                # Verify the record belongs to the student
                if record_details.get('student_id') != user_id:
                    return {
                        'success': False,
                        'error': 'You are not authorized to appeal this record'
                    }
                
                return {
                    'success': True,
                    'attendance_record_id': attendance_record_id,
                    **record_details
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Error loading appeal form data: {str(e)}'
            }
    
    @staticmethod
    def submit_appeal(user_id, attendance_record_id, reason):
        """Submit an appeal"""
        try:
            with get_session() as db_session:
                appeal_model = AttendanceAppealModel(db_session)
                attendance_model = AttendanceRecordModel(db_session)
                
                # Validate reason
                if not reason or not reason.strip():
                    return {
                        'success': False,
                        'error': 'Appeal reason cannot be empty'
                    }
                
                # Check if student can appeal this record
                can_appeal = StudentControl.can_appeal_record(user_id, attendance_record_id)
                if not can_appeal.get('can_appeal'):
                    return {
                        'success': False,
                        'error': can_appeal.get('message')
                    }
                
                # Get attendance record to verify it exists
                record = attendance_model.get_by_id(attendance_record_id)
                if not record:
                    return {
                        'success': False,
                        'error': 'Attendance record not found'
                    }
                
                # Create appeal
                appeal = appeal_model.create(
                    attendance_id=attendance_record_id,
                    student_id=user_id,
                    reason=reason.strip(),
                    status='pending'
                )
                
                return {
                    'success': True,
                    'message': 'Appeal submitted successfully',
                    'appeal_id': appeal.appeal_id
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Error submitting appeal: {str(e)}'
            }
    
    @staticmethod
    def retract_appeal(user_id, appeal_id):
        """Retract (delete) an appeal"""
        try:
            with get_session() as db_session:
                appeal_model = AttendanceAppealModel(db_session)
                
                # Get appeal
                appeal = appeal_model.get_by_id(appeal_id)
                if not appeal:
                    return {
                        'success': False,
                        'error': 'Appeal does not exist'
                    }
                
                # Check if appeal belongs to student
                if appeal.student_id != user_id:
                    return {
                        'success': False,
                        'error': 'You are not authorized to retract this appeal'
                    }
                
                # Check if appeal is pending
                if appeal.status != 'pending':
                    return {
                        'success': False,
                        'error': 'Only pending appeals can be retracted'
                    }
                
                # Delete appeal
                success = appeal_model.delete(appeal_id)
                
                if success:
                    return {
                        'success': True,
                        'message': 'Appeal retracted successfully'
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Failed to retract appeal'
                    }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Error retracting appeal: {str(e)}'
            }
    
    @staticmethod
    def get_absent_records(user_id):
        """Get all absent records for student"""
        try:
            with get_session() as db_session:
                attendance_model = AttendanceRecordModel(db_session)
                user_model = UserModel(db_session)
                
                # Get student info
                student = user_model.get_by_id(user_id)
                if not student:
                    return {'error': 'Student not found', 'success': False}
                
                # Get all attendance records
                all_records = attendance_model.get_by_student(user_id)
                
                # Filter for absent records
                absent_records = []
                for record in all_records:
                    if record.status == 'absent':
                        # Get class details
                        with get_session() as inner_session:
                            from database.models import Class, Course, User as UserModelDB
                            class_details = inner_session.query(
                                Class, Course, UserModelDB
                            ).join(
                                Course, Class.course_id == Course.course_id
                            ).join(
                                UserModelDB, Class.lecturer_id == UserModelDB.user_id
                            ).filter(Class.class_id == record.class_id).first()
                            
                            if class_details:
                                class_obj, course, lecturer = class_details
                                absent_records.append({
                                    'date': class_obj.start_time.strftime("%Y-%m-%d"),
                                    'time': class_obj.start_time.strftime("%H:%M"),
                                    'course_code': course.code,
                                    'course_name': course.name,
                                    'lecturer': lecturer.name,
                                    'recorded_at': record.recorded_at.strftime("%Y-%m-%d %H:%M") if record.recorded_at else None,
                                    'notes': record.notes
                                })
                
                # Calculate summary
                total_absences = len(absent_records)
                total_classes = len(all_records)
                absence_percentage = (total_absences / total_classes * 100) if total_classes > 0 else 0
                
                return {
                    'success': True,
                    'student': student.as_sanitized_dict(),
                    'summary': {
                        'total_absences': total_absences,
                        'total_classes': total_classes,
                        'absence_percentage': round(absence_percentage, 1)
                    },
                    'records': absent_records
                }
                
        except Exception as e:
            return {'error': f'Error loading absent records: {str(e)}', 'success': False}
        
    @staticmethod
    def get_dashboard_data(user_id):
        """Get all dashboard data for student"""
        try:
            with get_session() as db_session:
                user_model = UserModel(db_session)
                class_model = ClassModel(db_session)
                semester_model = SemesterModel(db_session)
                attendance_model = AttendanceRecordModel(db_session)
                
                # Get student info
                student = user_model.get_by_id(user_id)
                if not student:
                    return {'error': 'Student not found', 'success': False}
                
                # Get current date and time
                current_time = datetime.now()
                current_date = date.today()
                
                # Get today's classes
                # First, get student's enrolled courses for current semester
                from database.models import CourseUser, Semester, Course, Class, Venue, User as UserModelDB
                
                # Get current semester
                current_semester = semester_model.get_current_semester(student.institution_id)
                if not current_semester:
                    today_classes = []
                else:
                    # Get today's classes
                    today_classes_query = (
                        db_session.query(Class, Course, Venue, UserModelDB)
                        .join(Course, Class.course_id == Course.course_id)
                        .join(Venue, Class.venue_id == Venue.venue_id)
                        .join(UserModelDB, Class.lecturer_id == UserModelDB.user_id)
                        .join(CourseUser, Course.course_id == CourseUser.course_id)
                        .filter(CourseUser.user_id == user_id)
                        .filter(CourseUser.semester_id == current_semester.semester_id)
                        .filter(func.date(Class.start_time) == current_date)
                        .order_by(Class.start_time)
                        .all()
                    )
                    
                    today_classes = []
                    for class_obj, course, venue, lecturer in today_classes_query:
                        # Check if attendance is taken for this class
                        attendance_taken = (
                            db_session.query(AttendanceRecord)
                            .filter(AttendanceRecord.class_id == class_obj.class_id)
                            .filter(AttendanceRecord.student_id == user_id)
                            .first()
                        )
                        
                        # Determine class status
                        now = datetime.now()
                        class_status = 'upcoming'
                        if class_obj.start_time and class_obj.end_time:
                            if now > class_obj.end_time:
                                class_status = 'completed'
                            elif class_obj.start_time <= now <= class_obj.end_time:
                                class_status = 'in_progress'
                        
                        today_classes.append({
                            'class_id': class_obj.class_id,
                            'course_code': course.code,
                            'course_name': course.name,
                            'section': getattr(class_obj, 'section', 'T01'),
                            'start_time': class_obj.start_time.strftime('%I:%M %p') if class_obj.start_time else 'N/A',
                            'end_time': class_obj.end_time.strftime('%I:%M %p') if class_obj.end_time else 'N/A',
                            'venue': venue.name,
                            'lecturer_name': lecturer.name,
                            'lecturer_email': lecturer.email,
                            'status': class_status,
                            'attendance_taken': attendance_taken is not None,
                            'attendance_status': attendance_taken.status if attendance_taken else 'unmarked'
                        })
                
                # Get attendance statistics
                term_stats = semester_model.student_dashboard_term_attendance(user_id)
                p = term_stats.get("present", 0)
                a = term_stats.get("absent", 0)
                l = term_stats.get("late", 0)
                e = term_stats.get("excused", 0)
                unmarked = term_stats.get("unmarked", 0)
                
                marked = p + a + l + e
                total = marked + unmarked
                
                present_percent = ((p + l + e) / marked * 100) if marked > 0 else 0
                absent_percent = (a / marked * 100) if marked > 0 else 0
                
                # Get student program info (you might need to add this to your User model)
                # For now, use placeholder or extend your model
                program_info = {
                    'program': getattr(student, 'program', 'Computer Science'),
                    'year': getattr(student, 'year', 'Year 2')
                }
                
                # Get recent announcements (placeholder - implement AnnouncementModel as needed)
                announcements = []  # You'll need to implement AnnouncementModel similar to lecturer
                
                return {
                    'success': True,
                    'student': {
                        'name': student.name,
                        'email': student.email,
                        'student_id': f"S{student.user_id:07d}",
                        'program': program_info['program'],
                        'year': program_info['year'],
                        'institution_id': student.institution_id
                    },
                    'today_classes': today_classes,
                    'announcements': announcements,
                    'statistics': {
                        'overall_attendance': round(present_percent, 1),
                        'present_count': p + l + e,
                        'absent_count': a,
                        'late_count': l,
                        'excused_count': e,
                        'total_classes': total,
                        'present_percent': round(present_percent, 1),
                        'absent_percent': round(absent_percent, 1)
                    },
                    'current_time': current_time.strftime('%I:%M %p'),
                    'current_date': current_date.strftime('%d %B %Y')
                }
                
        except Exception as e:
            return {'error': f'Error loading dashboard data: {str(e)}', 'success': False}
    """Control class for student business logic"""
    
    @staticmethod
    def get_student_dashboard(user_id):
        """Get student dashboard data"""
        try:
            with get_session() as db_session:
                user_model = UserModel(db_session)
                semester_model = SemesterModel(db_session)
                class_model = ClassModel(db_session)
                
                # Get basic student info
                student = user_model.get_by_id(user_id)
                if not student:
                    return {'error': 'Student not found', 'success': False}
                
                # Get current semester info
                term_info = semester_model.get_current_semester_info()
                term_info["student_id"] = user_id
                term_info["cutoff"] = 90  # 90% attendance cutoff
                
                # Calculate attendance overview
                term_stats = semester_model.student_dashboard_term_attendance(user_id)
                
                # Extract counts from term_stats
                p = term_stats.get("present", 0)
                a = term_stats.get("absent", 0)
                l = term_stats.get("late", 0)
                e = term_stats.get("excused", 0)
                unmarked = term_stats.get("unmarked", 0)
                
                marked = p + a + l + e
                total = marked + unmarked
                
                # Calculate percentages
                present_percent = ((p + l + e) / marked * 100) if marked > 0 else 0
                absent_percent = (a / marked * 100) if marked > 0 else 0
                
                return {
                    'success': True,
                    'student': {
                        'name': student.name,
                        'email': student.email,
                        'institution_id': student.institution_id
                    },
                    'term_info': term_info,
                    'overview': {
                        'present_percent': round(present_percent, 1),
                        'absent_percent': round(absent_percent, 1),
                        'present': p + l + e,
                        'absent': a,
                        'late': l,
                        'excused': e,
                        'unmarked': unmarked,
                        'total': total,
                        'marked': marked
                    }
                }
                
        except Exception as e:
            return {'error': f'Error loading dashboard: {str(e)}', 'success': False}
    
    @staticmethod
    def get_student_profile(user_id):
        """Get student profile data"""
        try:
            with get_session() as db_session:
                user_model = UserModel(db_session)
                student = user_model.get_by_id(user_id)
                
                if not student:
                    return {'error': 'Student not found', 'success': False}
                
                # Get enrollment data
                class_model = ClassModel(db_session)
                course_model = CourseModel(db_session)
                
                # Get current courses
                courses = course_model.get_by_user_id(user_id)
                
                return {
                    'success': True,
                    'student': student.as_sanitized_dict(),
                    'courses': [{
                        'course_id': course.course_id,
                        'code': course.code,
                        'name': course.name,
                        'description': course.description,
                        'credits': course.credits
                    } for course in courses]
                }
                
        except Exception as e:
            return {'error': f'Error loading profile: {str(e)}', 'success': False}
    
    @staticmethod
    def get_student_attendance(user_id):
        """Get student attendance overview with monthly breakdown"""
        try:
            with get_session() as db_session:
                good_attendance_cutoff = 0.9
                class_model = ClassModel(db_session)
                semester_model = SemesterModel(db_session)
                
                # Get current semester info
                term_info = semester_model.get_current_semester_info()
                term_info["student_id"] = user_id
                term_info["cutoff"] = good_attendance_cutoff * 100
                
                # Analyze monthly report
                def analyse_report(report):
                    y, m = report["year"], report["month"]
                    p, a, l, e = report["p"], report["a"], report["l"], report["e"]
                    total = report["total_classes"]
                    present_count = p + l + e
                    present_percent = (present_count / total * 100) if total > 0 else 0
                    
                    return {
                        "month": date(int(y), int(m), 1).strftime("%B %Y"),
                        "present": p,
                        "absent": a,
                        "late": l,
                        "excused": e,
                        "present_percent": round(present_percent, 1),
                        "absent_percent": round((a / total * 100) if total > 0 else 0, 1),
                        "total_classes": total,
                        "is_good": present_percent >= (good_attendance_cutoff * 100)
                    }
                
                # Get monthly attendance data
                monthly_data = class_model.student_attendance_monthly(user_id, 4)
                monthly_report = [analyse_report(report) for report in monthly_data]
                
                # Get term statistics
                term_stats = semester_model.student_dashboard_term_attendance(user_id)
                p = term_stats.get("present", 0)
                a = term_stats.get("absent", 0)
                l = term_stats.get("late", 0)
                e = term_stats.get("excused", 0)
                unmarked = term_stats.get("unmarked", 0)
                
                marked = p + a + l + e
                total = marked + unmarked
                
                # Calculate percentages
                present_percent = ((p + l + e) / marked * 100) if marked > 0 else 0
                absent_percent = (a / marked * 100) if marked > 0 else 0
                
                # Get absent/late records
                absent_late_records = class_model.student_attendance_absent_late(user_id)
                
                return {
                    'success': True,
                    'term_info': term_info,
                    'monthly_report': monthly_report,
                    'overview': {
                        'present_percent': round(present_percent, 1),
                        'absent_percent': round(absent_percent, 1),
                        'present': p + l + e,
                        'absent': a,
                        'late': l,
                        'excused': e,
                        'total': total,
                        'marked': marked
                    },
                    'classes': absent_late_records
                }
                
        except Exception as e:
            return {'error': f'Error loading attendance data: {str(e)}', 'success': False}
    
    @staticmethod
    def get_attendance_history(user_id):
        """Get student attendance history"""
        try:
            with get_session() as db_session:
                attendance_model = AttendanceRecordModel(db_session)
                user_model = UserModel(db_session)
                
                # Get student info
                student = user_model.get_by_id(user_id)
                if not student:
                    return {'error': 'Student not found', 'success': False}
                
                # Get attendance records
                attendance_records = attendance_model.get_by_student(user_id)
                
                # Format records for display
                formatted_records = []
                for record in attendance_records:
                    # Get class details
                    with get_session() as inner_session:
                        from database.models import Class, Course
                        class_details = inner_session.query(Class, Course).join(
                            Course, Class.course_id == Course.course_id
                        ).filter(Class.class_id == record.class_id).first()
                        
                        if class_details:
                            class_obj, course = class_details
                            formatted_records.append({
                                'date': class_obj.start_time.strftime("%Y-%m-%d"),
                                'time': class_obj.start_time.strftime("%H:%M"),
                                'course_code': course.code,
                                'course_name': course.name,
                                'status': record.status,
                                'marked_by': record.marked_by,
                                'recorded_at': record.recorded_at.strftime("%Y-%m-%d %H:%M") if record.recorded_at else None,
                                'notes': record.notes
                            })
                
                # Calculate summary
                total_classes = len(formatted_records)
                present_count = sum(1 for r in formatted_records if r['status'] in ['present', 'late'])
                attendance_percentage = (present_count / total_classes * 100) if total_classes > 0 else 0
                
                return {
                    'success': True,
                    'student': student.as_sanitized_dict(),
                    'summary': {
                        'total_classes': total_classes,
                        'present_count': present_count,
                        'attendance_percentage': round(attendance_percentage, 1)
                    },
                    'records': formatted_records
                }
                
        except Exception as e:
            return {'error': f'Error loading attendance history: {str(e)}', 'success': False}
    
    @staticmethod
    def get_student_appeals(user_id):
        """Get student appeals with filtering options"""
        try:
            with get_session() as db_session:
                appeal_model = AttendanceAppealModel(db_session)
                class_model = ClassModel(db_session)
                
                # Get appeals
                appeals = appeal_model.student_appeals(student_id=user_id)
                
                # Get absent/late records for potential appeals
                absent_late = class_model.student_attendance_absent_late(user_id)
                
                # Prepare filters
                modules = set(appeal["course_code"] for appeal in appeals)
                
                return {
                    'success': True,
                    'filters': {
                        'modules': list(modules),
                        'statuses': [status.value for status in AttendanceAppealStatusEnum],
                    },
                    'appeals': appeals,
                    'absent_late': absent_late
                }
                
        except Exception as e:
            return {'error': f'Error loading appeals: {str(e)}', 'success': False}
    
    @staticmethod
    def can_appeal_record(user_id, attendance_record_id):
        """Check if student can appeal a specific record"""
        try:
            with get_session() as db_session:
                attendance_model = AttendanceRecordModel(db_session)
                appeal_model = AttendanceAppealModel(db_session)
                
                # Check if record exists
                record = attendance_model.get_by_id(attendance_record_id)
                if not record:
                    return {
                        'success': False,
                        'can_appeal': False,
                        'message': 'Attendance record not found'
                    }
                
                # Check if record belongs to student
                if record.student_id != user_id:
                    return {
                        'success': False,
                        'can_appeal': False,
                        'message': 'You are not authorized to appeal this record'
                    }
                
                # Check if appeal already exists
                existing_appeal = appeal_model.get_one(attendance_id=attendance_record_id)
                if existing_appeal:
                    return {
                        'success': False,
                        'can_appeal': False,
                        'message': 'An appeal for this attendance record already exists'
                    }
                
                # Check if status is appealable (absent or late)
                if record.status not in ['absent', 'late']:
                    return {
                        'success': False,
                        'can_appeal': False,
                        'message': 'Only absent or late records can be appealed'
                    }
                
                return {
                    'success': True,
                    'can_appeal': True,
                    'message': 'Record can be appealed'
                }
                
        except Exception as e:
            return {
                'success': False,
                'can_appeal': False,
                'message': f'Error checking appeal eligibility: {str(e)}'
            }
    
    @staticmethod
    def get_appeal_form_data(user_id, attendance_record_id):
        """Get data for appeal form"""
        try:
            with get_session() as db_session:
                attendance_model = AttendanceRecordModel(db_session)
                
                # Verify student can appeal this record
                can_appeal = StudentControl.can_appeal_record(user_id, attendance_record_id)
                if not can_appeal.get('can_appeal'):
                    return {
                        'success': False,
                        'error': can_appeal.get('message')
                    }
                
                # Get attendance record details
                record_details = attendance_model.student_get_attendance_for_appeal(attendance_record_id)
                
                # Verify the record belongs to the student
                if record_details.get('student_id') != user_id:
                    return {
                        'success': False,
                        'error': 'You are not authorized to appeal this record'
                    }
                
                return {
                    'success': True,
                    'attendance_record_id': attendance_record_id,
                    **record_details
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Error loading appeal form data: {str(e)}'
            }
    
    @staticmethod
    def submit_appeal(user_id, attendance_record_id, reason):
        """Submit an appeal"""
        try:
            with get_session() as db_session:
                appeal_model = AttendanceAppealModel(db_session)
                attendance_model = AttendanceRecordModel(db_session)
                
                # Validate reason
                if not reason or not reason.strip():
                    return {
                        'success': False,
                        'error': 'Appeal reason cannot be empty'
                    }
                
                # Check if student can appeal this record
                can_appeal = StudentControl.can_appeal_record(user_id, attendance_record_id)
                if not can_appeal.get('can_appeal'):
                    return {
                        'success': False,
                        'error': can_appeal.get('message')
                    }
                
                # Get attendance record to verify it exists
                record = attendance_model.get_by_id(attendance_record_id)
                if not record:
                    return {
                        'success': False,
                        'error': 'Attendance record not found'
                    }
                
                # Create appeal
                appeal = appeal_model.create(
                    attendance_id=attendance_record_id,
                    student_id=user_id,
                    reason=reason.strip(),
                    status='pending'
                )
                
                return {
                    'success': True,
                    'message': 'Appeal submitted successfully',
                    'appeal_id': appeal.appeal_id
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Error submitting appeal: {str(e)}'
            }
    
    @staticmethod
    def retract_appeal(user_id, appeal_id):
        """Retract (delete) an appeal"""
        try:
            with get_session() as db_session:
                appeal_model = AttendanceAppealModel(db_session)
                
                # Get appeal
                appeal = appeal_model.get_by_id(appeal_id)
                if not appeal:
                    return {
                        'success': False,
                        'error': 'Appeal does not exist'
                    }
                
                # Check if appeal belongs to student
                if appeal.student_id != user_id:
                    return {
                        'success': False,
                        'error': 'You are not authorized to retract this appeal'
                    }
                
                # Check if appeal is pending
                if appeal.status != 'pending':
                    return {
                        'success': False,
                        'error': 'Only pending appeals can be retracted'
                    }
                
                # Delete appeal
                success = appeal_model.delete(appeal_id)
                
                if success:
                    return {
                        'success': True,
                        'message': 'Appeal retracted successfully'
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Failed to retract appeal'
                    }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Error retracting appeal: {str(e)}'
            }
    
    @staticmethod
    def get_absent_records(user_id):
        """Get all absent records for student"""
        try:
            with get_session() as db_session:
                attendance_model = AttendanceRecordModel(db_session)
                user_model = UserModel(db_session)
                
                # Get student info
                student = user_model.get_by_id(user_id)
                if not student:
                    return {'error': 'Student not found', 'success': False}
                
                # Get all attendance records
                all_records = attendance_model.get_by_student(user_id)
                
                # Filter for absent records
                absent_records = []
                for record in all_records:
                    if record.status == 'absent':
                        # Get class details
                        with get_session() as inner_session:
                            from database.models import Class, Course, User as UserModelDB
                            class_details = inner_session.query(
                                Class, Course, UserModelDB
                            ).join(
                                Course, Class.course_id == Course.course_id
                            ).join(
                                UserModelDB, Class.lecturer_id == UserModelDB.user_id
                            ).filter(Class.class_id == record.class_id).first()
                            
                            if class_details:
                                class_obj, course, lecturer = class_details
                                absent_records.append({
                                    'date': class_obj.start_time.strftime("%Y-%m-%d"),
                                    'time': class_obj.start_time.strftime("%H:%M"),
                                    'course_code': course.code,
                                    'course_name': course.name,
                                    'lecturer': lecturer.name,
                                    'recorded_at': record.recorded_at.strftime("%Y-%m-%d %H:%M") if record.recorded_at else None,
                                    'notes': record.notes
                                })
                
                # Calculate summary
                total_absences = len(absent_records)
                total_classes = len(all_records)
                absence_percentage = (total_absences / total_classes * 100) if total_classes > 0 else 0
                
                return {
                    'success': True,
                    'student': student.as_sanitized_dict(),
                    'summary': {
                        'total_absences': total_absences,
                        'total_classes': total_classes,
                        'absence_percentage': round(absence_percentage, 1)
                    },
                    'records': absent_records
                }
                
        except Exception as e:
            return {'error': f'Error loading absent records: {str(e)}', 'success': False}
        
    @staticmethod
    def get_dashboard_data(user_id):
        """Get all dashboard data for student"""
        try:
            with get_session() as db_session:
                user_model = UserModel(db_session)
                class_model = ClassModel(db_session)
                semester_model = SemesterModel(db_session)
                attendance_model = AttendanceRecordModel(db_session)
                
                # Get student info
                student = user_model.get_by_id(user_id)
                if not student:
                    return {'error': 'Student not found', 'success': False}
                
                # Get current date and time
                current_time = datetime.now()
                current_date = date.today()
                
                # Get today's classes
                # First, get student's enrolled courses for current semester
                from database.models import CourseUser, Semester, Course, Class, Venue, User as UserModelDB
                
                # Get current semester
                current_semester = semester_model.get_current_semester(student.institution_id)
                if not current_semester:
                    today_classes = []
                else:
                    # Get today's classes
                    today_classes_query = (
                        db_session.query(Class, Course, Venue, UserModelDB)
                        .join(Course, Class.course_id == Course.course_id)
                        .join(Venue, Class.venue_id == Venue.venue_id)
                        .join(UserModelDB, Class.lecturer_id == UserModelDB.user_id)
                        .join(CourseUser, Course.course_id == CourseUser.course_id)
                        .filter(CourseUser.user_id == user_id)
                        .filter(CourseUser.semester_id == current_semester.semester_id)
                        .filter(func.date(Class.start_time) == current_date)
                        .order_by(Class.start_time)
                        .all()
                    )
                    
                    today_classes = []
                    for class_obj, course, venue, lecturer in today_classes_query:
                        # Check if attendance is taken for this class
                        attendance_taken = (
                            db_session.query(AttendanceRecord)
                            .filter(AttendanceRecord.class_id == class_obj.class_id)
                            .filter(AttendanceRecord.student_id == user_id)
                            .first()
                        )
                        
                        # Determine class status
                        now = datetime.now()
                        class_status = 'upcoming'
                        if class_obj.start_time and class_obj.end_time:
                            if now > class_obj.end_time:
                                class_status = 'completed'
                            elif class_obj.start_time <= now <= class_obj.end_time:
                                class_status = 'in_progress'
                        
                        today_classes.append({
                            'class_id': class_obj.class_id,
                            'course_code': course.code,
                            'course_name': course.name,
                            'section': getattr(class_obj, 'section', 'T01'),
                            'start_time': class_obj.start_time.strftime('%I:%M %p') if class_obj.start_time else 'N/A',
                            'end_time': class_obj.end_time.strftime('%I:%M %p') if class_obj.end_time else 'N/A',
                            'venue': venue.name,
                            'lecturer_name': lecturer.name,
                            'lecturer_email': lecturer.email,
                            'status': class_status,
                            'attendance_taken': attendance_taken is not None,
                            'attendance_status': attendance_taken.status if attendance_taken else 'unmarked'
                        })
                
                # Get attendance statistics
                term_stats = semester_model.student_dashboard_term_attendance(user_id)
                p = term_stats.get("present", 0)
                a = term_stats.get("absent", 0)
                l = term_stats.get("late", 0)
                e = term_stats.get("excused", 0)
                unmarked = term_stats.get("unmarked", 0)
                
                marked = p + a + l + e
                total = marked + unmarked
                
                present_percent = ((p + l + e) / marked * 100) if marked > 0 else 0
                absent_percent = (a / marked * 100) if marked > 0 else 0
                
                # Get student program info (you might need to add this to your User model)
                # For now, use placeholder or extend your model
                program_info = {
                    'program': getattr(student, 'program', 'Computer Science'),
                    'year': getattr(student, 'year', 'Year 2')
                }
                
                # Get recent announcements (placeholder - implement AnnouncementModel as needed)
                announcements = []  # You'll need to implement AnnouncementModel similar to lecturer
                
                return {
                    'success': True,
                    'student': {
                        'name': student.name,
                        'email': student.email,
                        'student_id': f"S{student.user_id:07d}",
                        'program': program_info['program'],
                        'year': program_info['year'],
                        'institution_id': student.institution_id
                    },
                    'today_classes': today_classes,
                    'announcements': announcements,
                    'statistics': {
                        'overall_attendance': round(present_percent, 1),
                        'present_count': p + l + e,
                        'absent_count': a,
                        'late_count': l,
                        'excused_count': e,
                        'total_classes': total,
                        'present_percent': round(present_percent, 1),
                        'absent_percent': round(absent_percent, 1)
                    },
                    'current_time': current_time.strftime('%I:%M %p'),
                    'current_date': current_date.strftime('%d %B %Y')
                }
                
        except Exception as e:
            return {'error': f'Error loading dashboard data: {str(e)}', 'success': False}