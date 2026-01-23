from flask import Blueprint, render_template, session, redirect, url_for, flash, current_app, request, jsonify
from application.controls.auth_control import AuthControl, requires_roles
from application.controls.student_control import StudentControl
from database.base import get_session
from datetime import datetime, date, timedelta
import calendar

student_bp = Blueprint('student', __name__)

@student_bp.route('/')
@requires_roles('student')
def dashboard():
    """Main dashboard route"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to access the dashboard', 'warning')
            return redirect(url_for('auth.login'))
        
        # Get all dashboard data including announcements
        dashboard_data = StudentControl.get_dashboard_data(user_id)
        
        if not dashboard_data.get('success'):
            flash(dashboard_data.get('error', 'Error loading dashboard'), 'danger')
            return render_template('institution/student/student_dashboard.html')
        
        # Prepare context similar to lecturer dashboard
        context = {
            'student_name': dashboard_data.get('student', {}).get('name', 'Student'),
            'student_info': dashboard_data.get('student', {}),
            'today_classes': dashboard_data.get('today_classes', []),
            'announcements': dashboard_data.get('announcements', []),
            'current_time': dashboard_data.get('current_time', ''),
            'current_date': dashboard_data.get('current_date', ''),
            'statistics': dashboard_data.get('statistics', {})
        }
        
        return render_template('institution/student/student_dashboard.html', **context)
        
    except Exception as e:
        current_app.logger.error(f"Error loading student dashboard: {e}")
        flash('An error occurred while loading your dashboard', 'danger')
        return render_template('institution/student/student_dashboard.html')
    
@student_bp.route('/profile')
@requires_roles('student')
def profile():
    """User profile route"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to access your profile', 'warning')
            return redirect(url_for('auth.login'))
        
        profile_data = StudentControl.get_student_profile(user_id)
        return render_template('institution/student/student_profile_management.html', **profile_data)
        
    except Exception as e:
        current_app.logger.error(f"Error loading student profile: {e}")
        flash('An error occurred while loading your profile', 'danger')
        return render_template('institution/student/student_profile_management.html')

@student_bp.route('/facial-recognition-retrain')
@requires_roles('student')
def facial_recognition_retrain():
    """Facial recognition retrain page for students"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('auth.login'))
        
        # Get student info
        with get_session() as db_session:
            from database.models import User
            student = db_session.query(User).filter(User.user_id == user_id).first()
            student_data = {
                'name': student.name if student else 'Student',
                'email': student.email if student else '',
                'user_id': user_id
            }
        
        return render_template('institution/student/student_facial_recognition_retrain.html', **student_data)
        
    except Exception as e:
        current_app.logger.error(f"Error loading facial recognition retrain page: {e}")
        flash('An error occurred while loading the page', 'danger')
        return redirect(url_for('student.profile'))

@student_bp.route('/attendance')
@requires_roles('student')
def attendance():
    """Student attendance overview"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to view attendance', 'warning')
            return redirect(url_for('auth.login'))
        
        attendance_data = StudentControl.get_student_attendance(user_id)
        return render_template('institution/student/student_attendance_management.html', **attendance_data)
        
    except Exception as e:
        current_app.logger.error(f"Error loading student attendance: {e}")
        flash('An error occurred while loading attendance data', 'danger')
        return render_template('institution/student/student_attendance_management.html')
    
@student_bp.route('/attendance/statistics')
def attendance_statistics():
    """Get attendance statistics as JSON for JavaScript"""
    if 'user_id' not in session or session.get('user_role') != 'student':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    user_id = session['user_id']
    stats = StudentControl.get_attendance_statistics(user_id)
    
    return jsonify(stats)

