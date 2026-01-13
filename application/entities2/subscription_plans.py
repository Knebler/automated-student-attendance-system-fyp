from typing import List, Optional, Dict, Any
from sqlalchemy import or_
from .base_entity import BaseEntity
from database.models import SubscriptionPlan


class SubscriptionPlanModel(BaseEntity[SubscriptionPlan]):
    """Entity providing read-only convenience methods for subscription plans.

    Note: This class intentionally exposes only GET/read helpers. Any write
    operations (create/update/delete) should be performed via higher-level
    controls or administrative tools where transactional rules are enforced.
    """

    def __init__(self, session):
        super().__init__(session, SubscriptionPlan)

    def get_by_plan_id(self, plan_id: int) -> Optional[SubscriptionPlan]:
        """Return a plan by its id or None."""
        return self.get_by_id(plan_id)

    def get_by_name(self, name: str) -> Optional[SubscriptionPlan]:
        """Return a plan matching the exact name (case-sensitive)."""
        return self.get_one(name=name)

    def get_active_plans(self) -> List[SubscriptionPlan]:
        """Return all active subscription plans."""
        return self.get_all(is_active=True)

    def search(self, query: str) -> List[SubscriptionPlan]:
        """Search plans by name or description (case-insensitive substring).

        Returns an empty list when `query` is falsy.
        """
        if not query:
            return []
        return (
            self.session.query(self.model)
            .filter(or_(self.model.name.ilike(f"%{query}%"), self.model.description.ilike(f"%{query}%")))
            .all()
        )

    def get_by_price_range(self, min_price: Optional[float] = None, max_price: Optional[float] = None) -> List[SubscriptionPlan]:
        """Return plans whose price falls within the given bounds."""
        q = self.session.query(self.model)
        if min_price is not None:
            q = q.filter(self.model.price_per_cycle >= min_price)
        if max_price is not None:
            q = q.filter(self.model.price_per_cycle <= max_price)
        return q.all()

    def get_features(self, plan_id: int) -> Optional[Dict[str, Any]]:
        """Return the features JSON for a plan or None if not found."""
        plan = self.get_by_plan_id(plan_id)
        return plan.features if plan else None

    def get_paginated_active(self, page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        """Return paginated active plans using the shared pagination helper."""
        return self.get_paginated(page, per_page, is_active=True)