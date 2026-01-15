# attendance_boundary.py (updated to use ORM patterns)
from flask import Blueprint, request, jsonify, session, current_app
from application.controls.auth_control import requires_roles, authenticate_user
from application.controls.attendance_control import AttendanceControl
from application.boundaries.dev_actions import register_action
from datetime import datetime, date
import functools

attendance_bp = Blueprint('attendance', __name__)

def verify_attendance_auth():
    """Verify authentication for attendance endpoints"""
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session or 'role' not in session:
                return jsonify({
                    'success': False,
                    'error': 'Authentication required'
                }), 401
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@attendance_bp.route('/mark', methods=['POST'])
@verify_attendance_auth()
def mark_attendance():
    """Mark attendance for a student in a class"""
    user_id = session.get('user_id')
    user_role = session.get('role')
    
    data = request.get_json() or {}
    
    # Get required parameters
    class_id = data.get('class_id')
    student_id = data.get('student_id') or user_id  # Use logged-in user's ID if not specified
    status = data.get('status', 'present')
    
    # Optional parameters
    marked_by = data.get('marked_by', 'system')
    lecturer_id = data.get('lecturer_id')
    notes = data.get('notes')
    
    # For lecturers marking attendance for students, use lecturer's ID
    if user_role in ['lecturer', 'admin'] and not lecturer_id:
        lecturer_id = user_id
        marked_by = 'lecturer'
    
    # For students marking their own attendance
    if user_role == 'student':
        marked_by = 'system'
    
    if not class_id:
        return jsonify({
            'success': False,
            'error': 'Class ID is required'
        }), 400
    
    if not student_id:
        return jsonify({
            'success': False,
            'error': 'Student ID is required'
        }), 400
    
    result = AttendanceControl.mark_attendance(
        current_app, 
        class_id, 
        student_id, 
        status, 
        marked_by, 
        lecturer_id, 
        notes
    )
    
    return jsonify(result)

@attendance_bp.route('/class/<int:class_id>', methods=['GET'])
@verify_attendance_auth()
def get_class_attendance(class_id):
    """Get attendance records for a specific class"""
    user_role = session.get('role')
    user_id = session.get('user_id')
    
    # Check permissions - only lecturers, admins, or students in that class should access
    if user_role == 'student':
        # Students can only view if they're in the class
        # This would need additional logic to check enrollment
        pass  # For now, allow all authenticated users
    
    result = AttendanceControl.get_class_attendance(current_app, class_id)
    
    return jsonify(result)

@attendance_bp.route('/student/<int:student_id>/summary', methods=['GET'])
@verify_attendance_auth()
def get_student_attendance_summary(student_id):
    """Get attendance summary for a student"""
    user_role = session.get('role')
    user_id = session.get('user_id')
    
    # Check permissions
    if user_role == 'student' and user_id != student_id:
        return jsonify({
            'success': False,
            'error': 'You can only view your own attendance summary'
        }), 403
    
    days = request.args.get('days', 30, type=int)
    
    result = AttendanceControl.get_student_attendance_summary(current_app, student_id, days)
    
    return jsonify(result)

@attendance_bp.route('/student/summary', methods=['GET'])
@verify_attendance_auth()
def get_my_attendance_summary():
    """Get attendance summary for the logged-in student"""
    user_role = session.get('role')
    
    if user_role != 'student':
        return jsonify({
            'success': False,
            'error': 'This endpoint is for students only'
        }), 403
    
    student_id = session.get('user_id')
    days = request.args.get('days', 30, type=int)
    
    result = AttendanceControl.get_student_attendance_summary(current_app, student_id, days)
    
    return jsonify(result)

@attendance_bp.route('/today/classes', methods=['GET'])
@verify_attendance_auth()
def get_today_classes_attendance():
    """Get attendance for all classes happening today"""
    user_role = session.get('role')
    
    # Only lecturers/admins can view all today's classes
    if user_role not in ['lecturer', 'admin', 'platform_manager']:
        return jsonify({
            'success': False,
            'error': 'Permission denied'
        }), 403
    
    lecturer_id = request.args.get('lecturer_id')
    if user_role in ['lecturer'] and not lecturer_id:
        # Default to current lecturer's ID
        lecturer_id = session.get('user_id')
    
    result = AttendanceControl.get_today_classes_attendance(current_app, lecturer_id)
    
    return jsonify(result)

@attendance_bp.route('/update/<int:attendance_id>', methods=['PUT'])
@verify_attendance_auth()
def update_attendance_status(attendance_id):
    """Update attendance status (e.g., from absent to excused)"""
    user_role = session.get('role')
    
    # Only lecturers/admins can update attendance
    if user_role not in ['lecturer', 'admin', 'platform_manager']:
        return jsonify({
            'success': False,
            'error': 'Permission denied'
        }), 403
    
    data = request.get_json() or {}
    status = data.get('status')
    notes = data.get('notes')
    
    if not status:
        return jsonify({
            'success': False,
            'error': 'Status is required'
        }), 400
    
    result = AttendanceControl.update_attendance_status(current_app, attendance_id, status, notes)
    
    return jsonify(result)

