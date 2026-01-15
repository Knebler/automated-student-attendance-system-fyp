from flask import Blueprint, render_template, request, jsonify, session, current_app, flash, redirect, url_for
from application.controls.auth_control import AuthControl, requires_roles
from application.controls.attendance_control import AttendanceControl
from application.entities2.classes import ClassModel
from application.entities2.course import CourseModel
from application.entities2.user import UserModel
from application.entities2.attendance_record import AttendanceRecordModel
from application.controls.announcement_control import AnnouncementControl
from application.controls.lecturer_control import LecturerControl
from datetime import datetime, date, timedelta
import calendar
from database.base import get_session

lecturer_bp = Blueprint('institution_lecturer', __name__)

def get_lecturer_id():
    """Get lecturer ID from session"""
    return session.get('user_id')

def get_institution_id():
    """Get institution ID from session"""
    return session.get('institution_id')

@lecturer_bp.route('/dashboard')
@requires_roles('lecturer')
def lecturer_dashboard():
    """Lecturer dashboard with today's classes and announcements"""
    try:
        lecturer_id = get_lecturer_id()
        institution_id = get_institution_id()
        
        # Get all dashboard data including announcements
        result = LecturerControl.get_dashboard_data(
            current_app,
            lecturer_id,
            institution_id
        )
        
        if not result.get('success'):
            flash('Error loading dashboard data', 'danger')
            return render_template('institution/lecturer/lecturer_dashboard.html')
        
        # Prepare context
        context = {
            'lecturer_name': result.get('lecturer_info', {}).get('name', 'Lecturer'),
            'today_classes': result.get('today_classes', []),
            'announcements': result.get('announcements', []),  # Announcements from LecturerControl
            'current_time': datetime.now().strftime('%I:%M %p'),
            'current_date': date.today().strftime('%d %B %Y'),
            'statistics': result.get('statistics', {})
        }
        
        return render_template('institution/lecturer/lecturer_dashboard.html', **context)
        
    except Exception as e:
        current_app.logger.error(f"Error loading lecturer dashboard: {e}")
        flash('Error loading dashboard', 'danger')
        return render_template('institution/lecturer/lecturer_dashboard.html')

@lecturer_bp.route('/manage_attendance')
@requires_roles('lecturer')
def manage_attendance():
    """Render the lecturer attendance-management page for a specific class"""
    class_id = request.args.get('class_id')
    
    if not class_id:
        flash('Class ID is required', 'warning')
        return redirect(url_for('institution_lecturer.lecturer_dashboard'))
    
    try:
        with get_session() as db_session:
            class_model = ClassModel(db_session)
            user_model = UserModel(db_session)
            
            # Get class details
            class_obj = class_model.get_by_id(class_id)
            if not class_obj:
                flash('Class not found', 'danger')
                return redirect(url_for('institution_lecturer.lecturer_dashboard'))
            
            # Check if lecturer is authorized for this class
            if class_obj.lecturer_id != get_lecturer_id():
                flash('You are not authorized for this class', 'danger')
                return redirect(url_for('institution_lecturer.lecturer_dashboard'))
            
            # Get course details
            course_model = CourseModel(db_session)
            course = course_model.get_by_id(class_obj.course_id) if class_obj.course_id else None
            
            # Get enrolled students for this class
            students = class_model.get_enrolled_students(class_id)
            
            # Get existing attendance records for this class
            attendance_model = AttendanceRecordModel(db_session)
            attendance_records = attendance_model.get_all(class_id=class_id)
            
            # Create attendance status dictionary
            attendance_status = {record.student_id: record.status for record in attendance_records}
            
            context = {
                'class': {
                    'id': class_obj.class_id,
                    'course_code': course.code if course else 'N/A',
                    'section': f"{getattr(class_obj, 'section', '') or 'N/A'}",
                    'date': class_obj.start_time.strftime('%B %d, %Y') if class_obj.start_time else 'N/A',
                    'time': f"{class_obj.start_time.strftime('%I:%M %p') if class_obj.start_time else 'N/A'} - {class_obj.end_time.strftime('%I:%M %p') if class_obj.end_time else 'N/A'}",
                    'room': class_obj.venue.name if hasattr(class_obj, 'venue') and class_obj.venue else 'N/A',
                },
                'students': [
                    {
                        'id': student.user_id,
                        'id_number': getattr(student, 'student_id', ''),
                        'name': student.name,
                        'email': student.email,
                        'initials': ''.join([name[0] for name in student.name.split()[:2]]).upper(),
                        'photo_url': getattr(student, 'photo_url', ''),
                        'attendance_status': attendance_status.get(student.user_id, 'pending')
                    }
                    for student in students
                ],
                'total_students': len(students)
            }
        
        return render_template('institution/lecturer/lecturer_attendance_management.html', **context)
        
    except Exception as e:
        current_app.logger.error(f"Error loading attendance management: {e}")
        flash('Error loading attendance management page', 'danger')
        return redirect(url_for('institution_lecturer.lecturer_dashboard'))

