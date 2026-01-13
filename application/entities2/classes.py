from .base_entity import BaseEntity
from database.models import Class, Course, Venue, User
from datetime import date, datetime, timedelta

class ClassModel(BaseEntity[Class]):
    """Specific entity for User model with custom methods"""
    
    def __init__(self, session):
        super().__init__(session, Class)

    def get_today(self, institution_id):
        return (
            self.session
            .query(Class)
            .join(Course, Class.course_id == Course.course_id)
            .filter(Course.institution_id == institution_id)
            .filter(Class.start_time > date.today())
            .all()
        )
    
    def get_completed(self, course_id):
        return (
            self.session
            .query(Class.class_id, Class.start_time, Class.end_time, Venue.name, User.name)
            .join(User, User.user_id == Class.lecturer_id)
            .join(Venue, Class.venue_id == Venue.venue_id)
            .filter(Class.course_id == course_id)
            .filter(Class.end_time < datetime.now())
            .filter(User.role == "lecturer")
            .all()
        )

    def get_upcoming(self, course_id):
        return (
            self.session
            .query(Class.class_id, Class.start_time, Class.end_time, Venue.name, User.name)
            .join(User, User.user_id == Class.lecturer_id)
            .join(Venue, Class.venue_id == Venue.venue_id)
            .filter(Class.course_id == course_id)
            .filter(Class.start_time > datetime.now())
            .filter(User.role == "lecturer")
            .all()
        )

    def admin_dashboard_classes_today(self, institution_id):
        cols = ["module", "venue", "lecturer"]
        classes = (
            self.session
            .query(Course.name, Venue.name, User.name)
            .select_from(Class)
            .join(Course, Class.course_id == Course.course_id)
            .join(User, Class.lecturer_id == User.user_id)
            .join(Venue, Class.venue_id == Venue.venue_id)
            .filter(Course.institution_id == institution_id)
            .filter(Class.start_time > date.today())
            .filter(Class.start_time < date.today() + timedelta(days=1))
            .all()
        )
        return [dict(zip(cols, row)) for row in classes]
