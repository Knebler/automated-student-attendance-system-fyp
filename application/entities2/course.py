from .base_entity import BaseEntity
from database.models import *

class CourseModel(BaseEntity[Course]):
    """Specific entity for User model with custom methods"""
    
    def __init__(self, session):
        super().__init__(session, Course)

    def get_manage_course_info(self, institution_id, course_id=None):
        q = (
            self.session
            .query(Course.course_id, Course.name, Course.code, User.name)
            .join(CourseUser, CourseUser.course_id == Course.course_id)
            .join(User, User.user_id == CourseUser.user_id)
            .filter(Course.institution_id == institution_id)
            .filter(User.role == "lecturer")
        )
        if course_id:
            q.filter(Course.course_id == course_id)
        return q.all()

    def get_by_user_id(self, user_id):
        return (
            self.session
            .query(Course)
            .join(CourseUser, CourseUser.course_id == Course.course_id)
            .join(User, User.user_id == CourseUser.user_id)
            .filter(User.user_id == user_id)
            .all()
        )
    
    def get_by_user_id(self, user_id):
        """Get courses for a specific user (lecturer)"""
        return (
            self.session.query(Course)
            .join(CourseUser, CourseUser.course_id == Course.course_id)
            .filter(CourseUser.user_id == user_id)
            .all()
        )
    
    def admin_view_courses(self, user_id):
        headers = ["course_id", "name", "code", "semester_id", "semester_name", "start_date", "end_date"]
        data = (
            self.session
            .query(Course.course_id, Course.name, Course.code, Semester.semester_id, Semester.name, Semester.start_date, Semester.end_date)
            .select_from(CourseUser)
            .join(Course, Course.course_id == CourseUser.course_id)
            .join(Semester, Semester.semester_id == CourseUser.semester_id)
            .join(User, User.user_id == CourseUser.user_id)
            .filter(CourseUser.user_id == user_id)
            .all()
        )
        return self.add_headers(headers, data)
