from .base_entity import BaseEntity
from database.models import Semester, Institution
from typing import List, Optional
from datetime import datetime, date

class SemesterModel(BaseEntity[Semester]):
    """Entity for Semester model with custom methods"""
    
    def __init__(self, session):
        super().__init__(session, Semester)
    
    def get_by_institution(self, institution_id: int) -> List[Semester]:
        """Get all semesters for a specific institution"""
        return self.session.query(Semester)\
            .filter(Semester.institution_id == institution_id)\
            .order_by(Semester.start_date.desc())\
            .all()
    
    def get_current_semester(self, institution_id: int) -> Optional[Semester]:
        """Get the current active semester for an institution"""
        today = date.today()
        
        return self.session.query(Semester)\
            .filter(
                Semester.institution_id == institution_id,
                Semester.start_date <= today,
                Semester.end_date >= today
            )\
            .first()
    
    def create_semester(self, institution_id: int, name: str, 
                       start_date: date, end_date: date) -> Semester:
        """Create a new semester"""
        semester = Semester(
            institution_id=institution_id,
            name=name,
            start_date=start_date,
            end_date=end_date
        )
        self.session.add(semester)
        self.session.commit()
        return semester
    
    def get_upcoming_semesters(self, institution_id: int) -> List[Semester]:
        """Get upcoming semesters (starting in the future)"""
        today = date.today()
        
        return self.session.query(Semester)\
            .filter(
                Semester.institution_id == institution_id,
                Semester.start_date > today
            )\
            .order_by(Semester.start_date.asc())\
            .all()
    
    def get_past_semesters(self, institution_id: int) -> List[Semester]:
        """Get past semesters"""
        today = date.today()
        
        return self.session.query(Semester)\
            .filter(
                Semester.institution_id == institution_id,
                Semester.end_date < today
            )\
            .order_by(Semester.end_date.desc())\
            .all()
    
    def get_semester_by_date(self, institution_id: int, target_date: date) -> Optional[Semester]:
        """Get semester that contains a specific date"""
        return self.session.query(Semester)\
            .filter(
                Semester.institution_id == institution_id,
                Semester.start_date <= target_date,
                Semester.end_date >= target_date
            )\
            .first()