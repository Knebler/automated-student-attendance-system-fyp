from flask import Blueprint, request, jsonify, session, current_app
from application.controls.auth_control import AuthControl
from application.controls.attendance_control import AttendanceControl
from application.boundaries.dev_actions import register_action
from datetime import datetime, date

attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/mark', methods=['POST'])
def mark_attendance():
    """Mark attendance for a student in a session"""
    # Verify authentication
    auth_result = AuthControl.verify_session(current_app, session)
    
    if not auth_result['success']:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
    
    user_info = auth_result['user']
    data = request.get_json() or {}
    
    # Get required parameters
    session_id = data.get('session_id')
    student_id = data.get('student_id') or user_info.get('user_id')  # Use logged-in user's ID if not specified
    status = data.get('status', 'present')
    
    # Optional parameters
    marked_by = data.get('marked_by', 'system')
    lecturer_id = data.get('lecturer_id')
    captured_image_path = data.get('captured_image_path')
    notes = data.get('notes')
    
    # For lecturers marking attendance for students, use lecturer's ID
    if user_info.get('user_type') in ['lecturer', 'teacher'] and not lecturer_id:
        lecturer_id = user_info.get('user_id')
        marked_by = 'lecturer'
    
    # For students marking their own attendance
    if user_info.get('user_type') == 'student':
        marked_by = 'system'
    
    if not session_id:
        return jsonify({
            'success': False,
            'error': 'Session ID is required'
        }), 400
    
    if not student_id:
        return jsonify({
            'success': False,
            'error': 'Student ID is required'
        }), 400
    
    result = AttendanceControl.mark_attendance(
        current_app, 
        session_id, 
        student_id, 
        status, 
        marked_by, 
        lecturer_id, 
        captured_image_path, 
        notes
    )
    
    return jsonify(result)

@attendance_bp.route('/session/<int:session_id>', methods=['GET'])
def get_session_attendance(session_id):
    """Get attendance records for a specific session"""
    auth_result = AuthControl.verify_session(current_app, session)
    
    if not auth_result['success']:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
    
    user_info = auth_result['user']
    user_role = user_info.get('user_type', 'student')
    
    # Check permissions - only lecturers, admins, or students in that session should access
    if user_role == 'student':
        # Students can only view if they're in the session
        # This would need additional logic to check enrollment
        pass  # For now, allow all authenticated users
    
    result = AttendanceControl.get_session_attendance(current_app, session_id)
    
    return jsonify(result)

@attendance_bp.route('/student/<int:student_id>/summary', methods=['GET'])
def get_student_attendance_summary(student_id):
    """Get attendance summary for a student"""
    auth_result = AuthControl.verify_session(current_app, session)
    
    if not auth_result['success']:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
    
    user_info = auth_result['user']
    user_role = user_info.get('user_type', 'student')
    user_id = user_info.get('user_id')
    
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
def get_my_attendance_summary():
    """Get attendance summary for the logged-in student"""
    auth_result = AuthControl.verify_session(current_app, session)
    
    if not auth_result['success']:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
    
    user_info = auth_result['user']
    
    if user_info.get('user_type') != 'student':
        return jsonify({
            'success': False,
            'error': 'This endpoint is for students only'
        }), 403
    
    student_id = user_info.get('user_id')
    days = request.args.get('days', 30, type=int)
    
    result = AttendanceControl.get_student_attendance_summary(current_app, student_id, days)
    
    return jsonify(result)

@attendance_bp.route('/today/sessions', methods=['GET'])
def get_today_sessions_attendance():
    """Get attendance for all sessions happening today"""
    auth_result = AuthControl.verify_session(current_app, session)
    
    if not auth_result['success']:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
    
    user_info = auth_result['user']
    user_role = user_info.get('user_type', 'student')
    
    # Only lecturers/admins can view all today's sessions
    if user_role not in ['lecturer', 'teacher', 'admin', 'institution_admin']:
        return jsonify({
            'success': False,
            'error': 'Permission denied'
        }), 403
    
    lecturer_id = request.args.get('lecturer_id')
    if user_role in ['lecturer', 'teacher'] and not lecturer_id:
        # Default to current lecturer's ID
        lecturer_id = user_info.get('user_id')
    
    result = AttendanceControl.get_today_sessions_attendance(current_app, lecturer_id)
    
    return jsonify(result)

