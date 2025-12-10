from flask import Blueprint, render_template, request, jsonify, session, current_app, flash, redirect, url_for
from application.controls.auth_control import AuthControl
from application.controls.attendance_control import AttendanceControl

lecturer_bp = Blueprint('institution_lecturer', __name__)


@lecturer_bp.route('/dashboard')
def lecturer_dashboard():
    """Lecturer dashboard"""
    auth_result = AuthControl.verify_session(current_app, session)

    if not auth_result['success']:
        flash('Please login to access lecturer dashboard', 'warning')
        return redirect(url_for('auth.login'))

    user_type = auth_result['user'].get('user_type')

    if user_type not in ['lecturer', 'teacher']:
        flash('Access denied. Lecturer privileges required.', 'danger')
        return redirect(url_for('dashboard.dashboard'))

    user_id = auth_result['user'].get('user_id')
    attendance_summary = {}
    if user_id:
        attendance_result = AttendanceControl.get_student_attendance_summary(current_app, user_id, days=30)
        if attendance_result['success']:
            attendance_summary = attendance_result['summary']

    return render_template('institution/lecturer/lecturer_dashboard.html',
                         user=auth_result['user'],
                         attendance_summary=attendance_summary)

@lecturer_bp.route('/manage_appeals')
def manage_appeals():
    """Render the lecturer appeal-management page"""
    auth_result = AuthControl.verify_session(current_app, session)
    if not auth_result['success'] or auth_result['user'].get('user_type') not in ['lecturer', 'teacher']:
        flash('Access denied. Lecturer privileges required.', 'danger')
        return redirect(url_for('auth.login'))

    return render_template('institution/lecturer/lecturer_appeal_management.html', user=auth_result['user'])