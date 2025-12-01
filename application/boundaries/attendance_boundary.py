from flask import Blueprint, request, jsonify, session, current_app
from application.controls.auth_control import AuthControl
from application.controls.attendance_control import AttendanceControl
from datetime import datetime

attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/mark', methods=['POST'])
def mark_attendance():
    """Mark attendance API endpoint"""
    # Verify authentication
    auth_result = AuthControl.verify_session(current_app, session)
    
    if not auth_result['success']:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
    
    user_id = auth_result['user']['firebase_uid']
    data = request.get_json() or {}
    
    status = data.get('status', 'present')
    check_in_time = data.get('check_in_time')
    notes = data.get('notes')
    
    result = AttendanceControl.mark_attendance(
        current_app, 
        user_id, 
        status, 
        check_in_time, 
        notes
    )
    
    return jsonify(result)

@attendance_bp.route('/today', methods=['GET'])
def get_today_attendance():
    """Get today's attendance for the user"""
    auth_result = AuthControl.verify_session(current_app, session)
    
    if not auth_result['success']:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
    
    user_id = auth_result['user']['firebase_uid']
    
    # This would need to be implemented in AttendanceControl
    # For now, return a placeholder response
    
    return jsonify({
        'success': True,
        'attendance': {
            'date': datetime.now().date().isoformat(),
            'status': 'not_marked',
            'check_in_time': None,
            'check_out_time': None
        }
    })

@attendance_bp.route('/summary', methods=['GET'])
def get_attendance_summary():
    """Get attendance summary for the user"""
    auth_result = AuthControl.verify_session(current_app, session)
    
    if not auth_result['success']:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
    
    user_id = auth_result['user']['firebase_uid']
    days = request.args.get('days', 30, type=int)
    
    result = AttendanceControl.get_user_attendance_summary(current_app, user_id, days)
    
    return jsonify(result)

@attendance_bp.route('/report/daily', methods=['GET'])
def get_daily_report():
    """Get daily attendance report (for teachers/admins)"""
    auth_result = AuthControl.verify_session(current_app, session)
    
    if not auth_result['success']:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
    
    # Check if user has permission (teacher/admin)
    user_role = auth_result['user'].get('role', 'student')
    
    if user_role not in ['teacher', 'admin']:
        return jsonify({
            'success': False,
            'error': 'Permission denied'
        }), 403
    
    report_date = request.args.get('date')
    
    result = AttendanceControl.get_daily_report(current_app, report_date)
    
    return jsonify(result)