from .base_entity import BaseEntity
from database.models import Notification

class NotificationModel(BaseEntity[Notification]):
    """Specific entity for User model with custom methods"""
    
    def __init__(self, session):
        super().__init__(session, Notification)
