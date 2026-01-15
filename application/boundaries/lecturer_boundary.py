from flask import Blueprint, render_template, request, jsonify, session, current_app, flash, redirect, url_for
from application.controls.auth_control import AuthControl, requires_roles
from application.controls.attendance_control import AttendanceControl
from application.controls.class_control import ClassControl
from application.controls.course_control import CourseControl
from database.base import get_session
from database.models import AttendanceRecord, Venue
from datetime import datetime

lecturer_bp = Blueprint('institution_lecturer', __name__)


@lecturer_bp.route('/dashboard')
@requires_roles('lecturer')
def lecturer_dashboard():
    """Lecturer dashboard"""
    return render_template('institution/lecturer/lecturer_dashboard.html')

@lecturer_bp.route('/manage_appeals')
def manage_appeals():
    """Render the lecturer appeal-management page"""
    return render_template('institution/lecturer/lecturer_appeal_management.html')


@lecturer_bp.route('/manage_attendance')
@requires_roles('lecturer')
def manage_attendance():
    """Render the lecturer attendance-management page"""
    class_id = request.args.get('class_id')
    if not class_id:
        flash('Class ID is required', 'warning')
        return redirect(url_for('institution_lecturer.manage_classes'))
    try:
        class_id = int(class_id)
    except ValueError:
        flash('Invalid class ID', 'danger')
        return redirect(url_for('institution_lecturer.manage_classes'))
    
    user_id = session.get('user_id')
    class_result = ClassControl.get_class_by_id(class_id)
    if not class_result['success']:
        flash(class_result.get('error', 'Class not found'), 'danger')
        return redirect(url_for('institution_lecturer.manage_classes'))
    class_data = class_result['class']

    course_id = class_data['course_id']
    course_result = CourseControl.get_course_by_id(course_id)
    if not course_result['success']:
        flash(course_result.get('error', 'Course not found'), 'danger')
        return redirect(url_for('institution_lecturer.manage_classes'))
    course = course_result['course']
    
    # Step 3: Get all course_users who are students
    students_result = CourseControl.get_students_by_course_id(course_id)
    if not students_result['success']:
        flash(students_result.get('error', 'Error retrieving students'), 'warning')
        students_list = []
    else:
        students_list = students_result['students']
    
    # Process attendance records
    with get_session() as db_session:
        
        # Step 4 & 5: Check if attendance records exist, create if not
        attendance_records_created = 0
        students_data = []
        
        for student_info in students_list:
            student_id = student_info['user_id']
            
            # Check if attendance record exists
            existing_record = (
                db_session.query(AttendanceRecord)
                .filter(AttendanceRecord.class_id == class_id)
                .filter(AttendanceRecord.student_id == student_id)
                .first()
            )
            
            if not existing_record:
                # Use AttendanceControl to create attendance record
                result = AttendanceControl.mark_attendance(
                    class_id=class_id,
                    student_id=student_id,
                    status='unmarked',
                    marked_by='system',
                    lecturer_id=user_id,
                    notes=None
                )
                
                if result['success']:
                    attendance_records_created += 1
                else:
                    # Log error but continue processing other students
                    current_app.logger.warning(f"Failed to create attendance for student {student_id}: {result.get('error')}")
            
            # Prepare student data for template
            student_record = (
                db_session.query(AttendanceRecord)
                .filter(AttendanceRecord.class_id == class_id)
                .filter(AttendanceRecord.student_id == student_id)
                .first()
            )
            
            students_data.append(
                {
                    'id': student_id,
                    'name': student_info['name'],
                    'email': student_info.get('email', ''),
                    'id_number': student_info.get('id_number', str(student_id)),
                    'status': student_record.status if student_record else 'pending',
                    'photo_url': None,
                    'recorded_at': student_record.recorded_at if student_record else None,
                    'notes': student_record.notes if student_record else None,
                }
            )
   
        # Get attendance statistics
        total_students = len(students_data)
        present_count = sum(1 for s in students_data if s['status'] == 'present')
        absent_count = sum(1 for s in students_data if s['status'] == 'absent')
        late_count = sum(1 for s in students_data if s['status'] == 'late')
        pending_count = sum(1 for s in students_data if s['status'] == 'pending')
        
        # Get venue information
        venue = db_session.query(Venue).filter(Venue.venue_id == class_data['venue_id']).first()
        venue_name = venue.name if venue else 'Room TBD'
        
        # # Format class data for template
        class_info = {
            'id': class_data['class_id'],
            'course_code': course.get('code', 'N/A') if course else 'N/A',
            'section': 'A',  # Default section - adjust if you have section data
            'date': class_data['start_time'].strftime('%B %d, %Y'),
            'room': venue_name,
            'time': class_data['start_time'].strftime('%I:%M %p') + ' - ' + class_data['end_time'].strftime('%I:%M %p'),
        }

    context = {
        'user': {
            'user_id': user_id,
            'user_type': session.get('role'),
            'name': session.get('name', 'Lecturer')
        },
        'class': class_info,
        'students': students_data,
        'total_students': total_students,
        'stats': {
            'total_students': total_students,
            'present_students': present_count,
            'absent_students': absent_count,
            'late_students': late_count,
            'pending_students': pending_count
        }
    }
    
    return render_template('institution/lecturer/lecturer_attendance_management.html',
                           **context)



@lecturer_bp.route('/manage_attendance/statistics')
def attendance_statistics():
    """Render the lecturer attendance statistics page"""
    return render_template('institution/lecturer/lecturer_attendance_management_statistics.html')


@lecturer_bp.route('/manage_classes')
def manage_classes():
    """Render the lecturer class-management page"""
    return render_template('institution/lecturer/lecturer_class_management.html')


@lecturer_bp.route('/timetable')
def timetable():
    """Render the lecturer timetable page"""
    return render_template('institution/lecturer/lecturer_timetable.html')