from application.entities.base_entity import BaseEntity

class InstitutionAdmin(BaseEntity):
    """InstitutionAdmin entity as a SQLAlchemy model"""
    
    @classmethod
    def _get_db(cls):
        """Helper method to get SQLAlchemy instance from app"""
        from flask import current_app
        return current_app.config.get('db')
    
    @classmethod
    def get_model(cls):
        """Return the SQLAlchemy model class"""
        db = cls._get_db()
        
        if not hasattr(cls, '_model_class'):
            
            class InstitutionAdminModel(db.Model, BaseEntity):
                """Actual SQLAlchemy model class"""
                __tablename__ = "Institution_Admins"
                
                # Column definitions matching schema.sql
                inst_admin_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
                email = db.Column(db.String(255), nullable=False)
                password_hash = db.Column(db.String(255), nullable=False)
                full_name = db.Column(db.String(100), nullable=False)
                institution_id = db.Column(
                    db.Integer, 
                    db.ForeignKey('Institutions.institution_id', ondelete='CASCADE'), 
                    nullable=False
                )
                created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
                
                # Unique constraints
                __table_args__ = (
                    db.UniqueConstraint('institution_id', 'email', name='unique_institution_email'),
                    db.Index('idx_institution_admin', 'institution_id'),
                )
                
                def __repr__(self):
                    return f"<InstitutionAdmin {self.email}: {self.full_name}>"
                
                def to_dict(self):
                    """Convert to dictionary"""
                    return {
                        'inst_admin_id': self.inst_admin_id,
                        'email': self.email,
                        'full_name': self.full_name,
                        'institution_id': self.institution_id,
                        'created_at': self.created_at
                    }
                
                @classmethod
                def get_by_institution(cls, app, institution_id):
                    """Get all admins for an institution"""
                    filters = {'institution_id': institution_id}
                    return BaseEntity.get_all(app, cls, filters=filters) or []
                
                @classmethod
                def get_by_email(cls, app, email, institution_id=None):
                    """Get admin by email"""
                    try:
                        session = BaseEntity.get_db_session(app)
                        query = session.query(cls).filter_by(email=email)
                        
                        if institution_id:
                            query = query.filter_by(institution_id=institution_id)
                        
                        return query.first()
                    except Exception as e:
                        app.logger.error(f"Error getting institution admin by email: {e}")
                        return None
            
            cls._model_class = InstitutionAdminModel
        
        return cls._model_class
    
    # Forward methods to the actual model
    @classmethod
    def get_by_institution(cls, app, institution_id):
        return cls.get_model().get_by_institution(app, institution_id)
    
    @classmethod
    def get_by_email(cls, app, email, institution_id=None):
        return cls.get_model().get_by_email(app, email, institution_id)
    
    @classmethod
    def get_by_id(cls, app, admin_id):
        """Get admin by ID"""
        try:
            model = cls.get_model()
            return BaseEntity.get_by_id(app, model, admin_id)
        except Exception as e:
            app.logger.error(f"Error getting institution admin by ID: {e}")
            return None
    
    @classmethod
    def create_admin(cls, app, admin_data):
        """Create a new institution admin"""
        try:
            model = cls.get_model()
            return BaseEntity.create(app, model, admin_data)
        except Exception as e:
            app.logger.error(f"Error creating institution admin: {e}")
            BaseEntity.rollback_changes(app)
            return None
    
    @classmethod
    def from_db_result(cls, result_tuple):
        """Backward compatibility method"""
        if not result_tuple:
            return None
        
        if hasattr(result_tuple, 'inst_admin_id'):
            return result_tuple
        
        # If it's a tuple from raw SQL
        return cls.get_model()(
            inst_admin_id=result_tuple[0],
            email=result_tuple[1],
            password_hash=result_tuple[2],
            full_name=result_tuple[3],
            institution_id=result_tuple[4],
            created_at=result_tuple[5] if len(result_tuple) > 5 else None
        )