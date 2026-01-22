from flask import Blueprint, render_template, request, jsonify, session, current_app, flash, redirect, url_for
from application.controls.auth_control import AuthControl, requires_roles
from application.controls.attendance_control import AttendanceControl
from application.controls.class_control import ClassControl
from application.controls.course_control import CourseControl
from application.entities2.classes import ClassModel
from application.entities2.course import CourseModel
from application.entities2.user import UserModel
from application.entities2.attendance_record import AttendanceRecordModel
from application.entities2.venue import VenueModel
from application.controls.announcement_control import AnnouncementControl
from application.controls.lecturer_control import LecturerControl
from datetime import datetime, date, timedelta
import calendar
from database.base import get_session
from database.models import AttendanceRecord, Venue

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
            'announcements': result.get('announcements', []),  # Preview announcements (2 items)
            'all_announcements': result.get('all_announcements', []),  # All announcements for modal (up to 50)
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
    """Render the lecturer attendance-management page"""
    class_id = request.args.get('class_id')
    if not class_id:
        flash('Class ID is required', 'warning')
        return redirect(url_for('institution_lecturer.manage_classes'))
    try:
        class_id = int(class_id)
    except ValueError:
        flash('Invalid class ID', 'danger')
        return redirect(url_for('institution_lecturer.manage_classes'))
    
    user_id = session.get('user_id')
    class_result = ClassControl.get_class_by_id(class_id)
    if not class_result['success']:
        flash(class_result.get('error', 'Class not found'), 'danger')
        return redirect(url_for('institution_lecturer.manage_classes'))
    class_data = class_result['class']

    course_id = class_data['course_id']
    course_result = CourseControl.get_course_by_id(course_id)
    if not course_result['success']:
        flash(course_result.get('error', 'Course not found'), 'danger')
        return redirect(url_for('institution_lecturer.manage_classes'))
    course = course_result['course']
    
    # Step 3: Get all course_users who are students
    students_result = CourseControl.get_students_by_course_id(course_id)
    if not students_result['success']:
        flash(students_result.get('error', 'Error retrieving students'), 'warning')
        students_list = []
    else:
        students_list = students_result['students']
    
    # Process attendance records
    with get_session() as db_session:
        
        # Step 4 & 5: Check if attendance records exist, create if not
        attendance_records_created = 0
        students_data = []
        
        for student_info in students_list:
            student_id = student_info['user_id']
            
            # Check if attendance record exists
            existing_record = (
                db_session.query(AttendanceRecord)
                .filter(AttendanceRecord.class_id == class_id)
                .filter(AttendanceRecord.student_id == student_id)
                .first()
            )
            
            if not existing_record:
                # Use AttendanceControl to create attendance record
                result = AttendanceControl.mark_attendance(
                    current_app,
                    class_id=class_id,
                    student_id=student_id,
                    status='unmarked',
                    marked_by='system',
                    lecturer_id=user_id,
                    notes=None
                )
                
                if result['success']:
                    attendance_records_created += 1
                else:
                    # Log error but continue processing other students
                    current_app.logger.warning(f"Failed to create attendance for student {student_id}: {result.get('error')}")
            
            # Prepare student data for template
            student_record = (
                db_session.query(AttendanceRecord)
                .filter(AttendanceRecord.class_id == class_id)
                .filter(AttendanceRecord.student_id == student_id)
                .first()
            )
            
            students_data.append(
                {
                    'id': student_id,
                    'name': student_info['name'],
                    'email': student_info.get('email', ''),
                    'id_number': student_info.get('id_number', str(student_id)),
                    'status': student_record.status if student_record else 'pending',
                    'photo_url': None,
                    'recorded_at': student_record.recorded_at.strftime('%d %B %Y %I:%M %p') if student_record else None,
                    'notes': student_record.notes if student_record else None,
                }
            )
   
        # Get attendance statistics
        total_students = len(students_data)
        present_count = sum(1 for s in students_data if s['status'] == 'present')
        absent_count = sum(1 for s in students_data if s['status'] == 'absent')
        late_count = sum(1 for s in students_data if s['status'] == 'late')
        pending_count = sum(1 for s in students_data if s['status'] == 'pending')
        
        # Get venue information
        venue = db_session.query(Venue).filter(Venue.venue_id == class_data['venue_id']).first()
        venue_name = venue.name if venue else 'Room TBD'
        
        # # Format class data for template
        class_info = {
            'id': class_data['class_id'],
            'course_code': course.get('code', 'N/A') if course else 'N/A',
            'section': 'A',  # Default section - adjust if you have section data
            'date': class_data['start_time'].strftime('%B %d, %Y'),
            'room': venue_name,
            'time': class_data['start_time'].strftime('%I:%M %p') + ' - ' + class_data['end_time'].strftime('%I:%M %p'),
        }

    context = {
        'user': {
            'user_id': user_id,
            'user_type': session.get('role'),
            'name': session.get('name', 'Lecturer')
        },
        'class': class_info,
        'students': students_data,
        'total_students': total_students,
        'stats': {
            'total_students': total_students,
            'present_students': present_count,
            'absent_students': absent_count,
            'late_students': late_count,
            'pending_students': pending_count
        }
    }
    
    return render_template('institution/lecturer/lecturer_attendance_management.html',
                           **context)

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
            statistics_data = {
                'attendance_trend': [],
                'trend_labels': [],
                'distribution': {'excellent': 0, 'good': 0, 'average': 0, 'bad': 0},
                'total_classes': 0,
                'total_attendance': 0,
                'total_students': 0
            }
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
            
            # Format statistics data for template
            attendance_trend = statistics_data.get('attendance_trend', [])
            trend_labels = statistics_data.get('trend_labels', [])
            distribution = statistics_data.get('distribution', {'excellent': 0, 'good': 0, 'average': 0, 'bad': 0})
            
            # Ensure we have at least 5 data points for the chart
            while len(attendance_trend) < 5:
                attendance_trend.insert(0, 0)
                if trend_labels:
                    prev_month = (datetime.now().month - len(attendance_trend)) % 12
                    if prev_month == 0:
                        prev_month = 12
                    trend_labels.insert(0, calendar.month_abbr[prev_month])
                else:
                    trend_labels.insert(0, '')
            
            # Take only last 5 for display
            attendance_trend = attendance_trend[-5:]
            trend_labels = trend_labels[-5:]
            
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
                'statistics': {
                    'attendance_trend': attendance_trend,
                    'trend_labels': trend_labels,
                    'distribution': distribution,
                    'total_classes': statistics_data.get('total_classes', 0),
                    'total_attendance': statistics_data.get('total_attendance', 0),
                    'total_students': statistics_data.get('total_students', 0)
                },
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
    class_id = request.args.get('class_id')  # Add this to get specific class
    
    try:
        with get_session() as db_session:
            lecturer_id = get_lecturer_id()
            institution_id = get_institution_id()
            course_model = CourseModel(db_session)
            class_model = ClassModel(db_session)
            user_model = UserModel(db_session)
            venue_model = VenueModel(db_session)
            
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
            
            # Get specific class details if class_id is provided
            current_class = None
            students = []
            if class_id:
                # Get class details
                class_obj = class_model.get_by_id(class_id)
                if class_obj and class_obj.lecturer_id == lecturer_id:
                    # Get course details
                    course = course_model.get_by_id(class_obj.course_id) if class_obj.course_id else None
                    
                    # Get venue details
                    venue = venue_model.get_by_id(class_obj.venue_id) if class_obj.venue_id else None
                    
                    # Get lecturer details
                    lecturer = user_model.get_by_id(class_obj.lecturer_id) if class_obj.lecturer_id else None
                    
                    # Get enrolled students for this class
                    students = class_model.get_enrolled_students(class_id)
                    
                    # Format current class data
                    current_class = {
                        'id': class_obj.class_id,
                        'course_id': class_obj.course_id,
                        'course_code': course.code if course else 'N/A',
                        'course_name': course.name if course else 'N/A',
                        'section': getattr(class_obj, 'section', '') or 'N/A',
                        'room': venue.name if venue else 'N/A',
                        'venue_id': class_obj.venue_id,
                        'start_time': class_obj.start_time,
                        'end_time': class_obj.end_time,
                        'start_datetime': class_obj.start_time.strftime('%B %d, %Y %I:%M %p') if class_obj.start_time else 'N/A',
                        'end_datetime': class_obj.end_time.strftime('%B %d, %Y %I:%M %p') if class_obj.end_time else 'N/A',
                        'lecturer_id': class_obj.lecturer_id,
                        'lecturer': lecturer.name if lecturer else 'N/A',
                        'lecturer_email': lecturer.email if lecturer else 'N/A',
                        'capacity': venue.capacity if venue else 0,
                        'status': class_obj.status,
                        'class_type': getattr(class_obj, 'class_type', 'Lecture')
                    }
            
            # Format classes for dropdown
            formatted_classes = []
            for class_obj in classes:
                course = course_model.get_by_id(class_obj.course_id) if class_obj.course_id else None
                formatted_classes.append({
                    'id': class_obj.class_id,
                    'course_code': course.code if course else 'N/A',
                    'course_name': course.name if course else 'N/A',
                    'start_time': class_obj.start_time.strftime('%B %d, %Y') if class_obj.start_time else 'N/A',
                    'start_datetime': class_obj.start_time.strftime('%B %d, %Y %I:%M %p') if class_obj.start_time else 'N/A',
                })
            
            # Format students for roster
            formatted_students = []
            for student in students:
                # Get student enrollment details (you may need to add this to your models)
                # For now, we'll use default values
                formatted_students.append({
                    'id': student.user_id,
                    'id_number': getattr(student, 'student_id', f'STU{student.user_id:06d}'),
                    'name': student.name,
                    'email': student.email,
                    'program': getattr(student, 'program', 'Not specified'),
                    'year': getattr(student, 'year', 'Year 1'),
                    'status': 'active',  # You'll need to get this from enrollment records
                    'enrollment_date': date.today().strftime('%d/%m/%Y'),  # Default for now
                    'initials': ''.join([name[0] for name in student.name.split()[:2]]).upper() if student.name else '??',
                    'phone_number': getattr(student, 'phone_number', 'N/A')
                })
            
            context = {
                'courses': [
                    {
                        'course_id': course.course_id,
                        'code': course.code,
                        'name': course.name,
                        'is_active': True
                    }
                    for course in courses
                ],
                'classes': formatted_classes,
                'selected_course_id': course_id,
                'current_class': current_class,
                'students': formatted_students,
                'total_students': len(formatted_students),
                'current_time': datetime.now().strftime('%I:%M %p'),
                'current_date': date.today().strftime('%d %B %Y'),
                'lecturer_name': user_model.get_by_id(lecturer_id).name if user_model.get_by_id(lecturer_id) else 'Lecturer'
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
    course_filter = request.args.get('course', 'all')
    class_type_filter = request.args.get('type', 'all')
    
    try:
        lecturer_id = get_lecturer_id()
        if not lecturer_id:
            flash('Please log in to view timetable', 'warning')
            return redirect(url_for('auth.login'))
        
        # Parse date or use today
        if selected_date:
            current_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        else:
            current_date = date.today()
        
        # Get lecturer's courses for filter dropdown - extract data within session
        courses_data = []
        with get_session() as db_session:
            course_model = CourseModel(db_session)
            courses = course_model.get_by_user_id(lecturer_id)
            # Extract the data we need while still in the session
            courses_data = [{'code': course.code, 'name': course.name} for course in courses]
        
        # Prepare context based on view type
        context = {
            'view_type': view_type,
            'courses': courses_data,  # Use the extracted data
            'today': date.today(),
            'course_filter': course_filter,
            'class_type_filter': class_type_filter
        }
        
        if view_type == 'monthly':
            # Generate monthly calendar
            calendar_data = generate_monthly_calendar(
                current_date, lecturer_id, course_filter, class_type_filter
            )
            
            context.update({
                'current_month': current_date.strftime('%B'),
                'current_year': current_date.year,
                'calendar_weeks': calendar_data
            })
            
        elif view_type == 'weekly':
            # Get weekly data
            week_data = generate_weekly_data(
                current_date, lecturer_id, course_filter, class_type_filter
            )
            
            context.update({
                'week_start': week_data['week_start'].strftime('%b %d'),
                'week_end': week_data['week_end'].strftime('%b %d'),
                'week_days': week_data['days']
            })
            
        else:  # list view
            # Get upcoming classes
            upcoming_classes = LecturerControl.get_upcoming_classes(
                lecturer_id, current_date, course_filter, class_type_filter
            )
            
            context.update({
                'upcoming_classes': upcoming_classes
            })
        
        return render_template('institution/lecturer/lecturer_timetable.html', **context)
        
    except Exception as e:
        current_app.logger.error(f"Error loading lecturer timetable: {e}")
        flash('Error loading timetable', 'danger')
        return render_template('institution/lecturer/lecturer_timetable.html')

def generate_lecturer_monthly_calendar(target_date, lecturer_id, course_filter=None, class_type_filter=None):
    """Generate monthly calendar data with classes for lecturer"""
    # Use LecturerControl to get classes
    classes = LecturerControl.get_lecturer_classes_in_date_range(
        lecturer_id, 
        date(target_date.year, target_date.month, 1),
        date(target_date.year, target_date.month, 
            calendar.monthrange(target_date.year, target_date.month)[1]),
        course_filter,
        class_type_filter
    )
    
    # Group classes by date
    classes_by_date = {}
    for class_data in classes:
        if class_data.get('start_time'):
            class_date = class_data['start_time'].date() if isinstance(class_data['start_time'], datetime) else class_data['start_time']
            if class_date not in classes_by_date:
                classes_by_date[class_date] = []
            
            classes_by_date[class_date].append({
                'id': class_data['id'],
                'course_code': class_data.get('course_code', 'N/A'),
                'course_name': class_data.get('course_name', 'N/A'),
                'type': class_data.get('type', 'Lecture'),
                'time': class_data.get('time', 'N/A'),
                'room': class_data.get('room', 'N/A'),
                'time_slot': class_data.get('time_slot', 'morning'),
                'lecturer': class_data.get('lecturer', 'N/A')
            })
    
    # Generate calendar grid
    calendar_data = []
    
    # Find the first Sunday on or before the first day of month
    first_day = date(target_date.year, target_date.month, 1)
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
                'classes': day_classes
            })
            current_day += timedelta(days=1)
        
        calendar_data.append(week_days)
    
    return calendar_data

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
    
