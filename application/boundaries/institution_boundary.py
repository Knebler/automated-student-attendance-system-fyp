from flask import Blueprint, render_template, request, jsonify, session, current_app, flash, redirect, url_for
from application.controls.auth_control import AuthControl
from application.controls.institution_control import InstitutionControl
from application.controls.attendance_control import AttendanceControl

institution_bp = Blueprint('institution', __name__)

@institution_bp.route('/dashboard')
def institution_dashboard():
    """Institution dashboard for admins/lecturers"""
    auth_result = AuthControl.verify_session(current_app, session)
    
    if not auth_result['success']:
        flash('Please login to access institution dashboard', 'warning')
        return redirect(url_for('auth.login'))
    
    user_type = auth_result['user'].get('user_type')
    
    if user_type not in ['institution_admin', 'lecturer', 'platform_manager']:
        flash('Access denied. Institution privileges required.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    institution_id = auth_result['user'].get('institution_id')
    
    # Get institution statistics
    stats_result = InstitutionControl.get_institution_stats(current_app, institution_id)
    
    return render_template('institution/dashboard.html',
                         user=auth_result['user'],
                         stats=stats_result.get('stats') if stats_result['success'] else {})