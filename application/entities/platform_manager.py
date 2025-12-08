from application.entities.base_entity import BaseEntity

class PlatformManager(BaseEntity):
    """Platform Manager entity as a SQLAlchemy model"""
    
    # We need to get the db instance from the app
    @classmethod
    def _get_db(cls):
        """Helper method to get SQLAlchemy instance from app"""
        from flask import current_app
        return current_app.config.get('db')
    
    # Define as SQLAlchemy model dynamically
    @classmethod
    def get_model(cls):
        """Return the SQLAlchemy model class"""
        db = cls._get_db()
        
        # Define the model class (only once)
        if not hasattr(cls, '_model_class'):
            
            class PlatformManagerModel(db.Model, BaseEntity):
                """Actual SQLAlchemy model class"""
                __tablename__ = "Platform_Managers"
                
                # Column definitions matching schema.sql
                platform_mgr_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
                email = db.Column(db.String(255), unique=True, nullable=False)
                password_hash = db.Column(db.String(255), nullable=False)
                full_name = db.Column(db.String(100), nullable=False)
                created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
                
                def __repr__(self):
                    return f"<PlatformManager {self.email}: {self.full_name}>"
                
                def to_dict(self):
                    """Convert to dictionary"""
                    return {
                        'platform_mgr_id': self.platform_mgr_id,
                        'email': self.email,
                        'full_name': self.full_name,
                        'created_at': self.created_at
                    }
                
                @classmethod
                def get_by_email(cls, app, email):
                    """Get platform manager by email using ORM"""
                    try:
                        session = BaseEntity.get_db_session(app)
                        manager = session.query(cls).filter_by(email=email).first()
                        return manager
                    except Exception as e:
                        app.logger.error(f"Error getting platform manager by email: {e}")
                        return None
                
                @classmethod
                def get_all_managers(cls, app):
                    """Get all platform managers"""
                    try:
                        return BaseEntity.get_all(app, cls) or []
                    except Exception as e:
                        app.logger.error(f"Error getting all platform managers: {e}")
                        return []
            
            cls._model_class = PlatformManagerModel
        
        return cls._model_class
    
    # Forward methods to the actual model
    @classmethod
    def get_by_email(cls, app, email):
        """Get platform manager by email"""
        return cls.get_model().get_by_email(app, email)
    
    @classmethod
    def get_by_id(cls, app, manager_id):
        """Get platform manager by ID"""
        try:
            model = cls.get_model()
            return BaseEntity.get_by_id(app, model, manager_id)
        except Exception as e:
            app.logger.error(f"Error getting platform manager by ID: {e}")
            return None
    
    @classmethod
    def get_all_managers(cls, app):
        """Get all platform managers"""
        return cls.get_model().get_all_managers(app)
    
    @classmethod
    def create_manager(cls, app, manager_data):
        """Create a new platform manager"""
        try:
            model = cls.get_model()
            return BaseEntity.create(app, model, manager_data)
        except Exception as e:
            app.logger.error(f"Error creating platform manager: {e}")
            BaseEntity.rollback_changes(app)
            return None
    
    @classmethod
    def update_manager(cls, app, manager_id, update_data):
        """Update platform manager information"""
        try:
            model = cls.get_model()
            return BaseEntity.update(app, model, manager_id, update_data)
        except Exception as e:
            app.logger.error(f"Error updating platform manager: {e}")
            BaseEntity.rollback_changes(app)
            return None
    
    @classmethod
    def from_db_result(cls, result_tuple):
        """Backward compatibility method"""
        if not result_tuple:
            return None
        
        # If it's already a model instance
        if hasattr(result_tuple, 'platform_mgr_id'):
            return result_tuple
        
        # If it's a tuple from raw SQL
        return cls.get_model()(
            platform_mgr_id=result_tuple[0],
            email=result_tuple[1],
            password_hash=result_tuple[2],
            full_name=result_tuple[3],
            created_at=result_tuple[4] if len(result_tuple) > 4 else None
        )
    
    @classmethod
    def create_table(cls, app):
        """Create platform managers table (for backward compatibility)"""
        query = """
        CREATE TABLE IF NOT EXISTS Platform_Managers (
            platform_mgr_id INT PRIMARY KEY AUTO_INCREMENT,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(100) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        cls.execute_query(app, query)