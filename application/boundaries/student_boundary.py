from flask import Blueprint, render_template, session, redirect, url_for, flash, current_app
from application.controls.auth_control import AuthControl
from application.controls.attendance_control import AttendanceControl

student_bp = Blueprint('student', __name__)

@student_bp.route('/')
def dashboard():
    """Main dashboard route"""
    # Check authentication
    auth_result = AuthControl.verify_session(current_app, session)
    
    if not auth_result['success']:
        flash('Please login to access the dashboard', 'warning')
        return redirect(url_for('auth.login'))
    
    # Get user from session
    user = auth_result.get('user', {})
    user_id = user.get('firebase_uid') or session.get('user_id')
    
    # Get attendance summary
    attendance_summary = {}
    if user_id:
        attendance_result = AttendanceControl.get_student_attendance_summary(current_app, user_id, days=30)
        if attendance_result['success']:
            attendance_summary = attendance_result['summary']
    
    return render_template('institution/student/student_dashboard.html',
                         user=user,
                         attendance_summary=attendance_summary)

@student_bp.route('/profile')
def profile():
    """User profile route"""
    auth_result = AuthControl.verify_session(current_app, session)
    
    if not auth_result['success']:
        flash('Please login to view profile', 'warning')
        return redirect(url_for('auth.login'))
    
    return render_template('institution/student/student_profile_management.html', user=auth_result['user'])

@student_bp.route('/attendance-history')
def attendance_history():
    """Attendance history route"""
    auth_result = AuthControl.verify_session(current_app, session)
    
    if not auth_result['success']:
        flash('Please login to view attendance history', 'warning')
        return redirect(url_for('auth.login'))
    
    user_id = auth_result['user']['firebase_uid']
    attendance_result = AttendanceControl.get_user_attendance_summary(current_app, user_id, days=90)
    
    if attendance_result['success']:
        return render_template('attendance_history.html',
                             user=auth_result['user'],
                             summary=attendance_result['summary'],
                             records=attendance_result['records'])
    else:
        flash('Failed to load attendance history', 'danger')
        return redirect(url_for('student.dashboard'))
    
# TODO: Add more student-specific routes and functionalities as needed