@attendance_bp.route('/student/record', methods=['GET'])
@verify_attendance_auth()
def get_student_attendance_record():
    """Get detailed attendance records for a student with filters"""
    user_role = session.get('role')
    user_id = session.get('user_id')
    
    student_id = request.args.get('student_id', type=int)
    course_id = request.args.get('course_id', type=int)
    
    # Parse date parameters
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    start_date = None
    end_date = None
    
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid start_date format. Use YYYY-MM-DD'
            }), 400
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid end_date format. Use YYYY-MM-DD'
            }), 400
    
    # If student_id not provided, use current user's ID (if student)
    if not student_id and user_role == 'student':
        student_id = user_id
    
    # Check permissions
    if user_role == 'student' and user_id != student_id:
        return jsonify({
            'success': False,
            'error': 'You can only view your own attendance records'
        }), 403
    
    result = AttendanceControl.get_student_attendance_record(
        current_app, 
        student_id, 
        course_id, 
        start_date, 
        end_date
    )
    
    return jsonify(result)

@attendance_bp.route('/report/daily', methods=['GET'])
@verify_attendance_auth()
def get_daily_attendance_report():
    """Get daily attendance report (for teachers/admins)"""
    user_role = session.get('role')
    
    # Only lecturers/admins can view reports
    if user_role not in ['lecturer', 'admin', 'platform_manager']:
        return jsonify({
            'success': False,
            'error': 'Permission denied'
        }), 403
    
    report_date = request.args.get('date', date.today().isoformat())
    course_id = request.args.get('course_id', type=int)
    
    # Parse date
    try:
        report_date_obj = datetime.strptime(report_date, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid date format. Use YYYY-MM-DD'
        }), 400
    
    # This would need implementation in AttendanceControl
    # For now, return a placeholder response
    return jsonify({
        'success': True,
        'message': 'Daily report feature coming soon',
        'date': report_date,
        'course_id': course_id
    })

# Register dev actions for attendance endpoints
try:
    register_action(
        'mark_attendance',
        AttendanceControl.mark_attendance,
        params=[
            {'name': 'class_id', 'label': 'Class ID', 'placeholder': 'e.g. 123'},
            {'name': 'student_id', 'label': 'Student ID', 'placeholder': 'e.g. 456'},
            {'name': 'status', 'label': 'Status', 'placeholder': 'present | absent | late | excused'},
            {'name': 'marked_by', 'label': 'Marked By', 'placeholder': 'system | lecturer'},
            {'name': 'lecturer_id', 'label': 'Lecturer ID', 'placeholder': 'optional'},
            {'name': 'notes', 'label': 'Notes', 'placeholder': 'optional notes'},
        ],
        description='Mark attendance as present/absent for a student'
    )

    register_action(
        'get_class_attendance',
        AttendanceControl.get_class_attendance,
        params=[{'name': 'class_id', 'label': 'Class ID', 'placeholder': 'e.g. 123'}],
        description='Get attendance records for a class'
    )

    register_action(
        'get_student_attendance_summary',
        AttendanceControl.get_student_attendance_summary,
        params=[
            {'name': 'student_id', 'label': 'Student ID', 'placeholder': 'e.g. 456'},
            {'name': 'days', 'label': 'Days', 'placeholder': 'Number of days to summarize (default 30)'}
        ],
        description='Get attendance summary for a student'
    )

    register_action(
        'get_today_classes_attendance',
        AttendanceControl.get_today_classes_attendance,
        params=[
            {'name': 'lecturer_id', 'label': 'Lecturer ID', 'placeholder': 'Optional'}
        ],
        description='Get attendance for all classes happening today'
    )

    register_action(
        'update_attendance_status',
        AttendanceControl.update_attendance_status,
        params=[
            {'name': 'attendance_id', 'label': 'Attendance ID', 'placeholder': 'e.g. 789'},
            {'name': 'status', 'label': 'Status', 'placeholder': 'present, absent, late, excused'},
            {'name': 'notes', 'label': 'Notes', 'placeholder': 'Optional notes'}
        ],
        description='Update attendance status'
    )

    register_action(
        'get_student_attendance_record',
        AttendanceControl.get_student_attendance_record,
        params=[
            {'name': 'student_id', 'label': 'Student ID', 'placeholder': 'e.g. 456'},
            {'name': 'course_id', 'label': 'Course ID', 'placeholder': 'Optional'},
            {'name': 'start_date', 'label': 'Start Date', 'placeholder': 'YYYY-MM-DD'},
            {'name': 'end_date', 'label': 'End Date', 'placeholder': 'YYYY-MM-DD'}
        ],
        description='Get detailed attendance records with filters'
    )

except Exception as e:
    current_app.logger.error(f"Failed to register dev actions: {e}")