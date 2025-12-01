from application.entities.base_entity import BaseEntity

class TimetableSlot(BaseEntity):
    """Timetable Slot entity"""
    
    TABLE_NAME = "Timetable_Slots"
    
    def __init__(self, slot_id=None, institution_id=None, day_of_week=None,
                 start_time=None, end_time=None, slot_name=None):
        self.slot_id = slot_id
        self.institution_id = institution_id
        self.day_of_week = day_of_week
        self.start_time = start_time
        self.end_time = end_time
        self.slot_name = slot_name