from flask import Blueprint, render_template, request, jsonify, session, current_app, flash, redirect, url_for
from application.controls.auth_control import AuthControl
from application.entities.base_entity import BaseEntity

platform_bp = Blueprint('platform', __name__)


@platform_bp.route('/')
def platform_dashboard():
    """Platform manager dashboard (alias of admin/platform)"""
    auth_result = AuthControl.verify_session(current_app, session)

    if not auth_result['success'] or auth_result['user'].get('user_type') != 'platform_manager':
        flash('Access denied. Platform manager privileges required.', 'danger')
        return redirect(url_for('auth.login'))

    # Render platform manager dashboard template (exists under templates/platmanager or platform_manager)
    try:
        return render_template('platmanager/platform_manager_dashboard.html', user=auth_result['user'])
    except Exception:
        return render_template('admin/platform_dashboard.html', user=auth_result['user'])


@platform_bp.route('/pending-registrations')
def pending_registrations():
    """List pending registration requests for review (platform manager view)"""
    auth_result = AuthControl.verify_session(current_app, session)
    if not auth_result['success'] or auth_result['user'].get('user_type') != 'platform_manager':
        flash('Access denied. Platform manager privileges required.', 'danger')
        return redirect(url_for('auth.login'))

    try:
        cursor = BaseEntity.get_db_connection(current_app)
        cursor.execute("SELECT unreg_user_id, email, full_name, institution_name, applied_at, selected_plan_id FROM Unregistered_Users WHERE status = 'pending' ORDER BY applied_at DESC")
        rows = cursor.fetchall() or []
    except Exception:
        rows = []

    return render_template('admin/pending_registrations.html', user=auth_result['user'], requests=rows)


@platform_bp.route('/pending-registrations/approve/<int:unreg_user_id>', methods=['POST'])
def approve_registration(unreg_user_id):
    auth_result = AuthControl.verify_session(current_app, session)
    if not auth_result['success'] or auth_result['user'].get('user_type') != 'platform_manager':
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    temp_pw = request.form.get('temp_password')
    reviewer_id = auth_result['user'].get('user_id')
    result = AuthControl.approve_unregistered_user(current_app, unreg_user_id, reviewer_id=reviewer_id, admin_password=temp_pw)

    if result.get('success'):
        flash('Request approved. Admin account created.', 'success')
        if result.get('admin_password'):
            flash('Temporary admin password: ' + result.get('admin_password'), 'info')
        return redirect(url_for('platform.pending_registrations'))

    flash(result.get('error') or 'Failed to approve request', 'danger')
    return redirect(url_for('platform.pending_registrations'))
