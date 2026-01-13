from .base_entity import BaseEntity
from database.models import Course, User, CourseUser

class CourseModel(BaseEntity[Course]):
    """Specific entity for User model with custom methods"""
    
    def __init__(self, session):
        super().__init__(session, Course)

    def get_manage_course_info(self, institution_id, course_id=None):
        q = (
            self.session
            .query(Course.course_id, Course.name, Course.code, User.name, Course.is_active)
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
    
    def get_unenrolled(self, user_id):
        return (
            self.session
            .query(Course)
            .filter(Course.institution_id == self.session.query(User.institution_id).filter(User.user_id == user_id))
            .filter(Course.course_id.notin_(self.session.query(CourseUser.course_id).filter(CourseUser.user_id == user_id)))
            .all()
        )
    