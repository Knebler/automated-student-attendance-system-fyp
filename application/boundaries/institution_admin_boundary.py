from flask import Blueprint, render_template, request, session, current_app, flash, redirect, url_for, abort
from sqlalchemy.exc import IntegrityError
from application.controls.auth_control import AuthControl
from application.controls.institution_control import InstitutionControl
from application.controls.attendance_control import AttendanceControl
from application.controls.auth_control import requires_roles
from application.entities2 import ClassModel, UserModel, InstitutionModel, SubscriptionModel, CourseModel, VenueModel, CourseUserModel
from database.base import get_session
from database.models import *

institution_bp = Blueprint('institution', __name__)


@institution_bp.route('/dashboard')
@requires_roles('admin')
def institution_dashboard():
    """Institution admin dashboard (admins / platform managers)"""
    institution_id = session.get('institution_id')
    with get_session() as db_session:
        user_model = UserModel(db_session)
        institution_model = InstitutionModel(db_session)
        sub_model = SubscriptionModel(db_session)
        class_model = ClassModel(db_session)
        course_model = CourseModel(db_session)
        venue_model = VenueModel(db_session)

        user_count = user_model.count()
        student_count = user_model.count(institution_id=institution_id, role='student')
        lecturer_count = user_model.count(institution_id=institution_id, role='lecturer')
        admin_count = user_model.count(institution_id=institution_id, role='admin')
        
        institution = institution_model.get_one(institution_id=institution_id)
        institution_name = institution.name if institution else "Unknown Institution"

        sub = sub_model.get_by_id(institution.subscription_id)
        sub_active = True if sub and sub.is_active else False

        classes = class_model.get_today(institution_id=institution_id)

        context = {
            "institution": {
                "name": institution_name,
                "is_active": sub_active,
                "renewal": sub.end_date,
            },
            "overview": {
                "user_count": user_count,
                "student_count": student_count,
                "lecturer_count": lecturer_count,
                "admin_count": admin_count
            },
            "classes": [{
                "module": course_model.get_by_id(c.course_id).name,
                "venue": venue_model.get_by_id(c.venue_id).name,
                "lecturer": user_model.get_by_id(c.lecturer_id).name,
            } for c in classes],
        }

    return render_template('institution/admin/institution_admin_dashboard.html',
                        user=session['user_id'],
                        **context)


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
        course_model = CourseModel(db_session)
        target_user = user_model.get_by_id(user_id)
        # Should admins be able to view other admins?
        if target_user.role == 'admin' or target_user.institution_id != session.get('institution_id'):
            return abort(401)
        user = user_model.get_by_id(user_id)
        user_details = user.as_sanitized_dict() if user else None
        courses = course_model.get_by_user_id(user_id=user_id)
        user_details["courses"] = [course.__dict__.copy() for course in courses]

        possible_courses = course_model.get_unenrolled(user_id=user_id)
        user_details["possible_courses"] = [course.as_dict() for course in possible_courses]
    return render_template(
        'institution/admin/institution_admin_user_management_user_details.html',
        user_details=user_details,
        redirect_path=f"{request.path}",
    )


@institution_bp.route('/manage_users/<int:user_id>/add_course', methods=['POST'])
@requires_roles('admin')
def add_user_to_course(user_id):
    # Remember to only allow students and lecturers to be assigned
    # and admins must be from the same institution
    try:
        with get_session() as db_session:
            target_user = UserModel(db_session).get_by_id(user_id)
            if target_user.role == 'admin' or target_user.institution_id != session.get('institution_id'):
                return abort(401)
            cu_model = CourseUserModel(db_session)
            cu_model.assign(user_id=user_id, course_id=request.form.get('course_id'))
    except IntegrityError as e:
        flash("User already assigned to course", "error")
    redirect_path = request.form.get("redirect")
    if redirect_path:
        return redirect(redirect_path)
    return redirect(url_for('institution.manage_users'))


@institution_bp.route('/manage_users/<int:user_id>/remove_course', methods=['POST'])
@requires_roles('admin')
def remove_user_from_course(user_id):
    with get_session() as db_session:
        target_user = UserModel(db_session).get_by_id(user_id)
        if target_user.role == 'admin' or target_user.institution_id != session.get('institution_id'):
            return abort(401)

        cu_model = CourseUserModel(db_session)
        cu_model.unassign(user_id=user_id, course_id=request.form.get('course_id'))
    redirect_path = request.form.get("redirect")
    if redirect_path:
        return redirect(redirect_path)
    return redirect(url_for('institution.manage_users'))

@institution_bp.route('/manage_attendance')
@requires_roles('admin')
def manage_attendance():

    return render_template('institution/admin/institution_admin_attendance_management.html')


@institution_bp.route('/manage_classes')
@requires_roles('admin')
def manage_classes():
    """Render the admin class-management page"""
    with get_session() as db_session:
        course_model = CourseModel(db_session)
        courses = course_model.get_manage_course_info(institution_id=session.get('institution_id'))
        context = {
            "courses": courses
        }
    return render_template('institution/admin/institution_admin_class_management.html', **context)

@institution_bp.route('/manage_classes/<int:course_id>')
@requires_roles('admin')
def module_details(course_id):
    """Render the module details page for admins"""
    with get_session() as db_session:
        class_model = ClassModel(db_session)
        course_model = CourseModel(db_session)
        if course_model.get_by_id(course_id).institution_id != session.get('institution_id'):
            return abort(401)
        completed = class_model.get_completed(course_id)
        upcoming = class_model.get_upcoming(course_id)
        context = {
            "course": course_model.get_manage_course_info(session.get('institution_id'), course_id)[0],
            "completed": completed,
            "upcoming": upcoming,
        }
    return render_template('institution/admin/institution_admin_class_management_module_details.html', **context)

@institution_bp.route('/institution_profile')
@requires_roles('admin')
def institution_profile():
    """Render the institution profile page for admins"""
    return render_template('institution/admin/institution_admin_institution_profile.html',)


@institution_bp.route('/import_data')
@requires_roles('admin')
def import_data():
    """Render import institution data page for admins"""
    return render_template('institution/admin/import_institution_data.html')


@institution_bp.route('/attendance/student/<int:student_id>')
@requires_roles('admin')
def attendance_student_details(student_id):
    """Show attendance details for a single student (admin view)"""
    # Remember to only allow admins from the same institution
    # Load attendance summary for the student
    result = AttendanceControl.get_student_attendance_summary(current_app, student_id, days=365)
    if not result.get('success'):
        flash(result.get('error') or 'Failed to load student attendance', 'danger')
        return redirect(url_for('institution.manage_attendance'))

    return render_template(
        'institution/admin/institution_admin_attendance_management_student_details.html',
        student_info=result.get('student_info'),
        summary=result.get('summary'),
        records=result.get('attendance_records')
    )


@institution_bp.route('/attendance/class')
@requires_roles('admin')
def attendance_class_details():
    return render_template(
        'institution/admin/institution_admin_attendance_management_class_details.html',
    )


@institution_bp.route('/attendance/reports')
@requires_roles('admin')
def attendance_reports():
    """Show attendance reports view (admin view)"""
    # Build a reports overview using today's sessions (or overall reports later)
    result = AttendanceControl.get_today_sessions_attendance(current_app)
    if not result.get('success'):
        flash(result.get('error') or 'Failed to load attendance reports', 'danger')
        return redirect(url_for('institution.manage_attendance'))

    # result['sessions'] is a list of session attendance payloads
    return render_template(
        'institution/admin/institution_admin_attendance_management_report.html',
        sessions=result.get('sessions')
    )
    

    
        