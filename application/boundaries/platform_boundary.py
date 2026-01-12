from flask import Blueprint, render_template, request, jsonify, session, current_app, flash, redirect, url_for
from application.controls.auth_control import AuthControl, requires_roles
from application.entities.base_entity import BaseEntity

platform_bp = Blueprint('platform', __name__)

@platform_bp.route('/')
@requires_roles('platform_manager')
def platform_dashboard():
    """Platform manager dashboard (alias of platform manager)"""

    # Initialize defaults
    total_institutions = 0
    active_institutions = 0
    pending_subscriptions_count = 0
    total_registered_users = 0
    pending_subscriptions = []
    recent_changes = []
    recent_reports = []

    try:
        cursor = BaseEntity.get_db_connection(current_app)

        # Counts
        cursor.execute("SELECT COUNT(*) FROM Institutions")
        row = cursor.fetchone()
        total_institutions = int(row[0]) if row and row[0] is not None else 0

        cursor.execute("SELECT COUNT(*) FROM Institutions WHERE is_active = TRUE")
        row = cursor.fetchone()
        active_institutions = int(row[0]) if row and row[0] is not None else 0

        cursor.execute("SELECT COUNT(*) FROM Unregistered_Users WHERE status = 'pending'")
        row = cursor.fetchone()
        pending_subscriptions_count = int(row[0]) if row and row[0] is not None else 0

        # Registered user counts (aggregate from known tables)
        try:
            cursor.execute("SELECT COUNT(*) FROM Platform_Managers")
            row = cursor.fetchone()
            pm_count = int(row[0]) if row and row[0] is not None else 0
        except Exception:
            pm_count = 0

        try:
            cursor.execute("SELECT COUNT(*) FROM Institution_Admins")
            row = cursor.fetchone()
            admin_count = int(row[0]) if row and row[0] is not None else 0
        except Exception:
            admin_count = 0

        try:
            cursor.execute("SELECT COUNT(*) FROM Lecturers")
            row = cursor.fetchone()
            lecturer_count = int(row[0]) if row and row[0] is not None else 0
        except Exception:
            lecturer_count = 0

        try:
            cursor.execute("SELECT COUNT(*) FROM Students")
            row = cursor.fetchone()
            student_count = int(row[0]) if row and row[0] is not None else 0
        except Exception:
            student_count = 0

        total_registered_users = pm_count + admin_count + lecturer_count + student_count

        # Pending subscriptions (top 5)
        try:
            cursor.execute("SELECT unreg_user_id, email, full_name, institution_name, applied_at, selected_plan_id FROM Unregistered_Users WHERE status = 'pending' ORDER BY applied_at DESC LIMIT 5")
            pending_rows = cursor.fetchall() or []
            pending_subscriptions = []
            for r in pending_rows:
                # r may be a tuple-like row
                pending_subscriptions.append({
                    'id': r[0],
                    'email': r[1],
                    'full_name': r[2],
                    'institution_name': r[3],
                    'request_date': r[4].strftime('%Y-%m-%d') if hasattr(r[4], 'strftime') else str(r[4]),
                    'plan_id': r[5]
                })
        except Exception:
            pending_subscriptions = []

        # Recent institution changes (use created_at as proxy)
        try:
            cursor.execute("SELECT institution_id, name, created_at, is_active FROM Institutions ORDER BY created_at DESC LIMIT 5")
            inst_rows = cursor.fetchall() or []
            recent_changes = []
            for r in inst_rows:
                recent_changes.append({
                    'action': f"Created institution: {r[1]}",
                    'date': r[2].strftime('%Y-%m-%d') if hasattr(r[2], 'strftime') else str(r[2]),
                    'link': url_for('institution.institution_profile') if 'institution' in globals() else url_for('platform.pending_registrations')
                })
        except Exception:
            recent_changes = []

        # Recent reports (if a Reports table exists)
        try:
            cursor.execute("SELECT report_id, institution_name, created_at, report_type FROM Reports ORDER BY created_at DESC LIMIT 5")
            rep_rows = cursor.fetchall() or []
            recent_reports = []
            for r in rep_rows:
                recent_reports.append({
                    'id': r[0],
                    'case_id': r[0],
                    'institution': r[1],
                    'date': r[2].strftime('%Y-%m-%d') if hasattr(r[2], 'strftime') else str(r[2]),
                    'type': r[3]
                })
        except Exception:
            recent_reports = []

    except Exception:
        # If any DB errors happen, fall back to empty/default data
        pass


    return render_template('platmanager/platform_manager_dashboard.html',
                               user=session['user'],
                               total_institutions=total_institutions,
                               active_institutions=active_institutions,
                               pending_subscriptions_count=pending_subscriptions_count,
                               total_registered_users=total_registered_users,
                               pending_subscriptions=pending_subscriptions,
                               recent_changes=recent_changes,
                               recent_reports=recent_reports)


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

    return render_template('platmanager/pending_registrations.html', user=auth_result['user'], requests=rows)


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


