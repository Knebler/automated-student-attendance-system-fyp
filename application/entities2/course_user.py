from .base_entity import BaseEntity
from database.models import CourseUser

class CourseUserModel(BaseEntity[CourseUser]):
    """Specific entity for User model with custom methods"""
    
    def __init__(self, session):
        super().__init__(session, CourseUser)

    def assign(self, course_id, user_id, semester_id) -> bool:
        course_user = CourseUser(course_id=course_id, user_id=user_id, semester_id=semester_id)
        self.session.add(course_user)
        self.session.commit()
        return True

    def unassign(self, course_id, user_id, semester_id) -> bool:
        course_user = (
            self.session
            .query(CourseUser)
            .filter(
                CourseUser.course_id == course_id,
                CourseUser.user_id == user_id,
                CourseUser.semester_id == semester_id,
            )
            .first()
        )
        if course_user:
            self.session.delete(course_user)
            self.session.commit()
            return True
        return False