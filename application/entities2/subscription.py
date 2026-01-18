from typing import List, Optional, Dict, Any
from datetime import date, timedelta, datetime
from .base_entity import BaseEntity
from database.models import Subscription, Institution, SubscriptionPlan
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
        - 'suspended': is_active=False
        - 'pending': is_active=False AND end_date is null
        - 'expired': end_date is in past
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
            return (
                self.session.query(Subscription)
                .filter(Subscription.is_active == False)
                .count()
            )
        elif status == 'pending':
            # Pending subscriptions are inactive with no end date (not yet activated)
            return (
                self.session.query(Subscription)
                .filter(
                    Subscription.is_active == False,
                    Subscription.end_date.is_(None)
                )
                .count()
            )
        elif status == 'expired':
            # Expired subscriptions have end_date in the past
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

    def get_pending_subscriptions(self) -> List[Dict[str, Any]]:
        """Get all pending subscription requests with institution details."""
        from application.entities2.institution import InstitutionModel
        
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
        
        return {
            'subscription': subscription.as_dict(),
            'institution': institution.as_dict() if institution else None,
            'plan': plan.as_dict() if plan else None
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
            result.append({
                'subscription_id': subscription.subscription_id,
                'institution_name': institution.name if institution else 'Unknown',
                'institution_id': institution.institution_id if institution else None,
                'plan_id': subscription.plan_id,
                'start_date': subscription.start_date,
                'end_date': subscription.end_date,
                'is_active': subscription.is_active,
                'created_at': subscription.created_at
            })
        
        return result