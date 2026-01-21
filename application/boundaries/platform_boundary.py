from flask import Blueprint, render_template, request, jsonify, session, current_app, flash, redirect, url_for
from datetime import datetime, timedelta

from application.controls.auth_control import AuthControl, requires_roles, requires_roles_api
from application.controls.platform_control import PlatformControl
from application.controls.testimonial_control import TestimonialControl
from application.entities.base_entity import BaseEntity
from application.entities2.institution import InstitutionModel
from application.entities2.subscription import SubscriptionModel
from application.entities2.testimonial import TestimonialModel
from application.entities2.user import UserModel
from database.base import get_session
from database.models import User

platform_bp = Blueprint('platform', __name__)

@platform_bp.route('/')
@requires_roles('platform_manager')
def platform_dashboard():
    """Platform manager dashboard"""
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
@requires_roles('platform_manager')
def pending_registrations():
    """List pending registration requests for review (platform manager view)"""


    # Use PlatformControl to get pending subscriptions
    result = PlatformControl.get_pending_subscriptions()
    
    if not result['success']:
        flash(result.get('error', 'Error loading pending registrations'), 'danger')
        pending_requests = []
    else:
        pending_requests = result.get('pending_subscriptions', [])
    
    return render_template('platmanager/platform_manager_subscription_management_pending_registrations.html',
                         requests=pending_requests)


@platform_bp.route('/pending-registrations/approve/<int:subscription_id>', methods=['POST'])
@requires_roles('platform_manager')
def approve_registration(subscription_id):
    """Approve a pending registration request"""
    reviewer_id = session.get('user_id')
    
    # Use PlatformControl to handle the approval
    result = PlatformControl.approve_subscription(
        subscription_id=subscription_id,
        reviewer_id=reviewer_id
    )

    if result.get('success'):
        flash('Registration approved successfully.', 'success')
        return redirect(url_for('platform.pending_registrations'))

    flash(result.get('error') or 'Failed to approve registration', 'danger')
    return redirect(url_for('platform.pending_registrations'))

@platform_bp.route('/pending-registrations/reject/<int:subscription_id>', methods=['POST'])
@requires_roles('platform_manager')
def reject_registration(subscription_id):
    """Reject a pending registration request"""
    reviewer_id = session.get('user_id')
    
    # Use PlatformControl to handle the rejection
    result = PlatformControl.reject_subscription(
        subscription_id=subscription_id,
        reviewer_id=reviewer_id
    )

    if result.get('success'):
        flash(f'Registration rejected: {result.get("message", "")}', 'success')
        return redirect(url_for('platform.pending_registrations'))

    flash(result.get('error') or 'Failed to reject registration', 'danger')
    return redirect(url_for('platform.pending_registrations'))

@platform_bp.route('/users')
@requires_roles('platform_manager')
def user_management():
    """Platform manager - user management"""
    with get_session() as session:
        user_model = UserModel(session)
        context = {
            "overview_stats": user_model.pm_user_stats(),
        }
    return render_template('platmanager/platform_manager_user_management.html', **context)


@platform_bp.route('/users/retrieve', methods=['GET'])
@requires_roles('platform_manager')
def retrieve_paginated_users():
    """Retrieve paginated user information"""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 5))
    with get_session() as session:
        user_model = UserModel(session)
        return jsonify(user_model.pm_retrieve_page(page, per_page))