@student_bp.route('/attendance/history')
@requires_roles('student')
def attendance_history():
    """Attendance history route"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to view attendance history', 'warning')
            return redirect(url_for('auth.login'))
        
        # Get filter parameters from request
        search_query = request.args.get('search', '')
        status_filter = request.args.get('status', '')
        month_filter = request.args.get('month', '')
        venue_filter = request.args.get('venue', '')
        page = request.args.get('page', 1, type=int)
        
        history_data = StudentControl.get_attendance_history(
            user_id,
            search_query=search_query,
            status_filter=status_filter,
            month_filter=month_filter,
            venue_filter=venue_filter,
            page=page,
            per_page=8
        )
        
        return render_template('institution/student/student_attendance_management_history.html', **history_data)
        
    except Exception as e:
        current_app.logger.error(f"Error loading attendance history: {e}")
        flash('An error occurred while loading attendance history', 'danger')
        return render_template('institution/student/student_attendance_management_history.html')

@student_bp.route('/appeal')
@requires_roles('student')
def appeal_management():
    """Student appeal management"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to manage appeals', 'warning')
            return redirect(url_for('auth.login'))
        
        # Get filter parameters from request
        module_filter = request.args.get('module', '')
        status_filter = request.args.get('status', '')
        date_filter = request.args.get('date', '')
        
        appeal_data = StudentControl.get_student_appeals(
            current_app,
            user_id, 
            module_filter=module_filter, 
            status_filter=status_filter, 
            date_filter=date_filter
        )
        
        return render_template('institution/student/student_appeal_management.html', **appeal_data)
        
    except Exception as e:
        current_app.logger.error(f"Error loading appeal management: {e}")
        flash('An error occurred while loading appeal data', 'danger')
        return render_template('institution/student/student_appeal_management.html')

@student_bp.route('/appeal/form/<int:attendance_record_id>', endpoint='appeal_form')
@requires_roles('student')
def appeal_form(attendance_record_id):
    """Show appeal form"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to submit an appeal', 'warning')
            return redirect(url_for('auth.login'))
        
        # Check if user can appeal this record
        can_appeal = StudentControl.can_appeal_record(user_id, attendance_record_id)
        if not can_appeal.get('can_appeal'):
            flash(can_appeal.get('message', 'Cannot appeal this record'), 'error')
            return redirect(url_for('student.appeal_management'))
        
        form_data = StudentControl.get_appeal_form_data(user_id, attendance_record_id)
        return render_template('institution/student/student_appeal_management_appeal_form.html', **form_data)
        
    except Exception as e:
        current_app.logger.error(f"Error loading appeal form: {e}")
        flash('An error occurred while loading the appeal form', 'danger')
        return redirect(url_for('student.appeal_management'))

@student_bp.route('/appeal/form/<int:attendance_record_id>/submit', methods=['POST'], endpoint='appeal_form_submit')
@requires_roles('student')
def appeal_form_submit(attendance_record_id):
    """Handle appeal form submission"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to submit an appeal', 'warning')
            return redirect(url_for('auth.login'))
        
        reason = request.form.get('appeal_reason', '').strip()
        
        if not reason:
            flash("Appeal reason cannot be empty.", "error")
            return redirect(url_for('student.appeal_form', attendance_record_id=attendance_record_id))
        
        result = StudentControl.submit_appeal(user_id, attendance_record_id, reason)
        
        if result.get('success'):
            flash(result.get('message', 'Your appeal has been submitted successfully.'), 'success')
            return redirect(url_for('student.appeal_management'))
        else:
            flash(result.get('error', 'Failed to submit appeal'), 'error')
            return redirect(url_for('student.appeal_form', attendance_record_id=attendance_record_id))
            
    except Exception as e:
        current_app.logger.error(f"Error submitting appeal: {e}")
        flash('An error occurred while submitting your appeal', 'danger')
        return redirect(url_for('student.appeal_management'))