@attendance_bp.route('/update/<int:attendance_id>', methods=['PUT'])
def update_attendance_status(attendance_id):
    """Update attendance status (e.g., from absent to excused)"""
    auth_result = AuthControl.verify_session(current_app, session)
    
    if not auth_result['success']:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
    
    user_info = auth_result['user']
    user_role = user_info.get('user_type', 'student')
    
    # Only lecturers/admins can update attendance
    if user_role not in ['lecturer', 'teacher', 'admin', 'institution_admin']:
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
def get_student_attendance_record():
    """Get detailed attendance records for a student with filters"""
    auth_result = AuthControl.verify_session(current_app, session)
    
    if not auth_result['success']:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
    
    user_info = auth_result['user']
    user_role = user_info.get('user_type', 'student')
    
    student_id = request.args.get('student_id')
    course_id = request.args.get('course_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # If student_id not provided, use current user's ID (if student)
    if not student_id and user_role == 'student':
        student_id = user_info.get('user_id')
    
    # Check permissions
    if user_role == 'student' and user_info.get('user_id') != int(student_id):
        return jsonify({
            'success': False,
            'error': 'You can only view your own attendance records'
        }), 403
    
    # This would need implementation in AttendanceControl
    # For now, return a placeholder response
    return jsonify({
        'success': True,
        'message': 'Feature coming soon - attendance record with filters',
        'filters': {
            'student_id': student_id,
            'course_id': course_id,
            'start_date': start_date,
            'end_date': end_date
        }
    })

@attendance_bp.route('/report/daily', methods=['GET'])
def get_daily_attendance_report():
    """Get daily attendance report (for teachers/admins)"""
    auth_result = AuthControl.verify_session(current_app, session)
    
    if not auth_result['success']:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
    
    user_info = auth_result['user']
    user_role = user_info.get('user_type', 'student')
    
    # Only lecturers/admins can view reports
    if user_role not in ['lecturer', 'teacher', 'admin', 'institution_admin']:
        return jsonify({
            'success': False,
            'error': 'Permission denied'
        }), 403
    
    report_date = request.args.get('date', date.today().isoformat())
    course_id = request.args.get('course_id')
    
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
            {'name': 'session_id', 'label': 'Session ID', 'placeholder': 'e.g. 123'},
            {'name': 'student_id', 'label': 'Student ID', 'placeholder': 'e.g. 456'},
            {'name': 'status', 'label': 'Status', 'placeholder': 'present | absent | late | excused'},
            {'name': 'marked_by', 'label': 'Marked By', 'placeholder': 'system | lecturer'},
            {'name': 'lecturer_id', 'label': 'Lecturer ID', 'placeholder': 'optional'},
            {'name': 'notes', 'label': 'Notes', 'placeholder': 'optional notes'},
        ],
        description='Mark attendance as present/absent for a student'
    )

    register_action(
        'get_session_attendance',
        AttendanceControl.get_session_attendance,
        params=[{'name': 'session_id', 'label': 'Session ID', 'placeholder': 'e.g. 123'}],
        description='Get attendance records for a session'
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
        'get_today_sessions_attendance',
        AttendanceControl.get_today_sessions_attendance,
        params=[
            {'name': 'lecturer_id', 'label': 'Lecturer ID', 'placeholder': 'Optional'}
        ],
        description='Get attendance for all sessions happening today'
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

except Exception as e:
    current_app.logger.error(f"Failed to register dev actions: {e}")