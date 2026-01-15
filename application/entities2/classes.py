from .base_entity import BaseEntity
from database.models import Class, Course, Venue, User, CourseUser, AttendanceRecord
from datetime import date, datetime, timedelta
from sqlalchemy import func

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
        cols = ["id", "module", "venue", "lecturer"]
        classes = (
            self.session
            .query(Class.class_id, Course.name, Venue.name, User.name)
            .select_from(Class)
            .join(Course, Class.course_id == Course.course_id)
            .join(User, Class.lecturer_id == User.user_id)
            .join(Venue, Class.venue_id == Venue.venue_id)
            .filter(Course.institution_id == institution_id)
            .filter(Class.start_time > date.today())
            .filter(Class.start_time < date.today() + timedelta(days=1))
            .all()
        )
        return self.add_headers(cols, classes)
    
    def admin_class_details(self, class_id):
        headers = ["start_time", "venue", "lecturer"]
        class_data = (
            self.session
            .query(Class.start_time, Venue.name, User.name)
            .join(Venue, Class.venue_id == Venue.venue_id)
            .join(User, Class.lecturer_id == User.user_id)
            .filter(Class.class_id == class_id)
            .one()
        )
        class_details: dict = dict(zip(headers, class_data))
        q_in_course = (
            self.session
            .query(func.count(User.user_id))
            .select_from(Class)
            .join(Course, Class.course_id == Course.course_id)
            .join(CourseUser, CourseUser.course_id == Course.course_id)
            .join(User, User.user_id == CourseUser.user_id)
            .filter(Class.class_id == class_id)
            .filter(User.role == "student")
        )
        q_total = q_in_course.scalar_subquery()
        q_attendance_exists = q_in_course.join(AttendanceRecord, AttendanceRecord.class_id == Class.class_id)
        q_present = q_attendance_exists.filter(AttendanceRecord.status == "present").scalar_subquery()
        q_late = q_attendance_exists.filter(AttendanceRecord.status == "late").scalar_subquery()
        q_excused = q_attendance_exists.filter(AttendanceRecord.status == "excused").scalar_subquery()
        q_absent = q_attendance_exists.filter(AttendanceRecord.status == "absent").scalar_subquery()

        cols = ["total", "present", "late", "excused", "absent"]
        row = self.session.query(q_total, q_present, q_late, q_excused, q_absent).one()

        class_details.update(dict(zip(cols, row)))
        class_details["marked"] = sum(row[1:])
        return class_details

    def get_attendance_records(self, class_id):
        headers = ["student_name", "student_id", "status"]
        records = (
            self.session
            .query(User.name, User.user_id, func.coalesce(AttendanceRecord.status, "unmarked"))
            .select_from(Class)
            .join(Course, Class.course_id == Course.course_id)
            .join(CourseUser, CourseUser.course_id == Course.course_id)
            .join(User, User.user_id == CourseUser.user_id)
            .outerjoin(AttendanceRecord, AttendanceRecord.class_id == Class.class_id)
            .filter(Class.class_id == class_id)
            .filter(User.role == "student")
            .all()
        )
        return self.add_headers(headers, records)

    def class_is_institution(self, class_id, institution_id) -> bool:
        return (
            self.session
            .query(Course.institution_id)
            .join(Class, Class.course_id == Course.course_id)
            .filter(Class.class_id == class_id)
            .filter(Course.institution_id == institution_id)
            .count() > 0
        )
    
    def get_course_name(self, class_id) -> str:
        result = (
            self.session
            .query(Course.name)
            .join(Class, Class.course_id == Course.course_id)
            .filter(Class.class_id == class_id)
            .one_or_none()
        )
        return result[0] if result else ""
    
    def get_today_classes_for_lecturer(self, lecturer_id, today_date):
        """Get today's classes for a specific lecturer"""
        return (
            self.session.query(Class)
            .filter(Class.lecturer_id == lecturer_id)
            .filter(func.date(Class.start_time) == today_date)
            .order_by(Class.start_time)
            .all()
        )

    def get_enrolled_students(self, class_id):
        """Get students enrolled in a specific class"""
        return (
            self.session.query(User)
            .join(CourseUser, CourseUser.user_id == User.user_id)
            .join(Course, Course.course_id == CourseUser.course_id)
            .join(Class, Class.course_id == Course.course_id)
            .filter(Class.class_id == class_id)
            .filter(User.role == 'student')
            .all()
        )

    def get_enrolled_count(self, class_id):
        """Get count of students enrolled in a class"""
        return (
            self.session.query(func.count(User.user_id))
            .join(CourseUser, CourseUser.user_id == User.user_id)
            .join(Course, Course.course_id == CourseUser.course_id)
            .join(Class, Class.course_id == Course.course_id)
            .filter(Class.class_id == class_id)
            .filter(User.role == 'student')
            .scalar() or 0
        )

    def get_attendance_statistics(self, course_id, lecturer_id, start_date, end_date):
        """Get attendance statistics for a course"""
        # This would calculate statistics like attendance trends, distribution, etc.
        # Implementation depends on your specific statistics needs
        return {
            'attendance_trend': [],  # List of daily/weekly attendance percentages
            'distribution': {  # Distribution of attendance performance
                'excellent': 50,  # ≥90%
                'good': 40,      # 80-89%
                'average': 10    # 70-79%
            },
            'total_classes': 25,
            'total_attendance': 85  # Percentage
        }

    def get_classes_for_course(self, course_id, lecturer_id):
        """Get classes for a specific course taught by a lecturer"""
        return (
            self.session.query(Class)
            .filter(Class.course_id == course_id)
            .filter(Class.lecturer_id == lecturer_id)
            .order_by(Class.start_time)
            .all()
        )

    def get_upcoming_classes_for_lecturer(self, lecturer_id, from_date, course_filter=None, class_type_filter=None):
        """Get upcoming classes for a lecturer"""
        query = (
            self.session.query(Class)
            .filter(Class.lecturer_id == lecturer_id)
            .filter(Class.start_time >= from_date)
            .order_by(Class.start_time)
        )
    
        if course_filter:
            query = query.join(Course).filter(Course.code == course_filter)
    
        if class_type_filter:
            query = query.filter(Class.class_type == class_type_filter)
    
        return query.all()

    def get_classes_for_lecturer_in_date_range(self, lecturer_id, start_date, end_date, course_filter=None, class_type_filter=None):
        """Get classes for a lecturer within a date range"""
        query = (
            self.session.query(Class)
            .filter(Class.lecturer_id == lecturer_id)
            .filter(Class.start_time >= start_date)
            .filter(Class.start_time <= end_date)
            .order_by(Class.start_time)
        )
    
        if course_filter:
            query = query.join(Course).filter(Course.code == course_filter)
    
        if class_type_filter:
            query = query.filter(Class.class_type == class_type_filter)
    
        return query.all()