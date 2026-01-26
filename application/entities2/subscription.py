from typing import List, Optional, Dict, Any
from datetime import date, timedelta, datetime
from .base_entity import BaseEntity
from database.models import Subscription, Institution, SubscriptionPlan, User
from application.entities2.user import UserModel
from sqlalchemy import or_, and_


class SubscriptionModel(BaseEntity[Subscription]):
    """Entity for subscriptions with handy helpers for querying and state changes.

    Methods include read helpers and safe write helpers to set a subscription active/inactive.
    """

    def __init__(self, session):
        super().__init__(session, Subscription)

    def get_by_subscription_id(self, subscription_id: int) -> Optional[Subscription]:
        """Return a subscription by its PK or None."""
        return self.get_by_id(subscription_id)

    def get_by_stripe_id(self, stripe_id: str) -> Optional[Subscription]:
        """Return a subscription matching an external Stripe ID."""
        return self.get_one(stripe_subscription_id=stripe_id)

    def get_by_institution(self, institution_id: int) -> List[Subscription]:
        """Return all subscriptions for an institution."""
        return self.get_all(institution_id=institution_id) or []

    def get_active(self, institution_id: Optional[int] = None) -> List[Subscription]:
        """Return active subscriptions; filter by institution_id when provided."""
        filters = {'is_active': True}
        if institution_id is not None:
            filters['institution_id'] = institution_id
        return self.get_all(**filters) or []

    def activate(self, subscription_id: int) -> Optional[Subscription]:
        """Mark a subscription active and return the updated model (or None if not found)."""
        return self.update(subscription_id, is_active=True)

    def deactivate(self, subscription_id: int) -> Optional[Subscription]:
        """Mark a subscription inactive and return the updated model (or None if not found)."""
        return self.update(subscription_id, is_active=False)

    def get_expiring_soon(self, days: int = 30) -> List[Subscription]:
        """Return subscriptions whose end_date is within the next `days` days."""
        cutoff = date.today() + timedelta(days=days)
        q = self.session.query(self.model).filter(self.model.end_date != None).filter(self.model.end_date <= cutoff)
        return q.all()

    def get_paginated(self, page: int = 1, per_page: int = 10, **filters) -> Dict[str, Any]:
        """Paginated query for subscriptions using BaseEntity helper.

        Filters are passed through to BaseEntity.get_paginated.
        """
        return super().get_paginated(page, per_page, **filters)

    def count_by_status(self, status: str = 'active') -> int:
        """Count subscriptions by status.
        
        Args:
            status: 'active', 'suspended', 'pending', 'expired', or 'all'
        
        Returns:
            Number of subscriptions with the given status
            
        Note: 
        - 'active': is_active=True AND (end_date is null OR end_date in future)
        - 'suspended': is_active=False AND end_date is not null AND end_date in future
        - 'pending': is_active=False AND end_date is null
        - 'expired': end_date is in past (regardless of is_active)
        """
        now = datetime.now()
        
        if status == 'all':
            return self.session.query(Subscription).count()
        elif status == 'active':
            return (
                self.session.query(Subscription)
                .filter(
                    Subscription.is_active == True,
                    or_(
                        Subscription.end_date.is_(None),
                        Subscription.end_date >= now
                    )
                )
                .count()
            )
        elif status == 'suspended':
            # Suspended: inactive, has an end date in future
            return (
                self.session.query(Subscription)
                .filter(
                    Subscription.is_active == False,
                    Subscription.end_date.isnot(None),
                    Subscription.end_date >= now
                )
                .count()
            )
        elif status == 'pending':
            # Pending: inactive, no end date set yet
            return (
                self.session.query(Subscription)
                .filter(
                    Subscription.is_active == False,
                    Subscription.end_date.is_(None)
                )
                .count()
            )
        elif status == 'expired':
            # Expired: end date in past
            return (
                self.session.query(Subscription)
                .filter(
                    Subscription.end_date.isnot(None),
                    Subscription.end_date < now
                )
                .count()
            )
        else:
            return 0  # Invalid status

    def create_subscription_with_user_check(
        self, 
        user_id: Optional[int] = None, 
        **subscription_data
    ) -> Optional[Subscription]:
        """Create a new subscription, checking user status to determine initial status.
        
        If user_id is provided and the user is inactive, the subscription will be 
        created as 'pending' (is_active=False, end_date=None).
        Otherwise, it will be created as 'suspended' (is_active=False, end_date set).
        """ 
        # Check user status if user_id is provided
        if user_id is not None:
            user_model = UserModel(self.session)
            user = user_model.get_by_id(user_id)
            
            if user and not user.is_active:
                # User is inactive, create subscription as pending
                subscription_data['is_active'] = False
                subscription_data['end_date'] = None
            else:
                # User is active or user not found, create as suspended
                subscription_data['is_active'] = False
                # Set end_date to something in future for suspended status
                if 'end_date' not in subscription_data:
                    subscription_data['end_date'] = datetime.now() + timedelta(days=365)
        else:
            # No user_id provided, default to suspended
            subscription_data['is_active'] = False
            if 'end_date' not in subscription_data:
                subscription_data['end_date'] = datetime.now() + timedelta(days=365)
        
        # Create the subscription
        return self.create(**subscription_data)

    def determine_subscription_status(self, subscription_id: int) -> str:
        """Determine the current status of a subscription based on its fields.
        
        Returns: 'active', 'suspended', 'pending', or 'expired'
        """
        subscription = self.get_by_id(subscription_id)
        if not subscription:
            return 'unknown'
        
        now = datetime.now()
        
        if subscription.is_active and (subscription.end_date is None or subscription.end_date >= now):
            return 'active'
        elif not subscription.is_active:
            return 'pending'
        elif not subscription.is_active and subscription.end_date and subscription.end_date >= now:
            return 'suspended'
        elif subscription.end_date and subscription.end_date < now:
            return 'expired'
        else:
            return 'unknown'

    def update_subscription_based_on_user_status(self, subscription_id: int) -> bool:
        """Update subscription status based on associated user's status.
        
        This checks if the subscription's associated user (if any) is active or not,
        and updates the subscription status accordingly.
        
        Returns True if updated, False otherwise.
        """
        subscription = self.get_by_id(subscription_id)
        if not subscription:
            return False
        
        # Method 1: If users have subscription_id field
        users = self.session.query(User).filter(
            User.subscription_id == subscription_id
        ).all()
        
        
        if not users:
            return False
        
        # Check if any associated user is active
        any_user_active = any(user.is_active for user in users)
        
        current_status = self.determine_subscription_status(subscription_id)
        
        if not any_user_active and current_status == 'suspended':
            # All associated users are inactive, change from suspended to pending
            subscription.is_active = False
            subscription.end_date = None
            self.session.commit()
            return True
        elif any_user_active and current_status == 'pending':
            # At least one user is active, change from pending to suspended
            subscription.is_active = False
            subscription.end_date = datetime.now() + timedelta(days=365)
            self.session.commit()
            return True
        
        return False

    def get_pending_subscriptions(self) -> List[Dict[str, Any]]:
        """Get all pending subscription requests with institution details."""
        pending_subs = (
            self.session.query(Subscription)
            .filter(
                Subscription.is_active == False,
                Subscription.end_date.is_(None)
            )
            .order_by(Subscription.created_at.desc())
            .all()
        )
        
        result = []
        for sub in pending_subs:
            # Get institution details
            institution = self.session.query(Institution).filter(
                Institution.subscription_id == sub.subscription_id
            ).first()
            
            # Get plan details
            plan = None
            if sub.plan_id:
                plan = self.session.query(SubscriptionPlan).get(sub.plan_id)
            
            # Get avatar initials
            if institution:
                name_parts = institution.name.split()
                if len(name_parts) >= 2:
                    initials = name_parts[0][0] + name_parts[-1][0]
                else:
                    initials = institution.name[:2].upper()
            else:
                initials = '??'
            
            result.append({
                'subscription_id': sub.subscription_id,
                'institution_id': institution.institution_id if institution else None,
                'institution_name': institution.name if institution else 'Unknown',
                'location': institution.address if institution else '',
                'contact_person': institution.poc_name if institution else '',
                'contact_email': institution.poc_email if institution else '',
                'contact_phone': institution.poc_phone if institution else '',
                'plan': plan.name if plan else 'none',
                'plan_id': sub.plan_id,
                'status': 'pending',
                'request_date': sub.created_at,
                'created_at': sub.created_at,
                'initials': initials,
                'subscription_start_date': sub.start_date,
                'subscription_end_date': sub.end_date
            })
        
        return result

    def update_subscription_status(
        self,
        subscription_id: int,
        new_status: str,
        reviewer_id: Optional[int] = None
    ) -> bool:
        """Update subscription status.
        
        Returns True if successful, False otherwise.
        """
        subscription = self.get_by_id(subscription_id)
        if not subscription:
            return False
        
        if new_status == 'active':
            subscription.is_active = True
            # Set end date to 1 year from now if not set
            if not subscription.end_date:
                subscription.end_date = datetime.now() + timedelta(days=365)
        elif new_status == 'suspended':
            subscription.is_active = False
            # Ensure end date is set (for suspended status)
            if not subscription.end_date:
                subscription.end_date = datetime.now() + timedelta(days=365)
        elif new_status == 'expired':
            subscription.is_active = False
            # Optionally set end date to past if not set
            if not subscription.end_date:
                subscription.end_date = datetime.now() - timedelta(days=1)
        elif new_status == 'pending':
            subscription.is_active = False
            subscription.end_date = None
        
        try:
            self.session.commit()
            return True
        except Exception:
            self.session.rollback()
            return False

    def get_subscription_with_details(self, subscription_id: int) -> Optional[Dict[str, Any]]:
        """Get subscription with institution and plan details."""
        subscription = self.get_by_id(subscription_id)
        if not subscription:
            return None
        
        # Get institution
        institution = self.session.query(Institution).filter(
            Institution.subscription_id == subscription_id
        ).first()
        
        # Get plan
        plan = None
        if subscription.plan_id:
            plan = self.session.query(SubscriptionPlan).get(subscription.plan_id)
        
        # Determine current status
        current_status = self.determine_subscription_status(subscription_id)
        
        return {
            'subscription': subscription.as_dict(),
            'institution': institution.as_dict() if institution else None,
            'plan': plan.as_dict() if plan else None,
            'current_status': current_status
        }

    def get_recent_subscriptions(self, since_date: datetime, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent subscriptions created after a specific date."""
        subscriptions = (
            self.session.query(Subscription, Institution)
            .join(Institution, Subscription.subscription_id == Institution.subscription_id)
            .filter(Subscription.created_at >= since_date)
            .order_by(Subscription.created_at.desc())
            .limit(limit)
            .all()
        )
        
        result = []
        for subscription, institution in subscriptions:
            # Determine status for each subscription
            status = self.determine_subscription_status(subscription.subscription_id)
            
            result.append({
                'subscription_id': subscription.subscription_id,
                'institution_name': institution.name if institution else 'Unknown',
                'institution_id': institution.institution_id if institution else None,
                'plan_id': subscription.plan_id,
                'start_date': subscription.start_date,
                'end_date': subscription.end_date,
                'is_active': subscription.is_active,
                'created_at': subscription.created_at,
                'status': status
            })
        
        return result
    
    def search_with_filters(
        self,
        search_term: str = '',
        status: str = '',
        plan: str = '',
        include_pending: bool = False
    ) -> List[Dict[str, Any]]:
        """Search subscriptions with filters and return joined data with institutions.
        
        Args:
            search_term: Search in institution name, contact person, contact email
            status: Filter by status ('active', 'suspended', 'pending', 'expired')
            plan: Filter by plan name ('starter', 'pro', 'enterprise', 'custom')
            include_pending: Whether to include pending subscriptions (False by default)
            
        Returns:
            List of dictionaries with subscription and institution data
        """
        # Start with base query joining Subscription with Institution
        query = (
            self.session.query(Subscription, Institution, SubscriptionPlan)
            .join(Institution, Subscription.subscription_id == Institution.subscription_id)
            .outerjoin(SubscriptionPlan, Subscription.plan_id == SubscriptionPlan.plan_id)
        )
        
        # Apply search filter
        if search_term:
            search_pattern = f'%{search_term}%'
            query = query.filter(
                or_(
                    Institution.name.ilike(search_pattern),
                    Institution.poc_name.ilike(search_pattern),
                    Institution.poc_email.ilike(search_pattern),
                    Institution.address.ilike(search_pattern)
                )
            )
        
        # Apply status filter
        now = datetime.now()
        if status:
            if status == 'active':
                query = query.filter(
                    Subscription.is_active == True,
                    or_(
                        Subscription.end_date.is_(None),
                        Subscription.end_date >= now
                    )
                )
            elif status == 'suspended':
                query = query.filter(
                    Subscription.is_active == False,
                    Subscription.end_date.isnot(None),
                    Subscription.end_date >= now
                )
            elif status == 'pending':
                query = query.filter(
                    Subscription.is_active == False,
                    Subscription.end_date.is_(None)
                )
            elif status == 'expired':
                query = query.filter(
                    Subscription.end_date.isnot(None),
                    Subscription.end_date < now
                )
        elif not include_pending:
            # Exclude pending by default if no specific status filter
            query = query.filter(
                or_(
                    Subscription.end_date.isnot(None),  # Has end date (suspended, active, expired)
                    Subscription.is_active == True  # Or is active with no end date
                )
            )
        
        # Apply plan filter
        if plan:
            if plan == 'none':
                query = query.filter(Subscription.plan_id.is_(None))
            else:
                query = query.filter(SubscriptionPlan.name.ilike(f'%{plan}%'))
        
        # Order by latest first
        query = query.order_by(Subscription.created_at.desc())
        
        # Execute query
        results = query.all()
        
        # Format results
        formatted_results = []
        for subscription, institution, plan_obj in results:
            # Determine current status
            if subscription.is_active and (subscription.end_date is None or subscription.end_date >= now):
                current_status = 'active'
            elif not subscription.is_active and subscription.end_date is None:
                current_status = 'pending'
            elif not subscription.is_active and subscription.end_date and subscription.end_date >= now:
                current_status = 'suspended'
            elif subscription.end_date and subscription.end_date < now:
                current_status = 'expired'
            else:
                current_status = 'unknown'
            
            # Get avatar initials
            if institution:
                name_parts = institution.name.split()
                if len(name_parts) >= 2:
                    initials = name_parts[0][0] + name_parts[-1][0]
                else:
                    initials = institution.name[:2].upper()
            else:
                initials = '??'
            
            formatted_results.append({
                'subscription_id': subscription.subscription_id,
                'institution_id': institution.institution_id if institution else None,
                'name': institution.name if institution else 'Unknown',
                'institution_name': institution.name if institution else 'Unknown',
                'location': institution.address if institution else '',
                'address': institution.address if institution else '',
                'poc_name': institution.poc_name if institution else '',
                'poc_email': institution.poc_email if institution else '',
                'poc_phone': institution.poc_phone if institution else '',
                'contact_person': institution.poc_name if institution else '',
                'contact_email': institution.poc_email if institution else '',
                'contact_phone': institution.poc_phone if institution else '',
                'plan_id': subscription.plan_id,
                'plan_name': plan_obj.name if plan_obj else 'none',
                'plan': plan_obj.name.lower() if plan_obj else 'none',
                'start_date': subscription.start_date,
                'end_date': subscription.end_date,
                'is_active': subscription.is_active,
                'status': current_status,
                'created_at': subscription.created_at,
                'initials': initials,
                'subscription_start_date': subscription.start_date.strftime('%b %d, %Y') if subscription.start_date else '',
                'subscription_end_date': subscription.end_date.strftime('%b %d, %Y') if subscription.end_date else '',
                'request_date': subscription.created_at.strftime('%b %d, %Y') if subscription.created_at else ''
            })
        
        return formatted_results