from .base_entity import BaseEntity
from database.models import SubscriptionPlan

class SubscriptionPlanModel(BaseEntity[SubscriptionPlan]):
    """Specific entity for User model with custom methods"""
    
    def __init__(self, session):
        super().__init__(session, SubscriptionPlan)