@lecturer_bp.route('/manage_attendance/statistics')
@requires_roles('lecturer')
def attendance_statistics():
    """Render the lecturer attendance statistics page"""
    course_id = request.args.get('course_id')
    time_period = request.args.get('period', 'month')  # week, month, semester
    tutorial_group = request.args.get('group', 'T01')
    
    try:
        with get_session() as db_session:
            class_model = ClassModel(db_session)
            course_model = CourseModel(db_session)
            user_model = UserModel(db_session)
            attendance_model = AttendanceRecordModel(db_session)
            
            lecturer_id = get_lecturer_id()
            
            # Get lecturer's courses
            courses = course_model.get_by_user_id(lecturer_id)
            
            # Get selected course or default to first course
            selected_course = None
            if course_id:
                selected_course = course_model.get_by_id(course_id)
            elif courses:
                selected_course = courses[0]
            
            # Get statistics data
            statistics_data = {}
            if selected_course:
                # Calculate date range based on time period
                end_date = date.today()
                if time_period == 'week':
                    start_date = end_date - timedelta(days=7)
                elif time_period == 'semester':
                    # Assuming semester is ~4 months
                    start_date = end_date - timedelta(days=120)
                else:  # month
                    start_date = end_date - timedelta(days=30)
                
                # Get attendance statistics for the course
                statistics_data = class_model.get_attendance_statistics(
                    selected_course.course_id, 
                    lecturer_id, 
                    start_date, 
                    end_date
                )
            
            context = {
                'courses': [
                    {
                        'course_id': course.course_id,
                        'code': course.code,
                        'name': course.name
                    }
                    for course in courses
                ],
                'selected_course': {
                    'course_id': selected_course.course_id if selected_course else None,
                    'code': selected_course.code if selected_course else 'N/A',
                    'name': selected_course.name if selected_course else 'N/A'
                },
                'time_period': time_period,
                'tutorial_group': tutorial_group,
                'statistics': statistics_data,
                'current_time': datetime.now().strftime('%I:%M %p'),
                'current_date': date.today().strftime('%d %B %Y')
            }
        
        return render_template('institution/lecturer/lecturer_attendance_management_statistics.html', **context)
        
    except Exception as e:
        current_app.logger.error(f"Error loading attendance statistics: {e}")
        flash('Error loading attendance statistics', 'danger')
        return render_template('institution/lecturer/lecturer_attendance_management_statistics.html')

@lecturer_bp.route('/manage_classes')
@requires_roles('lecturer')
def manage_classes():
    """Render the lecturer class-management page"""
    course_id = request.args.get('course_id')
    
    try:
        with get_session() as db_session:
            lecturer_id = get_lecturer_id()
            course_model = CourseModel(db_session)
            class_model = ClassModel(db_session)
            
            # Get lecturer's courses
            courses = course_model.get_by_user_id(lecturer_id)
            
            # Get classes for selected course or all courses
            classes = []
            if course_id:
                classes = class_model.get_classes_for_course(course_id, lecturer_id)
            elif courses:
                # Get classes for all lecturer's courses
                for course in courses:
                    course_classes = class_model.get_classes_for_course(course.course_id, lecturer_id)
                    classes.extend(course_classes)
            
            context = {
                'courses': [
                    {
                        'course_id': course.course_id,
                        'code': course.code,
                        'name': course.name,
                        'is_active': course.is_active
                    }
                    for course in courses
                ],
                'classes': [
                    {
                        'class_id': class_obj.class_id,
                        'course_code': next((c.code for c in courses if c.course_id == class_obj.course_id), 'N/A'),
                        'course_name': next((c.name for c in courses if c.course_id == class_obj.course_id), 'N/A'),
                        'start_time': class_obj.start_time.strftime('%I:%M %p') if class_obj.start_time else 'N/A',
                        'end_time': class_obj.end_time.strftime('%I:%M %p') if class_obj.end_time else 'N/A',
                        'date': class_obj.start_time.strftime('%B %d, %Y') if class_obj.start_time else 'N/A',
                        'venue': class_obj.venue.name if hasattr(class_obj, 'venue') and class_obj.venue else 'N/A',
                        'section': getattr(class_obj, 'section', ''),
                        'enrolled_count': class_model.get_enrolled_count(class_obj.class_id)
                    }
                    for class_obj in classes
                ],
                'selected_course_id': course_id
            }
        
        return render_template('institution/lecturer/lecturer_class_management.html', **context)
        
    except Exception as e:
        current_app.logger.error(f"Error loading class management: {e}")
        flash('Error loading class management page', 'danger')
        return render_template('institution/lecturer/lecturer_class_management.html')

