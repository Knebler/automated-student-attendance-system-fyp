from flask import Blueprint, render_template, request, jsonify, session, current_app, flash, redirect, url_for
from datetime import datetime

from application.controls.auth_control import AuthControl, requires_roles
from application.entities.base_entity import BaseEntity
from application.entities2.institution import InstitutionModel
from application.entities2.subscription import SubscriptionModel
from application.entities2.user import UserModel
from database.base import get_session
from database.models import User

platform_bp = Blueprint('platform', __name__)

@platform_bp.route('/')
@requires_roles('platform_manager')
def platform_dashboard():
    """Platform manager dashboard (alias of platform manager)"""
    with get_session() as session:
        inst_model = InstitutionModel(session)
        sub_model = SubscriptionModel(session)
        user_model = UserModel(session)

        subscriptions = sub_model.get_all()
        active_subscriptions = [sub for sub in subscriptions if sub.is_active == True]
        recent_subscriptions = sorted(active_subscriptions, key=lambda sub: sub.created_at, reverse=True)[:5]

        context = {
            'total_subscription_count': len(subscriptions),
            'active_subscription_count': len(active_subscriptions),
            'total_user_count': user_model.count(),
            'recent_subscriptions': [{
                "institution_name": inst_model.get_one(subscription_id=sub.subscription_id).name,
                "request_date": sub.created_at,
            } for sub in recent_subscriptions],
        }
    return render_template('platmanager/platform_manager_dashboard.html', **context)


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
@requires_roles('platform_manager')
def user_management():
    """Platform manager - user management"""
    PER_PAGE = 5
    with get_session() as session:
        user_model = UserModel(session)
        inst_model = InstitutionModel(session)
        page = int(request.args.get('page', 1))
        paginated_info = user_model.get_paginated(page, PER_PAGE)
        users = paginated_info.pop('items')
        def get_info(user: User):
            info = user.as_sanitized_dict()
            name_split = user.name.split(' ')
            if len(name_split) > 1:
                info['initials'] = name_split[0][0] + name_split[-1][0]
            else:
                info['initials'] = name_split[0][:2]
            info['institution'] = inst_model.get_by_id(user.institution_id).name
            return info
        context = {
            "overview_stats": user_model.pm_user_stats(),
            "users": [
                get_info(user) for user in users
            ],
            "table": {
                "start": (page-1)*PER_PAGE + 1,
                "end": min(page * PER_PAGE, paginated_info['total']),
                "total": paginated_info['total'],
                "pages": paginated_info['pages'],
                "page": page,
            },
        }
    print(context)
    return render_template('platmanager/platform_manager_user_management.html', **context)


@platform_bp.route('/subscriptions')
@requires_roles('platform_manager')
def subscription_management():
    """Platform manager - subscription management"""
    return render_template('platmanager/platform_manager_subscription_management.html')


@platform_bp.route('/subscriptions/profile-creator')
def subscription_profile_creator():
    """Platform manager - create/edit subscription profiles"""
    auth_result = AuthControl.verify_session(current_app, session)
    if not auth_result['success'] or auth_result['user'].get('user_type') != 'platform_manager':
        flash('Access denied. Platform manager privileges required.', 'danger')
        return redirect(url_for('auth.login'))
    return render_template('platmanager/platform_manager_subscription_management_profile_creator.html', user=auth_result['user'])


@platform_bp.route('/reports')
@requires_roles('platform_manager')
def report_management():
    """Platform manager - reports overview"""
    # TODO: query reports from DB
    return render_template('platmanager/platform_manager_report_management.html')


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
@requires_roles('platform_manager')
def performance_management():
    """Platform manager - performance management"""
    return render_template('platmanager/platform_manager_performance_management.html')


@platform_bp.route('/settings')
@requires_roles('platform_manager')
def settings_management():
    """Platform manager - settings"""
    return render_template('platmanager/platform_manager_settings_management.html')
