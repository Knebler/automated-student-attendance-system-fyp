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

    role = auth_result['user'].get('role')

    if role not in ['lecturer', 'teacher']:
        flash('Access denied. Lecturer privileges required.', 'danger')
        return redirect(url_for('main.home'))

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
    if not auth_result['success'] or auth_result['user'].get('role') not in ['lecturer', 'teacher']:
        flash('Access denied. Lecturer privileges required.', 'danger')
        return redirect(url_for('auth.login'))

    return render_template('institution/lecturer/lecturer_appeal_management.html', user=auth_result['user'])


@lecturer_bp.route('/manage_attendance')
def manage_attendance():
    """Render the lecturer attendance-management page"""
    auth_result = AuthControl.verify_session(current_app, session)
    if not auth_result['success'] or auth_result['user'].get('role') not in ['lecturer', 'teacher']:
        flash('Access denied. Lecturer privileges required.', 'danger')
        return redirect(url_for('auth.login'))

    user_id = auth_result['user'].get('user_id')

    # Load sessions and attendance for this lecturer
    result = AttendanceControl.get_all_sessions_attendance(current_app, lecturer_id=user_id)
    sessions = result.get('sessions') if result.get('success') else []

    return render_template('institution/lecturer/lecturer_attendance_management.html',
                           user=auth_result['user'],
                           sessions=sessions)


@lecturer_bp.route('/manage_attendance/statistics')
def attendance_statistics():
    """Render the lecturer attendance statistics page"""
    auth_result = AuthControl.verify_session(current_app, session)
    if not auth_result['success'] or auth_result['user'].get('role') not in ['lecturer', 'teacher']:
        flash('Access denied. Lecturer privileges required.', 'danger')
        return redirect(url_for('auth.login'))

    user_id = auth_result['user'].get('user_id')
    attendance_summary = {}
    if user_id:
        # Optionally fetch attendance summary for this lecturer
        result = AttendanceControl.get_student_attendance_summary(current_app, user_id, days=30)
        if result.get('success'):
            attendance_summary = result.get('summary')

    return render_template('institution/lecturer/lecturer_attendance_management_statistics.html',
                           user=auth_result['user'],
                           attendance_summary=attendance_summary)


@lecturer_bp.route('/manage_classes')
def manage_classes():
    """Render the lecturer class-management page"""
    auth_result = AuthControl.verify_session(current_app, session)
    if not auth_result['success'] or auth_result['user'].get('role') not in ['lecturer', 'teacher']:
        flash('Access denied. Lecturer privileges required.', 'danger')
        return redirect(url_for('auth.login'))

    # Optionally load a specific class if provided
    class_id = request.args.get('class_id')
    current_class = None
    if class_id:
        try:
            from application.entities.session import Session
            sess = Session.get_model().query.get(int(class_id))
            if sess:
                current_class = {
                    'id': sess.session_id,
                    'course_id': sess.course_id,
                    'session_date': sess.session_date.isoformat() if sess.session_date else None,
                    'session_topic': sess.session_topic,
                    'status': sess.status
                }
        except Exception:
            current_class = None

    return render_template('institution/lecturer/lecturer_class_management.html',
                           user=auth_result['user'],
                           current_class=current_class)


@lecturer_bp.route('/timetable')
def timetable():
    """Render the lecturer timetable page"""
    auth_result = AuthControl.verify_session(current_app, session)
    if not auth_result['success'] or auth_result['user'].get('role') not in ['lecturer', 'teacher']:
        flash('Access denied. Lecturer privileges required.', 'danger')
        return redirect(url_for('auth.login'))

    user_id = auth_result['user'].get('user_id')

    # Load sessions for the lecturer
    try:
        from application.entities.session import Session
        sessions = Session.get_by_lecturer(current_app, user_id) if user_id else []
        sessions_list = [s.to_dict() for s in sessions]
    except Exception:
        sessions_list = []

    view_type = request.args.get('view_type', 'monthly')

    return render_template('institution/lecturer/lecturer_timetable.html',
                           user=auth_result['user'],
                           sessions=sessions_list,
                           view_type=view_type)