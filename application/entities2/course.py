from .base_entity import BaseEntity
from database.models import Course

class CourseModel(BaseEntity[Course]):
    """Specific entity for User model with custom methods"""
    
    def __init__(self, session):
        super().__init__(session, Course)