@student_bp.route('/appeal/retract/<int:appeal_id>', endpoint='appeal_retract')
@requires_roles('student')
def appeal_retract(appeal_id):
    """Handle appeal retraction"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to retract appeals', 'warning')
            return redirect(url_for('auth.login'))
        
        result = StudentControl.retract_appeal(user_id, appeal_id)
        
        if result.get('success'):
            flash(result.get('message', 'Your appeal has been retracted successfully.'), 'success')
        else:
            flash(result.get('error', 'Failed to retract appeal'), 'error')
            
        return redirect(url_for('student.appeal_management'))
        
    except Exception as e:
        current_app.logger.error(f"Error retracting appeal: {e}")
        flash('An error occurred while retracting your appeal', 'danger')
        return redirect(url_for('student.appeal_management'))

@student_bp.route('/absent-records', endpoint='absent_records')
@requires_roles('student')
def absent_records():
    """View all absent records"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to view absent records', 'warning')
            return redirect(url_for('auth.login'))
        
        absent_data = StudentControl.get_absent_records(user_id)
        return render_template('institution/student/student_attendance_management_history.html', **absent_data)
        
    except Exception as e:
        current_app.logger.error(f"Error loading absent records: {e}")
        flash('An error occurred while loading absent records', 'danger')
        return render_template('institution/student/student_attendance_management_history.html')
    
@student_bp.route('/timetable')
@requires_roles('student')
def timetable():
    """Render the student timetable page with multiple views"""
    view_type = request.args.get('view', 'monthly')  # monthly, weekly, list
    selected_date = request.args.get('date')
    course_filter = request.args.get('course')
    class_type_filter = request.args.get('type')
    time_filter = request.args.get('time')
    
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to view timetable', 'warning')
            return redirect(url_for('auth.login'))
        
        # Parse date or use today
        if selected_date:
            current_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        else:
            current_date = date.today()
        
        # Get student's courses for filter dropdown
        courses = StudentControl.get_student_courses(user_id)
        
        # Get timetable data
        timetable_data = StudentControl.get_timetable_data(
            current_app, 
            user_id, 
            view_type, 
            current_date
        )
        
        if not timetable_data.get('success'):
            flash(timetable_data.get('error', 'Error loading timetable'), 'danger')
            return render_template('institution/student/student_timetable.html')
        
        # Prepare context based on view type
        context = {
            'view_type': view_type,
            'courses': courses,
            'today': date.today()
        }
        
        if view_type == 'monthly':
            # Generate monthly calendar
            calendar_data = generate_student_monthly_calendar(
                current_date, user_id, course_filter, class_type_filter
            )
            
            context.update({
                'current_month': current_date.strftime('%B'),
                'current_year': current_date.year,
                'calendar_weeks': calendar_data
            })
            
        elif view_type == 'weekly':
            # Get weekly data
            week_data = generate_student_weekly_data(
                current_date, user_id, course_filter, class_type_filter
            )
            
            context.update({
                'week_start': week_data['week_start'].strftime('%b %d'),
                'week_end': week_data['week_end'].strftime('%b %d'),
                'week_days': week_data['days']
            })
            
        else:  # list view
            # Get upcoming classes
            upcoming_classes = StudentControl.get_upcoming_classes(
                user_id, current_date, course_filter, class_type_filter
            )
            
            context.update({
                'upcoming_classes': upcoming_classes
            })
        
        return render_template('institution/student/student_timetable.html', **context)
        
    except Exception as e:
        current_app.logger.error(f"Error loading student timetable: {e}")
        flash('Error loading timetable', 'danger')
        return render_template('institution/student/student_timetable.html')
    
def generate_student_monthly_calendar(target_date, student_id, course_filter=None, class_type_filter=None):
    """Generate monthly calendar data with classes for student"""
    # Use StudentControl to get classes
    classes = StudentControl.get_student_classes_in_date_range(
        student_id, 
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

def generate_student_weekly_data(target_date, student_id, course_filter=None, class_type_filter=None):
    """Generate weekly calendar data for student"""
    # Get start of week (Sunday)
    week_start = target_date - timedelta(days=target_date.weekday() + 1)
    if week_start.weekday() != 6:  # Not Sunday
        week_start -= timedelta(days=week_start.weekday() + 1)
    
    week_end = week_start + timedelta(days=6)
    
    # Get classes for this week
    classes = StudentControl.get_student_classes_in_date_range(
        student_id, week_start, week_end, course_filter, class_type_filter
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