# platform_control.py
from datetime import datetime, timedelta, date
from functools import wraps
from unittest import result
from flask import flash, redirect, url_for, session
from sqlalchemy.exc import IntegrityError
from typing import Dict, List, Any, Optional
from sqlalchemy import or_, func
import bcrypt
from database.base import get_session
from application.entities2.user import UserModel
from application.entities2.institution import InstitutionModel
from application.entities2.subscription import SubscriptionModel
from application.entities2.subscription_plans import SubscriptionPlanModel
from database.models import (
    User, Institution, Subscription, SubscriptionPlan,
    Course, Venue, Semester, Announcement, Notification,
    CourseUser, Class, AttendanceRecord, FacialData,
    Testimonial, PlatformIssue, ReportSchedule
)

class PlatformControl:
    """Control class for platform manager business logic"""
    
    def get_subscription_statistics() -> Dict[str, Any]:
        """Get subscription statistics for platform manager dashboard."""
        try:
            with get_session() as db_session:
                institution_model = InstitutionModel(db_session)
                subscription_model = SubscriptionModel(db_session)
            
                # Get counts using the new count_by_status method
                total_institutions = institution_model.count_by_subscription_status('all')
                active_subscriptions = subscription_model.count_by_status('active')
                suspended_subscriptions = subscription_model.count_by_status('suspended')
                pending_requests = subscription_model.count_by_status('pending')
                expired_subscriptions = subscription_model.count_by_status('expired')
            
                # Calculate growth statistics (simplified - would query historical data in real app)
                # This could be moved to a separate method that queries historical data
                growth_data = {
                    'total_growth': 3,  # +3 this quarter
                    'active_growth': '+5%',  # +5% growth
                    'suspended_growth': '-1',  # -1 this month
                }
            
                return {
                    'success': True,
                    'statistics': {
                        'total_institutions': total_institutions,
                        'active_institutions': active_subscriptions,
                        'suspended_subscriptions': suspended_subscriptions,
                        'pending_requests': pending_requests,
                        'expired_subscriptions': expired_subscriptions,
                        'growth': growth_data
                    }
                }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error fetching statistics: {str(e)}'
            }
    
    def get_institutions_with_filters(
        search: str = '',
        status: str = '',
        plan: str = '',
        page: int = 1,
        per_page: int = 5
    ) -> Dict[str, Any]:
        """Get institutions with optional search and filters."""
        try:
            with get_session() as db_session:
                institution_model = InstitutionModel(db_session)
                
                # Get institutions with filters
                institutions = institution_model.search_with_filters(
                    search_term=search,
                    status=status,
                    plan=plan
                )
                
                # Apply pagination
                total_institutions = len(institutions)
                total_pages = (total_institutions + per_page - 1) // per_page if total_institutions > 0 else 1
                start_idx = (page - 1) * per_page
                end_idx = min(start_idx + per_page, total_institutions)
                paginated_institutions = institutions[start_idx:end_idx]
                
                return {
                    'success': True,
                    'institutions': paginated_institutions,
                    'pagination': {
                        'current_page': page,
                        'total_pages': total_pages,
                        'total_items': total_institutions,
                        'per_page': per_page,
                        'has_prev': page > 1,
                        'has_next': page < total_pages,
                        'start_idx': start_idx + 1 if total_institutions > 0 else 0,
                        'end_idx': end_idx,
                    }
                }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error fetching institutions: {str(e)}'
            }
    
    def get_subscription_requests(limit: int = 5) -> Dict[str, Any]:
        """Get pending subscription requests."""
        try:
            with get_session() as db_session:
                subscription_model = SubscriptionModel(db_session)
            
                # Get pending subscriptions - this method returns a list of dicts
                pending_subscriptions = subscription_model.get_pending_subscriptions()
            
                # Apply limit
                limited_requests = pending_subscriptions[:limit] if limit else pending_subscriptions
            
                return {
                    'success': True,
                    'requests': limited_requests,
                    'total_requests': len(pending_subscriptions),
                    'limited_requests': len(limited_requests)
                }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error fetching subscription requests: {str(e)}'
            }
    
    def get_subscriptions_with_institutions(
        search: str = '',
        status: str = '',
        plan: str = '',
        page: int = 1,
        per_page: int = 5
    ) -> Dict[str, Any]:
        """Get subscriptions with institution details and filters."""
        try:
            with get_session() as db_session:
                subscription_model = SubscriptionModel(db_session)
                institution_model = InstitutionModel(db_session)
                
                # Get subscriptions with filters
                subscriptions = subscription_model.search_with_filters(
                    search_term=search,
                    status=status,
                    plan=plan
                )
                
                # Filter out pending subscriptions for main institutions table
                # (they'll appear in subscription requests table instead)
                active_subscriptions = [sub for sub in subscriptions if sub.get('status') != 'pending']
                
                # Apply pagination to active subscriptions only
                total_active = len(active_subscriptions)
                total_pages = (total_active + per_page - 1) // per_page if total_active > 0 else 1
                start_idx = (page - 1) * per_page
                end_idx = min(start_idx + per_page, total_active)
                paginated_subscriptions = active_subscriptions[start_idx:end_idx]
                
                return {
                    'success': True,
                    'subscriptions': paginated_subscriptions,
                    'pagination': {
                        'current_page': page,
                        'total_pages': total_pages,
                        'total_items': total_active,
                        'per_page': per_page,
                        'has_prev': page > 1,
                        'has_next': page < total_pages,
                        'start_idx': start_idx + 1 if total_active > 0 else 0,
                        'end_idx': end_idx,
                    },
                    'total_all_subscriptions': len(subscriptions)  # includes pending
                }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error fetching subscriptions: {str(e)}'
            }

    def create_institution_profile(institution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new institution profile with subscription."""
        try:
            required_fields = ['name', 'contact_name', 'contact_email']
            for field in required_fields:
                if not institution_data.get(field):
                    return {
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }
            
            with get_session() as db_session:
                institution_model = InstitutionModel(db_session)
                
                # Check if institution name already exists
                existing_institution = institution_model.get_by_name(institution_data['name'])
                if existing_institution:
                    return {
                        'success': False,
                        'error': 'An institution with this name already exists.'
                    }
                
                # Check if contact email is already in use
                existing_by_email = institution_model.get_by_email(institution_data['contact_email'])
                if existing_by_email:
                    return {
                        'success': False,
                        'error': 'This email is already associated with another institution.'
                    }
                
                # Create institution with subscription
                created_institution = institution_model.create_institution_with_details(
                    name=institution_data['name'],
                    address=institution_data.get('location', ''),
                    poc_name=institution_data.get('contact_name', ''),
                    poc_email=institution_data.get('contact_email', ''),
                    poc_phone=institution_data.get('contact_phone', ''),
                    status=institution_data.get('status', 'pending')
                )
                
                # Create admin user for the institution
                user_model = UserModel(db_session)
                subscription_model = SubscriptionModel(db_session)
                
                # Get the subscription to set admin user
                subscription = subscription_model.get_by_id(created_institution['subscription_id'])
                if subscription:
                    temp_password = "password"
                    password_hash = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    
                    # Create admin user
                    admin_user = user_model.create(
                        institution_id=created_institution['institution_id'],
                        role='admin',
                        name=institution_data.get('contact_name', ''),
                        phone_number=institution_data.get('contact_phone', ''),
                        email=institution_data.get('contact_email', ''),
                        password_hash=password_hash,
                        is_active=(institution_data.get('status', 'active') == 'active')
                    )
                    
                    # Store temporary password in result
                    created_institution['admin_temp_password'] = temp_password
                    created_institution['admin_user_id'] = admin_user.user_id
                
                db_session.commit()
                
                return {
                    'success': True,
                    'message': f'Institution "{institution_data["name"]}" created successfully',
                    'institution': created_institution
                }
                
        except IntegrityError as e:
            if 'db_session' in locals():
                db_session.rollback()
            return {
                'success': False,
                'error': 'Database integrity error. Please try again.'
            }
        except Exception as e:
            if 'db_session' in locals():
                db_session.rollback()
            return {
                'success': False,
                'error': f'Error creating institution: {str(e)}'
            }
    
    def update_subscription_status(
        subscription_id: int,
        new_status: str,
        reviewer_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Update subscription status (activate, suspend, etc.)."""
        try:
            valid_statuses = ['active', 'suspended', 'pending', 'expired']
            if new_status not in valid_statuses:
                return {
                    'success': False,
                    'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
                }

            with get_session() as db_session:
                subscription_model = SubscriptionModel(db_session)
                institution_model = InstitutionModel(db_session)
                user_model = UserModel(db_session)

                # Get subscription
                subscription = subscription_model.get_by_id(subscription_id)
                if not subscription:
                    return {
                        'success': False,
                        'error': 'Subscription not found.'
                    }
                
                # Use the entity method to update subscription status
                success = subscription_model.update_subscription_status(
                    subscription_id=subscription_id,
                    new_status=new_status,
                    reviewer_id=reviewer_id
                )
                
                if not success:
                    return {
                        'success': False,
                        'error': 'Failed to update subscription status.'
                    }
                
                # Update admin user status based on subscription
                institution = institution_model.get_by_subscription_id(subscription_id)
                if institution:
                    admin_user = user_model.get_by_email(institution.poc_email)
                    if admin_user:
                        admin_user.is_active = (new_status == 'active')
                
                db_session.commit()
                
                return {
                    'success': True,
                    'message': f'Subscription status updated to {new_status}',
                    'subscription_id': subscription_id,
                    'new_status': new_status,
                    'is_active': subscription.is_active  # Get the actual is_active value
                }
            
        except Exception as e:
            if 'db_session' in locals():
                db_session.rollback()
            return {
                'success': False,
                'error': f'Error updating subscription status: {str(e)}'
            }
    
    def process_subscription_request(
        request_id: int,
        action: str,
        reviewer_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Approve or reject a subscription request."""
        try:
            if action not in ['approve', 'reject']:
                return {
                    'success': False,
                    'error': 'Invalid action. Must be "approve" or "reject".'
                }
        
            with get_session() as db_session:
                subscription_model = SubscriptionModel(db_session)
                institution_model = InstitutionModel(db_session)
                user_model = UserModel(db_session)
            
                if action == 'approve':
                    # Use the new update_subscription_status method
                    success = subscription_model.update_subscription_status(
                        subscription_id=request_id,
                        new_status='active',
                        reviewer_id=reviewer_id
                    )
                
                    if success:
                        # Activate the institution's admin user
                        institution = institution_model.get_by_subscription_id(request_id)
                        if institution:
                            admin_user = user_model.get_by_email(institution.poc_email)
                            if admin_user:
                                admin_user.is_active = True
                                db_session.commit()
                    
                        message = 'Subscription request approved'
                    else:
                        return {
                            'success': False,
                            'error': 'Failed to update subscription status.'
                        }
                else:
                    # For reject, we should use the reject_subscription method
                    result = PlatformControl.reject_subscription(request_id, reviewer_id)
                    if result['success']:
                        message = 'Subscription request rejected and data cleaned up'
                    else:
                        return result
            
                return {
                    'success': True,
                    'message': message,
                    'subscription_id': request_id
                }
            
        except Exception as e:
            if 'db_session' in locals():
                db_session.rollback()
            return {
                'success': False,
                'error': f'Error processing subscription request: {str(e)}'
            }
    
    def get_institution_details(institution_id: int) -> Dict[str, Any]:
        """Get detailed information about an institution."""
        try:
            with get_session() as db_session:
                institution_model = InstitutionModel(db_session)
                subscription_model = SubscriptionModel(db_session)
                user_model = UserModel(db_session)
                
                # Get institution with subscription details
                institution_data = institution_model.get_with_subscription_details(institution_id)
                if not institution_data:
                    return {
                        'success': False,
                        'error': 'Institution not found.'
                    }
                
                # Get admin user information
                institution = institution_model.get_by_id(institution_id)
                admin_users = user_model.get_by_institution_and_role(
                    institution_id=institution_id,
                    role='admin'
                )
                
                # Get subscription for this institution
                # Assuming Institution has subscription_id field
                subscription_id = institution.subscription_id if hasattr(institution, 'subscription_id') else None
                subscription = subscription_model.get_by_id(subscription_id) if subscription_id else None
                
                return {
                    'success': True,
                    'institution': institution_data['institution'],
                    'subscription': institution_data['subscription'],
                    'plan': institution_data['plan'],
                    'admin_users': [user.as_sanitized_dict() for user in admin_users] if admin_users else [],
                    'is_active': subscription.is_active if subscription else False
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Error fetching institution details: {str(e)}'
            }
    
    def update_institution_profile(
        institution_id: int,
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update institution profile information."""
        try:
            with get_session() as db_session:
                institution_model = InstitutionModel(db_session)
                subscription_model = SubscriptionModel(db_session)
                
                # Check if institution exists
                institution = institution_model.get_by_id(institution_id)
                if not institution:
                    return {
                        'success': False,
                        'error': 'Institution not found.'
                    }
                
                # Map form field names to model field names for institution
                institution_updates = {}
                
                # Institution fields mapping from form to model
                field_mapping = {
                    'name': 'name',
                    'location': 'address',  # form 'location' maps to 'address' field
                    'contact_person': 'poc_name',
                    'contact_email': 'poc_email', 
                    'contact_phone': 'poc_phone'
                }
                
                for form_field, model_field in field_mapping.items():
                    if form_field in update_data and update_data[form_field]:
                        institution_updates[model_field] = update_data[form_field]
                
                # Check if updating email and it's already in use
                if 'poc_email' in institution_updates:
                    existing_by_email = institution_model.get_by_email(institution_updates['poc_email'])
                    if existing_by_email and existing_by_email.institution_id != institution_id:
                        return {
                            'success': False,
                            'error': 'This email is already associated with another institution.'
                        }
                
                # Update institution if there are changes
                if institution_updates:
                    updated_institution = institution_model.update_institution(
                        institution_id=institution_id,
                        **institution_updates
                    )
                else:
                    updated_institution = institution
                
                # Handle subscription updates
                # First, get the subscription ID from the institution
                subscription_id = institution.subscription_id if hasattr(institution, 'subscription_id') else None
                
                if subscription_id:
                    # Get the subscription
                    subscription = subscription_model.get_by_subscription_id(subscription_id)
                    
                    if subscription:
                        # Handle plan update - need to find plan by name
                        if 'plan' in update_data and update_data['plan']:
                            plan_name = update_data['plan']
                            # Find the plan by name
                            from database.models import SubscriptionPlan
                            plan = db_session.query(SubscriptionPlan).filter(
                                SubscriptionPlan.name.ilike(f'%{plan_name}%')
                            ).first()
                            
                            if plan:
                                subscription.plan_id = plan.plan_id
                            else:
                                # If plan not found, try to match common plan names
                                plan_mapping = {
                                    'starter': 'Starter',
                                    'pro': 'Professional',
                                    'enterprise': 'Enterprise',
                                    'custom': 'Custom'
                                }
                                if plan_name in plan_mapping:
                                    plan = db_session.query(SubscriptionPlan).filter(
                                        SubscriptionPlan.name == plan_mapping[plan_name]
                                    ).first()
                                    if plan:
                                        subscription.plan_id = plan.plan_id
                        
                        # Handle status update
                        if 'status' in update_data and update_data['status']:
                            new_status = update_data['status']
                            now = datetime.now()
                            
                            if new_status == 'active':
                                subscription.is_active = True
                                # Set end date to 1 year from now if not set
                                if not subscription.end_date:
                                    subscription.end_date = now + timedelta(days=365)
                            elif new_status == 'suspended':
                                subscription.is_active = False
                                # Ensure end date is set (for suspended status)
                                if not subscription.end_date:
                                    subscription.end_date = now + timedelta(days=365)
                            elif new_status == 'pending':
                                subscription.is_active = False
                                subscription.end_date = None
                            elif new_status == 'expired':
                                subscription.is_active = False
                                # Set end date to past if not set
                                if not subscription.end_date:
                                    subscription.end_date = now - timedelta(days=1)
                        
                        # Handle date updates
                        if 'start_date' in update_data and update_data['start_date']:
                            try:
                                subscription.start_date = datetime.strptime(update_data['start_date'], '%Y-%m-%d')
                            except ValueError:
                                # Try different format if needed
                                pass
                        
                        if 'end_date' in update_data and update_data['end_date']:
                            try:
                                subscription.end_date = datetime.strptime(update_data['end_date'], '%Y-%m-%d')
                            except ValueError:
                                # Try different format if needed
                                pass
                        
                        # Handle max_users (if your Subscription model has this field)
                        if 'max_users' in update_data and update_data['max_users']:
                            # Check if subscription has max_users field
                            if hasattr(subscription, 'max_users'):
                                try:
                                    subscription.max_users = int(update_data['max_users'])
                                except (ValueError, TypeError):
                                    pass
                
                # Also update admin user if email or name changed
                if 'poc_email' in institution_updates or 'poc_name' in institution_updates:
                    user_model = UserModel(db_session)
                    # Get current admin email before it changes
                    current_email = institution.poc_email
                    admin_user = user_model.get_by_email(current_email)
                    if admin_user:
                        if 'poc_email' in institution_updates:
                            admin_user.email = institution_updates['poc_email']
                        if 'poc_name' in institution_updates:
                            admin_user.name = institution_updates['poc_name']
                
                db_session.commit()
                
                # Get updated institution data
                updated_institution = institution_model.get_by_id(institution_id)
                
                return {
                    'success': True,
                    'message': 'Institution profile updated successfully',
                    'institution': updated_institution.as_dict() if updated_institution else None
                }
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in update_institution_profile: {str(e)}")
            print(f"Traceback: {error_details}")
            
            if 'db_session' in locals():
                db_session.rollback()
            return {
                'success': False,
                'error': f'Error updating institution profile: {str(e)}'
            }
    
    def get_platform_dashboard_stats() -> Dict[str, Any]:
        """Get comprehensive statistics for platform manager dashboard."""
        try:
            with get_session() as db_session:
                institution_model = InstitutionModel(db_session)
                subscription_model = SubscriptionModel(db_session)
                user_model = UserModel(db_session)
                subscription_plan_model = SubscriptionPlanModel(db_session)
                
                # Get basic counts
                total_institutions = institution_model.count_by_subscription_status('all')
                active_institutions = institution_model.count_by_subscription_status('active')
                total_users = user_model.count()
                
                # Get recent subscriptions (last 30 days)
                thirty_days_ago = datetime.now() - timedelta(days=30)
                recent_subscriptions = subscription_model.get_recent_subscriptions(thirty_days_ago)
                
                # Get plan distribution
                all_subscriptions = subscription_model.get_all()
                plan_distribution = {}
                for sub in all_subscriptions:
                    # Get plan name from plan_id
                    plan_name = 'none'
                    if sub.plan_id:
                        plan = subscription_plan_model.get_by_id(sub.plan_id)
                        plan_name = plan.name if plan else f'plan_{sub.plan_id}'
                    plan_distribution[plan_name] = plan_distribution.get(plan_name, 0) + 1
                
                # Get growth metrics (simplified)
                last_quarter = datetime.now() - timedelta(days=90)
                try:
                    new_institutions_last_quarter = institution_model.count_created_after(last_quarter)
                except AttributeError:
                    new_institutions_last_quarter = 0
                
                return {
                    'success': True,
                    'statistics': {
                        'total_institutions': total_institutions,
                        'active_institutions': active_institutions,
                        'total_users': total_users,
                        'new_institutions_quarter': new_institutions_last_quarter,
                        'recent_subscriptions_count': len(recent_subscriptions),
                        'plan_distribution': plan_distribution,
                        'subscription_status_distribution': {
                            'active': active_institutions,
                            'suspended': institution_model.count_by_subscription_status('suspended'),
                            'pending': subscription_model.count_by_status('pending'),
                            'expired': subscription_model.count_by_status('expired'),
                        }
                    }
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Error fetching dashboard statistics: {str(e)}'
            }
        
    def approve_institution_registration(subscription_id: int) -> Dict[str, Any]:
        """Activate a pending institution registration.
        
        This consolidates the functionality from AuthControl into PlatformControl.
        """
        try:
            with get_session() as db_session:
                subscription_model = SubscriptionModel(db_session)
                institution_model = InstitutionModel(db_session)
                user_model = UserModel(db_session)
            
                # Get subscription details
                subscription_data = subscription_model.get_subscription_with_details(subscription_id)
                if not subscription_data:
                    return {'success': False, 'error': 'Subscription not found.'}
                
                subscription = subscription_data['subscription']
                institution_data = subscription_data.get('institution')
                
                if not institution_data:
                    return {'success': False, 'error': 'Institution not found for this subscription.'}
                
                if subscription['is_active']:
                    return {'success': False, 'error': 'Subscription is already active.'}
            
                # Get the institution object
                institution = institution_model.get_by_id(institution_data['institution_id'])
                if not institution:
                    return {'success': False, 'error': 'Institution object not found.'}
            
                # Use the entity method to update subscription status
                success = subscription_model.update_subscription_status(
                    subscription_id=subscription_id,
                    new_status='active',
                    reviewer_id=None  # Can be added as parameter if needed
                )
            
                if not success:
                    return {
                        'success': False,
                        'error': 'Failed to update subscription status.'
                    }
            
                # Set renewal date to 1 year from now
                subscription_obj = subscription_model.get_by_id(subscription_id)
                if subscription_obj:
                    subscription_obj.renewal_date = datetime.now() + timedelta(days=365)
            
                # Activate the admin user or create if doesn't exist
                admin_user = user_model.get_by_email(institution.poc_email)
                temp_password_display = None
            
                if admin_user:
                    admin_user.is_active = True
                else:
                    # Create admin user if doesn't exist
                    import secrets
                    temp_password = secrets.token_urlsafe(12)
                    password_hash = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                    admin_user = user_model.create(
                        institution_id=institution.institution_id,
                        role='admin',
                        name=institution.poc_name,
                        phone_number=institution.poc_phone or '',
                        email=institution.poc_email,
                        password_hash=password_hash,
                        is_active=True
                    )
                
                    # Store temp password for display
                    temp_password_display = temp_password
            
                db_session.commit()
            
                result_data = {
                    'success': True,
                    'message': f'Institution registration approved for {institution.name}',
                    'institution_id': institution.institution_id,
                    'subscription_id': subscription_id,
                    'institution_name': institution.name
                }
            
                # Include temp password if user was created
                if temp_password_display:
                    result_data['admin_temp_password'] = temp_password_display
            
                return result_data
            
        except Exception as e:
            if 'db_session' in locals():
                db_session.rollback()
            return {
                'success': False,
                'error': f'Error approving institution registration: {str(e)}'
            }
        
    def reject_institution_registration(subscription_id: int) -> Dict[str, Any]:
        """Reject a pending institution registration and clean up all data.
    
        This is an alias for reject_subscription for consistency.
        """
        return PlatformControl.reject_subscription(subscription_id)

    def approve_subscription(subscription_id: int, reviewer_id: Optional[int] = None) -> Dict[str, Any]:
        """Approve a pending subscription and activate the institution.
    
        Now uses the consolidated approve_institution_registration method.
        """
        # Call the consolidated method
        result = PlatformControl.approve_institution_registration(subscription_id)
    
        # Add reviewer_id to result if needed
        if result['success'] and reviewer_id:
            result['reviewer_id'] = reviewer_id
    
        return result
        
    def reject_subscription(subscription_id: int, reviewer_id: Optional[int] = None) -> Dict[str, Any]:
        """Reject a pending subscription and clean up associated data."""
        try:
            with get_session() as db_session:
                subscription_model = SubscriptionModel(db_session)
                institution_model = InstitutionModel(db_session)
                user_model = UserModel(db_session)
            
                # Get the subscription details with institution
                subscription_data = subscription_model.get_subscription_with_details(subscription_id)
                if not subscription_data:
                    return {
                        'success': False,
                        'error': 'Subscription not found.'
                    }
            
                institution_data = subscription_data.get('institution')
                if not institution_data:
                    return {
                        'success': False,
                        'error': 'Institution not found for this subscription.'
                    }
            
                institution_name = institution_data['name']
                institution_email = institution_data['poc_email']
            
                # Get the institution object
                institution = institution_model.get_by_id(institution_data['institution_id'])
                if not institution:
                    return {
                        'success': False,
                        'error': 'Institution object not found.'
                    }
            
                # Delete the admin user if exists
                admin_user = user_model.get_by_email(institution_email)
                if admin_user:
                    db_session.delete(admin_user)
            
                # Delete the institution
                db_session.delete(institution)
            
                # Delete the subscription
                subscription = subscription_model.get_by_id(subscription_id)
                if subscription:
                    db_session.delete(subscription)
            
                db_session.commit()
            
                result = {
                    'success': True,
                    'message': f'Registration rejected for {institution_name}',
                    'rejected_institution': institution_name,
                    'rejected_email': institution_email
                }
            
                # Add reviewer_id to result if provided
                if reviewer_id:
                    result['reviewer_id'] = reviewer_id
            
                return result
            
        except Exception as e:
            if 'db_session' in locals():
                db_session.rollback()
            return {
                'success': False,
                'error': f'Error rejecting subscription: {str(e)}'
            }

    def get_pending_subscriptions() -> Dict[str, Any]:
        """Get all pending subscription requests."""
        try:
            with get_session() as db_session:
                subscription_model = SubscriptionModel(db_session)
            
                # Use the entity method that already exists
                pending_subs = subscription_model.get_pending_subscriptions()
            
                return {
                    'success': True,
                    'pending_subscriptions': pending_subs,
                    'count': len(pending_subs)
                }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error fetching pending subscriptions: {str(e)}'
            }   
        
    def get_institution_registration_status(subscription_id: int) -> Dict[str, Any]:
        """Check the status of an institution registration."""
        try:
            with get_session() as db_session:
                subscription_model = SubscriptionModel(db_session)
                institution_model = InstitutionModel(db_session)
            
                # Get subscription details
                subscription_data = subscription_model.get_subscription_with_details(subscription_id)
                if not subscription_data:
                    return {
                        'success': False,
                        'error': 'Registration not found.'
                    }
            
                subscription = subscription_data['subscription']
                institution = subscription_data.get('institution')
            
                if not institution:
                    return {
                        'success': False,
                        'error': 'Institution not found for this registration.'
                    }
            
                # Determine status
                if subscription['is_active']:
                    status = 'approved'
                    status_message = 'Registration approved and active'
                else:
                    if subscription['end_date'] is None:
                        status = 'inactive'
                        status_message = 'Registration not active'
                    else:
                        status = 'pending'
                        status_message = 'Registration pending approval'
            
                return {
                    'success': True,
                    'status': status,
                    'status_message': status_message,
                    'institution_name': institution['name'],
                    'institution_email': institution['poc_email'],
                    'subscription_active': subscription['is_active'],
                    'admin_user_active': institution.get('poc_email_active', False)  # Would need to check user model
                }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error checking registration status: {str(e)}'
            }
        
    def delete_institution_completely(
        institution_id: int,
        reviewer_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Delete an institution completely with all associated data."""
        try:
            with get_session() as db_session:
                institution_model = InstitutionModel(db_session)
                subscription_model = SubscriptionModel(db_session)
                user_model = UserModel(db_session)
                
                # Get institution details
                institution = institution_model.get_by_id(institution_id)
                if not institution:
                    return {
                        'success': False,
                        'error': f'Institution with ID {institution_id} not found.'
                    }
                
                institution_name = institution.name
                subscription_id = institution.subscription_id
                
                # Track what we're deleting
                deletion_summary = {
                    'institution_name': institution_name,
                    'subscription_id': subscription_id,
                    'deleted_users': 0,
                    'deleted_courses': 0,
                    'deleted_venues': 0,
                    'deleted_semesters': 0,
                    'deleted_facial_data': 0,
                    'deleted_attendance_records': 0,
                    'deleted_classes': 0,
                    'deleted_announcements': 0,
                    'deleted_notifications': 0,
                    'deleted_testimonials': 0,
                    'deleted_platform_issues': 0
                }
                
                # Get all users associated with this institution
                users = db_session.query(User).filter(
                    User.institution_id == institution_id
                ).all()
                
                user_ids = [user.user_id for user in users]
                deletion_summary['deleted_users'] = len(user_ids)
                
                if user_ids:
                    # Delete facial data for all users
                    facial_deleted = db_session.query(FacialData).filter(
                        FacialData.user_id.in_(user_ids)
                    ).delete(synchronize_session=False)
                    deletion_summary['deleted_facial_data'] = facial_deleted
                    
                    # Delete attendance records for all users as students
                    attendance_deleted = db_session.query(AttendanceRecord).filter(
                        AttendanceRecord.student_id.in_(user_ids)
                    ).delete(synchronize_session=False)
                    deletion_summary['deleted_attendance_records'] = attendance_deleted
                    
                    # Delete notifications for all users
                    notifications_deleted = db_session.query(Notification).filter(
                        Notification.user_id.in_(user_ids)
                    ).delete(synchronize_session=False)
                    deletion_summary['deleted_notifications'] = notifications_deleted
                    
                    # Delete testimonials by these users
                    testimonials_deleted = db_session.query(Testimonial).filter(
                        Testimonial.user_id.in_(user_ids)
                    ).delete(synchronize_session=False)
                    deletion_summary['deleted_testimonials'] = testimonials_deleted
                    
                    # Delete course enrollments for all users
                    db_session.query(CourseUser).filter(
                        CourseUser.user_id.in_(user_ids)
                    ).delete(synchronize_session=False)
                    
                    # Delete platform issues reported by these users
                    platform_issues_deleted = db_session.query(PlatformIssue).filter(
                        PlatformIssue.user_id.in_(user_ids)
                    ).delete(synchronize_session=False)
                    deletion_summary['deleted_platform_issues'] = platform_issues_deleted
                    
                    # Delete users themselves
                    db_session.query(User).filter(
                        User.institution_id == institution_id
                    ).delete(synchronize_session=False)
                
                # Delete classes where users from this institution are lecturers
                # First get all classes where lecturer is from this institution
                if user_ids:
                    classes_deleted = db_session.query(Class).filter(
                        Class.lecturer_id.in_(user_ids)
                    ).delete(synchronize_session=False)
                    deletion_summary['deleted_classes'] = classes_deleted
                
                # Delete institution-specific data
                # Delete courses
                courses_deleted = db_session.query(Course).filter(
                    Course.institution_id == institution_id
                ).delete(synchronize_session=False)
                deletion_summary['deleted_courses'] = courses_deleted
                
                # Delete venues
                venues_deleted = db_session.query(Venue).filter(
                    Venue.institution_id == institution_id
                ).delete(synchronize_session=False)
                deletion_summary['deleted_venues'] = venues_deleted
                
                # Delete semesters
                semesters_deleted = db_session.query(Semester).filter(
                    Semester.institution_id == institution_id
                ).delete(synchronize_session=False)
                deletion_summary['deleted_semesters'] = semesters_deleted
                
                # Delete announcements
                announcements_deleted = db_session.query(Announcement).filter(
                    Announcement.institution_id == institution_id
                ).delete(synchronize_session=False)
                deletion_summary['deleted_announcements'] = announcements_deleted
                
                # Delete report schedules
                db_session.query(ReportSchedule).filter(
                    ReportSchedule.institution_id == institution_id
                ).delete(synchronize_session=False)
                
                # Delete the institution
                db_session.delete(institution)
                
                # Delete the subscription (if exists)
                deleted_subscription = False
                if subscription_id:
                    subscription = subscription_model.get_by_id(subscription_id)
                    if subscription:
                        db_session.delete(subscription)
                        deleted_subscription = True
                
                # Commit all deletions
                db_session.commit()
                
                result = {
                    'success': True,
                    'message': f'Institution "{institution_name}" and all associated data deleted successfully.',
                    'institution_id': institution_id,
                    'institution_name': institution_name,
                    'subscription_id': subscription_id,
                    'subscription_deleted': deleted_subscription,
                    'deletion_summary': deletion_summary
                }
                
                # Add reviewer info if provided
                if reviewer_id:
                    result['reviewer_id'] = reviewer_id
                
                return result
                
        except Exception as e:
            if 'db_session' in locals():
                db_session.rollback()
            return {
                'success': False,
                'error': f'Error deleting institution: {str(e)}'
            }
        
    def create_admin_user(user_data):
        """Create a new admin user account"""
        try:
            with get_session() as db_session:
                user_model = UserModel(db_session)
                
                # Check if email already exists
                existing_user = user_model.get_by_email(user_data.get('email'))
                if existing_user:
                    return {
                        'success': False,
                        'error': 'Email address already in use'
                    }
                
                # Hash password
                from werkzeug.security import generate_password_hash
                password_hash = generate_password_hash(user_data.get('password', 'changeme123'))
                
                # Create the admin user
                new_user = {
                    'name': user_data.get('name'),
                    'email': user_data.get('email'),
                    'phone_number': user_data.get('phone'),
                    'role': 'admin',
                    'institution_id': user_data.get('institution_id'),
                    'password_hash': password_hash,
                    'is_active': True
                }
                
                # Use the create method from BaseEntity
                created_user = user_model.create(**new_user)
                
                db_session.commit()
                
                return {
                    'success': True,
                    'message': 'Admin account created successfully',
                    'user': created_user.as_dict() if created_user else None
                }
                
        except Exception as e:
            if 'db_session' in locals():
                db_session.rollback()
            return {
                'success': False,
                'error': f'Error creating admin user: {str(e)}'
            }

    def get_user_details(user_id):
        """Get detailed information about a user"""
        try:
            with get_session() as db_session:
                user_model = UserModel(db_session)
                
                user = user_model.get_by_id(user_id)
                if not user:
                    return {
                        'success': False,
                        'error': 'User not found'
                    }
                
                # Get institution name if applicable
                institution_name = None
                if user.institution_id:
                    institution_model = InstitutionModel(db_session)
                    institution = institution_model.get_by_id(user.institution_id)
                    institution_name = institution.name if institution else None
                
                user_data = {
                    'user_id': user.user_id,
                    'name': user.name,
                    'email': user.email,
                    'phone': user.phone_number,
                    'role': user.role,
                    'institution_id': user.institution_id,
                    'institution_name': institution_name,
                    'is_active': user.is_active,
                    'created_at': user.date_joined.isoformat() if user.date_joined else None,
                }
                
                return {
                    'success': True,
                    'user': user_data
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Error fetching user details: {str(e)}'
            }

    def update_user_profile(user_id, update_data):
        """Update user profile information"""
        try:
            with get_session() as db_session:
                user_model = UserModel(db_session)
                
                # Check if user exists
                user = user_model.get_by_id(user_id)
                if not user:
                    return {
                        'success': False,
                        'error': 'User not found'
                    }
                
                # Check if email is being updated and if it's already in use
                if 'email' in update_data and update_data['email'] != user.email:
                    existing_user = user_model.get_by_email(update_data['email'])
                    if existing_user and existing_user.user_id != user_id:
                        return {
                            'success': False,
                            'error': 'Email address already in use by another user'
                        }
                
                # Prepare update data
                user_updates = {}
                allowed_fields = ['name', 'email', 'phone', 'role', 'institution_id', 'is_active']
                
                for field in allowed_fields:
                    if field in update_data:
                        if field == 'is_active':
                            # Convert string to boolean if needed
                            value = update_data[field]
                            if isinstance(value, str):
                                user_updates[field] = value.lower() == 'true'
                            else:
                                user_updates[field] = bool(value)
                        else:
                            # Map 'phone' to 'phone_number' for the model
                            if field == 'phone':
                                user_updates['phone_number'] = update_data[field]
                            else:
                                user_updates[field] = update_data[field]
                
                # Update password if provided
                if 'password' in update_data and update_data['password']:
                    # Hash the password before storing
                    from werkzeug.security import generate_password_hash
                    user_updates['password_hash'] = generate_password_hash(update_data['password'])
                
                # Update user using the existing update method
                updated_user = user_model.update(user_id, **user_updates)
                
                db_session.commit()
                
                return {
                    'success': True,
                    'message': 'User updated successfully',
                    'user': updated_user.as_dict() if updated_user else None
                }
                
        except Exception as e:
            if 'db_session' in locals():
                db_session.rollback()
            return {
                'success': False,
                'error': f'Error updating user: {str(e)}'
            }

    def toggle_user_status(user_id, action):
        """Activate or suspend a user account"""
        try:
            with get_session() as db_session:
                user_model = UserModel(db_session)
                
                user = user_model.get_by_id(user_id)
                if not user:
                    return {
                        'success': False,
                        'error': 'User not found'
                    }
                
                new_status = action == 'activate'
                
                # Use existing suspend/unsuspend methods
                if new_status:
                    success = user_model.unsuspend(user_id)
                else:
                    success = user_model.suspend(user_id)
                
                if success:
                    return {
                        'success': True,
                        'message': f'User {"activated" if new_status else "suspended"} successfully'
                    }
                else:
                    return {
                        'success': False,
                        'error': f'Failed to {"activate" if new_status else "suspend"} user'
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'error': f'Error updating user status: {str(e)}'
            }

    def search_users(search_term='', role='', status='', page=1, per_page=10):
        """Search users with filters - using existing pm_retrieve_page method"""
        try:
            with get_session() as db_session:
                user_model = UserModel(db_session)
                
                # Build filters
                filters = {}
                if role:
                    filters['role'] = role
                if status:
                    # Convert status string to boolean
                    if status == 'active':
                        filters['is_active'] = True
                    elif status == 'suspended':
                        filters['is_active'] = False
                
                # Get paginated results
                result = user_model.pm_retrieve_page(page, per_page, **filters)
                
                # If search term provided, filter results manually
                if search_term:
                    search_term_lower = search_term.lower()
                    filtered_items = []
                    for item in result['items']:
                        # Check if search term appears in name, email, or user_id
                        if (search_term_lower in item.get('name', '').lower() or
                            search_term_lower in item.get('email', '').lower() or
                            str(search_term) in str(item.get('user_id', ''))):
                            filtered_items.append(item)
                    
                    # Update result with filtered items
                    result['items'] = filtered_items
                    result['total'] = len(filtered_items)
                    result['pages'] = (len(filtered_items) + per_page - 1) // per_page
                
                return {
                    'success': True,
                    'users': result['items'],
                    'pagination': {
                        'total': result['total'],
                        'page': result['page'],
                        'per_page': result['per_page'],
                        'pages': result['pages']
                    }
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Error searching users: {str(e)}'
            }

    def get_user_count_by_role(role=None, institution_id=None):
        """Get user count by role"""
        try:
            with get_session() as db_session:
                user_model = UserModel(db_session)
                
                # Build query
                query = db_session.query(User)
                
                if role:
                    query = query.filter(User.role == role)
                if institution_id:
                    query = query.filter(User.institution_id == institution_id)
                
                count = query.count()
                
                return {
                    'success': True,
                    'count': count,
                    'role': role,
                    'institution_id': institution_id
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Error counting users: {str(e)}'
            }

    def get_user_institutions():
        """Get all institutions for user dropdown"""
        try:
            with get_session() as db_session:
                institution_model = InstitutionModel(db_session)
                
                # Get all institutions
                institutions = institution_model.get_all()
                
                institution_list = []
                for inst in institutions:
                    institution_list.append({
                        'institution_id': inst.institution_id,
                        'name': inst.name,
                        'address': inst.address,
                        'status': 'active' if inst.subscription and inst.subscription.is_active else 'inactive'
                    })
                
                return {
                    'success': True,
                    'institutions': institution_list,
                    'count': len(institution_list)
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Error fetching institutions: {str(e)}'
            }