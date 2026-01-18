from flask import Blueprint, render_template, session, redirect, url_for, flash, current_app, request
from application.controls.auth_control import AuthControl, requires_roles
from application.controls.student_control import StudentControl
from database.base import get_session

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

@student_bp.route('/attendance/history')
@requires_roles('student')
def attendance_history():
    """Attendance history route"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to view attendance history', 'warning')
            return redirect(url_for('auth.login'))
        
        history_data = StudentControl.get_attendance_history(user_id)
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
        
        appeal_data = StudentControl.get_student_appeals(
            user_id, 
            module_filter='module', 
            status_filter='status', 
            date_filter='date'
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