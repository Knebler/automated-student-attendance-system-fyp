from typing import List, Optional, Dict, Any
from .base_entity import BaseEntity
from database.models import Institution
from sqlalchemy import or_


class InstitutionModel(BaseEntity[Institution]):
    """Specific entity for Institution model with custom methods"""
    
    def __init__(self, session):
        super().__init__(session, Institution)
    
    def get_by_name(self, name: str) -> Optional[Institution]:
        """Return an institution by its exact name (case-insensitive)."""
        return self.get_one(name=name)
    
    def get_by_email(self, email: str) -> Optional[Institution]:
        """Return an institution by POC email (case-insensitive)."""
        return self.get_one(poc_email=email)
    
    def get_by_subscription_id(self, subscription_id: int) -> Optional[Institution]:
        """Return an institution by its subscription ID."""
        return self.get_one(subscription_id=subscription_id)
    
    def get_all_active(self) -> List[Institution]:
        """Return all institutions that have active subscriptions."""
        # Note: This assumes there's an is_active field on Institution or we check via subscription
        # Based on models.py, Institution doesn't have is_active directly
        # We'll need to join with Subscription to check if subscription is active
        from database.models import Subscription
        return (
            self.session.query(Institution)
            .join(Subscription)
            .filter(Subscription.is_active == True)
            .all()
        )
    
    def get_by_poc_email(self, email: str) -> Optional[Institution]:
        """Alias for get_by_email for clarity."""
        return self.get_by_email(email)
    
    def search(self, query: str) -> List[Institution]:
        """Search institutions by name or address (case-insensitive)."""
        if not query:
            return []
        return (
            self.session.query(self.model)
            .filter(
                or_(
                    self.model.name.ilike(f"%{query}%"),
                    self.model.address.ilike(f"%{query}%"),
                    self.model.poc_name.ilike(f"%{query}%")
                )
            )
            .all()
        )
    
    def get_with_subscription_details(self, institution_id: int) -> Optional[Dict[str, Any]]:
        """Get institution with subscription and plan details."""
        from database.models import Subscription, SubscriptionPlan
        
        institution = self.get_by_id(institution_id)
        if not institution:
            return None
        
        result = {
            'institution': institution.as_dict(),
            'subscription': None,
            'plan': None
        }
        
        if institution.subscription_id:
            subscription = (
                self.session.query(Subscription)
                .filter(Subscription.subscription_id == institution.subscription_id)
                .first()
            )
            if subscription:
                result['subscription'] = subscription.as_dict()
                
                if subscription.plan_id:
                    plan = (
                        self.session.query(SubscriptionPlan)
                        .filter(SubscriptionPlan.plan_id == subscription.plan_id)
                        .first()
                    )
                    if plan:
                        result['plan'] = plan.as_dict()
        
        return result
    
    def get_institutions_by_plan(self, plan_id: int) -> List[Institution]:
        """Get all institutions subscribed to a specific plan."""
        from database.models import Subscription
        
        return (
            self.session.query(Institution)
            .join(Subscription)
            .filter(Subscription.plan_id == plan_id)
            .all()
        )
    
    def create_with_admin(
        self,
        name: str,
        address: str,
        poc_name: str,
        poc_phone: str,
        poc_email: str,
        subscription_id: int,
        admin_user_data: Dict[str, Any]
    ) -> Optional[Institution]:
        """Create an institution along with its admin user.
        
        Returns the created institution or None on failure.
        """
        try:
            # Create institution
            institution = self.create(
                name=name,
                address=address,
                poc_name=poc_name,
                poc_phone=poc_phone,
                poc_email=poc_email,
                subscription_id=subscription_id
            )
            
            # Create admin user (you'll need UserModel imported)
            from application.entities2.user import UserModel
            user_model = UserModel(self.session)
            
            admin_user = user_model.create(
                institution_id=institution.institution_id,
                role='admin',
                name=admin_user_data.get('name', poc_name),
                email=admin_user_data.get('email', poc_email),
                phone_number=admin_user_data.get('phone_number', poc_phone),
                password_hash=admin_user_data.get('password_hash'),
                is_active=admin_user_data.get('is_active', True)
            )
            
            self.session.commit()
            return institution
            
        except Exception as e:
            self.session.rollback()
            raise e
    
    def update_institution(
        self,
        institution_id: int,
        **kwargs
    ) -> Optional[Institution]:
        """Update institution fields and return updated institution."""
        institution = self.get_by_id(institution_id)
        if not institution:
            return None
        
        for key, value in kwargs.items():
            if hasattr(institution, key):
                setattr(institution, key, value)
        
        self.session.commit()
        return institution
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get institution statistics."""
        total = self.session.query(self.model).count()
        
        # Count institutions with active subscriptions
        from database.models import Subscription
        active = (
            self.session.query(self.model)
            .join(Subscription)
            .filter(Subscription.is_active == True)
            .count()
        )
        
        return {
            'total_institutions': total,
            'active_institutions': active,
            'inactive_institutions': total - active
        }
    
    def get_paginated_active(self, page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        """Return paginated active institutions."""
        from database.models import Subscription
        
        query = (
            self.session.query(self.model)
            .join(Subscription)
            .filter(Subscription.is_active == True)
        )
        
        return self.get_paginated_from_query(query, page, per_page)