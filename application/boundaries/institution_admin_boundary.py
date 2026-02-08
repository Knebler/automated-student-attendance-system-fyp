from flask import Blueprint, render_template, request, session, current_app, flash, redirect, url_for, abort, jsonify, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from application.controls.auth_control import requires_roles
from application.controls.import_data_control import ALL_IMPORT_JOBS, submit_import_data_job
from application.entities2 import *
from database.base import get_session
from database.models import *
from datetime import date, timedelta, datetime
from collections import defaultdict
import json
import time

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
        sub_plan_model = SubscriptionPlanModel(db_session)
        class_model = ClassModel(db_session)
        
        # Update class statuses on dashboard load
        class_model.update_class_statuses(institution_id=institution_id)
        
        institution = institution_model.get_one(institution_id=institution_id)
        institution_name = institution.name if institution else "Unknown Institution"

        sub = sub_model.get_by_id(institution.subscription_id)
        sub_active = True if sub and sub.is_active else False
        max_users_allowed = sub_plan_model.get_max_users_allowed(sub.plan_id) if sub else None
        total_users = user_model.count_by_institution(institution_id=institution_id)

        context = {
            "institution": {
                "name": institution_name,
                "is_active": sub_active,
                "renewal": sub.end_date,
            },
            "overview": user_model.admin_user_stats(institution_id),
            "classes": class_model.admin_dashboard_classes_today(institution_id),
            "max_users_allowed": max_users_allowed,
            "total_users": total_users
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

@institution_bp.route('/manage_users/add', methods=['GET'])
@requires_roles('admin')
def add_user_form():
    """Display form to add a new user (student or lecturer only)"""
    return render_template('institution/admin/institution_admin_add_user.html')

@institution_bp.route('/manage_users/add', methods=['POST'])
@requires_roles('admin')
def add_user():
    """Create a new user (student or lecturer only)"""
    from application.controls.auth_control import hash_password
    
    role = request.form.get('role')
    
    # Restrict to student and lecturer roles only
    if role not in ['student', 'lecturer']:
        flash('Only students and lecturers can be added.', 'error')
        return redirect(url_for('institution.add_user_form'))
    
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    age = request.form.get('age')
    gender = request.form.get('gender')
    phone_number = request.form.get('phone_number')
    institution_id = session.get('institution_id')
    
    # Validate required fields
    if not all([name, email, password, role]):
        flash('Name, email, password, and role are required.', 'error')
        return redirect(url_for('institution.add_user_form'))
    
    with get_session() as db_session:
        user_model = UserModel(db_session)
        
        # Check if email already exists
        existing_user = user_model.get_by_email(email)
        if existing_user:
            flash('A user with this email already exists.', 'error')
            return redirect(url_for('institution.add_user_form'))
        
        try:
            # Create new user
            user_model.create(
                institution_id=institution_id,
                role=role,
                name=name,
                email=email,
                password_hash=hash_password(password),
                age=int(age) if age else None,
                gender=gender if gender else None,
                phone_number=phone_number if phone_number else None,
                is_active=True
            )
            flash(f'{role.capitalize()} account created successfully.', 'success')
            return redirect(url_for('institution.manage_users'))
        except Exception as e:
            flash(f'Error creating user: {str(e)}', 'error')
            return redirect(url_for('institution.add_user_form'))

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

@institution_bp.route('/manage_classes/add', methods=['GET'])
@requires_roles('admin')
def add_course_form():
    """Display form to add a new course"""
    institution_id = session.get('institution_id')
    with get_session() as db_session:
        user_model = UserModel(db_session)
        # Get all lecturers from the institution
        lecturers = user_model.get_by_institution_and_role(institution_id, 'lecturer')
        lecturers = [{'user_id': l.user_id, 'name': l.name} for l in lecturers]
    return render_template('institution/admin/institution_admin_add_course.html', lecturers=lecturers)

@institution_bp.route('/manage_classes/add', methods=['POST'])
@requires_roles('admin')
def add_course():
    """Create a new course"""
    code = request.form.get('code')
    name = request.form.get('name')
    description = request.form.get('description')
    credits = request.form.get('credits')
    lecturer_id = request.form.get('lecturer_id')
    institution_id = session.get('institution_id')
    
    # Validate required fields
    if not all([code, name]):
        flash('Course code and name are required.', 'error')
        return redirect(url_for('institution.add_course_form'))
    
    with get_session() as db_session:
        course_model = CourseModel(db_session)
        
        # Check if course code already exists in this institution
        existing_course = course_model.get_one(institution_id=institution_id, code=code)
        if existing_course:
            flash('A course with this code already exists in your institution.', 'error')
            return redirect(url_for('institution.add_course_form'))
        
        try:
            # Create new course
            new_course = course_model.create(
                institution_id=institution_id,
                code=code,
                name=name,
                description=description if description else None,
                credits=int(credits) if credits else None
            )
            
            # Assign lecturer to course if selected
            if lecturer_id:
                course_user_model = CourseUserModel(db_session)
                semester_model = SemesterModel(db_session)
                
                # Get or create a default semester for the institution
                # You might want to add semester selection in the form later
                semesters = semester_model.get_all(institution_id=institution_id)
                if semesters:
                    semester_id = semesters[0].semester_id
                    course_user_model.assign(
                        course_id=new_course.course_id,
                        user_id=int(lecturer_id),
                        semester_id=semester_id
                    )
            
            flash(f'Course "{name}" created successfully.', 'success')
            return redirect(url_for('institution.manage_classes'))
        except Exception as e:
            flash(f'Error creating course: {str(e)}', 'error')
            return redirect(url_for('institution.add_course_form'))

@institution_bp.route('/manage_classes/<int:course_id>')
@requires_roles('admin')
def module_details(course_id):
    """Render the module details page for admins"""
    with get_session() as db_session:
        class_model = ClassModel(db_session)
        course_model = CourseModel(db_session)
        if course_model.get_by_id(course_id).institution_id != session.get('institution_id'):
            return abort(401)
        # Get all classes with their status
        all_classes = class_model.get_all_with_status(course_id)
        context = {
            "course": course_model.get_manage_course_info(session.get('institution_id'), course_id)[0],
            "classes": all_classes,
        }
    return render_template('institution/admin/institution_admin_class_management_module_details.html', **context)

@institution_bp.route('/manage_classes/<int:course_id>/delete', methods=['POST'])
@requires_roles('admin')
def delete_course(course_id):
    """Delete a course"""
    institution_id = session.get('institution_id')
    
    with get_session() as db_session:
        course_model = CourseModel(db_session)
        
        # Verify course belongs to the institution
        course = course_model.get_by_id(course_id)
        if not course:
            flash('Course not found.', 'error')
            return redirect(url_for('institution.manage_classes'))
        
        if course.institution_id != institution_id:
            flash('You do not have permission to delete this course.', 'error')
            return redirect(url_for('institution.manage_classes'))
        
        try:
            # Delete the course (cascade will handle related records)
            course_name = course.name
            success = course_model.delete(course_id)
            
            if success:
                flash(f'Course "{course_name}" has been successfully deleted.', 'success')
            else:
                flash('Failed to delete the course.', 'error')
                
        except Exception as e:
            flash(f'Error deleting course: {str(e)}', 'error')
    
    return redirect(url_for('institution.manage_classes'))

@institution_bp.route('/manage_classes/<int:course_id>/add_class', methods=['GET'])
@requires_roles('admin')
def add_class_form(course_id):
    """Display form to add a new class to a course"""
    institution_id = session.get('institution_id')
    
    with get_session() as db_session:
        course_model = CourseModel(db_session)
        user_model = UserModel(db_session)
        venue_model = VenueModel(db_session)
        semester_model = SemesterModel(db_session)
        
        # Verify course belongs to institution
        course = course_model.get_by_id(course_id)
        if not course or course.institution_id != institution_id:
            flash('Course not found or access denied.', 'error')
            return redirect(url_for('institution.manage_classes'))
        
        # Get the course's assigned lecturer(s)
        course_lecturers = (
            db_session.query(User)
            .join(CourseUser, CourseUser.user_id == User.user_id)
            .filter(CourseUser.course_id == course_id)
            .filter(User.role == 'lecturer')
            .all()
        )
        
        # Get available resources
        venues = venue_model.get_all(institution_id=institution_id)
        semesters = semester_model.get_all(institution_id=institution_id)
        
        context = {
            'course': course.as_dict(),
            'lecturers': [{'user_id': l.user_id, 'name': l.name} for l in course_lecturers],
            'venues': [{'venue_id': v.venue_id, 'name': v.name} for v in venues],
            'semesters': [{'semester_id': s.semester_id, 'name': s.name} for s in semesters]
        }
    
    return render_template('institution/admin/institution_admin_add_class.html', **context)

@institution_bp.route('/manage_classes/<int:course_id>/add_class', methods=['POST'])
@requires_roles('admin')
def add_class(course_id):
    """Create a new class for a course"""
    from datetime import datetime
    
    institution_id = session.get('institution_id')
    
    # Get form data
    semester_id = request.form.get('semester_id')
    venue_id = request.form.get('venue_id')
    lecturer_id = request.form.get('lecturer_id')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    
    # Validate required fields
    if not all([semester_id, venue_id, lecturer_id, start_time, end_time]):
        flash('All fields are required.', 'error')
        return redirect(url_for('institution.add_class_form', course_id=course_id))
    
    try:
        # Parse datetime strings
        start_datetime = datetime.fromisoformat(start_time)
        end_datetime = datetime.fromisoformat(end_time)
        
        # Validate times
        if end_datetime <= start_datetime:
            flash('End time must be after start time.', 'error')
            return redirect(url_for('institution.add_class_form', course_id=course_id))
        
        with get_session() as db_session:
            course_model = CourseModel(db_session)
            class_model = ClassModel(db_session)
            
            # Verify course belongs to institution
            course = course_model.get_by_id(course_id)
            if not course or course.institution_id != institution_id:
                flash('Course not found or access denied.', 'error')
                return redirect(url_for('institution.manage_classes'))
            
            # Create the class
            new_class = class_model.create(
                course_id=course_id,
                semester_id=int(semester_id),
                venue_id=int(venue_id),
                lecturer_id=int(lecturer_id),
                start_time=start_datetime,
                end_time=end_datetime,
                status='scheduled'
            )
            
            flash(f'Class created successfully (ID: {new_class.class_id})', 'success')
            return redirect(url_for('institution.module_details', course_id=course_id))
            
    except ValueError as e:
        flash(f'Invalid date/time format: {str(e)}', 'error')
        return redirect(url_for('institution.add_class_form', course_id=course_id))
    except Exception as e:
        flash(f'Error creating class: {str(e)}', 'error')
        return redirect(url_for('institution.add_class_form', course_id=course_id))

@institution_bp.route('/manage_classes/<int:course_id>/edit_class/<int:class_id>', methods=['GET'])
@requires_roles('admin')
def edit_class_form(course_id, class_id):
    """Display form to edit a class"""
    institution_id = session.get('institution_id')
    
    with get_session() as db_session:
        course_model = CourseModel(db_session)
        class_model = ClassModel(db_session)
        venue_model = VenueModel(db_session)
        
        # Verify course belongs to institution
        course = course_model.get_by_id(course_id)
        if not course or course.institution_id != institution_id:
            flash('Course not found or access denied.', 'error')
            return redirect(url_for('institution.manage_classes'))
        
        # Get the class to edit
        cls = class_model.get_by_id(class_id)
        if not cls or cls.course_id != course_id:
            flash('Class not found or does not belong to this course.', 'error')
            return redirect(url_for('institution.module_details', course_id=course_id))
        
        # Get available venues
        venues = venue_model.get_all(institution_id=institution_id)
        
        context = {
            'course': course.as_dict(),
            'class': cls.as_dict(),
            'venues': [{'venue_id': v.venue_id, 'name': v.name} for v in venues]
        }
    
    return render_template('institution/admin/institution_admin_edit_class.html', **context)

@institution_bp.route('/manage_classes/<int:course_id>/edit_class/<int:class_id>', methods=['POST'])
@requires_roles('admin')
def edit_class(course_id, class_id):
    """Update a class"""
    from datetime import datetime
    
    institution_id = session.get('institution_id')
    
    # Get form data
    venue_id = request.form.get('venue_id')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    
    # Validate required fields
    if not all([venue_id, start_time, end_time]):
        flash('All fields are required.', 'error')
        return redirect(url_for('institution.edit_class_form', course_id=course_id, class_id=class_id))
    
    try:
        # Parse datetime strings
        start_datetime = datetime.fromisoformat(start_time)
        end_datetime = datetime.fromisoformat(end_time)
        
        # Validate times
        if end_datetime <= start_datetime:
            flash('End time must be after start time.', 'error')
            return redirect(url_for('institution.edit_class_form', course_id=course_id, class_id=class_id))
        
        with get_session() as db_session:
            course_model = CourseModel(db_session)
            class_model = ClassModel(db_session)
            venue_model = VenueModel(db_session)
            
            # Verify course belongs to institution
            course = course_model.get_by_id(course_id)
            course_code = course.code if course else "Unknown"
            if not course or course.institution_id != institution_id:
                flash('Course not found or access denied.', 'error')
                return redirect(url_for('institution.manage_classes'))
            
            # Verify class belongs to course
            cls = class_model.get_by_id(class_id)
            if not cls or cls.course_id != course_id:
                flash('Class not found or does not belong to this course.', 'error')
                return redirect(url_for('institution.module_details', course_id=course_id))
            
            # Update the class
            class_model.update(
                class_id,
                venue_id=int(venue_id),
                start_time=start_datetime,
                end_time=end_datetime
            )
            
                 # Announcement update
            announcement_model = AnnouncementModel(db_session)
            announcement_model.create_announcement(
                institution_id=institution_id,
                requested_by_user_id=session.get('user_id'),
                title=f'Class {course_code} - {class_id} Updated',
                content=f"Class {course_code} - {class_id} has been updated to {start_time} - {end_time} at {venue_model.get_by_id(int(venue_id)).name}."
            )
            
            flash('Class updated successfully', 'success')
            return redirect(url_for('institution.module_details', course_id=course_id))
            
    except ValueError as e:
        flash(f'Invalid date/time format: {str(e)}', 'error')
        return redirect(url_for('institution.edit_class_form', course_id=course_id, class_id=class_id))
    except Exception as e:
        flash(f'Error updating class: {str(e)}', 'error')
        return redirect(url_for('institution.edit_class_form', course_id=course_id, class_id=class_id))

@institution_bp.route('/manage_classes/<int:course_id>/cancel_class/<int:class_id>', methods=['POST'])
@requires_roles('admin')
def cancel_class(course_id, class_id):
    """Cancel a class"""
    institution_id = session.get('institution_id')
    
    with get_session() as db_session:
        course_model = CourseModel(db_session)
        class_model = ClassModel(db_session)
        announcement_model = AnnouncementModel(db_session)
        
        # Verify course belongs to institution
        course = course_model.get_by_id(course_id)
        course_code = course.code if course else "Unknown"
        if not course or course.institution_id != institution_id:
            flash('Course not found or access denied.', 'error')
            return redirect(url_for('institution.manage_classes'))
        
        # Get the class
        cls = class_model.get_by_id(class_id)
        if not cls:
            flash('Class not found.', 'error')
            return redirect(url_for('institution.module_details', course_id=course_id))
        
        # Verify class belongs to the course
        if cls.course_id != course_id:
            flash('Class does not belong to this course.', 'error')
            return redirect(url_for('institution.module_details', course_id=course_id))
        
        # Check if class is already completed
        if cls.status == 'completed':
            flash('Cannot cancel a completed class.', 'error')
            return redirect(url_for('institution.module_details', course_id=course_id))
        
        # Check if class is already cancelled
        if cls.status == 'cancelled':
            flash('Class is already cancelled.', 'warning')
            return redirect(url_for('institution.module_details', course_id=course_id))
        
        try:
            # Update class status to cancelled
            cls.status = 'cancelled'
            announcement_model.create_announcement(institution_id, cls.lecturer_id, f'Class {course_code} - {class_id} Cancelled', f'Class {course_code} - {class_id} cancelled by admin')
            # Get all attendance records for this class
            attendance_records = (
                db_session.query(AttendanceRecord)
                .filter(AttendanceRecord.class_id == class_id)
                .all()
            )
            
            # Update all attendance records to 'excused'
            excused_count = 0
            for record in attendance_records:
                if record.status != 'excused':
                    record.status = 'excused'
                    if not record.notes:
                        record.notes = 'Class cancelled by admin'
                    else:
                        record.notes += ' | Class cancelled by admin'
                    excused_count += 1
            
            # Get all enrolled students who don't have attendance records yet
            enrolled_students = (
                db_session.query(User.user_id)
                .join(CourseUser, CourseUser.user_id == User.user_id)
                .filter(CourseUser.course_id == cls.course_id)
                .filter(CourseUser.semester_id == cls.semester_id)
                .filter(User.role == 'student')
                .all()
            )
            
            student_ids = [s[0] for s in enrolled_students]
            
            # Get students who already have attendance records
            existing_student_ids = {r.student_id for r in attendance_records}
            
            # Create 'excused' records for students without attendance
            created_count = 0
            for student_id in student_ids:
                if student_id not in existing_student_ids:
                    new_record = AttendanceRecord(
                        class_id=class_id,
                        student_id=student_id,
                        status='excused',
                        marked_by='system',
                        notes='Class cancelled by admin'
                    )
                    db_session.add(new_record)
                    created_count += 1
            
            db_session.commit()
            
            total_affected = excused_count + created_count
            flash(f'Class on {cls.start_time.strftime("%Y-%m-%d %H:%M")} has been cancelled successfully. {total_affected} student(s) marked as excused.', 'success')
            return redirect(url_for('institution.module_details', course_id=course_id))
            
        except Exception as e:
            db_session.rollback()
            flash(f'Error cancelling class: {str(e)}', 'error')
            return redirect(url_for('institution.module_details', course_id=course_id))

@institution_bp.route('/manage_classes/<int:course_id>/delete_class/<int:class_id>', methods=['POST'])
@requires_roles('admin')
def delete_class(course_id, class_id):
    """Delete a cancelled class and its attendance records"""
    institution_id = session.get('institution_id')
    
    with get_session() as db_session:
        course_model = CourseModel(db_session)
        class_model = ClassModel(db_session)
        
        # Verify course belongs to institution
        course = course_model.get_by_id(course_id)
        if not course or course.institution_id != institution_id:
            flash('Course not found or access denied.', 'error')
            return redirect(url_for('institution.manage_classes'))
        
        # Get the class
        cls = class_model.get_by_id(class_id)
        if not cls:
            flash('Class not found.', 'error')
            return redirect(url_for('institution.module_details', course_id=course_id))
        
        # Verify class belongs to the course
        if cls.course_id != course_id:
            flash('Class does not belong to this course.', 'error')
            return redirect(url_for('institution.module_details', course_id=course_id))
        
        # Only allow deletion of cancelled classes
        if cls.status != 'cancelled':
            flash('Only cancelled classes can be deleted. Please cancel the class first.', 'error')
            return redirect(url_for('institution.module_details', course_id=course_id))
        
        try:
            # Store class details for the success message before deletion
            class_time = cls.start_time.strftime("%Y-%m-%d %H:%M")
            
            # Count records that will be deleted (for user feedback)
            attendance_count = (
                db_session.query(AttendanceRecord)
                .filter(AttendanceRecord.class_id == class_id)
                .count()
            )
            
            # Delete the class - CASCADE will automatically delete:
            # 1. All attendance_records (via class_id FK with CASCADE)
            # 2. All attendance_appeals (via attendance_id FK with CASCADE)
            db_session.delete(cls)
            db_session.commit()
            
            flash(f'Class on {class_time} has been permanently deleted along with {attendance_count} attendance record(s).', 'success')
            return redirect(url_for('institution.module_details', course_id=course_id))
            
        except Exception as e:
            db_session.rollback()
            flash(f'Error deleting class: {str(e)}', 'error')
            return redirect(url_for('institution.module_details', course_id=course_id))

@institution_bp.route('/institution_profile')
@requires_roles('admin')
def institution_profile():
    """Render the institution profile page for admins"""
    with get_session() as db_session:
        institution_model = InstitutionModel(db_session)
        user_model = UserModel(db_session)
        subscription_model = SubscriptionModel(db_session)
        sub_plan_model = SubscriptionPlanModel(db_session)
        institution_id = session.get('institution_id')
        institution = institution_model.get_one(institution_id=institution_id)
        subscription = subscription_model.get_by_id(institution.subscription_id) if institution else None
        sub_plan = sub_plan_model.get_by_id(subscription.plan_id) if subscription else None
        user_count = user_model.count_by_institution(institution_id=institution_id)
        max_allowed_users = sub_plan_model.get_max_users_allowed(subscription.plan_id) if sub_plan else None
        sub_status = "Active" if subscription and subscription.is_active else "Inactive"
        # Convert to dict to avoid DetachedInstanceError
        institution_data = {
            "institution_name": institution.name if institution else "",
            "address": institution.address if institution else "",
            "phone_number": institution.poc_phone if institution else "",
            "point_of_contact": institution.poc_name if institution else "",
            "email": institution.poc_email if institution else "",
            "subscription_plan_name": sub_plan.name if sub_plan else "",
            "subscription_start_date": subscription.start_date if subscription else None,
            "subscription_end_date": subscription.end_date if subscription else None,
            "user_count": user_count,
            "max_allowed_users": max_allowed_users,
            "subscription_status": sub_status,
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

@institution_bp.route('/import_data/upload_facial', methods=['POST'])
@requires_roles('admin')
def upload_facial_data():
    """Upload and import facial recognition data from JSON file"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.json'):
        return jsonify({'success': False, 'error': 'Only JSON files are supported'}), 400
    
    try:
        import json
        import base64
        from datetime import datetime
        from database.models import FacialData, User
        
        # Read and parse JSON file
        file_content = file.read()
        data = json.loads(file_content)
        
        students = data.get('students', [])
        if not students:
            return jsonify({'success': False, 'error': 'No student data found in file'}), 400
        
        institution_id = session.get('institution_id')
        stats = {
            'total': len(students),
            'imported': 0,
            'updated': 0,
            'failed': 0,
            'user_not_found': 0,
            'errors': []
        }
        
        with get_session() as db_session:
            for student_data in students:
                user_id = student_data.get('user_id')
                name = student_data.get('name')
                face_encoding_b64 = student_data.get('face_encoding')
                sample_count = student_data.get('sample_count', 0)
                
                # Validate data
                if not user_id or not face_encoding_b64:
                    stats['failed'] += 1
                    stats['errors'].append(f'{name or "Unknown"}: Missing required data')
                    continue
                
                # Check if user exists and belongs to this institution
                user = db_session.query(User).filter(
                    User.user_id == user_id,
                    User.institution_id == institution_id
                ).first()
                
                if not user:
                    stats['user_not_found'] += 1
                    stats['errors'].append(f'{name} (ID: {user_id}): User not found in this institution')
                    continue
                
                try:
                    # Decode base64 to binary
                    face_encoding_binary = base64.b64decode(face_encoding_b64)
                    
                    # Check if facial data already exists
                    existing = db_session.query(FacialData).filter(
                        FacialData.user_id == user_id,
                        FacialData.is_active == True
                    ).first()
                    
                    if existing:
                        # Update existing record
                        existing.face_encoding = face_encoding_binary
                        existing.sample_count = sample_count
                        existing.updated_at = datetime.now()
                        stats['updated'] += 1
                    else:
                        # Insert new record
                        new_facial_data = FacialData(
                            user_id=user_id,
                            face_encoding=face_encoding_binary,
                            sample_count=sample_count,
                            created_at=datetime.now(),
                            updated_at=datetime.now(),
                            is_active=True
                        )
                        db_session.add(new_facial_data)
                        stats['imported'] += 1
                        
                except Exception as e:
                    stats['failed'] += 1
                    stats['errors'].append(f'{name} (ID: {user_id}): {str(e)}')
                    continue
            
            # Commit all changes
            try:
                db_session.commit()
            except Exception as e:
                db_session.rollback()
                return jsonify({
                    'success': False,
                    'error': f'Failed to commit changes: {str(e)}'
                }), 500
        
        # Prepare response
        success_count = stats['imported'] + stats['updated']
        message = f"Import completed: {success_count}/{stats['total']} successful"
        
        if stats['imported'] > 0:
            message += f" ({stats['imported']} new)"
        if stats['updated'] > 0:
            message += f" ({stats['updated']} updated)"
        if stats['user_not_found'] > 0:
            message += f", {stats['user_not_found']} user(s) not found"
        if stats['failed'] > 0:
            message += f", {stats['failed']} failed"
        
        return jsonify({
            'success': True,
            'message': message,
            'stats': stats
        }), 200
        
    except json.JSONDecodeError as e:
        return jsonify({'success': False, 'error': f'Invalid JSON file: {str(e)}'}), 400
    except Exception as e:
        current_app.logger.error(f"Error importing facial data: {e}")
        return jsonify({'success': False, 'error': f'Import failed: {str(e)}'}), 500

@institution_bp.route('/import_data/upload', methods=['POST'])
@requires_roles('admin')
def upload_data():
    if 'file' not in request.files:
        return jsonify({'error': 'No file selected'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    try:
        return jsonify({'job_id': submit_import_data_job(session.get('institution_id'), file.stream.read())}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@institution_bp.route('/import_data/<job_id>', methods=['GET'])
@requires_roles('admin')
def get_status(job_id: str):
    return render_template('institution/admin/import_institution_data_results.html')

@institution_bp.route('/import_data/<job_id>/progress', methods=['GET'])
@requires_roles('admin')
def progress_stream(job_id: str):
    def get_progress():
        while job_id in ALL_IMPORT_JOBS:
            print(f"Progress: {ALL_IMPORT_JOBS[job_id]}")
            yield f"data: {json.dumps(ALL_IMPORT_JOBS[job_id])}\n\n"
            time.sleep(2) # Streams updates every 2 seconds
    return Response(get_progress(), mimetype='text/event-stream')

@institution_bp.route('/attendance/student/')
@requires_roles('admin')
def attendance_student_details():
    return render_template('institution/admin/institution_admin_attendance_management_student_details.html')

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
            "class_status": class_obj.status if class_obj else None,
        }
    return render_template('institution/admin/institution_admin_attendance_management_class_details.html', **context)


@institution_bp.route('/manage_attendance')
@requires_roles('admin')
def manage_attendance():
    institution_id = session.get('institution_id')
    with get_session() as db_session:
        class_model = ClassModel(db_session)
        # Update class statuses before fetching
        class_model.update_class_statuses(institution_id=institution_id)
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

@institution_bp.route('/manage_users/<int:user_id>/account_settings', methods=['POST'])
@requires_roles('admin')
def update_user_account_settings(user_id):
    """Update account settings including suspension status and password"""
    from application.controls.auth_control import hash_password
    
    with get_session() as db_session:
        user_model = UserModel(db_session)
        user = user_model.get_by_id(user_id)
        
        # Security check: prevent editing admins and users from other institutions
        if user.role == 'admin' or user.institution_id != session.get('institution_id'):
            flash('You cannot edit this user.', 'error')
            return abort(401)
        
        action = request.form.get('action')
        
        if action == 'suspend':
            user_model.suspend(user_id)
            flash('User account has been suspended.', 'success')
        elif action == 'unsuspend':
            user_model.unsuspend(user_id)
            flash('User account has been unsuspended.', 'success')
        elif action == 'update':
            # Handle password update
            new_password = request.form.get('new_password', '').strip()
            if new_password:
                # Hash the new password
                password_hash = hash_password(new_password)
                user_model.update(user_id, password_hash=password_hash)
                flash('Password has been updated successfully.', 'success')
            else:
                flash('No changes were made.', 'info')
    
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


@institution_bp.route('/update_class_statuses', methods=['POST'])
@requires_roles('admin')
def update_class_statuses():
    """Manually trigger class status updates for the institution"""
    institution_id = session.get('institution_id')
    
    with get_session() as db_session:
        class_model = ClassModel(db_session)
        updated_count = class_model.update_class_statuses(institution_id=institution_id)
    
    return jsonify({
        'success': True,
        'updated_count': updated_count,
        'message': f'Successfully updated {updated_count} class(es)'
    })

@institution_bp.route('/admin/announcements')
@requires_roles('admin')
def manage_announcements():
    with get_session() as db_session:
        institution_id = session.get('institution_id')
        announcement_model = AnnouncementModel(db_session)
        announcements = announcement_model.get_by_institution(institution_id)
        # Convert to dictionaries to avoid DetachedInstanceError
        announcements_data = [
            {
                'announcement_id': a.announcement_id,
                'title': a.title,
                'content': a.content,
                'date_posted': a.date_posted,
                'requested_by_user_id': a.requested_by_user_id
            }
            for a in announcements
        ]
    return render_template('institution/admin/institution_admin_manage_announcements.html', announcements=announcements_data)

@institution_bp.route('/admin/announcements/create', methods=['GET'])
@requires_roles('admin')
def create_announcement_form():
    """Display form to create a new announcement"""
    return render_template('institution/admin/institution_admin_create_announcement.html')

@institution_bp.route('/admin/announcements/create', methods=['POST'])
@requires_roles('admin')
def create_announcement():
    """Create a new announcement"""
    title = request.form.get('title')
    content = request.form.get('content')
    institution_id = session.get('institution_id')
    user_id = session.get('user_id')
    
    if not all([title, content]):
        flash('Title and content are required', 'error')
        return redirect(url_for('institution.create_announcement_form'))
    
    with get_session() as db_session:
        announcement_model = AnnouncementModel(db_session)
        announcement_model.create_announcement(
            institution_id=institution_id,
            requested_by_user_id=user_id,
            title=title,
            content=content
        )
    
    flash('Announcement created successfully', 'success')
    return redirect(url_for('institution.manage_announcements'))

@institution_bp.route('/admin/announcements/<int:announcement_id>/view', methods=['GET'])
@requires_roles('admin')
def view_announcement(announcement_id):
    """View announcement details"""
    institution_id = session.get('institution_id')
    
    with get_session() as db_session:
        announcement_model = AnnouncementModel(db_session)
        announcement = announcement_model.get_by_id(announcement_id)
        
        if not announcement or announcement.institution_id != institution_id:
            flash('Announcement not found', 'error')
            return redirect(url_for('institution.manage_announcements'))
        
        user_model = UserModel(db_session)
        created_by = user_model.get_by_id(announcement.requested_by_user_id)
        
        # Convert to dictionaries to avoid DetachedInstanceError
        announcement_data = {
            'announcement_id': announcement.announcement_id,
            'title': announcement.title,
            'content': announcement.content,
            'date_posted': announcement.date_posted,
            'requested_by_user_id': announcement.requested_by_user_id
        }
        
        created_by_data = {
            'name': created_by.name if created_by else 'Unknown'
        }
    
    return render_template('institution/admin/institution_admin_view_announcement.html', 
                         announcement=announcement_data, created_by=created_by_data)

@institution_bp.route('/admin/announcements/<int:announcement_id>/delete', methods=['POST'])
@requires_roles('admin')
def delete_announcement(announcement_id):
    """Delete an announcement"""
    institution_id = session.get('institution_id')
    
    with get_session() as db_session:
        announcement_model = AnnouncementModel(db_session)
        announcement = announcement_model.get_by_id(announcement_id)
        
        if not announcement or announcement.institution_id != institution_id:
            flash('Announcement not found', 'error')
            return redirect(url_for('institution.manage_announcements'))
        
        announcement_model.delete(announcement_id)
    
    flash('Announcement deleted successfully', 'success')
    return redirect(url_for('institution.manage_announcements'))


# =====================
# ATTENDANCE AUDIT ROUTES
# =====================

@institution_bp.route('/attendance/class/<int:class_id>/audit', methods=['GET'])
@requires_roles('admin')
def audit_class_attendance(class_id):
    """View audit page for a specific class"""
    institution_id = session.get('institution_id')
    
    with get_session() as db_session:
        class_model = ClassModel(db_session)
        
        # Verify class belongs to institution
        if not class_model.class_is_institution(class_id, institution_id):
            abort(401)
        
        class_obj = class_model.get_by_id(class_id)
        if not class_obj:
            flash('Class not found', 'error')
            return redirect(url_for('institution.manage_attendance'))
        
        # Get attendance records with audit status
        records = db_session.query(AttendanceRecord, User).join(
            User, AttendanceRecord.student_id == User.user_id
        ).filter(
            AttendanceRecord.class_id == class_id
        ).all()
        
        # Format records for display
        formatted_records = []
        for record, student in records:
            formatted_records.append({
                'attendance_id': record.attendance_id,
                'student_id': student.user_id,
                'student_name': student.name,
                'student_email': student.email,
                'status': record.status,
                'audit_status': record.audit_status,
                'audited_at': record.audited_at,
                'marked_by': record.marked_by,
                'recorded_at': record.recorded_at
            })
        
        context = {
            'class': class_model.admin_class_details(class_id),
            'records': formatted_records,
            'class_id': class_id,
            'course_id': class_obj.course_id,
            'course_name': class_model.get_course_name(class_id),
            'class_status': class_obj.status,
        }
    
    return render_template('institution/admin/institution_admin_audit_attendance.html', **context)


@institution_bp.route('/attendance/audit/<int:attendance_id>', methods=['POST'])
@requires_roles('admin')
def audit_attendance_record(attendance_id):
    """Audit a single attendance record using facial recognition"""
    institution_id = session.get('institution_id')
    admin_user_id = session.get('user_id')
    
    data = request.get_json() or {}
    image_data = data.get('image')
    
    if not image_data:
        return jsonify({'success': False, 'error': 'Image data is required'}), 400
    
    try:
        with get_session() as db_session:
            # Get attendance record
            attendance_record = db_session.query(AttendanceRecord).filter(
                AttendanceRecord.attendance_id == attendance_id
            ).first()
            
            if not attendance_record:
                return jsonify({'success': False, 'error': 'Attendance record not found'}), 404
            
            # Verify the class belongs to the institution
            class_obj = db_session.query(Class).join(Course).filter(
                Class.class_id == attendance_record.class_id,
                Course.institution_id == institution_id
            ).first()
            
            if not class_obj:
                return jsonify({'success': False, 'error': 'Unauthorized'}), 401
            
            # Get student info
            student = db_session.query(User).filter(
                User.user_id == attendance_record.student_id
            ).first()
            
            if not student:
                return jsonify({'success': False, 'error': 'Student not found'}), 404
            
            # Use facial recognition to verify
            from application.controls.facial_recognition_control import FacialRecognitionControl
            import base64
            
            fr_control = FacialRecognitionControl()
            if not fr_control.initialize(current_app):
                return jsonify({
                    'success': False,
                    'error': 'Facial recognition system not initialized'
                }), 500
            
            # Decode base64 image
            try:
                image_bytes = base64.b64decode(
                    image_data.split(',')[1] if ',' in image_data else image_data
                )
            except Exception as e:
                return jsonify({'success': False, 'error': f'Invalid image data: {str(e)}'}), 400
            
            # Recognize face
            recognition_result = fr_control.recognize_face_from_image(image_bytes)
            
            if not recognition_result['success']:
                # Facial recognition failed
                attendance_record.audit_status = 'fail'
                attendance_record.audited_at = datetime.now()
                attendance_record.audited_by = admin_user_id
                db_session.commit()
                
                return jsonify({
                    'success': True,
                    'audit_result': 'fail',
                    'message': f"Audit failed: {recognition_result.get('error', 'Face not recognized')}",
                    'attendance_id': attendance_id
                })
            
            # Check if recognized face matches the student
            recognitions = recognition_result.get('recognitions', [])
            if not recognitions:
                attendance_record.audit_status = 'fail'
                attendance_record.audited_at = datetime.now()
                attendance_record.audited_by = admin_user_id
                db_session.commit()
                
                return jsonify({
                    'success': True,
                    'audit_result': 'fail',
                    'message': 'No faces recognized in the image',
                    'attendance_id': attendance_id
                })
            
            # Get best recognition match
            best_match = max(recognitions, key=lambda r: r['confidence'])
            
            # Check if the recognized student ID matches
            recognized_id = best_match.get('student_id')
            confidence = best_match.get('confidence', 0)
            
            # Determine audit result based on match and confidence
            if confidence < 70:
                audit_result = 'fail'
                message = f"Low confidence ({confidence:.1f}%) - Audit failed"
            elif str(recognized_id) == str(student.user_id):
                audit_result = 'pass'
                message = f"Student verified successfully ({confidence:.1f}% confidence)"
            else:
                audit_result = 'fail'
                message = f"Face does not match expected student (detected: {best_match.get('name')})"
            
            # Update attendance record
            attendance_record.audit_status = audit_result
            attendance_record.audited_at = datetime.now()
            attendance_record.audited_by = admin_user_id
            db_session.commit()
            
            return jsonify({
                'success': True,
                'audit_result': audit_result,
                'message': message,
                'confidence': confidence,
                'recognized_name': best_match.get('name'),
                'attendance_id': attendance_id
            })
            
    except Exception as e:
        current_app.logger.error(f"Error auditing attendance: {e}")
        return jsonify({
            'success': False,
            'error': f'Error processing audit: {str(e)}'
        }), 500


@institution_bp.route('/attendance/class/<int:class_id>/bulk-audit', methods=['POST'])
@requires_roles('admin')
def bulk_audit_class(class_id):
    """Bulk audit all attendance records for a class using a class photo"""
    institution_id = session.get('institution_id')
    admin_user_id = session.get('user_id')
    
    data = request.get_json() or {}
    image_data = data.get('image')
    
    if not image_data:
        return jsonify({'success': False, 'error': 'Image data is required for bulk audit'}), 400
    
    try:
        with get_session() as db_session:
            class_model = ClassModel(db_session)
            
            # Verify class belongs to institution
            if not class_model.class_is_institution(class_id, institution_id):
                return jsonify({'success': False, 'error': 'Unauthorized'}), 401
            
            # Get all attendance records that haven't been audited or failed audit
            records = db_session.query(AttendanceRecord, User).join(
                User, AttendanceRecord.student_id == User.user_id
            ).filter(
                AttendanceRecord.class_id == class_id,
                AttendanceRecord.status.in_(['present', 'late'])  # Only audit students marked as present/late
            ).all()
            
            if not records:
                return jsonify({
                    'success': True,
                    'message': 'No records to audit',
                    'audited_count': 0,
                    'results': []
                })
            
            # Use facial recognition to detect multiple faces
            from application.controls.facial_recognition_control import FacialRecognitionControl
            import base64
            
            fr_control = FacialRecognitionControl()
            if not fr_control.initialize(current_app):
                return jsonify({
                    'success': False,
                    'error': 'Facial recognition system not initialized'
                }), 500
            
            # Decode base64 image
            try:
                image_bytes = base64.b64decode(
                    image_data.split(',')[1] if ',' in image_data else image_data
                )
            except Exception as e:
                return jsonify({'success': False, 'error': f'Invalid image data: {str(e)}'}), 400
            
            # Recognize all faces in the image
            recognition_result = fr_control.recognize_face_from_image(image_bytes)
            
            if not recognition_result['success']:
                return jsonify({
                    'success': False,
                    'error': f"Face recognition failed: {recognition_result.get('error', 'Unknown error')}"
                }), 400
            
            # Get all recognized faces
            recognitions = recognition_result.get('recognitions', [])
            
            if not recognitions:
                return jsonify({
                    'success': False,
                    'error': 'No faces detected in the image. Please ensure students are clearly visible.'
                }), 400
            
            # Create a map of student_id to best recognition match
            recognized_student_ids = {}
            for recognition in recognitions:
                student_id = recognition.get('student_id')
                confidence = recognition.get('confidence', 0)
                
                if student_id and confidence >= 70:  # Minimum confidence threshold
                    # Keep the highest confidence match for each student
                    if student_id not in recognized_student_ids or confidence > recognized_student_ids[student_id]['confidence']:
                        recognized_student_ids[student_id] = {
                            'confidence': confidence,
                            'name': recognition.get('name')
                        }
            
            # Process each attendance record
            audit_results = []
            pass_count = 0
            fail_count = 0
            
            for record, student in records:
                student_id_str = str(student.user_id)
                
                if student_id_str in recognized_student_ids:
                    # Student was recognized - PASS
                    match_info = recognized_student_ids[student_id_str]
                    record.audit_status = 'pass'
                    record.audited_at = datetime.now()
                    record.audited_by = admin_user_id
                    
                    audit_results.append({
                        'attendance_id': record.attendance_id,
                        'student_id': student.user_id,
                        'student_name': student.name,
                        'audit_result': 'pass',
                        'confidence': match_info['confidence'],
                        'message': f"Verified ({match_info['confidence']:.1f}% confidence)"
                    })
                    pass_count += 1
                else:
                    # Student was NOT recognized - FAIL
                    record.audit_status = 'fail'
                    record.audited_at = datetime.now()
                    record.audited_by = admin_user_id
                    
                    audit_results.append({
                        'attendance_id': record.attendance_id,
                        'student_id': student.user_id,
                        'student_name': student.name,
                        'audit_result': 'fail',
                        'confidence': 0,
                        'message': 'Not detected in class photo'
                    })
                    fail_count += 1
            
            db_session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Bulk audit completed: {pass_count} passed, {fail_count} failed',
                'audited_count': pass_count + fail_count,
                'pass_count': pass_count,
                'fail_count': fail_count,
                'faces_detected': len(recognitions),
                'results': audit_results
            })
            
    except Exception as e:
        current_app.logger.error(f"Error in bulk audit: {e}")
        return jsonify({
            'success': False,
            'error': f'Error processing bulk audit: {str(e)}'
        }), 500


@institution_bp.route('/attendance/audit/<int:attendance_id>/manual', methods=['POST'])
@requires_roles('admin')
def manual_audit_update(attendance_id):
    """Manually update audit status without facial recognition"""
    institution_id = session.get('institution_id')
    admin_user_id = session.get('user_id')
    
    data = request.get_json() or {}
    audit_status = data.get('audit_status')
    
    if audit_status not in ['pass', 'fail', 'no_audit']:
        return jsonify({'success': False, 'error': 'Invalid audit status'}), 400
    
    with get_session() as db_session:
        # Get attendance record
        attendance_record = db_session.query(AttendanceRecord).filter(
            AttendanceRecord.attendance_id == attendance_id
        ).first()
        
        if not attendance_record:
            return jsonify({'success': False, 'error': 'Attendance record not found'}), 404
        
        # Verify the class belongs to the institution
        class_obj = db_session.query(Class).join(Course).filter(
            Class.class_id == attendance_record.class_id,
            Course.institution_id == institution_id
        ).first()
        
        if not class_obj:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        # Update audit status
        attendance_record.audit_status = audit_status
        attendance_record.audited_at = datetime.now()
        attendance_record.audited_by = admin_user_id
        db_session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Audit status updated to {audit_status}',
            'attendance_id': attendance_id,
            'audit_status': audit_status
        })
            