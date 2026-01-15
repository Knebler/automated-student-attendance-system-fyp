from .base_entity import BaseEntity
from database.models import *
from datetime import datetime
from sqlalchemy import func

class UserModel(BaseEntity[User]):
    """Specific entity for User model with custom methods"""
    
    def __init__(self, session):
        super().__init__(session, User)

    def get_by_email(self, email) -> User:
        return self.session.query(User).filter(User.email == email).first()

    def suspend(self, user_id) -> bool:
        user = self.get_by_id(user_id)
        if user:
            user.is_active = False
            self.session.commit()
            return True
        return False
    
    def unsuspend(self, user_id) -> bool:
        user = self.get_by_id(user_id)
        if user:
            user.is_active = True
            self.session.commit()
            return True
        return False
    
    def pm_user_stats(self):
        cutoff_date = datetime(datetime.now().year, datetime.now().month, 1)

        q_user_count = self.session.query(func.count(User.user_id))
        q_user_count_last_month = q_user_count.filter(User.date_joined > cutoff_date)
        q_admin_count = q_user_count.filter(User.role == "admin").scalar_subquery()
        q_admin_count_last_month = q_user_count_last_month.filter(User.role == "admin").scalar_subquery()
        q_lecturer_count = q_user_count.filter(User.role == "lecturer").scalar_subquery()
        q_lecturer_count_last_month = q_user_count_last_month.filter(User.role == "lecturer").scalar_subquery()
        q_student_count = q_user_count.filter(User.role == "student").scalar_subquery()
        q_student_count_last_month = q_user_count_last_month.filter(User.role == "student").scalar_subquery()

        headers = [
            "user_count", "user_change_percentage",
            "admin_count", "admin_change_percentage",
            "lecturer_count", "lecturer_change_percentage",
            "student_count", "student_change_percentage"
        ]
        count_data = self.session.query(
            q_user_count.scalar_subquery(), q_user_count_last_month.scalar_subquery(),
            q_admin_count, q_admin_count_last_month,
            q_lecturer_count, q_lecturer_count_last_month,
            q_student_count, q_student_count_last_month
        ).one()
        count_data = list(count_data)
        def perc_change(added, total):
            try:
                return added / (total - added) * 100
            except ZeroDivisionError:
                return 9999
        for idx in range(1, len(headers), 2):
            count_data[idx] = perc_change(count_data[idx], count_data[idx - 1])
        return dict(zip(headers, count_data))

    def admin_user_stats(self, institution_id):
        base_filter = self.session.query(User).filter(User.institution_id == institution_id)
        user_count = base_filter.count()
        admin_count = base_filter.filter(User.role == "admin").count()
        lecturer_count = base_filter.filter(User.role == "lecturer").count()
        student_count = base_filter.filter(User.role == "student").count()

        return {
            "user_count": user_count,
            "admin_count": admin_count,
            "lecturer_count": lecturer_count,
            "student_count": student_count,
        }
    
    def student_stats(self, student_id):
        db_data = (
            self.session
            .query(
                Semester.name,
                Course.code,
                Class.class_id,
                func.coalesce(AttendanceRecord.status, "unmarked"),
            )
            .select_from(CourseUser)
            .join(Semester, Semester.semester_id == CourseUser.semester_id)
            .join(Course, Course.course_id == CourseUser.course_id)
            .join(Class,  (Class.course_id == Course.course_id) & (Class.semester_id == CourseUser.semester_id))
            .outerjoin(AttendanceRecord, AttendanceRecord.class_id == Class.class_id)
            .filter(CourseUser.user_id == student_id)
            .all()
        )
        student_data = {}
        for row in db_data:
            sem, course, class_id, status = row
            if sem not in student_data:
                student_data[sem] = {}
            if course not in student_data[sem]:
                student_data[sem][course] = {}
            student_data[sem][course][class_id] = status
        return student_data

    def delete(self, user_id) -> bool:
        user = self.get_by_id(user_id)
        if user:
            self.session.delete(user)
            self.session.commit()
            return True
        return False
    
    
