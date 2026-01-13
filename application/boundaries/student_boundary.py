from flask import Blueprint, render_template, session, redirect, url_for, flash, current_app, request
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
    user_id = user.get('user_id') or session.get('user_id')
    
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

@student_bp.route('/attendance')
def attendance():
    """Student attendance overview"""
    auth_result = AuthControl.verify_session(current_app, session)

    if not auth_result['success']:
        flash('Please login to view attendance', 'warning')
        return redirect(url_for('auth.login'))

    user = auth_result['user']
    user_id = user.get('user_id') or session.get('user_id')

    attendance_summary = {}
    records = []
    if user_id:
        attendance_result = AttendanceControl.get_student_attendance_summary(current_app, user_id, days=30)
        if attendance_result.get('success'):
            attendance_summary = attendance_result.get('summary')
            records = attendance_result.get('attendance_records')

    return render_template('institution/student/student_attendance_management.html',
                         user=user,
                         summary=attendance_summary,
                         records=records)


@student_bp.route('/attendance/history')
def attendance_history():
    """Attendance history route"""
    auth_result = AuthControl.verify_session(current_app, session)

    if not auth_result['success']:
        flash('Please login to view attendance history', 'warning')
        return redirect(url_for('auth.login'))

    user = auth_result['user']
    user_id = user.get('user_id') or session.get('user_id')

    attendance_summary = {}
    records = []
    if user_id:
        attendance_result = AttendanceControl.get_student_attendance_summary(current_app, user_id, days=365)
        if attendance_result.get('success'):
            attendance_summary = attendance_result.get('summary')
            records = attendance_result.get('attendance_records')

    return render_template('institution/student/student_attendance_management_history.html',
                         user=user,
                         summary=attendance_summary,
                         records=records)


@student_bp.route('/attendance/checkin')
def class_checkin():
    """Student class check-in view"""
    auth_result = AuthControl.verify_session(current_app, session)
    if not auth_result['success']:
        flash('Please login to check in', 'warning')
        return redirect(url_for('auth.login'))

    return render_template('institution/student/student_class_checkin.html', user=auth_result['user'])


@student_bp.route('/attendance/checkin/face')
def class_checkin_face():
    """Student class check-in (face capture)"""
    auth_result = AuthControl.verify_session(current_app, session)
    if not auth_result['success']:
        flash('Please login to check in', 'warning')
        return redirect(url_for('auth.login'))

    # Allow frontend to pass a session_id via query string for context (e.g. ?session_id=123)
    session_id = request.args.get('session_id')

    user = auth_result['user']
    user_id = user.get('user_id') or session.get('user_id')

    return render_template('institution/student/student_class_checkin_face.html',
                           user=user,
                           session_id=session_id,
                           user_id=user_id)


@student_bp.route('/appeal')
def appeal_management():
    """Student appeal management"""
    auth_result = AuthControl.verify_session(current_app, session)
    if not auth_result['success']:
        flash('Please login to view appeals', 'warning')
        return redirect(url_for('auth.login'))

    return render_template('institution/student/student_appeal_management.html', user=auth_result['user'])


@student_bp.route('/appeal/form', endpoint='appeal_form')
def appeal_form():
    """Show appeal form"""
    auth_result = AuthControl.verify_session(current_app, session)
    if not auth_result['success']:
        flash('Please login to submit an appeal', 'warning')
        return redirect(url_for('auth.login'))

    return render_template('institution/student/student_appeal_management_appeal_form.html', user=auth_result['user'])


@student_bp.route('/absent-records', endpoint='absent_records')
def absent_records():
    """View all absent records (stub)"""
    auth_result = AuthControl.verify_session(current_app, session)
    if not auth_result['success']:
        flash('Please login to view records', 'warning')
        return redirect(url_for('auth.login'))

    # For now reuse the attendance history template as a placeholder
    return render_template('institution/student/student_attendance_management_history.html', user=auth_result['user'], summary={}, records=[])

# TODO: Add more student-specific routes and functionalities as needed