@lecturer_bp.route('/timetable')
@requires_roles('lecturer')
def timetable():
    """Render the lecturer timetable page with multiple views"""
    view_type = request.args.get('view', 'monthly')  # monthly, weekly, list
    selected_date = request.args.get('date')
    course_filter = request.args.get('course')
    class_type_filter = request.args.get('type')
    
    try:
        with get_session() as db_session:
            lecturer_id = get_lecturer_id()
            class_model = ClassModel(db_session)
            course_model = CourseModel(db_session)
            
            # Parse date or use today
            if selected_date:
                current_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            else:
                current_date = date.today()
            
            # Get lecturer's courses for filter dropdown
            courses = course_model.get_by_user_id(lecturer_id)
            
            # Get classes based on view type
            if view_type == 'monthly':
                # Get calendar for the month
                calendar_data = generate_monthly_calendar(current_date, lecturer_id, course_filter, class_type_filter)
                context = {
                    'view_type': 'monthly',
                    'current_month': current_date.strftime('%B'),
                    'current_year': current_date.year,
                    'calendar_weeks': calendar_data,
                    'today': date.today(),
                    'courses': [
                        {'code': course.code, 'name': course.name}
                        for course in courses
                    ]
                }
                
            elif view_type == 'weekly':
                # Get week data
                week_data = generate_weekly_data(current_date, lecturer_id, course_filter, class_type_filter)
                context = {
                    'view_type': 'weekly',
                    'week_start': week_data['week_start'].strftime('%b %d'),
                    'week_end': week_data['week_end'].strftime('%b %d'),
                    'week_days': week_data['days'],
                    'courses': [
                        {'code': course.code, 'name': course.name}
                        for course in courses
                    ]
                }
                
            else:  # list view
                # Get upcoming classes
                upcoming_classes = class_model.get_upcoming_classes_for_lecturer(lecturer_id, current_date, course_filter, class_type_filter)
                context = {
                    'view_type': 'list',
                    'upcoming_classes': [
                        {
                            'id': class_obj.class_id,
                            'course_code': next((c.code for c in courses if c.course_id == class_obj.course_id), 'N/A'),
                            'title': next((c.name for c in courses if c.course_id == class_obj.course_id), 'N/A'),
                            'date': class_obj.start_time.strftime('%B %d, %Y') if class_obj.start_time else 'N/A',
                            'time': f"{class_obj.start_time.strftime('%I:%M %p') if class_obj.start_time else 'N/A'} - {class_obj.end_time.strftime('%I:%M %p') if class_obj.end_time else 'N/A'}",
                            'room': class_obj.venue.name if hasattr(class_obj, 'venue') and class_obj.venue else 'N/A',
                            'type': getattr(class_obj, 'class_type', 'Lecture'),
                            'time_slot': get_time_slot(class_obj.start_time) if class_obj.start_time else 'morning'
                        }
                        for class_obj in upcoming_classes
                    ],
                    'courses': [
                        {'code': course.code, 'name': course.name}
                        for course in courses
                    ]
                }
        
        return render_template('institution/lecturer/lecturer_timetable.html', **context)
        
    except Exception as e:
        current_app.logger.error(f"Error loading timetable: {e}")
        flash('Error loading timetable', 'danger')
        return render_template('institution/lecturer/lecturer_timetable.html')