@platform_bp.route('/subscriptions')
@requires_roles('platform_manager')
def subscription_management():
    """Platform manager - subscription management"""
    PER_PAGE = 5
    page = int(request.args.get('page', 1))
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '')
    plan_filter = request.args.get('plan', '')
    
    # Use PlatformControl to get data
    institutions_result = PlatformControl.get_institutions_with_filters(
        search=search,
        status=status_filter,
        plan=plan_filter,
        page=page,
        per_page=PER_PAGE
    )
    
    requests_result = PlatformControl.get_subscription_requests(limit=5)
    stats_result = PlatformControl.get_subscription_statistics()
    
    # Check for errors
    if not institutions_result['success']:
        flash(institutions_result.get('error', 'Error loading institutions'), 'danger')
        institutions = []
        pagination = {}
    else:
        institutions = institutions_result['institutions']
        pagination = institutions_result['pagination']
    
    if not requests_result['success']:
        flash(requests_result.get('error', 'Error loading subscription requests'), 'danger')
        subscription_requests = []
    else:
        subscription_requests = requests_result['requests']
    
    if not stats_result['success']:
        flash(stats_result.get('error', 'Error loading statistics'), 'danger')
        stats = {}
    else:
        stats = stats_result['statistics']
    
    context = {
        'institutions': institutions,
        'subscription_requests': subscription_requests,
        'stats': stats,
        
        # Pagination data
        'current_page': pagination.get('current_page', page),
        'total_pages': pagination.get('total_pages', 1),
        'has_prev': pagination.get('has_prev', False),
        'has_next': pagination.get('has_next', False),
        'start_idx': pagination.get('start_idx', 0),
        'end_idx': pagination.get('end_idx', 0),
        'total_institutions': pagination.get('total_items', 0),
        
        # Filter values (for preserving state)
        'search_term': search,
        'status_filter': status_filter,
        'plan_filter': plan_filter,
        
        # Statistics
        'active_institutions': stats.get('active_institutions', 0),
        'suspended_institutions': stats.get('suspended_institutions', 0),
        'pending_requests': stats.get('pending_requests', 0),
        'new_institutions_quarter': stats.get('new_institutions_quarter', 0),
    }
    
    return render_template('platmanager/platform_manager_subscription_management.html', **context)

@platform_bp.route('/api/institutions/create', methods=['POST'])
@requires_roles_api('platform_manager')
def create_institution():
    """Create a new institution profile"""
    data = request.json
    
    result = PlatformControl.create_institution_profile(data)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400
        
@platform_bp.route('/api/subscriptions/<int:subscription_id>/update-status', methods=['POST'])
@requires_roles_api('platform_manager')
def update_subscription_status(subscription_id):
    """Update subscription status (activate, suspend, etc.)"""
    data = request.json
    new_status = data.get('status')
    
    # Get reviewer_id from session
    reviewer_id = session.get('user_id')
    
    result = PlatformControl.update_subscription_status(
        subscription_id=subscription_id,
        new_status=new_status,
        reviewer_id=reviewer_id
    )
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400
        
@platform_bp.route('/api/subscription-requests/<int:request_id>/process', methods=['POST'])
@requires_roles_api('platform_manager')
def process_subscription_request(request_id):
    """Approve or reject a subscription request"""
    data = request.json
    action = data.get('action')
    
    # Get reviewer_id from session
    reviewer_id = session.get('user_id')
    
    result = PlatformControl.process_subscription_request(
        request_id=request_id,
        action=action,
        reviewer_id=reviewer_id
    )
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400
        
@platform_bp.route('/api/institutions/search', methods=['GET'])
@requires_roles_api('platform_manager')
def search_institutions():
    """Search institutions by name, contact, or plan"""
    search_term = request.args.get('q', '').strip()
    status = request.args.get('status', '')
    plan = request.args.get('plan', '')
    
    with get_session() as session:
        inst_model = InstitutionModel(session)
        
        # Get filtered institutions
        institutions = inst_model.search(
            search_term=search_term,
            status=status,
            plan=plan
        )
        
        return jsonify({
            'success': True,
            'institutions': institutions,
            'count': len(institutions)
        })


@platform_bp.route('/api/subscriptions/stats', methods=['GET'])
@requires_roles_api('platform_manager')
def get_subscription_stats():
    """Get subscription statistics for dashboard"""
    with get_session() as session:
        inst_model = InstitutionModel(session)
        sub_model = SubscriptionModel(session)
        
        # Get counts
        total_institutions = inst_model.count()
        active_subscriptions = sub_model.count_by_status('active')
        suspended_subscriptions = sub_model.count_by_status('suspended')
        pending_requests = sub_model.count_by_status('pending')
        
        # Calculate growth (simplified - would query historical data in real app)
        # This could be moved to a separate method that queries historical data
        growth_data = {
            'total_growth': 3,  # +3 this quarter
            'active_growth': '+5%',  # +5% growth
            'suspended_growth': '-1',  # -1 this month
        }
        
        return jsonify({
            'success': True,
            'stats': {
                'total_institutions': total_institutions,
                'active_institutions': active_subscriptions,
                'suspended_subscriptions': suspended_subscriptions,
                'pending_requests': pending_requests,
                'growth': growth_data
            }
        })
    
