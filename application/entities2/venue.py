from .base_entity import BaseEntity
from database.models import Venue, Institution, Class
from typing import List, Optional, Dict
from datetime import datetime, date

class VenueModel(BaseEntity[Venue]):
    """Entity for Venue model with custom methods"""
    
    def __init__(self, session):
        super().__init__(session, Venue)
    
    def get_by_institution(self, institution_id: int) -> List[Venue]:
        """Get all venues for a specific institution"""
        return self.session.query(Venue)\
            .filter(Venue.institution_id == institution_id)\
            .order_by(Venue.name.asc())\
            .all()
    
    def get_available_venues(self, institution_id: int, capacity_required: int) -> List[Venue]:
        """Get venues with sufficient capacity"""
        return self.session.query(Venue)\
            .filter(
                Venue.institution_id == institution_id,
                Venue.capacity >= capacity_required
            )\
            .order_by(Venue.capacity.asc())\
            .all()
    
    def check_availability(self, venue_id: int, start_time: datetime, 
                          end_time: datetime) -> bool:
        """Check if a venue is available during a specific time slot"""
        conflicting_classes = self.session.query(Class)\
            .filter(
                Class.venue_id == venue_id,
                Class.start_time < end_time,
                Class.end_time > start_time
            )\
            .count()
        
        return conflicting_classes == 0
    
    def get_venue_usage(self, venue_id: int, start_date: date, 
                       end_date: date) -> List[Dict]:
        """Get usage statistics for a venue within a date range"""
        classes = self.session.query(Class)\
            .filter(
                Class.venue_id == venue_id,
                Class.start_time >= start_date,
                Class.start_time <= end_date
            )\
            .all()
        
        usage_data = []
        for cls in classes:
            usage_data.append({
                'class_id': cls.class_id,
                'course_id': cls.course_id,
                'start_time': cls.start_time,
                'end_time': cls.end_time,
                'status': cls.status
            })
        
        return usage_data
    
    def create_venue(self, institution_id: int, name: str, 
                    capacity: Optional[int] = None) -> Venue:
        """Create a new venue"""
        venue = Venue(
            institution_id=institution_id,
            name=name,
            capacity=capacity
        )
        self.session.add(venue)
        self.session.commit()
        return venue
    
    def get_venue_capacity(self, venue_id: int) -> Optional[int]:
        """Get capacity of a specific venue"""
        venue = self.session.query(Venue)\
            .filter(Venue.venue_id == venue_id)\
            .first()
        
        return venue.capacity if venue else None
    
    def update_venue_capacity(self, venue_id: int, new_capacity: int) -> Optional[Venue]:
        """Update the capacity of a venue"""
        venue = self.session.query(Venue)\
            .filter(Venue.venue_id == venue_id)\
            .first()
        
        if venue:
            venue.capacity = new_capacity
            self.session.commit()
        
        return venue