@lecturer_bp.route('/api/attendance/mark', methods=['POST'])
@requires_roles('lecturer')
def mark_attendance_api():
    """API endpoint to mark attendance for a student"""
    try:
        data = request.get_json()
        class_id = data.get('class_id')
        student_id = data.get('student_id')
        status = data.get('status', 'present')
        notes = data.get('notes')
        
        if not class_id or not student_id:
            return jsonify({'success': False, 'error': 'Class ID and Student ID are required'}), 400
        
        # Verify lecturer has access to this class
        with get_session() as db_session:
            class_model = ClassModel(db_session)
            class_obj = class_model.get_by_id(class_id)
            
            if not class_obj or class_obj.lecturer_id != get_lecturer_id():
                return jsonify({'success': False, 'error': 'Unauthorized access'}), 403
            
            # Mark attendance
            result = AttendanceControl.mark_attendance(
                current_app,
                class_id,
                student_id,
                status,
                'lecturer',
                get_lecturer_id(),
                notes
            )
            
            return jsonify(result)
            
    except Exception as e:
        current_app.logger.error(f"Error marking attendance: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@lecturer_bp.route('/api/attendance/batch', methods=['POST'])
@requires_roles('lecturer')
def batch_mark_attendance():
    """API endpoint to mark attendance for multiple students at once"""
    try:
        data = request.get_json()
        class_id = data.get('class_id')
        attendance_data = data.get('attendance', [])
        
        if not class_id:
            return jsonify({'success': False, 'error': 'Class ID is required'}), 400
        
        # Verify lecturer has access to this class
        with get_session() as db_session:
            class_model = ClassModel(db_session)
            class_obj = class_model.get_by_id(class_id)
            
            if not class_obj or class_obj.lecturer_id != get_lecturer_id():
                return jsonify({'success': False, 'error': 'Unauthorized access'}), 403
            
            results = []
            for item in attendance_data:
                student_id = item.get('student_id')
                status = item.get('status', 'present')
                notes = item.get('notes')
                
                if student_id:
                    result = AttendanceControl.mark_attendance(
                        current_app,
                        class_id,
                        student_id,
                        status,
                        'lecturer',
                        get_lecturer_id(),
                        notes
                    )
                    results.append(result)
            
            return jsonify({
                'success': True,
                'message': f'Attendance marked for {len(results)} students',
                'results': results
            })
            
    except Exception as e:
        current_app.logger.error(f"Error in batch attendance: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@lecturer_bp.route('/api/attendance/<int:class_id>')
@requires_roles('lecturer')
def get_class_attendance_api(class_id):
    """API endpoint to get attendance for a specific class"""
    try:
        # Verify lecturer has access to this class
        with get_session() as db_session:
            class_model = ClassModel(db_session)
            class_obj = class_model.get_by_id(class_id)
            
            if not class_obj or class_obj.lecturer_id != get_lecturer_id():
                return jsonify({'success': False, 'error': 'Unauthorized access'}), 403
            
            result = AttendanceControl.get_class_attendance(current_app, class_id)
            return jsonify(result)
            
    except Exception as e:
        current_app.logger.error(f"Error getting class attendance: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@lecturer_bp.route('/api/attendance/statistics')
@requires_roles('lecturer')
def get_attendance_statistics_api():
    """API endpoint to get attendance statistics"""
    try:
        course_id = request.args.get('course_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date', date.today().isoformat())
        
        if not course_id:
            return jsonify({'success': False, 'error': 'Course ID is required'}), 400
        
        # Parse dates
        try:
            if start_date:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            else:
                # Default to 30 days ago
                start_date_obj = date.today() - timedelta(days=30)
            
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        with get_session() as db_session:
            class_model = ClassModel(db_session)
            
            # Get statistics
            statistics = class_model.get_attendance_statistics(
                course_id,
                get_lecturer_id(),
                start_date_obj,
                end_date_obj
            )
            
            return jsonify({
                'success': True,
                'statistics': statistics,
                'date_range': {
                    'start_date': start_date_obj.isoformat(),
                    'end_date': end_date_obj.isoformat()
                }
            })
            
    except Exception as e:
        current_app.logger.error(f"Error getting attendance statistics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Helper functions
def generate_monthly_calendar(target_date, lecturer_id, course_filter=None, class_type_filter=None):
    """Generate monthly calendar data with classes"""
    with get_session() as db_session:
        class_model = ClassModel(db_session)
        
        # Get first day of month and last day of month
        first_day = date(target_date.year, target_date.month, 1)
        last_day = date(target_date.year, target_date.month, 
                       calendar.monthrange(target_date.year, target_date.month)[1])
        
        # Get classes for this month
        classes = class_model.get_classes_for_lecturer_in_date_range(
            lecturer_id, first_day, last_day, course_filter, class_type_filter
        )
        
        # Group classes by date
        classes_by_date = {}
        for class_obj in classes:
            if class_obj.start_time:
                class_date = class_obj.start_time.date()
                if class_date not in classes_by_date:
                    classes_by_date[class_date] = []
                classes_by_date[class_date].append(class_obj)
        
        # Generate calendar grid
        calendar_data = []
        
        # Find the first Sunday on or before the first day of month
        current_day = first_day
        while current_day.weekday() != 6:  # 6 = Sunday
            current_day -= timedelta(days=1)
        
        # Generate 6 weeks (42 days) to cover the month
        for week in range(6):
            week_days = []
            for day in range(7):
                day_classes = classes_by_date.get(current_day, [])
                
                week_days.append({
                    'date': current_day,
                    'day': current_day.day,
                    'in_month': current_day.month == target_date.month,
                    'classes': [
                        {
                            'id': class_obj.class_id,
                            'course_code': getattr(class_obj.course, 'code', 'N/A') if hasattr(class_obj, 'course') else 'N/A',
                            'type': getattr(class_obj, 'class_type', 'Lecture'),
                            'time': f"{class_obj.start_time.strftime('%I:%M %p') if class_obj.start_time else 'N/A'}",
                            'room': class_obj.venue.name if hasattr(class_obj, 'venue') and class_obj.venue else 'N/A',
                            'time_slot': get_time_slot(class_obj.start_time) if class_obj.start_time else 'morning'
                        }
                        for class_obj in day_classes
                    ]
                })
                current_day += timedelta(days=1)
            
            calendar_data.append(week_days)
        
        return calendar_data

def generate_weekly_data(target_date, lecturer_id, course_filter=None, class_type_filter=None):
    """Generate weekly calendar data"""
    with get_session() as db_session:
        class_model = ClassModel(db_session)
        
        # Get start of week (Sunday)
        week_start = target_date - timedelta(days=target_date.weekday() + 1)
        if week_start.weekday() != 6:  # Not Sunday
            week_start -= timedelta(days=week_start.weekday() + 1)
        
        week_end = week_start + timedelta(days=6)
        
        # Get classes for this week
        classes = class_model.get_classes_for_lecturer_in_date_range(
            lecturer_id, week_start, week_end, course_filter, class_type_filter
        )
        
        # Group classes by date
        classes_by_date = {}
        for class_obj in classes:
            if class_obj.start_time:
                class_date = class_obj.start_time.date()
                if class_date not in classes_by_date:
                    classes_by_date[class_date] = []
                classes_by_date[class_date].append(class_obj)
        
        # Generate week days data
        week_days = []
        for i in range(7):
            current_date = week_start + timedelta(days=i)
            day_classes = classes_by_date.get(current_date, [])
            
            week_days.append({
                'name': current_date.strftime('%a'),
                'date': current_date.day,
                'classes': [
                    {
                        'id': class_obj.class_id,
                        'course_code': getattr(class_obj.course, 'code', 'N/A') if hasattr(class_obj, 'course') else 'N/A',
                        'title': getattr(class_obj.course, 'name', 'N/A') if hasattr(class_obj, 'course') else 'N/A',
                        'type': getattr(class_obj, 'class_type', 'Lecture'),
                        'time': f"{class_obj.start_time.strftime('%I:%M %p') if class_obj.start_time else 'N/A'} - {class_obj.end_time.strftime('%I:%M %p') if class_obj.end_time else 'N/A'}",
                        'room': class_obj.venue.name if hasattr(class_obj, 'venue') and class_obj.venue else 'N/A',
                        'time_slot': get_time_slot(class_obj.start_time) if class_obj.start_time else 'morning'
                    }
                    for class_obj in day_classes
                ]
            })
        
        return {
            'week_start': week_start,
            'week_end': week_end,
            'days': week_days
        }

def get_time_slot(datetime_obj):
    """Determine time slot based on hour"""
    if not datetime_obj:
        return 'morning'
    
    hour = datetime_obj.hour
    if hour < 12:
        return 'morning'
    elif hour < 17:
        return 'afternoon'
    else:
        return 'evening'