@lecturer_bp.route('/api/class/<int:class_id>/add_student', methods=['POST'])
@requires_roles('lecturer')
def add_student_api(class_id):
    """API endpoint to add a student to a class"""
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        student_email = data.get('student_email')
        
        if not class_id or (not student_id and not student_email):
            return jsonify({'success': False, 'error': 'Class ID and Student ID/Email are required'}), 400
        
        with get_session() as db_session:
            lecturer_id = get_lecturer_id()
            class_model = ClassModel(db_session)
            
            # Verify lecturer has access to this class
            class_obj = class_model.get_by_id(class_id)
            if not class_obj or class_obj.lecturer_id != lecturer_id:
                return jsonify({'success': False, 'error': 'Unauthorized access'}), 403
            
            # TODO: Implement actual student addition logic
            # This would typically involve adding to CourseUser table
            
            return jsonify({
                'success': True,
                'message': 'Student added to class',
                'student_id': student_id
            })
            
    except Exception as e:
        current_app.logger.error(f"Error adding student to class: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@lecturer_bp.route('/api/class/<int:class_id>/remove_student', methods=['POST'])
@requires_roles('lecturer')
def remove_student_api(class_id):
    """API endpoint to remove a student from a class"""
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        
        if not class_id or not student_id:
            return jsonify({'success': False, 'error': 'Class ID and Student ID are required'}), 400
        
        with get_session() as db_session:
            lecturer_id = get_lecturer_id()
            class_model = ClassModel(db_session)
            
            # Verify lecturer has access to this class
            class_obj = class_model.get_by_id(class_id)
            if not class_obj or class_obj.lecturer_id != lecturer_id:
                return jsonify({'success': False, 'error': 'Unauthorized access'}), 403
            
            # TODO: Implement actual student removal logic
            # This would typically involve removing from CourseUser table
            
            return jsonify({
                'success': True,
                'message': 'Student removed from class',
                'student_id': student_id
            })
            
    except Exception as e:
        current_app.logger.error(f"Error removing student from class: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Helper functions
def generate_monthly_calendar(target_date, lecturer_id, course_filter=None, class_type_filter=None):
    """Generate monthly calendar data with classes for lecturer"""
    # Use LecturerControl to get classes - this handles the session internally
    classes = LecturerControl.get_lecturer_classes_in_date_range(
        lecturer_id, 
        date(target_date.year, target_date.month, 1),
        date(target_date.year, target_date.month, 
            calendar.monthrange(target_date.year, target_date.month)[1]),
        course_filter,
        class_type_filter
    )
    
    # Group classes by date
    classes_by_date = {}
    for class_data in classes:
        if class_data.get('start_time'):
            # class_data already contains properly formatted data from within the session
            class_date = class_data['start_time'].date() if isinstance(class_data['start_time'], datetime) else class_data['start_time']
            if class_date not in classes_by_date:
                classes_by_date[class_date] = []
            
            classes_by_date[class_date].append({
                'id': class_data['id'],
                'course_code': class_data.get('course_code', 'N/A'),
                'course_name': class_data.get('course_name', 'N/A'),
                'type': class_data.get('type', 'Lecture'),
                'time': class_data.get('time', 'N/A'),
                'room': class_data.get('room', 'N/A'),
                'time_slot': class_data.get('time_slot', 'morning'),
                'lecturer': class_data.get('lecturer', 'N/A')
            })
    
    # Generate calendar grid
    calendar_data = []
    
    # Find the first Sunday on or before the first day of month
    first_day = date(target_date.year, target_date.month, 1)
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
                'classes': day_classes
            })
            current_day += timedelta(days=1)
        
        calendar_data.append(week_days)
    
    return calendar_data

