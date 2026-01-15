from .base_entity import BaseEntity
from database.models import Notification, User
from typing import List, Optional
from datetime import datetime, timedelta

class NotificationModel(BaseEntity[Notification]):
    """Entity for Notification model with custom methods"""
    
    def __init__(self, session):
        super().__init__(session, Notification)
    
    def get_user_notifications(self, user_id: int, unread_only: bool = False) -> List[Notification]:
        """Get notifications for a specific user"""
        query = self.session.query(Notification)\
            .filter(Notification.user_id == user_id)
        
        if unread_only:
            query = query.filter(Notification.acknowledged == False)
        
        return query.order_by(Notification.created_at.desc()).all()
    
    def create_notification(self, user_id: int, content: str) -> Notification:
        """Create a new notification"""
        notification = Notification(
            user_id=user_id,
            content=content,
            acknowledged=False,
            created_at=datetime.utcnow()
        )
        self.session.add(notification)
        self.session.commit()
        return notification
    
    def mark_as_read(self, notification_id: int) -> Optional[Notification]:
        """Mark a notification as read/acknowledged"""
        notification = self.session.query(Notification)\
            .filter(Notification.notification_id == notification_id)\
            .first()
        
        if notification:
            notification.acknowledged = True
            self.session.commit()
        
        return notification
    
    def mark_all_as_read(self, user_id: int) -> int:
        """Mark all notifications for a user as read"""
        result = self.session.query(Notification)\
            .filter(
                Notification.user_id == user_id,
                Notification.acknowledged == False
            )\
            .update({"acknowledged": True})
        
        self.session.commit()
        return result
    
    def get_unread_count(self, user_id: int) -> int:
        """Get count of unread notifications for a user"""
        return self.session.query(Notification)\
            .filter(
                Notification.user_id == user_id,
                Notification.acknowledged == False
            )\
            .count()
    
    def get_recent_notifications(self, user_id: int, hours: int = 24) -> List[Notification]:
        """Get notifications from the last N hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        return self.session.query(Notification)\
            .filter(
                Notification.user_id == user_id,
                Notification.created_at >= cutoff_time
            )\
            .order_by(Notification.created_at.desc())\
            .all()
    
    def bulk_create_notifications(self, user_ids: List[int], content: str) -> List[Notification]:
        """Create notifications for multiple users"""
        notifications = []
        for user_id in user_ids:
            notification = Notification(
                user_id=user_id,
                content=content,
                acknowledged=False,
                created_at=datetime.utcnow()
            )
            notifications.append(notification)
            self.session.add(notification)
        
        self.session.commit()
        return notifications