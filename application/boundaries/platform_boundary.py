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
from database.models import User, Feature, HeroFeature, Stat, AboutIntro, AboutStory, AboutMissionVision, TeamMember, AboutValue

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
        'active_values': active_values
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

@platform_bp.route('/api/debug-session', methods=['GET'])
def debug_session():
    return jsonify({
        'session': dict(session),
        'user_role': session.get('role'),
        'user_type': session.get('user_type'),
        'user_id': session.get('user_id')
    })
