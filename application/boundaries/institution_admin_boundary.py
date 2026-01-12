from flask import Blueprint, render_template, request, session, current_app, flash, redirect, url_for, abort
from application.controls.auth_control import AuthControl
from application.controls.institution_control import InstitutionControl
from application.controls.attendance_control import AttendanceControl
from application.controls.auth_control import requires_roles
from application.entities2.user import UserModel
from application.entities2.institution import InstitutionModel
from application.entities2.subscription import SubscriptionModel
from database.base import get_session

institution_bp = Blueprint('institution', __name__)


@institution_bp.route('/dashboard')
@requires_roles('admin')
def institution_dashboard():
    """Institution admin dashboard (admins / platform managers)"""
    institution_id = session.get('institution_id')
    print("entering institution dashboard")

    # Get institution statistics
    stats_result = InstitutionControl.get_institution_stats(current_app, institution_id)
    
    with get_session() as db_session:
        user_model = UserModel(db_session)
        user = user_model.get_all(institution_id=session.get('institution_id'))
        user_count = len(user)
        student_count = len([u for u in user if u.role == 'student'])
        lecturer_count = len([u for u in user if u.role == 'lecturer'])
        admin_count = len([u for u in user if u.role == 'admin'])
        
    with get_session() as db_session:
        institution_model = InstitutionModel(db_session)
        institution = institution_model.get_all(institution_id=session.get('institution_id'))
        institution_name = institution[0].name if institution else "Unknown Institution"
        
  
        
        
    
    return render_template('institution/admin/institution_admin_dashboard.html',
                        user=session['user_id'],
                        user_count=user_count,
                        student_count=student_count,
                        lecturer_count=lecturer_count,  
                        admin_count=admin_count,
                        institution_name=institution_name,
                        stats=stats_result.get('stats') if stats_result['success'] else {})


@institution_bp.route('/manage_users')
@requires_roles('admin')
def manage_users():
    with get_session() as db_session:
        user_model = UserModel(db_session)
        users = user_model.get_all(institution_id=session.get('institution_id'))
        users = [u.as_sanitized_dict() for u in users]
        #count total users
        user_count = len(users)
        student_count = len([u for u in users if u['role'] == 'student'])
        lecturer_count = len([u for u in users if u['role'] == 'lecturer'])
        admin_count = len([u for u in users if u['role'] == 'admin'])
        suspended_count = len([u for u in users if not u['is_active']])
    return render_template(
                        'institution/admin/institution_admin_user_management.html', 
                           users=users, 
                           user_count=user_count, 
                           student_count=student_count, 
                           lecturer_count=lecturer_count, 
                           admin_count=admin_count, 
                           suspended_count=suspended_count
                           )

@institution_bp.route('/manage_users/<int:user_id>/suspend', methods=['POST'])
@requires_roles('admin')
def suspend_user(user_id):
    with get_session() as db_session:
        user_model = UserModel(db_session)
        target_user = user_model.get_by_id(user_id)
        if target_user.role == 'admin' or target_user.institution_id != session.get('institution_id'):
            return abort(401)
        user_model.suspend(user_id)
    redirect_path = request.form.get("redirect")
    if redirect_path:
        return redirect(redirect_path)
    return redirect(url_for('institution.manage_users'))


@institution_bp.route('/manage_users/<int:user_id>/unsuspend', methods=['POST'])
@requires_roles('admin')
def unsuspend_user(user_id):
    with get_session() as db_session:
        user_model = UserModel(db_session)
        target_user = user_model.get_by_id(user_id)
        if target_user.role == 'admin' or target_user.institution_id != session.get('institution_id'):
            return abort(401)
        user_model.unsuspend(user_id)
    redirect_path = request.form.get("redirect")
    if redirect_path:
        return redirect(redirect_path)
    return redirect(url_for('institution.manage_users'))


@institution_bp.route('/manage_users/<int:user_id>/delete', methods=['POST'])
@requires_roles('admin')
def delete_user(user_id):
    with get_session() as db_session:
        user_model = UserModel(db_session)
        target_user = user_model.get_by_id(user_id)
        if target_user.role == 'admin' or target_user.institution_id != session.get('institution_id'):
            return abort(401)
        user_model.delete(user_id)
    redirect_path = request.form.get("redirect")
    if redirect_path:
        return redirect(redirect_path)
    return redirect(url_for('institution.manage_users'))


@institution_bp.route('/manage_users/<int:user_id>/view', methods=['GET'])
@requires_roles('admin')
def view_user_details(user_id):
    with get_session() as db_session:
        user_model = UserModel(db_session)
        target_user = user_model.get_by_id(user_id)
        # Should admins be able to view other admins?
        if target_user.role == 'admin' or target_user.institution_id != session.get('institution_id'):
            return abort(401)
        user = user_model.get_by_id(user_id)
        user_details = user.as_sanitized_dict() if user else None
            
    return render_template(
        'institution/admin/institution_admin_user_management_user_details.html',
        user_details=user_details,
        redirect_path=f"{request.path}",
    )

@institution_bp.route('/manage_users/<int:user_id>/add_course', methods=['POST'])
def add_user_to_course(user_id):
    # Remember to only allow students and lecturers to be assigned
    # and admins must be from the same institution
    auth = AuthControl.verify_session(current_app, session)
    if not auth['success'] or auth['user'].get('user_type') not in ['institution_admin', 'admin']:
        flash('Access denied. Institution admin privileges required.', 'danger')
        return redirect(url_for('auth.login'))

    InstitutionControl.add_user_to_course(current_app, user_id, course_id=request.form.get('course_id'), role=request.form.get('user_role'))
    redirect_path = request.form.get("redirect")
    if redirect_path:
        return redirect(redirect_path)
    return redirect(url_for('institution.manage_users'))

@institution_bp.route('/manage_users/<int:user_id>/remove_course', methods=['POST'])
def remove_user_from_course(user_id):
    # Only allow admins from the same institution
    auth = AuthControl.verify_session(current_app, session)
    if not auth['success'] or auth['user'].get('user_type') not in ['institution_admin', 'admin']:
        flash('Access denied. Institution admin privileges required.', 'danger')
        return redirect(url_for('auth.login'))

    InstitutionControl.remove_user_from_course(current_app, user_id, course_id=request.form.get('course_id'), role=request.form.get('user_role'))
    redirect_path = request.form.get("redirect")
    if redirect_path:
        return redirect(redirect_path)
    return redirect(url_for('institution.manage_users'))

@institution_bp.route('/manage_attendance')
@requires_roles('admin')
def manage_attendance():

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

    return render_template('institution/admin/institution_admin_attendance_management.html')


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
    # Remember to only allow admins from the same institution
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
    # Remember to only allow admins from the same institution
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
    

    
        