def generate_weekly_data(target_date, lecturer_id, course_filter=None, class_type_filter=None):
    """Generate weekly calendar data for lecturer"""
    # Get start of week (Sunday)
    week_start = target_date - timedelta(days=target_date.weekday() + 1)
    if week_start.weekday() != 6:  # Not Sunday
        week_start -= timedelta(days=week_start.weekday() + 1)
    
    week_end = week_start + timedelta(days=6)
    
    # Get classes for this week - handled within session by LecturerControl
    classes = LecturerControl.get_lecturer_classes_in_date_range(
        lecturer_id, week_start, week_end, course_filter, class_type_filter
    )
    
    # Group classes by date and format them
    classes_by_date = {}
    for class_data in classes:
        if class_data.get('start_time'):
            class_date = class_data['start_time'].date() if isinstance(class_data['start_time'], datetime) else class_data['start_time']
            if class_date not in classes_by_date:
                classes_by_date[class_date] = []
            
            classes_by_date[class_date].append({
                'id': class_data['id'],
                'course_code': class_data.get('course_code', 'N/A'),
                'title': class_data.get('course_name', 'N/A'),
                'type': class_data.get('type', 'Lecture'),
                'time': class_data.get('time', 'N/A'),
                'room': class_data.get('room', 'N/A'),
                'time_slot': class_data.get('time_slot', 'morning'),
                'lecturer': class_data.get('lecturer', 'N/A')
            })
    
    # Generate week days data
    week_days = []
    for i in range(7):
        current_date = week_start + timedelta(days=i)
        day_classes = classes_by_date.get(current_date, [])
        
        week_days.append({
            'name': current_date.strftime('%a'),
            'date': current_date.day,
            'classes': day_classes
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