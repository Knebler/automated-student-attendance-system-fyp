from flask import Blueprint, render_template, request, jsonify, session, current_app, flash, redirect, url_for
from datetime import datetime, timedelta

from application.controls.auth_control import AuthControl, requires_roles, requires_roles_api
from application.controls.platform_control import PlatformControl
from application.controls.testimonial_control import TestimonialControl
from application.controls.platformissue_control import PlatformIssueControl
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
    # Use PlatformControl to get dashboard statistics
    stats_result = PlatformControl.get_platform_dashboard_stats()
    
    if not stats_result['success']:
        flash(stats_result.get('error', 'Error loading dashboard statistics'), 'danger')
        stats = {}
    else:
        stats = stats_result['statistics']
    
    # Get recent subscription requests
    requests_result = PlatformControl.get_subscription_requests(limit=5)
    recent_requests = requests_result.get('requests', []) if requests_result['success'] else []
    
    # Get recent issues for dashboard (only open/pending issues)
    issues_result = PlatformIssueControl.get_recent_issues(limit=5)
    recent_issues = issues_result.get('issues', []) if issues_result['success'] else []
    
    context = {
        'statistics': stats,
        'recent_requests': recent_requests,
        'recent_issues': recent_issues,  # Added recent issues
        'total_subscription_count': stats.get('total_institutions', 0),
        'active_subscription_count': stats.get('active_institutions', 0),
        'total_user_count': stats.get('total_users', 0),
        'recent_subscriptions': recent_requests,  # Use recent requests for recent subscriptions
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
        'suspended_subscriptions': stats.get('suspended_subscriptions', 0),  # Fixed field name
        'pending_requests': stats.get('pending_requests', 0),
        'new_institutions_quarter': stats.get('new_institutions_quarter', 0),
        'expired_subscriptions': stats.get('expired_subscriptions', 0),
        'total_institutions_count': stats.get('total_institutions', 0),
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
    
    if not new_status:
        return jsonify({'success': False, 'error': 'Status is required'}), 400
    
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
    
    if not action or action not in ['approve', 'reject']:
        return jsonify({'success': False, 'error': 'Valid action (approve/reject) is required'}), 400
    
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
    # Use PlatformControl.get_subscription_statistics() which already handles this
    result = PlatformControl.get_subscription_statistics()
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 500

@platform_bp.route('/api/dashboard/stats', methods=['GET'])
@requires_roles_api('platform_manager')
def get_dashboard_stats():
    """Get comprehensive dashboard statistics"""
    result = PlatformControl.get_platform_dashboard_stats()
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 500
    
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

@platform_bp.route('/issues')
@requires_roles('platform_manager')
def issue_management():
    """Platform manager - issue management overview"""
    status_filter = request.args.get('status', 'open')
    priority_filter = request.args.get('priority', '')
    category_filter = request.args.get('category', '')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    
    # Get issues with filters
    issues_result = PlatformIssueControl.get_issues_for_platform_manager(
        status=status_filter,
        priority=priority_filter,
        category=category_filter,
        page=page,
        per_page=per_page
    )
    
    # Get issue statistics
    stats_result = PlatformIssueControl.get_issue_statistics_for_platform_manager()
    
    if not issues_result['success']:
        flash(issues_result.get('error', 'Error loading issues'), 'danger')
        issues = []
        pagination = {}
    else:
        issues = issues_result['issues']
        pagination = issues_result['pagination']
    
    if not stats_result['success']:
        flash(stats_result.get('error', 'Error loading issue statistics'), 'danger')
        stats = {}
    else:
        stats = stats_result['statistics']
    
    context = {
        'issues': issues,
        'stats': stats,
        'current_page': pagination.get('current_page', page),
        'total_pages': pagination.get('total_pages', 1),
        'has_prev': pagination.get('has_prev', False),
        'has_next': pagination.get('has_next', False),
        'total_issues': pagination.get('total_items', 0),
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'category_filter': category_filter,
    }
    
    return render_template('platmanager/platform_manager_report_management.html', **context)

@platform_bp.route('/issues/<int:issue_id>')
@requires_roles('platform_manager')
def issue_details(issue_id):
    """Platform manager - view specific issue details"""
    result = PlatformIssueControl.get_issue_details_for_platform_manager(issue_id)
    
    if not result['success']:
        flash(result.get('error', 'Issue not found'), 'danger')
        return redirect(url_for('platform.issue_management'))
    
    context = {
        'issue': result.get('issue', {}),
        'comments': result.get('comments', []),
        'history': result.get('history', []),
    }
    
    return render_template('platmanager/platform_manager_report_management_report_details.html', **context)

@platform_bp.route('/issues/resolve/<int:issue_id>', methods=['POST'])
@requires_roles('platform_manager')
def resolve_issue_platform_manager(issue_id):
    """Platform manager - resolve an issue"""
    resolver_id = session.get('user_id')
    resolution_notes = request.form.get('resolution_notes', '').strip()
    
    if not resolution_notes:
        flash('Resolution notes are required', 'danger')
        return redirect(url_for('platform.issue_details', issue_id=issue_id))
    
    result = PlatformIssueControl.resolve_issue_platform_manager(
        issue_id=issue_id,
        resolver_id=resolver_id,
        resolution_notes=resolution_notes
    )
    
    if result['success']:
        flash('Issue resolved successfully', 'success')
    else:
        flash(result.get('error', 'Failed to resolve issue'), 'danger')
    
    return redirect(url_for('platform.issue_details', issue_id=issue_id))

@platform_bp.route('/issues/reject/<int:issue_id>', methods=['POST'])
@requires_roles('platform_manager')
def reject_issue_platform_manager(issue_id):
    """Platform manager - reject an issue"""
    resolver_id = session.get('user_id')
    rejection_reason = request.form.get('rejection_reason', '').strip()
    
    if not rejection_reason:
        flash('Rejection reason is required', 'danger')
        return redirect(url_for('platform.issue_details', issue_id=issue_id))
    
    result = PlatformIssueControl.reject_issue_platform_manager(
        issue_id=issue_id,
        resolver_id=resolver_id,
        rejection_reason=rejection_reason
    )
    
    if result['success']:
        flash('Issue rejected', 'success')
    else:
        flash(result.get('error', 'Failed to reject issue'), 'danger')
    
    return redirect(url_for('platform.issue_details', issue_id=issue_id))

@platform_bp.route('/api/issues/stats')
@requires_roles_api('platform_manager')
def get_issue_stats():
    """Get issue statistics for dashboard (AJAX endpoint)"""
    result = PlatformIssueControl.get_issue_statistics_for_platform_manager()
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 500

@platform_bp.route('/api/issues/recent')
@requires_roles_api('platform_manager')
def get_recent_issues():
    """Get recent issues for dashboard (AJAX endpoint)"""
    limit = int(request.args.get('limit', 5))
    
    result = PlatformIssueControl.get_recent_issues(limit=limit)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 500

@platform_bp.route('/api/issues/search')
@requires_roles_api('platform_manager')
def search_issues():
    """Search issues by various criteria"""
    search_term = request.args.get('q', '').strip()
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')
    category = request.args.get('category', '')
    
    result = PlatformIssueControl.search_issues(
        search_term=search_term,
        status=status,
        priority=priority,
        category=category
    )
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 500

@platform_bp.route('/api/debug-session', methods=['GET'])
def debug_session():
    return jsonify({
        'session': dict(session),
        'user_role': session.get('role'),
        'user_type': session.get('user_type'),
        'user_id': session.get('user_id')
    })