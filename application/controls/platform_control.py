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
                    plan=institution_data.get('plan', 'starter'),
                    status=institution_data.get('status', 'active')
                )
                
                # Create admin user for the institution
                user_model = UserModel(db_session)
                subscription_model = SubscriptionModel(db_session)
                
                # Get the subscription to set admin user
                subscription = subscription_model.get_by_id(created_institution['subscription_id'])
                if subscription:
                    # Generate a temporary password
                    import secrets
                    temp_password = secrets.token_urlsafe(12)
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
                
                # Update subscription status
                subscription.status = new_status
                subscription.is_active = (new_status == 'active')
                subscription.updated_at = datetime.now()
                
                if new_status == 'active':
                    # Set renewal date if activating
                    subscription.renewal_date = datetime.now() + timedelta(days=365)
                elif new_status == 'suspended':
                    # Clear renewal date if suspending
                    subscription.renewal_date = None
                
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
                    'is_active': (new_status == 'active')  # For backward compatibility
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
                    # For reject, we could either delete or mark as rejected
                    # Since Subscription doesn't have a status field, we'll just deactivate
                    success = subscription_model.update_subscription_status(
                        subscription_id=request_id,
                        new_status='suspended',
                        reviewer_id=reviewer_id
                    )
                
                    if success:
                        message = 'Subscription request rejected'
                    else:
                        return {
                            'success': False,
                            'error': 'Failed to update subscription status.'
                        }
            
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
                
                # Get subscription statistics for this institution
                subscription = subscription_model.get_by_id(institution.subscription_id)
                
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
                
                # Check if institution exists
                institution = institution_model.get_by_id(institution_id)
                if not institution:
                    return {
                        'success': False,
                        'error': 'Institution not found.'
                    }
                
                # Check if updating email and it's already in use
                if 'poc_email' in update_data:
                    existing_by_email = institution_model.get_by_email(update_data['poc_email'])
                    if existing_by_email and existing_by_email.institution_id != institution_id:
                        return {
                            'success': False,
                            'error': 'This email is already associated with another institution.'
                        }
                
                # Update institution
                updated_institution = institution_model.update_institution(
                    institution_id=institution_id,
                    **update_data
                )
                
                # Also update admin user if email or name changed
                if 'poc_email' in update_data or 'poc_name' in update_data:
                    user_model = UserModel(db_session)
                    admin_user = user_model.get_by_email(institution.poc_email)
                    if admin_user:
                        if 'poc_email' in update_data:
                            admin_user.email = update_data['poc_email']
                        if 'poc_name' in update_data:
                            admin_user.name = update_data['poc_name']
                
                db_session.commit()
                
                return {
                    'success': True,
                    'message': 'Institution profile updated successfully',
                    'institution': updated_institution.as_dict() if updated_institution else None
                }
                
        except Exception as e:
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
                    plan_name = sub.plan or 'none'
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
            
                # Get and activate subscription
                subscription = subscription_model.get_by_id(subscription_id)
                if not subscription:
                    return {'success': False, 'error': 'Subscription not found.'}
                
                if subscription.is_active:
                    return {'success': False, 'error': 'Subscription is already active.'}
            
                # Get the institution linked to this subscription
                institution = institution_model.get_by_subscription_id(subscription_id)
                if not institution:
                    return {'success': False, 'error': 'Institution not found for this subscription.'}
            
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
                subscription.renewal_date = datetime.now() + timedelta(days=365)
            
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
                    'subscription_id': subscription.subscription_id,
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