from typing import List, Optional, Dict, Any
from datetime import date, timedelta
from .base_entity import BaseEntity
from database.models import Subscription


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