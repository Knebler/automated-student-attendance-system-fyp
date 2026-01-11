from .base_entity import BaseEntity
from database.models import User

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
    
    def delete(self, user_id) -> bool:
        user = self.get_by_id(user_id)
        if user:
            self.session.delete(user)
            self.session.commit()
            return True
        return False
    
    
