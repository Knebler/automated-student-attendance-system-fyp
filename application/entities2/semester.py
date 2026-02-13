from .base_entity import BaseEntity
from database.models import *
from datetime import date, datetime
from sqlalchemy import func
from typing import List, Optional

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
        today = datetime.now().date()
        
        return self.session.query(Semester)\
            .filter(
                Semester.institution_id == institution_id,
                func.date(Semester.start_date) <= today,
                func.date(Semester.end_date) >= today
            )\
            .first()
    
    def create_semester(self, institution_id: int, name: str, 
                       start_date: datetime, end_date: datetime) -> Semester:
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
        today = datetime.now()
        
        return self.session.query(Semester)\
            .filter(
                Semester.institution_id == institution_id,
                Semester.start_date > today
            )\
            .order_by(Semester.start_date.asc())\
            .all()
    
    def get_past_semesters(self, institution_id: int) -> List[Semester]:
        """Get past semesters"""
        today = datetime.now()
        
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
                func.date(Semester.start_date) <= target_date,
                func.date(Semester.end_date) >= target_date
            )\
            .first()
    
    def get_current_semester_info(self):
        """Get current semester info with institution name"""
        headers = ["institution_name", "semester_name"]
        today = datetime.now().date()
        
        data = (
            self.session
            .query(Institution.name, Semester.name)
            .select_from(Semester)
            .join(Institution, Institution.institution_id == Semester.institution_id)
            .filter(
                (func.date(Semester.start_date) <= today) &
                (func.date(Semester.end_date) >= today)
            )
            .first()
        )
        
        if data:
            return dict(zip(headers, data))
        return {}
    
    def student_dashboard_term_attendance(self, student_id):
        """Get student attendance summary for current semester"""
        return dict(
            self.session
            .query(
                AttendanceRecord.status.label("status"),
                func.count(Class.class_id).label("count")
            )
            .join(CourseUser, (CourseUser.course_id == Class.course_id) & (CourseUser.semester_id == Class.semester_id))
            .join(Semester, Semester.semester_id == Class.semester_id)
            .outerjoin(
                AttendanceRecord,
                (AttendanceRecord.class_id == Class.class_id) & (AttendanceRecord.student_id == CourseUser.user_id)
            )
            .filter(CourseUser.user_id == student_id)
            .filter(func.date(Semester.start_date) <= func.now(), func.date(Semester.end_date) >= func.now())
            .group_by(AttendanceRecord.status)
            .all()
        )