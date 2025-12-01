from flask import Blueprint, render_template, request, jsonify, session, current_app, flash, redirect, url_for
from application.controls.auth_control import AuthControl

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/platform')
def platform_dashboard():
    """Platform manager dashboard"""
    auth_result = AuthControl.verify_session(current_app, session)
    
    if not auth_result['success'] or auth_result['user'].get('user_type') != 'platform_manager':
        flash('Access denied. Platform manager privileges required.', 'danger')
        return redirect(url_for('auth.login'))
    
    return render_template('admin/platform_dashboard.html', user=auth_result['user'])