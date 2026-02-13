from application.entities2.classes import ClassModel
from application.entities2.semester import SemesterModel
from application.entities2.attendance_record import AttendanceRecordModel
from application.entities2.attendance_appeal import AttendanceAppealModel
from application.entities2.user import UserModel
from application.entities2.course import CourseModel
from application.entities2.venue import VenueModel
from application.entities2.announcement import AnnouncementModel
from application.entities2.notification import NotificationModel
from datetime import datetime, date, timedelta
from database.base import get_session
from database.models import AttendanceAppealStatusEnum, AttendanceRecord, Class, Course, CourseUser, User, Venue, User as UserModelDB
from sqlalchemy import or_, func, and_, extract
import math

class StudentControl:
    """Control class for student business logic"""
    
    def get_student_dashboard(user_id):
        """Get student dashboard data"""
        try:
            with get_session() as db_session:
                user_model = UserModel(db_session)
                semester_model = SemesterModel(db_session)
                class_model = ClassModel(db_session)
                announcement_model = AnnouncementModel(db_session)  # NEW: Add announcement model
                
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
                unmarked_count = term_stats.get(None, 0)  # None status means no record
                
                marked = p + a + l + e
                total = marked + unmarked_count
                
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
                        'unmarked_count': unmarked_count,
                        'total': total,
                        'marked': marked
                    }
                }
                
        except Exception as e:
            return {'error': f'Error loading dashboard: {str(e)}', 'success': False}
    
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
                unmarked_count = term_stats.get(None, 0)  # None status means no record
                
                marked = p + a + l + e
                total = marked + unmarked_count
                
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
    
    def get_attendance_history(user_id, search_query='', status_filter='', month_filter='', venue_filter='', page=1, per_page=8):
        """Get student attendance history with filtering and pagination"""
        try:
            with get_session() as db_session:
                attendance_model = AttendanceRecordModel(db_session)
                user_model = UserModel(db_session)
            
                # Get student info
                student = user_model.get_by_id(user_id)
                if not student:
                    return {'error': 'Student not found', 'success': False}
            
                # Build base query
                base_query = (
                    db_session.query(AttendanceRecord, Class, Course, User, Venue)
                    .join(Class, AttendanceRecord.class_id == Class.class_id)
                    .join(Course, Class.course_id == Course.course_id)
                    .join(User, Class.lecturer_id == User.user_id)
                    .join(Venue, Class.venue_id == Venue.venue_id)
                    .filter(AttendanceRecord.student_id == user_id)
                    .order_by(Class.start_time.desc())
                )
            
                # Apply search filter
                if search_query:
                    search_term = f"%{search_query.lower()}%"
                    base_query = base_query.filter(
                        or_(
                            Course.code.ilike(search_term),
                            Course.name.ilike(search_term),
                            User.name.ilike(search_term),
                            Venue.name.ilike(search_term)
                        )
                    )
                # Apply status filter
                if status_filter:
                    base_query = base_query.filter(AttendanceRecord.status == status_filter)
            
                # Apply month filter (format: YYYY-MM)
                if month_filter:
                    try:
                        year, month = month_filter.split('-')
                        base_query = base_query.filter(
                            extract('year', Class.start_time) == int(year),
                            extract('month', Class.start_time) == int(month)
                        )
                    except (ValueError, AttributeError):
                        # If month filter is invalid, ignore it
                        pass
            
                # Apply venue filter
                if venue_filter:
                    base_query = base_query.filter(Venue.venue_id == venue_filter)
            
                # Get total count for pagination
                total_records = base_query.count()
            
                # Apply pagination
                offset = (page - 1) * per_page
                paginated_query = base_query.offset(offset).limit(per_page)
            
                # Execute query
                results = paginated_query.all()
            
                # Format records for display
                formatted_records = []
                for record, class_obj, course, lecturer, venue in results:
                    # Check if appeal exists for this record
                    appeal_exists = (
                        db_session.query(AttendanceAppealModel(db_session).model)
                        .filter_by(attendance_id=record.attendance_id)
                        .first()
                        is not None
                    )
                
                    # Determine if appeal is possible
                    # Can appeal if: status is absent/late OR audit failed
                    can_appeal = (
                        (record.status in ['absent', 'late'] or record.audit_status == 'fail') and 
                        not appeal_exists and
                        (datetime.now() - class_obj.start_time).days <= 7  # Within 7 days
                    )
                
                    formatted_records.append({
                        'attendance_id': record.attendance_id,
                        'date_formatted': class_obj.start_time.strftime("%b %d, %Y"),
                        'date_iso': class_obj.start_time.strftime("%Y-%m-%d"),
                        'start_time': class_obj.start_time.strftime("%H:%M"),
                        'end_time': class_obj.end_time.strftime("%H:%M") if class_obj.end_time else "",
                        'course_code': course.code,
                        'course_name': course.name,
                        'venue': venue.name,
                        'venue_id': venue.venue_id,
                        'lecturer_name': lecturer.name,
                        'status': record.status,
                        'recorded_at': record.recorded_at.strftime("%Y-%m-%d %H:%M") if record.recorded_at else None,
                        'notes': record.notes,
                        'can_appeal': can_appeal,
                        'audit_status': record.audit_status,
                        'audited_at': record.audited_at.strftime("%Y-%m-%d %H:%M") if record.audited_at else None
                    })
            
                # Generate month filter options (last 6 months)
                months = []
                current_date = datetime.now()
                for i in range(6):
                    month_date = current_date - timedelta(days=30*i)
                    month_value = month_date.strftime("%Y-%m")
                    month_display = month_date.strftime("%B %Y")
                    months.append({
                        'value': month_value,
                        'display': month_display
                    })
            
                # Generate venue filter options
                venues = (
                    db_session.query(Venue)
                    .join(Class, Class.venue_id == Venue.venue_id)
                    .join(AttendanceRecord, AttendanceRecord.class_id == Class.class_id)
                    .filter(AttendanceRecord.student_id == user_id)
                    .distinct()
                    .order_by(Venue.name)
                    .all()
                )
            
                venue_options = [{'venue_id': venue.venue_id, 'name': venue.name} for venue in venues]
            
                # Calculate pagination info
                total_pages = math.ceil(total_records / per_page) if total_records > 0 else 1
                start_index = offset + 1 if total_records > 0 else 0
                end_index = min(offset + per_page, total_records)
            
                # Generate page numbers for pagination
                pages = []
                max_pages_to_show = 5
                half_range = max_pages_to_show // 2
            
                if total_pages <= max_pages_to_show:
                    pages = list(range(1, total_pages + 1))
                else:
                    if page <= half_range:
                        pages = list(range(1, max_pages_to_show + 1))
                    elif page > total_pages - half_range:
                        pages = list(range(total_pages - max_pages_to_show + 1, total_pages + 1))
                    else:
                        pages = list(range(page - half_range, page + half_range + 1))
            
                return {
                    'success': True,
                    'student': student.as_sanitized_dict(),
                    'records': formatted_records,
                    'months': months,
                    'venues': venue_options,
                    'search_query': search_query,
                    'status_filter': status_filter,
                    'month_filter': month_filter,
                    'venue_filter': venue_filter,
                    'pagination': {
                        'current_page': page,
                        'total_pages': total_pages,
                       'total_records': total_records,
                        'start_index': start_index,
                        'end_index': end_index,
                        'pages': pages,
                        'has_prev': page > 1,
                        'has_next': page < total_pages
                    }
                }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'error': f'Error loading attendance history: {str(e)}', 'success': False}

    def get_student_appeals(app, user_id, module_filter='', status_filter='', date_filter=''):
        """Get student appeals with filtering options"""
        try:
            with get_session() as db_session:
                appeal_model = AttendanceAppealModel(db_session)
                class_model = ClassModel(db_session)
                
                # Get all appeals for the student
                try:
                    all_appeals = appeal_model.student_appeals(student_id=user_id)
                except Exception as e:
                    # Fallback if the method fails
                    app.logger.error(f"Error getting appeals: {e}")
                    all_appeals = []
                
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
                        appeal_date = appeal.get("class_date")
                        if appeal_date:
                            if isinstance(appeal_date, date):
                                date_str = appeal_date.strftime("%Y-%m-%d")
                            elif isinstance(appeal_date, str):
                                try:
                                    # Try to parse the string date
                                    parsed_date = datetime.strptime(appeal_date, "%d %b %Y")
                                    date_str = parsed_date.strftime("%Y-%m-%d")
                                except ValueError:
                                    date_str = appeal_date
                            else:
                                date_str = str(appeal_date)
                            
                            if date_str != date_filter:
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
                
                # For SQLAlchemy Enum created with Enum("value1", "value2", ...)
                # The values are stored in the constructor arguments
                # We can access them from the __dict__ or hardcode based on models.py
                status_values = ['pending', 'approved', 'rejected']
                
                return {
                    'success': True,
                    'filters': {
                        'modules': sorted(list(modules)),
                        'statuses': status_values,
                    },
                    'appeals': filtered_appeals,
                    'absent_late': absent_late or []  # Ensure it's always a list
                }
                
        except Exception as e:
            # Return a minimal structure to prevent template errors
            app.logger.error(f"Error loading appeals: {str(e)}")
            return {
                'success': False,
                'filters': {
                    'modules': [],
                    'statuses': ['pending', 'approved', 'rejected'],
                },
                'appeals': [],
                'absent_late': [],
                'error': f'Error loading appeals: {str(e)}'
            }

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
                
                # Check if status is appealable (absent, late, or audit failed)
                if record.status not in ['absent', 'late'] and record.audit_status != 'fail':
                    return {
                        'success': False,
                        'can_appeal': False,
                        'message': 'Only absent, late, or audit-failed records can be appealed'
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
    
    def get_absent_records(user_id):
        """Get all absent records for student"""
        try:
            with get_session() as db_session:
                # Use the new get_attendance_history method with filters
                return StudentControl.get_attendance_history(
                    user_id=user_id,
                    status_filter='absent',
                    search_query='',
                    month_filter='',
                    page=1,
                    per_page=100  # Large number to get all records
                )
                
        except Exception as e:
            return {'error': f'Error loading absent records: {str(e)}', 'success': False}
        
    def get_dashboard_data(user_id):
        """Get all dashboard data for student"""
        try:
            with get_session() as db_session:
                from database.models import FacialData
                
                user_model = UserModel(db_session)
                class_model = ClassModel(db_session)
                semester_model = SemesterModel(db_session)
                attendance_model = AttendanceRecordModel(db_session)
                announcement_model = AnnouncementModel(db_session)
                notification_model = NotificationModel(db_session)
                
                # Get student info
                student = user_model.get_by_id(user_id)
                if not student:
                    return {'error': 'Student not found', 'success': False}
                
                # Check for facial data registration
                facial_data = db_session.query(FacialData).filter(
                    FacialData.user_id == user_id,
                    FacialData.is_active == True
                ).first()
                facial_data_registered = facial_data is not None
                
                # Get current date and time
                current_time = datetime.now()
                current_date = date.today()
                
                # Get current semester - FIXED: Added institution_id parameter
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
                            'attendance_status': attendance_taken.status if attendance_taken else None
                        })
                
                # Get attendance statistics
                term_stats = semester_model.student_dashboard_term_attendance(user_id)
                p = term_stats.get("present", 0)
                a = term_stats.get("absent", 0)
                l = term_stats.get("late", 0)
                e = term_stats.get("excused", 0)
                unmarked_count = term_stats.get(None, 0)  # None status means no record
                
                marked = p + a + l + e
                total = marked + unmarked_count
                
                present_percent = ((p + l + e) / marked * 100) if marked > 0 else 0
                absent_percent = (a / marked * 100) if marked > 0 else 0
                
                # Get unread notifications count
                unread_notifications_count = notification_model.get_unread_count(user_id)
                
                # Get recent announcements for the student's institution
                try:
                    # Get preview announcements (3 items) for dashboard
                    preview_announcements = announcement_model.get_recent_announcements(
                        institution_id=student.institution_id, 
                        limit=3
                    )
                    
                    # Get all announcements (up to 50 items) for the announcements page
                    all_announcements_list = announcement_model.get_recent_announcements(
                        institution_id=student.institution_id, 
                        limit=50
                    )
                    
                    # Format preview announcements
                    formatted_announcements = []
                    for announcement in preview_announcements:
                        # Get the user who created the announcement
                        requested_by = user_model.get_by_id(announcement.requested_by_user_id) if announcement.requested_by_user_id else None
                        
                        formatted_announcements.append({
                            'title': announcement.title,
                            'date': announcement.date_posted.strftime('%b %d, %Y') if announcement.date_posted else 'N/A',
                            'content': announcement.content,
                            'author': requested_by.name if requested_by else 'Unknown'
                        })
                    
                    # Format all announcements for the announcements page
                    formatted_all_announcements = []
                    for announcement in all_announcements_list:
                        requested_by = user_model.get_by_id(announcement.requested_by_user_id) if announcement.requested_by_user_id else None
                        
                        formatted_all_announcements.append({
                            'title': announcement.title,
                            'date': announcement.date_posted.strftime('%b %d, %Y') if announcement.date_posted else 'N/A',
                            'content': announcement.content,
                            'author': requested_by.name if requested_by else 'Unknown',
                            'date_raw': announcement.date_posted.isoformat() if announcement.date_posted else None
                        })
                except Exception as e:
                    # If there's an error getting announcements, log it and return empty list
                    print(f"Error getting announcements for student dashboard: {e}")
                    formatted_announcements = []
                    formatted_all_announcements = []
                
                # Get institution name
                institution_name = 'N/A'
                if student.institution_id:
                    from application.entities2.institution import InstitutionModel
                    institution_model = InstitutionModel(db_session)
                    institution = institution_model.get_by_id(student.institution_id)
                    if institution:
                        institution_name = institution.name
                
                # Format date joined
                date_enrolled = 'N/A'
                if hasattr(student, 'date_joined') and student.date_joined:
                    date_enrolled = student.date_joined.strftime('%b %d, %Y')
                
                return {
                    'success': True,
                    'student': {
                        'name': student.name,
                        'email': student.email,
                        'student_id': f"S{student.user_id:07d}",
                        'institution_id': student.institution_id,
                        'institution_name': institution_name,
                        'age': student.age if hasattr(student, 'age') and student.age else 'N/A',
                        'date_enrolled': date_enrolled
                    },
                    'facial_data_registered': facial_data_registered,
                    'today_classes': today_classes,
                    'announcements': formatted_announcements,  # Preview announcements (3 items)
                    'all_announcements': formatted_all_announcements,  # All announcements for page (up to 50)
                    'statistics': {
                        'overall_attendance': round(present_percent, 1),
                        'present_count': p + l + e,
                        'absent_count': a,
                        'late_count': l,
                        'excused_count': e,
                        'total_classes': total,
                        'present_percent': round(present_percent, 1),
                        'absent_percent': round(absent_percent, 1),
                        'unread_notifications_count': unread_notifications_count
                    },
                    'current_time': current_time.strftime('%I:%M %p'),
                    'current_date': current_date.strftime('%d %B %Y')
                }
                
        except Exception as e:
            return {'error': f'Error loading dashboard data: {str(e)}', 'success': False}
        
    def get_student_courses(user_id):
        """Get all courses a student is enrolled in"""
        try:
            with get_session() as db_session:
                user_model = UserModel(db_session)
                course_model = CourseModel(db_session)
                semester_model = SemesterModel(db_session)
                
                # Get student to get institution_id
                student = user_model.get_by_id(user_id)
                if not student:
                    return []
                
                # Get current semester - FIXED: Added institution_id parameter
                current_semester = semester_model.get_current_semester(student.institution_id)
                
                if not current_semester:
                    return []
                
                # Get courses where student is enrolled in current semester
                courses = (
                    db_session.query(course_model.model)
                    .join(CourseUser, CourseUser.course_id == course_model.model.course_id)
                    .filter(CourseUser.user_id == user_id)
                    .filter(CourseUser.semester_id == current_semester.semester_id)
                    .all()
                )
                
                return [
                    {
                        'course_id': course.course_id,
                        'code': course.code,
                        'name': course.name,
                        'description': course.description,
                        'credits': course.credits
                    }
                    for course in courses
                ]
                
        except Exception as e:
            print(f"Error getting student courses: {e}")
            return []

    def get_student_classes_in_date_range(student_id, start_date, end_date, course_filter=None, class_type_filter=None):
        """Get classes for a student within a date range"""
        try:
            with get_session() as db_session:
                user_model = UserModel(db_session)
                class_model = ClassModel(db_session)
                course_model = CourseModel(db_session)
                venue_model = VenueModel(db_session)
                semester_model = SemesterModel(db_session)
                
                # Get student to get institution_id
                student = user_model.get_by_id(student_id)
                if not student:
                    return []
                
                # Get current semester - FIXED: Added institution_id parameter
                current_semester = semester_model.get_current_semester(student.institution_id)
                
                if not current_semester:
                    return []
                
                # Base query to get classes for student
                classes = (
                    db_session.query(class_model.model)
                    .join(course_model.model, class_model.model.course_id == course_model.model.course_id)
                    .join(CourseUser, CourseUser.course_id == course_model.model.course_id)
                    .filter(CourseUser.user_id == student_id)
                    .filter(CourseUser.semester_id == current_semester.semester_id)
                    .filter(and_(
                        class_model.model.start_time >= start_date,
                        class_model.model.start_time <= end_date
                    ))
                    .order_by(class_model.model.start_time)
                    .all()
                )
                
                # Apply course filter if specified
                if course_filter and course_filter != 'all':
                    classes = [c for c in classes if c.course and c.course.code == course_filter]
                
                # Apply class type filter if specified
                if class_type_filter and class_type_filter != 'all':
                    classes = [c for c in classes if getattr(c, 'class_type', 'Lecture').lower() == class_type_filter.lower()]
                
                # Format classes
                formatted_classes = []
                for class_obj in classes:
                    course = course_model.get_by_id(class_obj.course_id) if class_obj.course_id else None
                    venue = venue_model.get_by_id(class_obj.venue_id) if class_obj.venue_id else None
                    lecturer = user_model.get_by_id(class_obj.lecturer_id) if class_obj.lecturer_id else None
                    
                    # Determine time slot
                    time_slot = 'morning'
                    if class_obj.start_time:
                        hour = class_obj.start_time.hour
                        if hour < 12:
                            time_slot = 'morning'
                        elif hour < 17:
                            time_slot = 'afternoon'
                        else:
                            time_slot = 'evening'
                    
                    formatted_classes.append({
                        'id': class_obj.class_id,
                        'course_id': class_obj.course_id,
                        'course_code': course.code if course else 'N/A',
                        'course_name': course.name if course else 'N/A',
                        'title': course.name if course else 'N/A',
                        'type': getattr(class_obj, 'class_type', 'Lecture'),
                        'start_time': class_obj.start_time,
                        'end_time': class_obj.end_time,
                        'time': f"{class_obj.start_time.strftime('%I:%M %p') if class_obj.start_time else 'N/A'} - {class_obj.end_time.strftime('%I:%M %p') if class_obj.end_time else 'N/A'}",
                        'room': venue.name if venue else 'N/A',
                        'venue_id': class_obj.venue_id,
                        'lecturer': lecturer.name if lecturer else 'N/A',
                        'lecturer_id': class_obj.lecturer_id,
                        'status': class_obj.status,
                        'time_slot': time_slot
                    })
                
                return formatted_classes
                
        except Exception as e:
            print(f"Error getting student classes: {e}")
            return []

    def get_upcoming_classes(student_id, current_date=None, course_filter=None, class_type_filter=None):
        """Get upcoming classes for a student"""
        try:
            with get_session() as db_session:
                user_model = UserModel(db_session)
                class_model = ClassModel(db_session)
                course_model = CourseModel(db_session)
                venue_model = VenueModel(db_session)
                semester_model = SemesterModel(db_session)
                
                if not current_date:
                    current_date = date.today()
                
                # Get student to get institution_id
                student = user_model.get_by_id(student_id)
                if not student:
                    return []
                
                # Get current semester - FIXED: Added institution_id parameter
                current_semester = semester_model.get_current_semester(student.institution_id)
                
                if not current_semester:
                    return []
                
                # Get upcoming classes (from current date onward)
                classes = (
                    db_session.query(class_model.model)
                    .join(course_model.model, class_model.model.course_id == course_model.model.course_id)
                    .join(CourseUser, CourseUser.course_id == course_model.model.course_id)
                    .filter(CourseUser.user_id == student_id)
                    .filter(CourseUser.semester_id == current_semester.semester_id)
                    .filter(and_(
                        class_model.model.start_time >= current_date
                    ))
                    .order_by(class_model.model.start_time)
                    .all()
                )
                
                # Apply course filter if specified
                if course_filter and course_filter != 'all':
                    classes = [c for c in classes if c.course and c.course.code == course_filter]
                
                # Apply class type filter if specified
                if class_type_filter and class_type_filter != 'all':
                    classes = [c for c in classes if getattr(c, 'class_type', 'Lecture').lower() == class_type_filter.lower()]
                
                # Format classes for list view
                formatted_classes = []
                for class_obj in classes:
                    course = course_model.get_by_id(class_obj.course_id) if class_obj.course_id else None
                    venue = venue_model.get_by_id(class_obj.venue_id) if class_obj.venue_id else None
                    lecturer = user_model.get_by_id(class_obj.lecturer_id) if class_obj.lecturer_id else None
                    
                    # Determine time slot
                    time_slot = 'morning'
                    if class_obj.start_time:
                        hour = class_obj.start_time.hour
                        if hour < 12:
                            time_slot = 'morning'
                        elif hour < 17:
                            time_slot = 'afternoon'
                        else:
                            time_slot = 'evening'
                    
                    formatted_classes.append({
                        'id': class_obj.class_id,
                        'course_code': course.code if course else 'N/A',
                        'title': course.name if course else 'N/A',
                        'date': class_obj.start_time.strftime('%B %d, %Y') if class_obj.start_time else 'N/A',
                        'time': f"{class_obj.start_time.strftime('%I:%M %p') if class_obj.start_time else 'N/A'} - {class_obj.end_time.strftime('%I:%M %p') if class_obj.end_time else 'N/A'}",
                        'room': venue.name if venue else 'N/A',
                        'type': getattr(class_obj, 'class_type', 'Lecture'),
                        'lecturer': lecturer.name if lecturer else 'N/A',
                        'time_slot': time_slot
                    })
                
                return formatted_classes
                
        except Exception as e:
            print(f"Error getting upcoming classes: {e}")
            return []

    def get_timetable_data(app, student_id, view_type='monthly', target_date=None):
        """Get timetable data for student based on view type"""
        try:
            with get_session() as db_session:
                user_model = UserModel(db_session)
                
                if not target_date:
                    target_date = date.today()
                
                # Get student to get institution_id
                student = user_model.get_by_id(student_id)
                if not student:
                    return {
                        'success': False,
                        'error': 'Student not found'
                    }
                
                if view_type == 'monthly':
                    # Generate monthly calendar
                    first_day = date(target_date.year, target_date.month, 1)
                    last_day = date(target_date.year, target_date.month, 
                                  (date(target_date.year, target_date.month + 1, 1) - timedelta(days=1)).day)
                    
                    classes = StudentControl.get_student_classes_in_date_range(
                        student_id, first_day, last_day
                    )
                    
                    # Group classes by date
                    classes_by_date = {}
                    for class_data in classes:
                        if class_data.get('start_time'):
                            class_date = class_data['start_time'].date() if isinstance(class_data['start_time'], datetime) else class_data['start_time']
                            if class_date not in classes_by_date:
                                classes_by_date[class_date] = []
                            
                            classes_by_date[class_date].append({
                                'class_id': class_data['id'],
                                'course_code': class_data['course_code'],
                                'course_name': class_data['course_name'],
                                'start_time': class_data['start_time'].strftime('%I:%M %p') if isinstance(class_data['start_time'], datetime) else 'N/A',
                                'end_time': class_data['end_time'].strftime('%I:%M %p') if isinstance(class_data['end_time'], datetime) else 'N/A',
                                'room': class_data['room'],
                                'lecturer': class_data['lecturer'],
                                'time_slot': class_data['time_slot']
                            })
                    
                    return {
                        'success': True,
                        'view_type': 'monthly',
                        'current_month': target_date.strftime('%B'),
                        'current_year': target_date.year,
                        'classes_by_date': classes_by_date
                    }
                    
                elif view_type == 'weekly':
                    # Generate weekly data
                    # Get start of week (Sunday)
                    week_start = target_date - timedelta(days=target_date.weekday() + 1)
                    if week_start.weekday() != 6:  # Not Sunday
                        week_start -= timedelta(days=week_start.weekday() + 1)
                    
                    week_end = week_start + timedelta(days=6)
                    
                    classes = StudentControl.get_student_classes_in_date_range(
                        student_id, week_start, week_end
                    )
                    
                    # Group by day of week
                    week_days = {}
                    for i in range(7):
                        current_date = week_start + timedelta(days=i)
                        week_days[current_date] = []
                    
                    for class_data in classes:
                        if class_data.get('start_time'):
                            class_date = class_data['start_time'].date() if isinstance(class_data['start_time'], datetime) else class_data['start_time']
                            if class_date in week_days:
                                week_days[class_date].append({
                                    'class_id': class_data['id'],
                                    'course_code': class_data['course_code'],
                                    'course_name': class_data['course_name'],
                                    'title': class_data['course_name'],
                                    'start_time': class_data['start_time'],
                                    'end_time': class_data['end_time'],
                                    'time': class_data['time'],
                                    'room': class_data['room'],
                                    'lecturer': class_data['lecturer'],
                                    'time_slot': class_data['time_slot']
                                })
                    
                    # Convert to list format
                    formatted_week_days = []
                    for day_date, day_classes in sorted(week_days.items()):
                        formatted_week_days.append({
                            'date': day_date,
                            'day_name': day_date.strftime('%A'),
                            'day_short': day_date.strftime('%a'),
                            'day_number': day_date.day,
                            'classes': sorted(
                                day_classes, 
                                key=lambda x: x['start_time'] if isinstance(x['start_time'], datetime) else datetime.min
                            )
                        })
                    
                    return {
                        'success': True,
                        'view_type': 'weekly',
                        'week_start': week_start,
                        'week_end': week_end,
                        'week_days': formatted_week_days
                    }
                    
                else:  # list view
                    # Get all upcoming classes
                    classes = StudentControl.get_upcoming_classes(student_id, target_date)
                    
                    return {
                        'success': True,
                        'view_type': 'list',
                        'upcoming_classes': classes
                    }
                
        except Exception as e:
            app.logger.error(f"Error getting student timetable data: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        
    def get_attendance_statistics(user_id):
        """Get comprehensive attendance statistics for student"""
        try:
            with get_session() as db_session:
                user_model = UserModel(db_session)
                semester_model = SemesterModel(db_session)
                class_model = ClassModel(db_session)
                
                # Get student info
                student = user_model.get_by_id(user_id)
                if not student:
                    return {'error': 'Student not found', 'success': False}
                
                # Get current semester
                current_semester = semester_model.get_current_semester(student.institution_id)
                if not current_semester:
                    return {
                        'success': False,
                        'error': 'No active semester found'
                    }
                
                # Get attendance statistics
                term_stats = semester_model.student_dashboard_term_attendance(user_id)
                p = term_stats.get("present", 0)
                a = term_stats.get("absent", 0)
                l = term_stats.get("late", 0)
                e = term_stats.get("excused", 0)
                unmarked_count = term_stats.get(None, 0)  # None status means no record
                
                marked = p + a + l + e
                total = marked + unmarked_count
                
                # Calculate percentages
                present_percent = ((p + l + e) / marked * 100) if marked > 0 else 0
                absent_percent = (a / marked * 100) if marked > 0 else 0
                
                # Get cutoff requirement from institution or use default
                required_percent = 90  # Default requirement
                
                # Determine status
                is_meeting_requirement = present_percent >= required_percent
                
                return {
                    'success': True,
                    'statistics': {
                        'overall_percent': round(present_percent, 1),
                        'present_count': p + l + e,
                        'absent_count': a,
                        'late_count': l,
                        'excused_count': e,
                        'marked_count': marked,
                        'unmarked_count': unmarked_count,
                        'total_count': total,
                        'required_percent': required_percent,
                        'is_meeting_requirement': is_meeting_requirement,
                        'present_percent': round(present_percent, 1),
                        'absent_percent': round(absent_percent, 1)
                    },
                    'term_info': {
                        'semester_name': current_semester.name,
                        'semester_id': current_semester.semester_id
                    },
                    'student_info': {
                        'student_id': student.user_id,
                        'name': student.name
                    }
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Error getting attendance statistics: {str(e)}'
            }
    
    def get_class_details(user_id, class_id):
        """Get detailed class information for a student"""
        try:
            with get_session() as db_session:
                class_model = ClassModel(db_session)
                course_model = CourseModel(db_session)
                user_model = UserModel(db_session)
                venue_model = VenueModel(db_session)
                attendance_model = AttendanceRecordModel(db_session)
                appeal_model = AttendanceAppealModel(db_session)
                semester_model = SemesterModel(db_session)
                
                # Get class details
                class_obj = class_model.get_by_id(class_id)
                if not class_obj:
                    return {'success': False, 'error': 'Class not found'}
                
                # Get student info
                student = user_model.get_by_id(user_id)
                if not student:
                    return {'success': False, 'error': 'Student not found'}
                
                # Verify student is enrolled in this class's course
                current_semester = semester_model.get_current_semester(student.institution_id)
                if not current_semester:
                    return {'success': False, 'error': 'No active semester found'}
                
                # Check if student is enrolled in the course
                is_enrolled = (
                    db_session.query(CourseUser)
                    .filter(CourseUser.user_id == user_id)
                    .filter(CourseUser.course_id == class_obj.course_id)
                    .filter(CourseUser.semester_id == current_semester.semester_id)
                    .first()
                )
                
                if not is_enrolled:
                    return {'success': False, 'error': 'You are not enrolled in this course'}
                
                # Get related data
                course = course_model.get_by_id(class_obj.course_id) if class_obj.course_id else None
                venue = venue_model.get_by_id(class_obj.venue_id) if class_obj.venue_id else None
                lecturer = user_model.get_by_id(class_obj.lecturer_id) if class_obj.lecturer_id else None
                
                # Get attendance record for this student
                attendance_record = (
                    db_session.query(AttendanceRecord)
                    .filter(AttendanceRecord.class_id == class_id)
                    .filter(AttendanceRecord.student_id == user_id)
                    .first()
                )
                
                # Check if appeal exists for this record
                appeal_exists = False
                appeal_status = None
                if attendance_record:
                    appeal = appeal_model.get_one(attendance_id=attendance_record.attendance_id)
                    if appeal:
                        appeal_exists = True
                        appeal_status = appeal.status
                
                # Determine class status
                now = datetime.now()
                class_status = 'upcoming'
                if class_obj.start_time and class_obj.end_time:
                    if now > class_obj.end_time:
                        class_status = 'completed'
                    elif class_obj.start_time <= now <= class_obj.end_time:
                        class_status = 'in_progress'
                
                # Determine if student can check in
                can_check_in = False
                if class_status in ['upcoming', 'in_progress']:
                    # Can check in if class hasn't ended and attendance not taken
                    if not attendance_record:
                        # Check if within check-in window (e.g., 15 minutes before start to end time)
                        if class_obj.start_time:
                            check_in_start = class_obj.start_time - timedelta(minutes=15)
                            check_in_end = class_obj.end_time if class_obj.end_time else class_obj.start_time + timedelta(hours=2)
                            if check_in_start <= now <= check_in_end:
                                can_check_in = True
                
                # Determine if student can appeal
                can_appeal = False
                if attendance_record and attendance_record.status in ['absent', 'late']:
                    if not appeal_exists:
                        # Can appeal if within 7 days of class
                        days_since_class = (now - class_obj.start_time).days if class_obj.start_time else 999
                        if days_since_class <= 7:
                            can_appeal = True
                
                # Format class details
                formatted_class = {
                    'class_id': class_obj.class_id,
                    'course_id': class_obj.course_id,
                    'course_code': course.code if course else 'N/A',
                    'course_name': course.name if course else 'N/A',
                    'section': getattr(class_obj, 'section', '') or 'N/A',
                    'room': venue.name if venue else 'N/A',
                    'venue_id': class_obj.venue_id,
                    'venue_capacity': venue.capacity if venue else 0,
                    'start_time': class_obj.start_time,
                    'end_time': class_obj.end_time,
                    'start_datetime': class_obj.start_time.strftime('%B %d, %Y %I:%M %p') if class_obj.start_time else 'N/A',
                    'end_datetime': class_obj.end_time.strftime('%B %d, %Y %I:%M %p') if class_obj.end_time else 'N/A',
                    'start_time_formatted': class_obj.start_time.strftime('%I:%M %p') if class_obj.start_time else 'N/A',
                    'end_time_formatted': class_obj.end_time.strftime('%I:%M %p') if class_obj.end_time else 'N/A',
                    'date_formatted': class_obj.start_time.strftime('%B %d, %Y') if class_obj.start_time else 'N/A',
                    'lecturer_id': class_obj.lecturer_id,
                    'lecturer_name': lecturer.name if lecturer else 'N/A',
                    'lecturer_email': lecturer.email if lecturer else 'N/A',
                    'status': class_status,
                    'class_type': getattr(class_obj, 'class_type', 'Lecture'),
                    'class_status': class_obj.status
                }
                
                # Format attendance info
                attendance_info = {
                    'attendance_taken': attendance_record is not None,
                    'attendance_status': attendance_record.status if attendance_record else None,
                    'attendance_id': attendance_record.attendance_id if attendance_record else None,
                    'recorded_at': attendance_record.recorded_at.strftime('%B %d, %Y %I:%M %p') if attendance_record and attendance_record.recorded_at else None,
                    'notes': attendance_record.notes if attendance_record else None,
                    'can_appeal': can_appeal,
                    'appeal_exists': appeal_exists,
                    'appeal_status': appeal_status
                }
                
                return {
                    'success': True,
                    'class': formatted_class,
                    'attendance': attendance_info,
                    'can_check_in': can_check_in,
                    'student': {
                        'name': student.name,
                        'student_id': f"S{student.user_id:07d}"
                    }
                }
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': f'Error loading class details: {str(e)}'
            }