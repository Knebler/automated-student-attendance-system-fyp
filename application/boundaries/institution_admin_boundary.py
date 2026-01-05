from flask import Blueprint, render_template, request, jsonify, session, current_app, flash, redirect, url_for
from application.controls.auth_control import AuthControl
from application.controls.institution_control import InstitutionControl
from application.controls.attendance_control import AttendanceControl

institution_bp = Blueprint('institution', __name__)


@institution_bp.route('/dashboard')
def institution_dashboard():
    """Institution admin dashboard (admins / platform managers)"""
    auth_result = AuthControl.verify_session(current_app, session)

    if not auth_result['success']:
        flash('Please login to access institution dashboard', 'warning')
        return redirect(url_for('auth.login'))

    user_type = auth_result['user'].get('user_type')

    # allow institution admins here
    if user_type not in ['institution_admin', 'admin']:
        flash('Access denied. Institution admin privileges required.', 'danger')
        return redirect(url_for('main.home'))

    institution_id = auth_result['user'].get('institution_id')

    # Get institution statistics
    stats_result = InstitutionControl.get_institution_stats(current_app, institution_id)

    return render_template('institution/admin/institution_admin_dashboard.html',
                         user=auth_result['user'],
                         stats=stats_result.get('stats') if stats_result['success'] else {})


@institution_bp.route('/manage_users')
def manage_users():
    """Render the admin user-management page"""
    auth_result = AuthControl.verify_session(current_app, session)
    if not auth_result['success'] or auth_result['user'].get('user_type') not in ['institution_admin', 'admin']:
        flash('Access denied. Institution admin privileges required.', 'danger')
        return redirect(url_for('auth.login'))
    
    institution_id = auth_result['user'].get('institution_id')
    
    # Get user details
    user_details_result = InstitutionControl.get_institution_user_details(current_app, institution_id)
    
    # Get user counts
    user_counts_result = InstitutionControl.get_user_counts(current_app, institution_id)
    counts = user_counts_result.get('counts') if user_counts_result['success'] else {
        'total_users': 0,
        'students': 0,
        'lecturers': 0,
        'admins': 0,
        'suspended': 0
    }
    
    data_to_pass = {
        'user': auth_result['user'],
        'user_count': counts['total_users'],
        'student_count': counts['students'],
        'lecturer_count': counts['lecturers'],
        'admin_count': counts['admins'],
        'suspended_count': counts['suspended'],
        'users': user_details_result.get('users') if user_details_result['success'] else []
    }

    return render_template('institution/admin/institution_admin_user_management.html', **data_to_pass)


@institution_bp.route('/manage_attendance')
def manage_attendance():
    """Render the admin attendance-management page"""
    auth_result = AuthControl.verify_session(current_app, session)
    if not auth_result['success'] or auth_result['user'].get('user_type') not in ['institution_admin', 'admin']:
        flash('Access denied. Institution admin privileges required.', 'danger')
        return redirect(url_for('auth.login'))

    # load all sessions (historical) so admin can manage attendance across all dates
    # default: returns sessions up to today
    result = AttendanceControl.get_all_sessions_attendance(current_app)
    sessions = []
    if result.get('success'):
        raw_sessions = result.get('sessions') or []
        for s in raw_sessions:
            sess = s.get('session') if isinstance(s, dict) else None
            records = s.get('attendance_records') if isinstance(s, dict) else []
            present = sum(1 for r in records if r.get('status') == 'present')
            absent = sum(1 for r in records if r.get('status') == 'absent')
            sessions.append({
                'session': sess,
                'attendance_records': records,
                'present_count': present,
                'absent_count': absent,
                'total': len(records)
            })
    else:
        flash(result.get('error') or 'Failed to load sessions', 'warning')

    return render_template('institution/admin/institution_admin_attendance_management.html', user=auth_result['user'], sessions=sessions)


