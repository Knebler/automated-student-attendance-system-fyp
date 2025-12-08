# student.py
from application.entities.base_entity import BaseEntity

class Student(BaseEntity):
    """Student entity as a SQLAlchemy model"""
    
    # We need to get the db instance from the app
    @classmethod
    def _get_db(cls):
        """Helper method to get SQLAlchemy instance from app"""
        from flask import current_app
        return current_app.config.get('db')
    
    # Dynamically get db instance
    @property
    def db(self):
        return self._get_db()
    
    # Define as SQLAlchemy model dynamically
    @classmethod
    def get_model(cls):
        """Return the SQLAlchemy model class"""
        db = cls._get_db()
        
        # Define the model class (only once)
        if not hasattr(cls, '_model_class'):
            
            class StudentModel(db.Model, BaseEntity):
                """Actual SQLAlchemy model class"""
                __tablename__ = "Students"
                
                # Column definitions matching schema.sql
                student_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
                institution_id = db.Column(
                    db.Integer, 
                    db.ForeignKey('Institutions.institution_id', ondelete='CASCADE'), 
                    nullable=False
                )
                student_code = db.Column(db.String(50), nullable=False)
                email = db.Column(db.String(255), nullable=False)
                password_hash = db.Column(db.String(255), nullable=False)
                full_name = db.Column(db.String(100), nullable=False)
                enrollment_year = db.Column(db.Integer)
                is_active = db.Column(db.Boolean, default=True)
                
                # Unique constraints
                __table_args__ = (
                    db.UniqueConstraint('institution_id', 'student_code', name='unique_student_code'),
                    db.UniqueConstraint('institution_id', 'email', name='unique_student_email'),
                    db.Index('idx_student_institution', 'institution_id'),
                )
                
                def __repr__(self):
                    return f"<Student {self.student_code}: {self.full_name}>"
                
                def to_dict(self):
                    """Convert to dictionary"""
                    return {
                        'student_id': self.student_id,
                        'institution_id': self.institution_id,
                        'student_code': self.student_code,
                        'email': self.email,
                        'full_name': self.full_name,
                        'enrollment_year': self.enrollment_year,
                        'is_active': self.is_active
                    }
                
                @classmethod
                def get_by_institution(cls, app, institution_id, active_only=True):
                    """Get all students for an institution"""
                    filters = {'institution_id': institution_id}
                    if active_only:
                        filters['is_active'] = True
                    
                    return BaseEntity.get_all(app, cls, filters=filters) or []
            
            cls._model_class = StudentModel
        
        return cls._model_class
    
    # Forward methods to the actual model
    @classmethod
    def get_by_institution(cls, app, institution_id, active_only=True):
        """Get all students for an institution"""
        return cls.get_model().get_by_institution(app, institution_id, active_only)
    
    @classmethod
    def get_by_email(cls, app, email, institution_id=None):
        """Get student by email"""
        try:
            model = cls.get_model()
            session = BaseEntity.get_db_session(app)
            query = session.query(model).filter_by(email=email)
            
            if institution_id:
                query = query.filter_by(institution_id=institution_id)
            
            return query.first()
        except Exception as e:
            app.logger.error(f"Error getting student by email: {e}")
            return None
    
    @classmethod
    def from_db_result(cls, result_tuple):
        """Backward compatibility method"""
        if not result_tuple:
            return None
        
        # If it's already a model instance
        if hasattr(result_tuple, 'student_id'):
            return result_tuple
        
        # If it's a tuple from raw SQL
        return cls.get_model()(
            student_id=result_tuple[0],
            institution_id=result_tuple[1],
            student_code=result_tuple[2],
            email=result_tuple[3],
            password_hash=result_tuple[4] if len(result_tuple) > 4 else None,
            full_name=result_tuple[5] if len(result_tuple) > 5 else None,
            enrollment_year=result_tuple[6] if len(result_tuple) > 6 else None,
            is_active=bool(result_tuple[7]) if len(result_tuple) > 7 else True
        )