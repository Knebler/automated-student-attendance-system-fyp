from .base_entity import BaseEntity
from database.models import User
from datetime import datetime

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

        user_count = self.session.query(User).count()
        user_added_last_month = self.session.query(User).filter(User.date_joined > cutoff_date).count()
        admin_count = self.session.query(User).filter(User.role == "admin").count()
        admin_added_last_month = self.session.query(User).filter(User.role == "admin", User.date_joined > cutoff_date).count()
        lecturer_count = self.session.query(User).filter(User.role == "lecturer").count()
        lecturer_added_last_month = self.session.query(User).filter(User.role == "lecturer", User.date_joined > cutoff_date).count()
        student_count = self.session.query(User).filter(User.role == "student").count()
        student_added_last_month = self.session.query(User).filter(User.role == "student", User.date_joined > cutoff_date).count()

        def perc_change(added, total):
            try:
                return added / (total - added) * 100
            except ZeroDivisionError:
                return 9999
    
        return {
            "user_count": user_count,
            "user_change_percentage": perc_change(user_added_last_month, user_count),
            "admin_count": admin_count,
            "admin_change_percentage": perc_change(admin_added_last_month, admin_count),
            "lecturer_count": lecturer_count,
            "lecturer_change_percentage": perc_change(lecturer_added_last_month, lecturer_count),
            "student_count": student_count,
            "student_change_percentage": perc_change(student_added_last_month, student_count),
        }

    def delete(self, user_id) -> bool:
        user = self.get_by_id(user_id)
        if user:
            self.session.delete(user)
            self.session.commit()
            return True
        return False
    
    
