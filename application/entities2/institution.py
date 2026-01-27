from typing import List, Optional, Dict, Any
from .base_entity import BaseEntity
from database.models import Institution, Subscription, SubscriptionPlan
from sqlalchemy import or_, func
from datetime import datetime, timedelta


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
    
    def get_all_with_subscriptions(self) -> List[Dict[str, Any]]:
        """Return all institutions with their subscription details regardless of subscription status."""
        
        results = (
            self.session.query(Institution, Subscription, SubscriptionPlan)
            .outerjoin(Subscription, Institution.subscription_id == Subscription.subscription_id)
            .outerjoin(SubscriptionPlan, Subscription.plan_id == SubscriptionPlan.plan_id)
            .order_by(Institution.institution_id.desc())  # Using institution_id since created_at doesn't exist
            .all()
        )
        
        institutions_list = []
        for institution, subscription, subscription_plan in results:
            if subscription:
                # Get plan name from SubscriptionPlan
                plan_name = subscription_plan.name if subscription_plan else 'none'
                
                # Determine status based on subscription fields
                if not subscription.is_active:
                    status = 'suspended'
                elif subscription.end_date and subscription.end_date < datetime.now():
                    status = 'expired'
                else:
                    status = 'active'
                    
                renewal_date = subscription.end_date
            else:
                # Default values if no subscription
                plan_name = 'none'
                status = 'none'
                renewal_date = None
            
            # Get avatar initials
            name_parts = institution.name.split()
            if len(name_parts) >= 2:
                initials = name_parts[0][0] + name_parts[-1][0]
            else:
                initials = institution.name[:2].upper()
            
            institutions_list.append({
                'institution_id': institution.institution_id,
                'name': institution.name,
                'location': institution.address,  # Using address as location
                'contact_person': institution.poc_name,
                'contact_email': institution.poc_email,
                'contact_phone': institution.poc_phone,
                'plan': plan_name,
                'status': status,
                'renewal_date': renewal_date,
                'subscription_id': institution.subscription_id,
                'initials': initials,
                'is_active': subscription.is_active if subscription else False,
                'created_at': institution.institution_id,  # Using ID as proxy for creation order
                'subscription_start_date': subscription.start_date if subscription else None,
                'subscription_end_date': subscription.end_date if subscription else None
            })
        
        return institutions_list
    
    def search_with_filters(self, search_term: str = '', status: str = '', plan: str = '') -> List[Dict[str, Any]]:
        """Search institutions with filters."""
        
        query = self.session.query(Institution, Subscription, SubscriptionPlan)
        query = query.outerjoin(Subscription, Institution.subscription_id == Subscription.subscription_id)
        query = query.outerjoin(SubscriptionPlan, Subscription.plan_id == SubscriptionPlan.plan_id)
        
        # Apply search filter
        if search_term:
            search_term = f"%{search_term}%"
            query = query.filter(
                or_(
                    Institution.name.ilike(search_term),
                    Institution.address.ilike(search_term),
                    Institution.poc_name.ilike(search_term),
                    Institution.poc_email.ilike(search_term),
                    SubscriptionPlan.name.ilike(search_term) if SubscriptionPlan.name is not None else False
                )
            )
        
        # Apply status filter
        if status:
            if status == 'active':
                query = query.filter(
                    Subscription.is_active == True,
                    (Subscription.end_date.is_(None) | (Subscription.end_date >= datetime.now()))
                )
            elif status == 'suspended':
                query = query.filter(Subscription.is_active == False)
            elif status == 'expired':
                query = query.filter(
                    Subscription.end_date.isnot(None),
                    Subscription.end_date < datetime.now()
                )
            elif status == 'pending':
                # For pending, we might need a different logic - perhaps based on is_active=False and no end date?
                # Assuming pending means not yet activated
                query = query.filter(Subscription.is_active == False)
        
        # Apply plan filter
        if plan and plan != 'none':
            query = query.filter(SubscriptionPlan.name == plan)
        
        results = query.order_by(Institution.institution_id.desc()).all()
        
        institutions_list = []
        for institution, subscription, subscription_plan in results:
            if subscription:
                # Determine status
                if not subscription.is_active:
                    current_status = 'suspended'
                elif subscription.end_date and subscription.end_date < datetime.now():
                    current_status = 'expired'
                else:
                    current_status = 'active'
                
                plan_name = subscription_plan.name if subscription_plan else 'none'
            else:
                current_status = 'none'
                plan_name = 'none'
            
            # Get avatar initials
            name_parts = institution.name.split()
            if len(name_parts) >= 2:
                initials = name_parts[0][0] + name_parts[-1][0]
            else:
                initials = institution.name[:2].upper()
            
            institutions_list.append({
                'institution_id': institution.institution_id,
                'name': institution.name,
                'location': institution.address,
                'contact_person': institution.poc_name,
                'contact_email': institution.poc_email,
                'contact_phone': institution.poc_phone,
                'plan': plan_name,
                'status': current_status,
                'subscription_id': institution.subscription_id,
                'initials': initials,
                'created_at': institution.institution_id,  # Using ID as proxy
                'subscription_start_date': subscription.start_date if subscription else None,
                'subscription_end_date': subscription.end_date if subscription else None
            })
        
        return institutions_list
    
    def get_with_subscription_details(self, institution_id: int) -> Optional[Dict[str, Any]]:
        """Get institution with subscription and plan details."""
        
        institution = self.get_by_id(institution_id)
        if not institution:
            return None
        
        result = {
            'institution': institution.as_dict(),
            'subscription': None,
            'plan': None
        }
        
        if institution.subscription_id:
            subscription = self.session.query(Subscription).get(institution.subscription_id)
            if subscription:
                result['subscription'] = subscription.as_dict()
                
                if subscription.plan_id:
                    plan = self.session.query(SubscriptionPlan).get(subscription.plan_id)
                    if plan:
                        result['plan'] = plan.as_dict()
        
        return result
    
    def get_institutions_by_plan(self, plan_id: int) -> List[Institution]:
        """Get all institutions subscribed to a specific plan."""
        
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
            
            # Create admin user
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
        
        query = (
            self.session.query(self.model)
            .join(Subscription)
            .filter(Subscription.is_active == True)
        )
        
        return self.get_paginated_from_query(query, page, per_page)
    
    def count_by_subscription_status(self, status: str = 'active') -> int:
        """Count institutions by subscription status."""
        
        if status == 'all':
            return self.session.query(Institution).count()
        elif status == 'active':
            return (
                self.session.query(Institution)
                .join(Subscription)
                .filter(
                    Subscription.is_active == True,
                    (Subscription.end_date.is_(None) | (Subscription.end_date >= datetime.now()))
                )
                .count()
            )
        elif status == 'suspended':
            return (
                self.session.query(Institution)
                .join(Subscription)
                .filter(Subscription.is_active == False)
                .count()
            )
        elif status == 'expired':
            return (
                self.session.query(Institution)
                .join(Subscription)
                .filter(
                    Subscription.end_date.isnot(None),
                    Subscription.end_date < datetime.now()
                )
                .count()
            )
        else:
            # For other statuses, we might need custom logic
            return 0
        
    def count_created_after(self, date_threshold) -> int:
        """Count institutions created after a specific date.
        Note: Institution doesn't have created_at, so we use a proxy if needed.
        """
        # Since Institution doesn't have created_at, we can't use date comparison
        # We'll return a default value or implement alternative logic
        return 0  # Default for now
    
    def get_pending_subscription_institutions(self) -> List[Dict[str, Any]]:
        """Get institutions with pending subscription requests.
        Note: 'pending' status doesn't exist in Subscription model.
        We'll treat inactive subscriptions without an end date as pending.
        """
        
        results = (
            self.session.query(Institution, Subscription, SubscriptionPlan)
            .join(Subscription, Institution.subscription_id == Subscription.subscription_id)
            .outerjoin(SubscriptionPlan, Subscription.plan_id == SubscriptionPlan.plan_id)
            .filter(
                Subscription.is_active == False,
                Subscription.end_date.is_(None)  # No end date = pending activation
            )
            .order_by(Subscription.subscription_id.desc())
            .all()
        )
        
        pending_list = []
        for institution, subscription, subscription_plan in results:
            # Get avatar initials
            name_parts = institution.name.split()
            if len(name_parts) >= 2:
                initials = name_parts[0][0] + name_parts[-1][0]
            else:
                initials = institution.name[:2].upper()
            
            plan_name = subscription_plan.name if subscription_plan else 'none'
            
            pending_list.append({
                'institution_id': institution.institution_id,
                'name': institution.name,
                'location': institution.address,
                'contact_person': institution.poc_name,
                'contact_email': institution.poc_email,
                'contact_phone': institution.poc_phone,
                'request_date': subscription.created_at,
                'plan': plan_name,
                'status': 'pending',
                'subscription_id': subscription.subscription_id,
                'initials': initials,
                'subscription_start_date': subscription.start_date,
                'subscription_end_date': subscription.end_date
            })
        
        return pending_list
    
    def create_institution_with_details(
        self,
        name: str,
        address: str,
        poc_name: str,
        poc_email: str,
        poc_phone: str,
        plan_name: str = 'starter',
        status: str = 'active'
    ) -> Dict[str, Any]:
        """Create a new institution with subscription details.
        
        Returns the created institution data or raises an exception.
        """
        
        try:
            # First, find the plan by id
            plan_id = 0
            match plan_name:
                case 'starter':
                    plan_id = 1
                case 'pro':
                    plan_id = 2
                case 'enterprise':
                    plan_id = 3
                case _:
                    plan_id = 1

            plan = self.session.query(SubscriptionPlan).filter(
                SubscriptionPlan.plan_id == plan_id
            ).first()
            
            if not plan:
                raise ValueError(f"Plan '{plan_id}' not found")
            
            # Create subscription
            subscription = Subscription(
                plan_id=plan.plan_id,
                start_date=datetime.now(),
                end_date=datetime.now() + timedelta(days=365) if status == 'active' else None,
                is_active=(status == 'active'),
                stripe_subscription_id=None  # Can be set later if using Stripe
            )
            self.session.add(subscription)
            self.session.flush()  # Get the subscription_id
            
            # Create institution
            institution = Institution(
                name=name,
                address=address,
                poc_name=poc_name,
                poc_email=poc_email,
                poc_phone=poc_phone,
                subscription_id=subscription.subscription_id
            )
            self.session.add(institution)
            
            self.session.commit()
            
            # Get avatar initials
            name_parts = name.split()
            if len(name_parts) >= 2:
                initials = name_parts[0][0] + name_parts[-1][0]
            else:
                initials = name[:2].upper()
            
            return {
                'institution_id': institution.institution_id,
                'name': institution.name,
                'location': institution.address,
                'contact_person': institution.poc_name,
                'contact_email': institution.poc_email,
                'contact_phone': institution.poc_phone,
                'plan': plan_name,
                'status': status,
                'renewal_date': subscription.end_date,
                'subscription_id': subscription.subscription_id,
                'initials': initials,
                'is_active': subscription.is_active,
                'subscription_start_date': subscription.start_date,
                'subscription_end_date': subscription.end_date
            }
            
        except Exception as e:
            self.session.rollback()
            raise e