@platform_bp.route('/users')
def user_management():
    """Platform manager - user management"""
    auth_result = AuthControl.verify_session(current_app, session)
    if not auth_result['success'] or auth_result['user'].get('user_type') != 'platform_manager':
        flash('Access denied. Platform manager privileges required.', 'danger')
        return redirect(url_for('auth.login'))


    return render_template('platmanager/platform_manager_user_management.html', user=auth_result['user'])



@platform_bp.route('/subscriptions')
def subscription_management():
    """Platform manager - subscription management"""
    auth_result = AuthControl.verify_session(current_app, session)
    if not auth_result['success'] or auth_result['user'].get('user_type') != 'platform_manager':
        flash('Access denied. Platform manager privileges required.', 'danger')
        return redirect(url_for('auth.login'))


    return render_template('platmanager/platform_manager_subscription_management.html', user=auth_result['user'])



@platform_bp.route('/subscriptions/profile-creator')
def subscription_profile_creator():
    """Platform manager - create/edit subscription profiles"""
    auth_result = AuthControl.verify_session(current_app, session)
    if not auth_result['success'] or auth_result['user'].get('user_type') != 'platform_manager':
        flash('Access denied. Platform manager privileges required.', 'danger')
        return redirect(url_for('auth.login'))


    return render_template('platmanager/platform_manager_subscription_management_profile_creator.html', user=auth_result['user'])




@platform_bp.route('/reports')
def report_management():
    """Platform manager - reports overview"""
    auth_result = AuthControl.verify_session(current_app, session)
    if not auth_result['success'] or auth_result['user'].get('user_type') != 'platform_manager':
        flash('Access denied. Platform manager privileges required.', 'danger')
        return redirect(url_for('auth.login'))

    # TODO: query reports from DB

    return render_template('platmanager/platform_manager_report_management.html', user=auth_result['user'])



@platform_bp.route('/reports/<int:report_id>')
def report_details(report_id):
    """Platform manager - specific report details"""
    auth_result = AuthControl.verify_session(current_app, session)
    if not auth_result['success'] or auth_result['user'].get('user_type') != 'platform_manager':
        flash('Access denied. Platform manager privileges required.', 'danger')
        return redirect(url_for('auth.login'))

    # TODO: fetch report by id from DB

    return render_template('platmanager/platform_manager_report_management_report_details.html', user=auth_result['user'], report_id=report_id)



@platform_bp.route('/performance')
def performance_management():
    """Platform manager - performance management"""
    auth_result = AuthControl.verify_session(current_app, session)
    if not auth_result['success'] or auth_result['user'].get('user_type') != 'platform_manager':
        flash('Access denied. Platform manager privileges required.', 'danger')
        return redirect(url_for('auth.login'))


    return render_template('platmanager/platform_manager_performance_management.html', user=auth_result['user'])



@platform_bp.route('/settings')
def settings_management():
    """Platform manager - settings"""
    auth_result = AuthControl.verify_session(current_app, session)
    if not auth_result['success'] or auth_result['user'].get('user_type') != 'platform_manager':
        flash('Access denied. Platform manager privileges required.', 'danger')
        return redirect(url_for('auth.login'))


    return render_template('platmanager/platform_manager_settings_management.html', user=auth_result['user'])
