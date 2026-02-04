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
from database.models import User, Feature, HeroFeature, Stat, AboutIntro, AboutStory, AboutMissionVision, TeamMember, AboutValue, SubscriptionPlan, HomepageFeatureCard

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
        institution_model = InstitutionModel(session)
        
        # Get all institutions for the dropdown
        institutions = institution_model.get_all()
        
        context = {
            "overview_stats": user_model.pm_user_stats(),
            "institutions": [
                {
                    'institution_id': inst.institution_id,
                    'name': inst.name
                }
                for inst in institutions
            ]
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
    
    # Get subscriptions (not institutions) with filters
    subscriptions_result = PlatformControl.get_subscriptions_with_institutions(
        search=search,
        status=status_filter,
        plan=plan_filter,
        page=page,
        per_page=PER_PAGE
    )
    
    # Get pending subscription requests separately
    requests_result = PlatformControl.get_subscription_requests(limit=5)
    stats_result = PlatformControl.get_subscription_statistics()
    
    # Get subscription plans for dropdowns
    with get_session() as db_session:
        subscription_plans = db_session.query(SubscriptionPlan).filter_by(is_active=True).all()
        plans_list = [{'plan_id': p.plan_id, 'name': p.name, 'max_users': p.max_users} for p in subscription_plans]
    
    # Check for errors
    if not subscriptions_result['success']:
        flash(subscriptions_result.get('error', 'Error loading subscriptions'), 'danger')
        subscriptions = []
        pagination = {}
    else:
        subscriptions = subscriptions_result['subscriptions']
        pagination = subscriptions_result['pagination']
    
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
    
    # Transform subscriptions to match template structure
    institutions_for_template = []
    for sub in subscriptions:
        # Extract institution data from subscription
        institution_data = {
            'institution_id': sub.get('institution_id'),
            'subscription_id': sub.get('subscription_id'),
            'name': sub.get('institution_name', 'Unknown'),
            'location': sub.get('institution_location', ''),
            'initials': sub.get('initials', ''),
            'plan': sub.get('plan_name', 'none'),
            'status': sub.get('status', 'inactive'),
            'subscription_start_date': sub.get('start_date', ''),
            'subscription_end_date': sub.get('end_date', ''),
            'contact_person': sub.get('contact_person', ''),
            'contact_email': sub.get('contact_email', '')
        }
        institutions_for_template.append(institution_data)
    
    context = {
        'institutions': institutions_for_template,
        'subscription_requests': subscription_requests,
        'stats': stats,
        'subscription_plans': plans_list,
        
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
        'suspended_subscriptions': stats.get('suspended_subscriptions', 0),
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
@requires_roles_api('platform_manager')
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

# =====================
# FEATURE MANAGEMENT
# =====================

@platform_bp.route('/landing-page')
@requires_roles('platform_manager')
def landing_page_management():
    """Platform manager - landing page and about us management"""
    import json
    with get_session() as db_session:
        # Get hero features
        hero_features = db_session.query(HeroFeature).order_by(HeroFeature.display_order, HeroFeature.hero_feature_id).all()
        hero_features_list = [hf.as_dict() for hf in hero_features]
        
        # Get stats
        stats = db_session.query(Stat).order_by(Stat.display_order, Stat.stat_id).all()
        stats_list = [s.as_dict() for s in stats]
        
        # Get features
        features = db_session.query(Feature).order_by(Feature.display_order, Feature.feature_id).all()
        features_list = [f.as_dict() for f in features]
        
        # Get About Us content
        about_intro = db_session.query(AboutIntro).first()
        about_intro_dict = about_intro.as_dict() if about_intro else None
        
        about_story = db_session.query(AboutStory).first()
        about_story_dict = about_story.as_dict() if about_story else None
        
        mission_vision = db_session.query(AboutMissionVision).all()
        mission_vision_list = [mv.as_dict() for mv in mission_vision]
        
        team_members = db_session.query(TeamMember).order_by(TeamMember.display_order).all()
        team_members_list = []
        for tm in team_members:
            tm_dict = tm.as_dict()
            tm_dict['contributions'] = json.loads(tm.contributions) if tm.contributions else []
            tm_dict['skills'] = json.loads(tm.skills) if tm.skills else []
            team_members_list.append(tm_dict)
        
        values = db_session.query(AboutValue).order_by(AboutValue.display_order).all()
        values_list = [v.as_dict() for v in values]
        
        # Calculate statistics
        total_hero_features = len(hero_features)
        active_hero_features = sum(1 for hf in hero_features if hf.is_active)
        
        total_stats = len(stats)
        active_stats = sum(1 for s in stats if s.is_active)
        
        total_features = len(features)
        active_features = sum(1 for f in features if f.is_active)
        main_features_count = sum(1 for f in features if not f.is_advanced)
        advanced_features_count = sum(1 for f in features if f.is_advanced)
        
        total_team_members = len(team_members)
        active_team_members = sum(1 for tm in team_members if tm.is_active)
        
        total_values = len(values)
        active_values = sum(1 for v in values if v.is_active)
        
        # Get subscription plans
        subscription_plans = db_session.query(SubscriptionPlan).order_by(SubscriptionPlan.plan_id).all()
        subscription_plans_list = []
        for sp in subscription_plans:
            sp_dict = sp.as_dict()
            sp_dict['features'] = json.loads(sp.features) if sp.features else {}
            subscription_plans_list.append(sp_dict)
        
        total_subscription_plans = len(subscription_plans)
        active_subscription_plans = sum(1 for sp in subscription_plans if sp.is_active)
        
        # Get homepage feature cards
        feature_cards = db_session.query(HomepageFeatureCard).order_by(HomepageFeatureCard.display_order).all()
        feature_cards_list = [fc.as_dict() for fc in feature_cards]
        
        total_feature_cards = len(feature_cards)
        active_feature_cards = sum(1 for fc in feature_cards if fc.is_active)
        
    context = {
        'hero_features': hero_features_list,
        'total_hero_features': total_hero_features,
        'active_hero_features': active_hero_features,
        
        'stats': stats_list,
        'total_stats': total_stats,
        'active_stats': active_stats,
        
        'features': features_list,
        'total_features': total_features,
        'active_features': active_features,
        'main_features_count': main_features_count,
        'advanced_features_count': advanced_features_count,
        
        'about_intro': about_intro_dict,
        'about_story': about_story_dict,
        'mission_vision': mission_vision_list,
        'team_members': team_members_list,
        'total_team_members': total_team_members,
        'active_team_members': active_team_members,
        'values': values_list,
        'total_values': total_values,
        'active_values': active_values,
        'subscription_plans': subscription_plans_list,
        'total_subscription_plans': total_subscription_plans,
        'active_subscription_plans': active_subscription_plans,
        'feature_cards': feature_cards_list,
        'total_feature_cards': total_feature_cards,
        'active_feature_cards': active_feature_cards
    }
    
    return render_template('platmanager/platform_manager_landing_page.html', **context)

@platform_bp.route('/api/features/create', methods=['POST'])
@requires_roles_api('platform_manager')
def create_feature():
    """Create a new feature"""
    try:
        data = request.json
        
        with get_session() as db_session:
            # Check if slug already exists
            existing = db_session.query(Feature).filter_by(slug=data['slug']).first()
            if existing:
                return jsonify({'success': False, 'error': 'A feature with this slug already exists'}), 400
            
            # Create new feature
            feature = Feature(
                slug=data['slug'],
                icon=data['icon'],
                title=data['title'],
                description=data['description'],
                details=data.get('details', ''),
                try_url=data.get('try_url', ''),
                display_order=data.get('display_order', 0),
                is_active=data.get('is_active', True),
                is_advanced=data.get('is_advanced', False)
            )
            
            db_session.add(feature)
            db_session.commit()
            
        return jsonify({'success': True, 'message': 'Feature created successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@platform_bp.route('/api/features/<int:feature_id>/update', methods=['POST'])
@requires_roles_api('platform_manager')
def update_feature(feature_id):
    """Update an existing feature"""
    try:
        data = request.json
        
        with get_session() as db_session:
            feature = db_session.query(Feature).filter_by(feature_id=feature_id).first()
            
            if not feature:
                return jsonify({'success': False, 'error': 'Feature not found'}), 404
            
            # Check if slug is being changed and if it conflicts
            if data['slug'] != feature.slug:
                existing = db_session.query(Feature).filter_by(slug=data['slug']).first()
                if existing:
                    return jsonify({'success': False, 'error': 'A feature with this slug already exists'}), 400
            
            # Update feature
            feature.slug = data['slug']
            feature.icon = data['icon']
            feature.title = data['title']
            feature.description = data['description']
            feature.details = data.get('details', '')
            feature.try_url = data.get('try_url', '')
            feature.display_order = data.get('display_order', 0)
            feature.is_active = data.get('is_active', True)
            feature.is_advanced = data.get('is_advanced', False)
            
            db_session.commit()
            
        return jsonify({'success': True, 'message': 'Feature updated successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@platform_bp.route('/api/features/<int:feature_id>/toggle-status', methods=['POST'])
@requires_roles_api('platform_manager')
def toggle_feature_status(feature_id):
    """Toggle feature active status"""
    try:
        data = request.json
        
        with get_session() as db_session:
            feature = db_session.query(Feature).filter_by(feature_id=feature_id).first()
            
            if not feature:
                return jsonify({'success': False, 'error': 'Feature not found'}), 404
            
            feature.is_active = data.get('is_active', not feature.is_active)
            db_session.commit()
            
        return jsonify({'success': True, 'message': 'Feature status updated successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@platform_bp.route('/api/features/<int:feature_id>/delete', methods=['POST'])
@requires_roles_api('platform_manager')
def delete_feature(feature_id):
    """Delete a feature"""
    try:
        with get_session() as db_session:
            feature = db_session.query(Feature).filter_by(feature_id=feature_id).first()
            
            if not feature:
                return jsonify({'success': False, 'error': 'Feature not found'}), 404
            
            db_session.delete(feature)
            db_session.commit()
            
        return jsonify({'success': True, 'message': 'Feature deleted successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ====================
# HERO FEATURES API
# ====================

@platform_bp.route('/api/hero-features/create', methods=['POST'])
@requires_roles_api('platform_manager')
def create_hero_feature():
    """Create a new hero feature"""
    try:
        data = request.json
        
        with get_session() as db_session:
            hero_feature = HeroFeature(
                title=data['title'],
                description=data['description'],
                summary=data['summary'],
                icon=data['icon'],
                bg_image=data['bg_image'],
                display_order=data.get('display_order', 0),
                is_active=data.get('is_active', True)
            )
            
            db_session.add(hero_feature)
            db_session.commit()
            
        return jsonify({'success': True, 'message': 'Hero feature created successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@platform_bp.route('/api/hero-features/<int:hero_feature_id>/update', methods=['POST'])
@requires_roles_api('platform_manager')
def update_hero_feature(hero_feature_id):
    """Update an existing hero feature"""
    try:
        data = request.json
        
        with get_session() as db_session:
            hero_feature = db_session.query(HeroFeature).filter_by(hero_feature_id=hero_feature_id).first()
            
            if not hero_feature:
                return jsonify({'success': False, 'error': 'Hero feature not found'}), 404
            
            hero_feature.title = data['title']
            hero_feature.description = data['description']
            hero_feature.summary = data['summary']
            hero_feature.icon = data['icon']
            hero_feature.bg_image = data['bg_image']
            hero_feature.display_order = data.get('display_order', 0)
            hero_feature.is_active = data.get('is_active', True)
            
            db_session.commit()
            
        return jsonify({'success': True, 'message': 'Hero feature updated successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@platform_bp.route('/api/hero-features/<int:hero_feature_id>/toggle-status', methods=['POST'])
@requires_roles_api('platform_manager')
def toggle_hero_feature_status(hero_feature_id):
    """Toggle hero feature active status"""
    try:
        data = request.json
        
        with get_session() as db_session:
            hero_feature = db_session.query(HeroFeature).filter_by(hero_feature_id=hero_feature_id).first()
            
            if not hero_feature:
                return jsonify({'success': False, 'error': 'Hero feature not found'}), 404
            
            hero_feature.is_active = data.get('is_active', not hero_feature.is_active)
            db_session.commit()
            
        return jsonify({'success': True, 'message': 'Hero feature status updated successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@platform_bp.route('/api/hero-features/<int:hero_feature_id>/delete', methods=['POST'])
@requires_roles_api('platform_manager')
def delete_hero_feature(hero_feature_id):
    """Delete a hero feature"""
    try:
        with get_session() as db_session:
            hero_feature = db_session.query(HeroFeature).filter_by(hero_feature_id=hero_feature_id).first()
            
            if not hero_feature:
                return jsonify({'success': False, 'error': 'Hero feature not found'}), 404
            
            db_session.delete(hero_feature)
            db_session.commit()
            
        return jsonify({'success': True, 'message': 'Hero feature deleted successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ====================
# STATS API
# ====================

@platform_bp.route('/api/stats/create', methods=['POST'])
@requires_roles_api('platform_manager')
def create_stat():
    """Create a new stat"""
    try:
        data = request.json
        
        with get_session() as db_session:
            stat = Stat(
                value=data['value'],
                label=data['label'],
                display_order=data.get('display_order', 0),
                is_active=data.get('is_active', True)
            )
            
            db_session.add(stat)
            db_session.commit()
            
        return jsonify({'success': True, 'message': 'Stat created successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@platform_bp.route('/api/stats/<int:stat_id>/update', methods=['POST'])
@requires_roles_api('platform_manager')
def update_stat(stat_id):
    """Update an existing stat"""
    try:
        data = request.json
        
        with get_session() as db_session:
            stat = db_session.query(Stat).filter_by(stat_id=stat_id).first()
            
            if not stat:
                return jsonify({'success': False, 'error': 'Stat not found'}), 404
            
            stat.value = data['value']
            stat.label = data['label']
            stat.display_order = data.get('display_order', 0)
            stat.is_active = data.get('is_active', True)
            
            db_session.commit()
            
        return jsonify({'success': True, 'message': 'Stat updated successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@platform_bp.route('/api/stats/<int:stat_id>/toggle-status', methods=['POST'])
@requires_roles_api('platform_manager')
def toggle_stat_status(stat_id):
    """Toggle stat active status"""
    try:
        data = request.json
        
        with get_session() as db_session:
            stat = db_session.query(Stat).filter_by(stat_id=stat_id).first()
            
            if not stat:
                return jsonify({'success': False, 'error': 'Stat not found'}), 404
            
            stat.is_active = data.get('is_active', not stat.is_active)
            db_session.commit()
            
        return jsonify({'success': True, 'message': 'Stat status updated successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@platform_bp.route('/api/stats/<int:stat_id>/delete', methods=['POST'])
@requires_roles_api('platform_manager')
def delete_stat(stat_id):
    """Delete a stat"""
    try:
        with get_session() as db_session:
            stat = db_session.query(Stat).filter_by(stat_id=stat_id).first()
            
            if not stat:
                return jsonify({'success': False, 'error': 'Stat not found'}), 404
            
            db_session.delete(stat)
            db_session.commit()
            
        return jsonify({'success': True, 'message': 'Stat deleted successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ====================
# ABOUT US API
# ====================

@platform_bp.route('/api/about-intro/update', methods=['POST'])
@requires_roles_api('platform_manager')
def update_about_intro():
    """Update about intro"""
    try:
        data = request.json
        
        with get_session() as db_session:
            about_intro = db_session.query(AboutIntro).first()
            
            if not about_intro:
                # Create new if doesn't exist
                about_intro = AboutIntro(
                    title=data['title'],
                    description=data['description'],
                    is_active=data.get('is_active', True)
                )
                db_session.add(about_intro)
            else:
                about_intro.title = data['title']
                about_intro.description = data['description']
                about_intro.is_active = data.get('is_active', True)
            
            db_session.commit()
            
        return jsonify({'success': True, 'message': 'About intro updated successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@platform_bp.route('/api/about-story/update', methods=['POST'])
@requires_roles_api('platform_manager')
def update_about_story():
    """Update about story"""
    try:
        data = request.json
        
        with get_session() as db_session:
            about_story = db_session.query(AboutStory).first()
            
            if not about_story:
                # Create new if doesn't exist
                about_story = AboutStory(
                    title=data['title'],
                    content=data['content'],
                    is_active=data.get('is_active', True)
                )
                db_session.add(about_story)
            else:
                about_story.title = data['title']
                about_story.content = data['content']
                about_story.is_active = data.get('is_active', True)
            
            db_session.commit()
            
        return jsonify({'success': True, 'message': 'About story updated successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@platform_bp.route('/api/mission-vision/<string:type>/update', methods=['POST'])
@requires_roles_api('platform_manager')
def update_mission_vision(type):
    """Update mission or vision"""
    try:
        data = request.json
        
        with get_session() as db_session:
            item = db_session.query(AboutMissionVision).filter_by(type=type).first()
            
            if not item:
                # Create new if doesn't exist
                item = AboutMissionVision(
                    type=type,
                    title=data['title'],
                    content=data['content'],
                    is_active=data.get('is_active', True)
                )
                db_session.add(item)
            else:
                item.title = data['title']
                item.content = data['content']
                item.is_active = data.get('is_active', True)
            
            db_session.commit()
            
        return jsonify({'success': True, 'message': f'{type.capitalize()} updated successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@platform_bp.route('/api/team-members/create', methods=['POST'])
@requires_roles_api('platform_manager')
def create_team_member():
    """Create a new team member"""
    import json
    try:
        data = request.json
        
        with get_session() as db_session:
            team_member = TeamMember(
                name=data['name'],
                role=data['role'],
                description=data.get('description', ''),
                contributions=json.dumps(data.get('contributions', [])),
                skills=json.dumps(data.get('skills', [])),
                display_order=data.get('display_order', 0),
                is_active=data.get('is_active', True)
            )
            
            db_session.add(team_member)
            db_session.commit()
            
        return jsonify({'success': True, 'message': 'Team member created successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@platform_bp.route('/api/team-members/<int:team_member_id>/update', methods=['POST'])
@requires_roles_api('platform_manager')
def update_team_member(team_member_id):
    """Update an existing team member"""
    import json
    try:
        data = request.json
        
        with get_session() as db_session:
            team_member = db_session.query(TeamMember).filter_by(team_member_id=team_member_id).first()
            
            if not team_member:
                return jsonify({'success': False, 'error': 'Team member not found'}), 404
            
            team_member.name = data['name']
            team_member.role = data['role']
            team_member.description = data.get('description', '')
            team_member.contributions = json.dumps(data.get('contributions', []))
            team_member.skills = json.dumps(data.get('skills', []))
            team_member.display_order = data.get('display_order', 0)
            team_member.is_active = data.get('is_active', True)
            
            db_session.commit()
            
        return jsonify({'success': True, 'message': 'Team member updated successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@platform_bp.route('/api/team-members/<int:team_member_id>/toggle-status', methods=['POST'])
@requires_roles_api('platform_manager')
def toggle_team_member_status(team_member_id):
    """Toggle team member active status"""
    try:
        data = request.json
        
        with get_session() as db_session:
            team_member = db_session.query(TeamMember).filter_by(team_member_id=team_member_id).first()
            
            if not team_member:
                return jsonify({'success': False, 'error': 'Team member not found'}), 404
            
            team_member.is_active = data.get('is_active', not team_member.is_active)
            db_session.commit()
            
        return jsonify({'success': True, 'message': 'Team member status updated successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@platform_bp.route('/api/team-members/<int:team_member_id>/delete', methods=['POST'])
@requires_roles_api('platform_manager')
def delete_team_member(team_member_id):
    """Delete a team member"""
    try:
        with get_session() as db_session:
            team_member = db_session.query(TeamMember).filter_by(team_member_id=team_member_id).first()
            
            if not team_member:
                return jsonify({'success': False, 'error': 'Team member not found'}), 404
            
            db_session.delete(team_member)
            db_session.commit()
            
        return jsonify({'success': True, 'message': 'Team member deleted successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@platform_bp.route('/api/values/create', methods=['POST'])
@requires_roles_api('platform_manager')
def create_value():
    """Create a new value"""
    try:
        data = request.json
        
        with get_session() as db_session:
            value = AboutValue(
                title=data['title'],
                description=data['description'],
                display_order=data.get('display_order', 0),
                is_active=data.get('is_active', True)
            )
            
            db_session.add(value)
            db_session.commit()
            
        return jsonify({'success': True, 'message': 'Value created successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@platform_bp.route('/api/values/<int:value_id>/update', methods=['POST'])
@requires_roles_api('platform_manager')
def update_value(value_id):
    """Update an existing value"""
    try:
        data = request.json
        
        with get_session() as db_session:
            value = db_session.query(AboutValue).filter_by(value_id=value_id).first()
            
            if not value:
                return jsonify({'success': False, 'error': 'Value not found'}), 404
            
            value.title = data['title']
            value.description = data['description']
            value.display_order = data.get('display_order', 0)
            value.is_active = data.get('is_active', True)
            
            db_session.commit()
            
        return jsonify({'success': True, 'message': 'Value updated successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@platform_bp.route('/api/values/<int:value_id>/toggle-status', methods=['POST'])
@requires_roles_api('platform_manager')
def toggle_value_status(value_id):
    """Toggle value active status"""
    try:
        data = request.json
        
        with get_session() as db_session:
            value = db_session.query(AboutValue).filter_by(value_id=value_id).first()
            
            if not value:
                return jsonify({'success': False, 'error': 'Value not found'}), 404
            
            value.is_active = data.get('is_active', not value.is_active)
            db_session.commit()
            
        return jsonify({'success': True, 'message': 'Value status updated successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@platform_bp.route('/api/values/<int:value_id>/delete', methods=['POST'])
@requires_roles_api('platform_manager')
def delete_value(value_id):
    """Delete a value"""
    try:
        with get_session() as db_session:
            value = db_session.query(AboutValue).filter_by(value_id=value_id).first()
            
            if not value:
                return jsonify({'success': False, 'error': 'Value not found'}), 404
            
            db_session.delete(value)
            db_session.commit()
            
        return jsonify({'success': True, 'message': 'Value deleted successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
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
    
@platform_bp.route('/api/institutions/<int:institution_id>/delete', methods=['POST'])
@requires_roles_api('platform_manager')
def delete_institution_api(institution_id):
    """API endpoint to delete an institution completely."""
    
    # Get confirmation from request JSON (optional but recommended)
    data = request.json or {}
    confirm = data.get('confirm', False)
    
    # Get reviewer ID from session (current platform manager)
    reviewer_id = session.get('user_id')
    
    # Optional: Add a confirmation requirement for safety
    if not confirm:
        return jsonify({
            'success': False,
            'error': 'Deletion requires explicit confirmation. Set "confirm": true in request body.',
            'requires_confirmation': True,
            'institution_id': institution_id
        }), 400
    
    # Call PlatformControl method
    result = PlatformControl.delete_institution_completely(
        institution_id=institution_id,
        reviewer_id=reviewer_id
    )
    
    if result['success']:
        return jsonify(result), 200
    else:
        # Return appropriate status code based on error
        status_code = 404 if 'not found' in result.get('error', '').lower() else 400
        return jsonify(result), status_code
    
@platform_bp.route('/api/users/create-admin', methods=['POST'])
@requires_roles_api('platform_manager')
def create_admin_user():
    """Create a new admin account"""
    data = request.json
    
    result = PlatformControl.create_admin_user(data)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400

@platform_bp.route('/api/users/<int:user_id>', methods=['GET'])
@requires_roles_api('platform_manager')
def get_user_details(user_id):
    """Get user details by ID"""
    result = PlatformControl.get_user_details(user_id)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 404

@platform_bp.route('/api/users/<int:user_id>/activity', methods=['GET'])
@requires_roles_api('platform_manager')
def get_user_activity(user_id):
    """Get user activity log"""
    limit = request.args.get('limit', 10, type=int)
    
    result = PlatformControl.get_user_activity_log(user_id, limit)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 404

@platform_bp.route('/api/users/<int:user_id>/update', methods=['POST'])
@requires_roles_api('platform_manager')
def update_user(user_id):
    """Update user information"""
    data = request.json
    
    result = PlatformControl.update_user_profile(user_id, data)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400

@platform_bp.route('/api/users/<int:user_id>/toggle-status', methods=['POST'])
@requires_roles_api('platform_manager')
def toggle_user_status(user_id):
    """Activate or suspend a user account"""
    data = request.json
    action = data.get('action')  # 'activate' or 'suspend'
    
    result = PlatformControl.toggle_user_status(user_id, action)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400

@platform_bp.route('/api/users/search', methods=['GET'])
@requires_roles_api('platform_manager')
def search_users():
    """Search users by name, email, or role"""
    search_term = request.args.get('q', '').strip()
    role = request.args.get('role', '')
    status = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    result = PlatformControl.search_users(
        search_term=search_term,
        role=role,
        status=status,
        page=page,
        per_page=per_page
    )
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400

@platform_bp.route('/api/users/recent-activity', methods=['GET'])
@requires_roles_api('platform_manager')
def get_recent_user_activity():
    """Get recent user activity"""
    institution_id = request.args.get('institution_id', type=int)
    limit = request.args.get('limit', 10, type=int)
    
    result = PlatformControl.get_recent_user_activity(institution_id, limit)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400

@platform_bp.route('/api/users/count-by-role', methods=['GET'])
@requires_roles_api('platform_manager')
def get_user_count_by_role():
    """Get user count by role"""
    role = request.args.get('role')
    institution_id = request.args.get('institution_id', type=int)
    
    result = PlatformControl.get_user_count_by_role(role, institution_id)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400

@platform_bp.route('/api/users/institutions', methods=['GET'])
@requires_roles_api('platform_manager')
def get_user_institutions():
    """Get all institutions for dropdown"""
    result = PlatformControl.get_user_institutions()
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400

# ====================
# SUBSCRIPTION PLANS API
# ====================

@platform_bp.route('/api/subscription-plans/create', methods=['POST'])
@requires_roles_api('platform_manager')
def create_subscription_plan():
    """Create a new subscription plan"""
    import json as json_lib
    try:
        data = request.json
        
        with get_session() as db_session:
            # Create new subscription plan
            new_plan = SubscriptionPlan(
                name=data['name'],
                description=data.get('description', ''),
                price_per_cycle=float(data['price_per_cycle']),
                billing_cycle=data['billing_cycle'],
                max_users=int(data['max_users']),
                features=json_lib.dumps(data.get('features', {})),
                is_active=data.get('is_active', True)
            )
            
            db_session.add(new_plan)
            db_session.commit()
            
            plan_dict = new_plan.as_dict()
            plan_dict['features'] = json_lib.loads(new_plan.features) if new_plan.features else {}
            
            return jsonify({'success': True, 'plan': plan_dict}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@platform_bp.route('/api/subscription-plans/<int:plan_id>/update', methods=['POST'])
@requires_roles_api('platform_manager')
def update_subscription_plan(plan_id):
    """Update a subscription plan"""
    import json as json_lib
    try:
        data = request.json
        
        with get_session() as db_session:
            plan = db_session.query(SubscriptionPlan).filter_by(plan_id=plan_id).first()
            
            if not plan:
                return jsonify({'success': False, 'error': 'Subscription plan not found'}), 404
            
            # Update fields
            plan.name = data.get('name', plan.name)
            plan.description = data.get('description', plan.description)
            plan.price_per_cycle = float(data.get('price_per_cycle', plan.price_per_cycle))
            plan.billing_cycle = data.get('billing_cycle', plan.billing_cycle)
            plan.max_users = int(data.get('max_users', plan.max_users))
            
            if 'features' in data:
                plan.features = json_lib.dumps(data['features'])
            
            if 'is_active' in data:
                plan.is_active = data['is_active']
            
            db_session.commit()
            
            plan_dict = plan.as_dict()
            plan_dict['features'] = json_lib.loads(plan.features) if plan.features else {}
            
            return jsonify({'success': True, 'plan': plan_dict}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@platform_bp.route('/api/subscription-plans/<int:plan_id>/toggle-status', methods=['POST'])
@requires_roles_api('platform_manager')
def toggle_subscription_plan_status(plan_id):
    """Toggle the active status of a subscription plan"""
    try:
        with get_session() as db_session:
            plan = db_session.query(SubscriptionPlan).filter_by(plan_id=plan_id).first()
            
            if not plan:
                return jsonify({'success': False, 'error': 'Subscription plan not found'}), 404
            
            plan.is_active = not plan.is_active
            db_session.commit()
            
            return jsonify({'success': True, 'is_active': plan.is_active}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@platform_bp.route('/api/subscription-plans/<int:plan_id>/delete', methods=['POST'])
@requires_roles_api('platform_manager')
def delete_subscription_plan(plan_id):
    """Delete a subscription plan"""
    try:
        with get_session() as db_session:
            plan = db_session.query(SubscriptionPlan).filter_by(plan_id=plan_id).first()
            
            if not plan:
                return jsonify({'success': False, 'error': 'Subscription plan not found'}), 404
            
            # Check if any subscriptions are using this plan
            from database.models import Subscription
            active_subscriptions = db_session.query(Subscription).filter_by(plan_id=plan_id, is_active=True).count()
            
            if active_subscriptions > 0:
                return jsonify({
                    'success': False, 
                    'error': f'Cannot delete plan with {active_subscriptions} active subscriptions'
                }), 400
            
            db_session.delete(plan)
            db_session.commit()
            
            return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


# ====================
# HOMEPAGE FEATURE CARDS API
# ====================

@platform_bp.route('/api/feature-cards/create', methods=['POST'])
@requires_roles_api('platform_manager')
def create_feature_card():
    """Create a new homepage feature card"""
    try:
        data = request.json
        
        with get_session() as db_session:
            # Create new feature card
            feature_card = HomepageFeatureCard(
                title=data['title'],
                description=data['description'],
                icon=data['icon'],
                bg_image=data['bg_image'],
                link_url=data.get('link_url'),
                link_text=data.get('link_text'),
                display_order=data.get('display_order', 0),
                is_active=data.get('is_active', True)
            )
            
            db_session.add(feature_card)
            db_session.commit()
            
            return jsonify({'success': True, 'feature_card': feature_card.as_dict()}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@platform_bp.route('/api/feature-cards/<int:feature_card_id>/update', methods=['POST'])
@requires_roles_api('platform_manager')
def update_feature_card(feature_card_id):
    """Update an existing homepage feature card"""
    try:
        data = request.json
        
        with get_session() as db_session:
            feature_card = db_session.query(HomepageFeatureCard).filter_by(feature_card_id=feature_card_id).first()
            
            if not feature_card:
                return jsonify({'success': False, 'error': 'Feature card not found'}), 404
            
            # Update fields
            feature_card.title = data['title']
            feature_card.description = data['description']
            feature_card.icon = data['icon']
            feature_card.bg_image = data['bg_image']
            feature_card.link_url = data.get('link_url')
            feature_card.link_text = data.get('link_text')
            feature_card.display_order = data.get('display_order', 0)
            
            db_session.commit()
            
            return jsonify({'success': True, 'feature_card': feature_card.as_dict()}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@platform_bp.route('/api/feature-cards/<int:feature_card_id>/toggle-status', methods=['POST'])
@requires_roles_api('platform_manager')
def toggle_feature_card_status(feature_card_id):
    """Toggle active status of a homepage feature card"""
    try:
        with get_session() as db_session:
            feature_card = db_session.query(HomepageFeatureCard).filter_by(feature_card_id=feature_card_id).first()
            
            if not feature_card:
                return jsonify({'success': False, 'error': 'Feature card not found'}), 404
            
            feature_card.is_active = not feature_card.is_active
            db_session.commit()
            
            return jsonify({'success': True, 'feature_card': feature_card.as_dict()}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@platform_bp.route('/api/feature-cards/<int:feature_card_id>/delete', methods=['POST'])
@requires_roles_api('platform_manager')
def delete_feature_card(feature_card_id):
    """Delete a homepage feature card"""
    try:
        with get_session() as db_session:
            feature_card = db_session.query(HomepageFeatureCard).filter_by(feature_card_id=feature_card_id).first()
            
            if not feature_card:
                return jsonify({'success': False, 'error': 'Feature card not found'}), 404
            
            db_session.delete(feature_card)
            db_session.commit()
            
            return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@platform_bp.route('/api/debug-session', methods=['GET'])
def debug_session():
    return jsonify({
        'session': dict(session),
        'user_role': session.get('role'),
        'user_type': session.get('user_type'),
        'user_id': session.get('user_id')
    })