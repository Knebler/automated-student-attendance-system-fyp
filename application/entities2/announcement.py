from .base_entity import BaseEntity
from database.models import Announcement, Institution, User
from typing import List, Optional
from datetime import datetime

class AnnouncementModel(BaseEntity[Announcement]):
    """Entity for Announcement model with custom methods"""
    
    def __init__(self, session):
        super().__init__(session, Announcement)
    
    def get_by_institution(self, institution_id: int) -> List[Announcement]:
        """Get all announcements for a specific institution"""
        return self.session.query(Announcement)\
            .filter(Announcement.institution_id == institution_id)\
            .order_by(Announcement.date_posted.desc())\
            .all()
    
    def get_recent_announcements(self, institution_id: int, limit: int = 10) -> List[Announcement]:
        """Get recent announcements for an institution"""
        return self.session.query(Announcement)\
            .filter(Announcement.institution_id == institution_id)\
            .order_by(Announcement.date_posted.desc())\
            .limit(limit)\
            .all()
    
    def create_announcement(self, institution_id: int, requested_by_user_id: int, 
                           title: str, content: str) -> Announcement:
        """Create a new announcement"""
        announcement = Announcement(
            institution_id=institution_id,
            requested_by_user_id=requested_by_user_id,
            title=title,
            content=content,
            date_posted=datetime.utcnow()
        )
        self.session.add(announcement)
        self.session.commit()
        return announcement
    
    def search_announcements(self, institution_id: int, search_term: str) -> List[Announcement]:
        """Search announcements by title or content"""
        return self.session.query(Announcement)\
            .filter(
                Announcement.institution_id == institution_id,
                (Announcement.title.ilike(f"%{search_term}%") | 
                 Announcement.content.ilike(f"%{search_term}%"))
            )\
            .order_by(Announcement.date_posted.desc())\
            .all()