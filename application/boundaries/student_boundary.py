from flask import Blueprint, render_template, session, redirect, url_for, flash, current_app, request
from application.controls.auth_control import AuthControl, requires_roles
from application.controls.attendance_control import AttendanceControl

student_bp = Blueprint('student', __name__)

@student_bp.route('/')
@requires_roles('student')
def dashboard():
    """Main dashboard route"""
    return render_template('institution/student/student_dashboard.html')

@student_bp.route('/profile')
@requires_roles('student')
def profile():
    """User profile route"""
    return render_template('institution/student/student_profile_management.html')

@student_bp.route('/attendance')
@requires_roles('student')
def attendance():
    """Student attendance overview"""
    return render_template('institution/student/student_attendance_management.html',
                            user=session.get('user'))


@student_bp.route('/attendance/history')
@requires_roles('student')
def attendance_history():
    """Attendance history route"""
    return render_template('institution/student/student_attendance_management_history.html',
                           user=session.get('user'))


@student_bp.route('/attendance/checkin')
@requires_roles('student')
def class_checkin():
    """Student class check-in view"""
    return render_template('institution/student/student_class_checkin.html',
                           user=session.get('user'))


@student_bp.route('/attendance/checkin/face')
@requires_roles('student')
def class_checkin_face():
    """Student class check-in (face capture)"""
    # Allow frontend to pass a session_id via query string for context (e.g. ?session_id=123)
    session_id = request.args.get('session_id')
    user_id = session.get('user_id')

    return render_template('institution/student/student_class_checkin_face.html',
                           user=session.get('user'),
                           session_id=session_id,
                           user_id=user_id)


@student_bp.route('/appeal')
@requires_roles('student')
def appeal_management():
    """Student appeal management"""
    return render_template('institution/student/student_appeal_management.html', user=session.get('user'))


@student_bp.route('/appeal/form', endpoint='appeal_form')
@requires_roles('student')
def appeal_form():
    """Show appeal form"""
    return render_template('institution/student/student_appeal_management_appeal_form.html', user=session.get('user'))


@student_bp.route('/absent-records', endpoint='absent_records')
@requires_roles('student')
def absent_records():
    """View all absent records (stub)"""
    # For now reuse the attendance history template as a placeholder
    return render_template('institution/student/student_attendance_management_history.html',
                            user=session.get('user'),
                            summary={},
                            records=[])

# TODO: Add more student-specific routes and functionalities as needed