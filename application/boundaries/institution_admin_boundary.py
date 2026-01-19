from flask import Blueprint, render_template, request, session, current_app, flash, redirect, url_for, abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from application.controls.attendance_control import AttendanceControl
from application.controls.auth_control import requires_roles
from application.entities2 import *
from database.base import get_session
from database.models import *
from datetime import date, datetime, timedelta
from collections import defaultdict

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
        
        institution = institution_model.get_one(institution_id=institution_id)
        institution_name = institution.name if institution else "Unknown Institution"

        sub = sub_model.get_by_id(institution.subscription_id)
        sub_active = True if sub and sub.is_active else False

        context = {
            "institution": {
                "name": institution_name,
                "is_active": sub_active,
                "renewal": sub.end_date,
            },
            "overview": user_model.admin_user_stats(institution_id),
            "classes": class_model.admin_dashboard_classes_today(institution_id),
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
    inst_id = session.get('institution_id')
    with get_session() as db_session:
        user_model = UserModel(db_session)
        course_model = CourseModel(db_session)
        sem_model = SemesterModel(db_session)
        target_user = user_model.get_by_id(user_id)
        # Should admins be able to view other admins?
        if target_user.role == 'admin' or target_user.institution_id != session.get('institution_id'):
            return abort(401)
        user = user_model.get_by_id(user_id)
        user_details = user.as_sanitized_dict() if user else None
        user_details["courses"] = course_model.admin_view_courses(user_id)
        user_details["possible_courses"] = [row.as_dict() for row in course_model.get_all(institution_id=inst_id)]
        user_details["possible_semesters"] = [row.as_dict() for row in sem_model.get_all(institution_id=inst_id)]
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
            cu_model.assign(user_id=user_id, course_id=request.form.get('course_id'), semester_id=request.form.get('semester_id'))
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
        cu_model.unassign(user_id=user_id, course_id=request.form.get('course_id'), semester_id=request.form.get('semester_id'))
    redirect_path = request.form.get("redirect")
    if redirect_path:
        return redirect(redirect_path)
    return redirect(url_for('institution.manage_users'))




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
    with get_session() as db_session:
        institution_model = InstitutionModel(db_session)
        institution_id = session.get('institution_id')
        institution = institution_model.get_one(institution_id=institution_id)
        
        # Convert to dict to avoid DetachedInstanceError
        institution_data = {
            "institution_name": institution.name if institution else "",
            "address": institution.address if institution else "",
            "phone_number": institution.poc_phone if institution else "",
            "point_of_contact": institution.poc_name if institution else "",
            "email": institution.poc_email if institution else "",
        }
        
        context = {
            "institution": institution_data,
        }
    return render_template('institution/admin/institution_admin_institution_profile.html', **context)

@institution_bp.route('/institution_profile/edit_form')
@requires_roles('admin')
def edit_institution_profile_form():
    with get_session() as db_session:
        institution_model = InstitutionModel(db_session)
        institution_id = session.get('institution_id')
        institution = institution_model.get_one(institution_id=institution_id)
        institution_data = {
            "institution_name": institution.name if institution else "",
            "address": institution.address if institution else "",
            "phone_number": institution.poc_phone if institution else "",
            "point_of_contact": institution.poc_name if institution else "",
            "email": institution.poc_email if institution else "",
        }
    return render_template('institution/admin/institution_admin_profile_update.html', institution=institution_data)

@institution_bp.route('/institution_profile/edit', methods=['POST'])
@requires_roles('admin')
def edit_institution_profile():
    with get_session() as db_session:
        institution_model = InstitutionModel(db_session)
        institution_id = session.get('institution_id')
        institution = institution_model.get_one(institution_id=institution_id)
        if not institution:
            return abort(404)

        # Update institution details from form data
        institution.name = request.form.get('institution_name')
        institution.address = request.form.get('address')
        institution.poc_phone = request.form.get('phone_number')
        institution.poc_name = request.form.get('point_of_contact')
        institution.poc_email = request.form.get('email')

        institution_model.update(institution)

    return redirect(url_for('institution.institution_profile'))

@institution_bp.route('/import_data')
@requires_roles('admin')
def import_data():
    """Render import institution data page for admins"""
    return render_template('institution/admin/import_institution_data.html')


@institution_bp.route('/attendance/student/')
@requires_roles('admin')
def attendance_student_details():

    return render_template(
        'institution/admin/institution_admin_attendance_management_student_details.html',
    )


@institution_bp.route('/attendance/class/<int:class_id>')
@requires_roles('admin')
def attendance_class_details(class_id):
    with get_session() as db_session:
        class_model = ClassModel(db_session)
        if not class_model.class_is_institution(class_id, session.get('institution_id')):
            return abort(401)
        class_obj = class_model.get_by_id(class_id)
        context = {
            "class": class_model.admin_class_details(class_id),
            "records": class_model.get_attendance_records(class_id),
            "class_id": class_id,
            "course_id": class_obj.course_id if class_obj else None,
            "course_name": class_model.get_course_name(class_id),
        }
    return render_template('institution/admin/institution_admin_attendance_management_class_details.html', **context)


@institution_bp.route('/manage_attendance')
@requires_roles('admin')
def manage_attendance():
    institution_id = session.get('institution_id')
    with get_session() as db_session:
        class_model = ClassModel(db_session)
        classes = class_model.get_all_classes_with_attendance(institution_id)

    return render_template('institution/admin/institution_admin_attendance_management.html', classes=classes)


@institution_bp.route('/attendance/reports')
@requires_roles('admin')
def attendance_reports():
    """Show attendance reports view (admin view)"""
    institution_id = session.get('institution_id')
    
    try:
        with get_session() as db_session:
            attendance_model = AttendanceRecordModel(db_session)
            course_model = CourseModel(db_session)
            user_model = UserModel(db_session)
            
            # Get all courses for this institution
            courses = course_model.get_all(institution_id=institution_id)
            course_ids = [c.course_id for c in courses] if courses else []
            
            if not course_ids:
                return render_template(
                    'institution/admin/institution_admin_attendance_management_report.html',
                    daily_report={'present_pct': 0, 'absent_pct': 0, 'total_students': 0, 'trending_absentees': []},
                    weekly_report={'present_pct': 0, 'absent_pct': 0, 'total_classes': 0, 'trending_absentees': []},
                    monthly_report={'present_pct': 0, 'absent_pct': 0, 'total_sessions': 0, 'trending_absentees': []}
                )
            
            # Calculate Daily Report (today)
            today = date.today()
            daily_classes = (
                db_session.query(Class)
                .join(Course, Class.course_id == Course.course_id)
                .filter(Course.institution_id == institution_id)
                .filter(func.date(Class.start_time) == today)
                .all()
            )
            
            daily_stats = calculate_period_stats(
                db_session, daily_classes, user_model, 'daily'
            )
            
            # Calculate Weekly Report (last 7 days)
            week_start = today - timedelta(days=6)
            weekly_classes = (
                db_session.query(Class)
                .join(Course, Class.course_id == Course.course_id)
                .filter(Course.institution_id == institution_id)
                .filter(func.date(Class.start_time) >= week_start)
                .filter(func.date(Class.start_time) <= today)
                .all()
            )
            
            weekly_stats = calculate_period_stats(
                db_session, weekly_classes, user_model, 'weekly'
            )
            
            # Calculate Monthly Report (last 30 days)
            month_start = today - timedelta(days=29)
            monthly_classes = (
                db_session.query(Class)
                .join(Course, Class.course_id == Course.course_id)
                .filter(Course.institution_id == institution_id)
                .filter(func.date(Class.start_time) >= month_start)
                .filter(func.date(Class.start_time) <= today)
                .all()
            )
            
            monthly_stats = calculate_period_stats(
                db_session, monthly_classes, user_model, 'monthly'
            )
            
            context = {
                'daily_report': daily_stats,
                'weekly_report': weekly_stats,
                'monthly_report': monthly_stats
            }
            
        return render_template(
            'institution/admin/institution_admin_attendance_management_report.html',
            **context
        )
        
    except Exception as e:
        current_app.logger.error(f"Error loading attendance reports: {e}")
        flash('Error loading attendance reports', 'danger')
        return render_template(
            'institution/admin/institution_admin_attendance_management_report.html',
            daily_report={'present_pct': 0, 'absent_pct': 0, 'total_students': 0, 'trending_absentees': []},
            weekly_report={'present_pct': 0, 'absent_pct': 0, 'total_classes': 0, 'trending_absentees': []},
            monthly_report={'present_pct': 0, 'absent_pct': 0, 'total_sessions': 0, 'trending_absentees': []}
        )


def calculate_period_stats(db_session, classes, user_model, period_type):
    """Calculate attendance statistics for a period"""
    
    if not classes:
        return {
            'present_pct': 0,
            'absent_pct': 0,
            'total_students': 0,
            'total_classes': 0,
            'total_sessions': 0,
            'trending_absentees': []
        }
    
    class_ids = [c.class_id for c in classes]
    
    # Get all attendance records for these classes
    attendance_records = (
        db_session.query(AttendanceRecord)
        .filter(AttendanceRecord.class_id.in_(class_ids))
        .all()
    )
    
    # Get all unique students who should have attended
    student_ids = set()
    for cls in classes:
        # Get students enrolled in the course
        course_students = (
            db_session.query(CourseUser.user_id)
            .filter(CourseUser.course_id == cls.course_id)
            .all()
        )
        student_ids.update([s[0] for s in course_students])
    
    student_ids = list(student_ids)
    total_students = len(student_ids)
    
    # Calculate attendance statistics
    # Count present/late and absent records
    present_count = sum(1 for r in attendance_records if r.status in ['present', 'late'])
    absent_count = sum(1 for r in attendance_records if r.status == 'absent')
    
    # Calculate total possible attendances (classes * students)
    total_possible = len(classes) * total_students if total_students > 0 else 0
    
    # Calculate percentages based on marked records (present + absent)
    marked_records = present_count + absent_count
    if marked_records > 0:
        present_pct = round((present_count / marked_records) * 100)
        absent_pct = round((absent_count / marked_records) * 100)
    else:
        present_pct = absent_pct = 0
    
    # Calculate trending absentees (students with most absences)
    student_absences = defaultdict(int)
    student_names = {}
    
    for record in attendance_records:
        if record.status == 'absent':
            student_absences[record.student_id] += 1
            if record.student_id not in student_names:
                student = user_model.get_by_id(record.student_id)
                student_names[record.student_id] = student.name if student else f"Student {record.student_id}"
    
    # Sort by absences and get top 3
    sorted_absentees = sorted(
        student_absences.items(),
        key=lambda x: x[1],
        reverse=True
    )[:3]
    
    trending_absentees = []
    for student_id, absences in sorted_absentees:
        student_name = student_names.get(student_id, f"Student {student_id}")
        if period_type == 'daily':
            trending_absentees.append({
                'name': student_name,
                'count': f"{absences} day{'s' if absences > 1 else ''}"
            })
        elif period_type == 'weekly':
            trending_absentees.append({
                'name': student_name,
                'count': f"{absences} class{'es' if absences > 1 else ''}"
            })
        else:  # monthly
            trending_absentees.append({
                'name': student_name,
                'count': f"{absences} session{'s' if absences > 1 else ''}"
            })
    
    return {
        'present_pct': present_pct,
        'absent_pct': absent_pct,
        'total_students': total_students,
        'total_classes': len(classes),
        'total_sessions': len(classes),
        'trending_absentees': trending_absentees
    }
    

# user edit page
@institution_bp.route('/manage_users/<int:user_id>/edit', methods=['GET'])
@requires_roles('admin')
def edit_user_details(user_id):
    with get_session() as db_session:
        user_model = UserModel(db_session)
        user = user_model.get_by_id(user_id)
        user_details = user.as_sanitized_dict()
        if user.role == 'admin' or user.institution_id != session.get('institution_id'):
            return abort(401)
    return render_template(
        'institution/admin/institution_admin_user_management_user_edit.html',
        user_details=user_details,
    )

@institution_bp.route('/manage_users/<int:user_id>/edit', methods=['POST'])
@requires_roles('admin')
def update_user_details(user_id):
    with get_session() as db_session:
        user_model = UserModel(db_session)
        user = user_model.get_by_id(user_id)
        if user.role == 'admin' or user.institution_id != session.get('institution_id'):
            return abort(401)
        #update user details
        user_model.update(user_id,
            name=request.form.get('name'),
            gender=request.form.get('gender'),
            email=request.form.get('email'),
            phone_number=request.form.get('phone_number'),
            age=request.form.get('age')
        )
    return redirect(url_for('institution.view_user_details', user_id=user_id))

@institution_bp.route('/manage_appeals')
@requires_roles('admin')
def manage_appeals():
    with get_session() as db_session:
        institution_id = session.get('institution_id')
        appeal_model = AttendanceAppealModel(db_session)
        
        # Get all appeals for the institution
        appeals = appeal_model.get_institution_appeals(institution_id)
        
    return render_template('institution/admin/institution_admin_appeal_management.html', appeals=appeals)  

@institution_bp.route('/manage_appeals/<int:appeal_id>/view')
@requires_roles('admin')
def view_appeal(appeal_id):
    """View detailed information about a specific appeal"""
    institution_id = session.get('institution_id')
    
    with get_session() as db_session:
        appeal_model = AttendanceAppealModel(db_session)
        course_model = CourseModel(db_session)
        appeal = appeal_model.get_appeal_with_details(appeal_id)
        
        # Verify the appeal belongs to this institution
        if appeal:
            # Check if the course belongs to this institution
            course = course_model.get_one(code=appeal['course_code'])
            if course and course.institution_id != institution_id:
                abort(403)
        else:
            flash("Appeal not found", "error")
            return redirect(url_for('institution.manage_appeals'))
    
    return render_template(
        'institution/admin/institution_admin_view_appeal.html',
        appeal=appeal
    )

@institution_bp.route('/manage_appeals/<int:appeal_id>/process', methods=['POST'])
@requires_roles('admin')
def process_appeal(appeal_id):
    """Process an appeal (approve or reject)"""
    institution_id = session.get('institution_id')
    action = request.form.get('action')
    
    if action not in ['approve', 'reject']:
        flash("Invalid action", "error")
        return redirect(url_for('institution.view_appeal', appeal_id=appeal_id))
    
    with get_session() as db_session:
        appeal_model = AttendanceAppealModel(db_session)
        attendance_model = AttendanceRecordModel(db_session)
        course_model = CourseModel(db_session)
        
        # Get appeal details
        appeal = appeal_model.get_appeal_with_details(appeal_id)
        
        if not appeal:
            flash("Appeal not found", "error")
            return redirect(url_for('institution.manage_appeals'))
        
        # Verify the appeal belongs to this institution
        course = course_model.get_one(code=appeal['course_code'])
        if not course or course.institution_id != institution_id:
            abort(403)
        
        # Check if appeal is already processed
        if appeal['status'] != 'pending':
            flash(f"This appeal has already been {appeal['status']}", "error")
            return redirect(url_for('institution.view_appeal', appeal_id=appeal_id))
        
        # Update appeal status
        new_status = 'approved' if action == 'approve' else 'rejected'
        appeal_model.update_status(appeal_id, new_status)
        
        # If approved, update the attendance record to 'present'
        if action == 'approve':
            attendance_record = attendance_model.get_by_id(appeal['attendance_id'])
            if attendance_record:
                attendance_record.status = 'present'
                db_session.commit()
        
        flash(f"Appeal has been {new_status} successfully", "success")
    
    return redirect(url_for('institution.manage_appeals'))

@institution_bp.route('/student_class_attendance_details/<int:course_id>/<int:class_id>/<int:student_id>')  
@requires_roles('admin')
def student_class_attendance_details(course_id, class_id, student_id):
    with get_session() as db_session:
        class_model = ClassModel(db_session)
        user_model = UserModel(db_session)
        course_model = CourseModel(db_session)
        venue_model = VenueModel(db_session)
        attendance_model = AttendanceRecordModel(db_session)
        
        # Verify that the course belongs to the institution
        if not course_model.get_by_id(course_id).institution_id == session.get('institution_id'):
            return abort(401)
        # Verify that the class belongs to the institution
        if not class_model.class_is_institution(class_id, session.get('institution_id')):
            return abort(401)
        # Verify that the student is part of the institution
        student = user_model.get_by_id(student_id)
        if not student or student.institution_id != session.get('institution_id'):
            return abort(401)
        user = user_model.get_by_id(student_id)
        student_details = user.as_sanitized_dict() if user else None
        
        course = course_model.get_by_id(course_id)
        course_details = {
            "course_id": course.course_id,
            "name": course.name,
        }
        
        venue = venue_model.get_by_id(class_model.get_by_id(class_id).venue_id)
        venue_details = {
            "venue_id": venue.venue_id,
            "name": venue.name,
        }


        attendance_record = attendance_model.get_student_class_attendance(student_id, class_id)
        record_details = {
            "attendance_id": attendance_record.attendance_id if attendance_record else None,
            "status": attendance_record.status if attendance_record else None,
            "marked_by": attendance_record.marked_by if attendance_record else None,
            "lecturer_id": attendance_record.lecturer_id if attendance_record else None,
            "notes": attendance_record.notes if attendance_record else None,
            "recorded_at": attendance_record.recorded_at if attendance_record else None,
        }
        class_details = class_model.get_by_id(class_id)
        class_details = {
            "class_id": class_details.class_id,
            "start_time": class_details.start_time,
            "end_time": class_details.end_time,
            "lecturer_id": class_details.lecturer_id,
            "lecturer_name": user_model.get_by_id(class_details.lecturer_id).name if user_model.get_by_id(class_details.lecturer_id) else "Unknown",
        }
        
    
        
    return render_template(
        'institution/admin/institution_admin_student_class_attendance_page.html',
        course_details=course_details,
        class_details=class_details,
        student_id=student_id, 
        student_details=student_details,
        venue_details=venue_details,
        record_details=record_details

    )

@institution_bp.route('/student_class_attendance_details/<int:course_id>/<int:class_id>/<int:student_id>', methods=['POST'])
@requires_roles('admin')
def update_student_class_attendance(course_id, class_id, student_id):
    """Update attendance status for a specific student in a class"""
    with get_session() as db_session:
        class_model = ClassModel(db_session)
        user_model = UserModel(db_session)
        course_model = CourseModel(db_session)
        attendance_model = AttendanceRecordModel(db_session)
        
        # Verify that the course belongs to the institution
        if not course_model.get_by_id(course_id).institution_id == session.get('institution_id'):
            return abort(401)
        # Verify that the class belongs to the institution
        if not class_model.class_is_institution(class_id, session.get('institution_id')):
            return abort(401)
        # Verify that the student is part of the institution
        student = user_model.get_by_id(student_id)
        if not student or student.institution_id != session.get('institution_id'):
            return abort(401)
        
        # Get the new attendance status from the form
        new_status = request.form.get('attendance')
        notes = request.form.get('notes', '')
        
        # Validate status
        valid_statuses = ['present', 'absent', 'late', 'excused']
        if new_status not in valid_statuses:
            flash('Invalid attendance status', 'error')
            return redirect(url_for('institution.attendance_class_details', class_id=class_id))
        
        # Check if attendance record exists
        attendance_record = attendance_model.get_student_class_attendance(student_id, class_id)
        
        if attendance_record:
            # Update existing record
            attendance_model.update(
                attendance_record.attendance_id,
                status=new_status,
                marked_by='lecturer',
                lecturer_id=session.get('user_id'),
                notes=notes
            )
            flash(f'Attendance updated to {new_status.capitalize()}', 'success')
            return redirect(url_for('institution.attendance_class_details', class_id=class_id))
        else:
            # No record exists - create a new one
            attendance_model.create(
                class_id=class_id,
                student_id=student_id,
                status=new_status,
                marked_by='lecturer',
                lecturer_id=session.get('user_id'),
                notes=notes
            )
            flash(f'Attendance marked as {new_status.capitalize()}', 'success')
            return redirect(url_for('institution.attendance_class_details', class_id=class_id))

            