@institution_bp.route('/manage_classes')
def manage_classes():
    """Render the admin class-management page"""
    auth_result = AuthControl.verify_session(current_app, session)
    if not auth_result['success'] or auth_result['user'].get('user_type') not in ['institution_admin', 'admin']:
        flash('Access denied. Institution admin privileges required.', 'danger')
        return redirect(url_for('auth.login'))

    return render_template('institution/admin/institution_admin_class_management.html', user=auth_result['user'])


@institution_bp.route('/institution_profile')
def institution_profile():
    """Render the institution profile page for admins"""
    auth_result = AuthControl.verify_session(current_app, session)
    if not auth_result['success'] or auth_result['user'].get('user_type') not in ['institution_admin', 'admin']:
        flash('Access denied. Institution admin privileges required.', 'danger')
        return redirect(url_for('auth.login'))

    return render_template('institution/admin/institution_admin_institute_profile.html', user=auth_result['user'])


@institution_bp.route('/import_data')
def import_data():
    """Render import institution data page for admins"""
    auth_result = AuthControl.verify_session(current_app, session)
    if not auth_result['success'] or auth_result['user'].get('user_type') not in ['institution_admin', 'admin']:
        flash('Access denied. Institution admin privileges required.', 'danger')
        return redirect(url_for('auth.login'))

    return render_template('institution/admin/import_institution_data.html', user=auth_result['user'])


@institution_bp.route('/attendance/student/<int:student_id>')
def attendance_student_details(student_id):
    """Show attendance details for a single student (admin view)"""
    auth_result = AuthControl.verify_session(current_app, session)
    if not auth_result['success'] or auth_result['user'].get('user_type') not in ['institution_admin', 'admin']:
        flash('Access denied. Institution admin privileges required.', 'danger')
        return redirect(url_for('auth.login'))

    # Load attendance summary for the student
    result = AttendanceControl.get_student_attendance_summary(current_app, student_id, days=365)
    if not result.get('success'):
        flash(result.get('error') or 'Failed to load student attendance', 'danger')
        return redirect(url_for('institution.manage_attendance'))

    return render_template(
        'institution/admin/institution_admin_attendance_management_student_details.html',
        user=auth_result['user'],
        student_info=result.get('student_info'),
        summary=result.get('summary'),
        records=result.get('attendance_records')
    )


@institution_bp.route('/attendance/class/<int:class_id>')
def attendance_class_details(class_id):
    """Show attendance details for a single class (admin view)"""
    auth_result = AuthControl.verify_session(current_app, session)
    if not auth_result['success'] or auth_result['user'].get('user_type') not in ['institution_admin', 'admin']:
        flash('Access denied. Institution admin privileges required.', 'danger')
        return redirect(url_for('auth.login'))

    # Load session (class) attendance
    result = AttendanceControl.get_session_attendance(current_app, class_id)
    if not result.get('success'):
        flash(result.get('error') or 'Failed to load class attendance', 'danger')
        return redirect(url_for('institution.manage_attendance'))

    return render_template(
        'institution/admin/institution_admin_attendance_management_class_details.html',
        user=auth_result['user'],
        session_info=result.get('session'),
        records=result.get('attendance_records')
    )


@institution_bp.route('/attendance/reports')
def attendance_reports():
    """Show attendance reports view (admin view)"""
    auth_result = AuthControl.verify_session(current_app, session)
    if not auth_result['success'] or auth_result['user'].get('user_type') not in ['institution_admin', 'admin']:
        flash('Access denied. Institution admin privileges required.', 'danger')
        return redirect(url_for('auth.login'))

    # Build a reports overview using today's sessions (or overall reports later)
    result = AttendanceControl.get_today_sessions_attendance(current_app)
    if not result.get('success'):
        flash(result.get('error') or 'Failed to load attendance reports', 'danger')
        return redirect(url_for('institution.manage_attendance'))

    # result['sessions'] is a list of session attendance payloads
    return render_template(
        'institution/admin/institution_admin_attendance_management_report.html',
        user=auth_result['user'],
        sessions=result.get('sessions')
    )
