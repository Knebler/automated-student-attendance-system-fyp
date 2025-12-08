from application.entities.base_entity import BaseEntity

class Lecturer(BaseEntity):
    """Lecturer entity as a SQLAlchemy model"""
    
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
            
            class LecturerModel(db.Model, BaseEntity):
                """Actual SQLAlchemy model class"""
                __tablename__ = "Lecturers"
                
                # Column definitions matching schema.sql
                lecturer_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
                institution_id = db.Column(
                    db.Integer, 
                    db.ForeignKey('Institutions.institution_id', ondelete='CASCADE'), 
                    nullable=False
                )
                email = db.Column(db.String(255), nullable=False)
                password_hash = db.Column(db.String(255), nullable=False)
                full_name = db.Column(db.String(100), nullable=False)
                department = db.Column(db.String(100))
                is_active = db.Column(db.Boolean, default=True)
                
                # Unique constraints
                __table_args__ = (
                    db.UniqueConstraint('institution_id', 'email', name='unique_lecturer_email'),
                    db.Index('idx_lecturer_institution', 'institution_id'),
                )
                
                def __repr__(self):
                    return f"<Lecturer {self.email}: {self.full_name}>"
                
                def to_dict(self):
                    """Convert to dictionary"""
                    return {
                        'lecturer_id': self.lecturer_id,
                        'institution_id': self.institution_id,
                        'email': self.email,
                        'full_name': self.full_name,
                        'department': self.department,
                        'is_active': self.is_active
                    }
                
                @classmethod
                def get_by_institution(cls, app, institution_id, active_only=True):
                    """Get all lecturers for an institution"""
                    filters = {'institution_id': institution_id}
                    if active_only:
                        filters['is_active'] = True
                    
                    return BaseEntity.get_all(app, cls, filters=filters) or []
                
                @classmethod
                def get_by_email(cls, app, email, institution_id=None):
                    """Get lecturer by email"""
                    try:
                        session = BaseEntity.get_db_session(app)
                        query = session.query(cls).filter_by(email=email)
                        
                        if institution_id:
                            query = query.filter_by(institution_id=institution_id)
                        
                        return query.first()
                    except Exception as e:
                        app.logger.error(f"Error getting lecturer by email: {e}")
                        return None
                
                @classmethod
                def search_lecturers(cls, app, institution_id, search_term=None):
                    """Search lecturers by name, email, or department"""
                    try:
                        session = BaseEntity.get_db_session(app)
                        query = session.query(cls).filter_by(
                            institution_id=institution_id,
                            is_active=True
                        )
                        
                        if search_term:
                            import sqlalchemy as sa
                            query = query.filter(
                                sa.or_(
                                    cls.full_name.ilike(f"%{search_term}%"),
                                    cls.email.ilike(f"%{search_term}%"),
                                    cls.department.ilike(f"%{search_term}%")
                                )
                            )
                        
                        return query.all()
                    except Exception as e:
                        app.logger.error(f"Error searching lecturers: {e}")
                        return []
            
            cls._model_class = LecturerModel
        
        return cls._model_class
    
    # Forward methods to the actual model
    @classmethod
    def get_by_institution(cls, app, institution_id, active_only=True):
        """Get all lecturers for an institution"""
        return cls.get_model().get_by_institution(app, institution_id, active_only)
    
    @classmethod
    def get_by_email(cls, app, email, institution_id=None):
        """Get lecturer by email"""
        return cls.get_model().get_by_email(app, email, institution_id)
    
    @classmethod
    def get_by_id(cls, app, lecturer_id):
        """Get lecturer by ID"""
        try:
            model = cls.get_model()
            return BaseEntity.get_by_id(app, model, lecturer_id)
        except Exception as e:
            app.logger.error(f"Error getting lecturer by ID: {e}")
            return None
    
    @classmethod
    def create_lecturer(cls, app, lecturer_data):
        """Create a new lecturer"""
        try:
            model = cls.get_model()
            return BaseEntity.create(app, model, lecturer_data)
        except Exception as e:
            app.logger.error(f"Error creating lecturer: {e}")
            BaseEntity.rollback_changes(app)
            return None
    
    @classmethod
    def update_lecturer(cls, app, lecturer_id, update_data):
        """Update lecturer information"""
        try:
            model = cls.get_model()
            return BaseEntity.update(app, model, lecturer_id, update_data)
        except Exception as e:
            app.logger.error(f"Error updating lecturer: {e}")
            BaseEntity.rollback_changes(app)
            return None
    
    @classmethod
    def deactivate_lecturer(cls, app, lecturer_id):
        """Deactivate a lecturer (soft delete)"""
        return cls.update_lecturer(app, lecturer_id, {'is_active': False})
    
    @classmethod
    def search_lecturers(cls, app, institution_id, search_term=None):
        """Search lecturers by name, email, or department"""
        return cls.get_model().search_lecturers(app, institution_id, search_term)
    
    @classmethod
    def from_db_result(cls, result_tuple):
        """Backward compatibility method"""
        if not result_tuple:
            return None
        
        # If it's already a model instance
        if hasattr(result_tuple, 'lecturer_id'):
            return result_tuple
        
        # If it's a tuple from raw SQL
        return cls.get_model()(
            lecturer_id=result_tuple[0],
            institution_id=result_tuple[1],
            email=result_tuple[2],
            password_hash=result_tuple[3] if len(result_tuple) > 3 else None,
            full_name=result_tuple[4] if len(result_tuple) > 4 else None,
            department=result_tuple[5] if len(result_tuple) > 5 else None,
            is_active=bool(result_tuple[6]) if len(result_tuple) > 6 else True
        )
    
    @classmethod
    def create_table(cls, app):
        """Create lecturers table (for backward compatibility)"""
        query = """
        CREATE TABLE IF NOT EXISTS Lecturers (
            lecturer_id INT PRIMARY KEY AUTO_INCREMENT,
            institution_id INT NOT NULL,
            email VARCHAR(255) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(100) NOT NULL,
            department VARCHAR(100),
            is_active BOOLEAN DEFAULT TRUE,
            UNIQUE KEY unique_lecturer_email (institution_id, email),
            INDEX idx_lecturer_institution (institution_id)
        )
        """
        cls.execute_query(app, query)