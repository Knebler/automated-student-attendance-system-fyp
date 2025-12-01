from application.entities.base_entity import BaseEntity

class Venue(BaseEntity):
    """Venue entity"""
    
    TABLE_NAME = "Venues"
    
    def __init__(self, venue_id=None, institution_id=None, venue_name=None,
                 building=None, capacity=None, facilities=None, is_active=True):
        self.venue_id = venue_id
        self.institution_id = institution_id
        self.venue_name = venue_name
        self.building = building
        self.capacity = capacity
        self.facilities = facilities
        self.is_active = is_active