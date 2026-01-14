from .base_entity import BaseEntity
from database.models import *
from datetime import date
from sqlalchemy import func

class SemesterModel(BaseEntity[Semester]):
    """Specific entity for User model with custom methods"""
    
    def __init__(self, session):
        super().__init__(session, Semester)

    def get_current_semester_info(self):
        headers = ["institution_name", "semester_name"]
        data = (
            self.session
            .query(Institution.name, Semester.name)
            .select_from(Semester)
            .join(Institution, Institution.institution_id == Semester.institution_id)
            .filter(
                (Semester.start_date <= date.today()) &
                (Semester.end_date >= date.today())
            )
            .first()
        )
        return dict(zip(headers, data))
    
    def student_dashboard_term_attendance(self, student_id):
        data = dict(
            self.session
            .query(
                func.coalesce(AttendanceRecord.status, "unmarked").label("status"),
                func.count(Class.class_id).label("count")
            )
            .join(CourseUser, (CourseUser.course_id == Class.course_id) & (CourseUser.semester_id == Class.semester_id))
            .join(Semester, Semester.semester_id == Class.semester_id)
            .outerjoin(
                AttendanceRecord,
                (AttendanceRecord.class_id == Class.class_id) & (AttendanceRecord.student_id == CourseUser.user_id)
            )
            .filter(CourseUser.user_id == student_id)
            .filter(Semester.start_date <= func.now(), Semester.end_date >= func.now())
            .group_by(func.coalesce(AttendanceRecord.status, "unmarked"))
            .all()
        )
        print(data)
        return data