@platform_bp.route('/api/institutions/<int:institution_id>', methods=['GET'])
@requires_roles_api('platform_manager')
def get_institution_details(institution_id):
    """Get institution details"""
    result = PlatformControl.get_institution_details(institution_id)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 404
    
@platform_bp.route('/api/institutions/<int:institution_id>/update', methods=['POST'])
def update_institution(institution_id):
    """Update institution profile"""
    data = request.json
    
    result = PlatformControl.update_institution_profile(
        institution_id=institution_id,
        update_data=data
    )
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400

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

@platform_bp.route('/testimonials')
@requires_roles('platform_manager')
def testimonial_review():
    """Platform manager - testimonial review and approval"""
    status_filter = request.args.get('status', 'pending')
    
    with get_session() as session:
        testimonial_model = TestimonialModel(session)
        
        # Get testimonials based on filter
        if status_filter == 'all':
            testimonials_data = testimonial_model.get_all_testimonials_with_status()
        else:
            testimonials_data = testimonial_model.get_all_testimonials_with_status(status=status_filter)
        
        # Get counts for each status
        stats = {
            'pending': testimonial_model.count_by_status('pending'),
            'approved': testimonial_model.count_by_status('approved'),
            'rejected': testimonial_model.count_by_status('rejected'),
        }
        
        context = {
            'testimonials': testimonials_data,
            'stats': stats,
            'status_filter': status_filter,
        }
    
    return render_template('platmanager/platform_manager_testimonial_approve.html', **context)

@platform_bp.route('/testimonials/approve/<int:testimonial_id>', methods=['POST'])
@requires_roles('platform_manager')
def approve_testimonial(testimonial_id):
    """Approve a testimonial"""
    reviewer_id = session.get('user_id')
    status_filter = request.args.get('status', 'pending')
    
    result = TestimonialControl.update_testimonial_status(
        app=current_app,
        testimonial_id=testimonial_id,
        new_status='approved',
        reviewer_id=reviewer_id
    )
    
    if result.get('success'):
        flash('Testimonial approved successfully.', 'success')
    else:
        flash(result.get('error', 'Failed to approve testimonial'), 'danger')
    
    return redirect(url_for('platform.testimonial_review', status=status_filter))

@platform_bp.route('/testimonials/reject/<int:testimonial_id>', methods=['POST'])
@requires_roles('platform_manager')
def reject_testimonial(testimonial_id):
    """Reject a testimonial"""
    reviewer_id = session.get('user_id')
    status_filter = request.args.get('status', 'pending')
    
    result = TestimonialControl.update_testimonial_status(
        app=current_app,
        testimonial_id=testimonial_id,
        new_status='rejected',
        reviewer_id=reviewer_id
    )
    
    if result.get('success'):
        flash('Testimonial rejected.', 'success')
    else:
        flash(result.get('error', 'Failed to reject testimonial'), 'danger')
    
    return redirect(url_for('platform.testimonial_review', status=status_filter))

@platform_bp.route('/testimonials/delete/<int:testimonial_id>', methods=['POST'])
@requires_roles('platform_manager')
def delete_testimonial(testimonial_id):
    """Delete a testimonial"""
    user_id = session.get('user_id')
    status_filter = request.args.get('status', 'pending')
    
    result = TestimonialControl.delete_testimonial(
        app=current_app,
        testimonial_id=testimonial_id,
        user_id=user_id,
        is_admin=True
    )
    
    if result.get('success'):
        flash('Testimonial deleted successfully.', 'success')
    else:
        flash(result.get('error', 'Failed to delete testimonial'), 'danger')
    
    return redirect(url_for('platform.testimonial_review', status=status_filter))

@platform_bp.route('/create')
@requires_roles('platform_manager')
def subscription_profile_creator():
    """Subscription profile creation page"""
    return render_template('platmanager/platform_manager_subscription_management_profile_creator.html')

@platform_bp.route('/api/debug-session', methods=['GET'])
def debug_session():
    return jsonify({
        'session': dict(session),
        'user_role': session.get('role'),
        'user_type': session.get('user_type'),
        'user_id': session.get('user_id')
    })
