from datetime import datetime
from flask import current_app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

class BaseEntity:
    """Base entity class providing common database operations using SQLAlchemy"""
    
    @staticmethod
    def get_db_session(app):
        """Get database session from app context"""
        db = app.config['db']  # SQLAlchemy instance
        return db.session
    
    @staticmethod
    def commit_changes(app):
        """Commit database changes"""
        db = app.config['db']
        db.session.commit()
    
    @staticmethod
    def rollback_changes(app):
        """Rollback database changes"""
        db = app.config['db']
        db.session.rollback()
    
    @staticmethod
    def execute_raw_query(app, query, params=None, fetch_one=False, fetch_all=False):
        """Execute raw SQL query with parameters"""
        session = BaseEntity.get_db_session(app)
        
        # Use SQLAlchemy's text() for raw SQL
        if params:
            result = session.execute(text(query), params)
        else:
            result = session.execute(text(query))
        
        if fetch_one:
            return result.fetchone()
        elif fetch_all:
            return result.fetchall()
        else:
            session.commit()
            return result.rowcount
    
    @staticmethod
    def get_all(app, model_class, filters=None, order_by=None, limit=None):
        """Get all records for a model class"""
        session = BaseEntity.get_db_session(app)
        query = session.query(model_class)
        
        if filters:
            query = query.filter_by(**filters)
        
        if order_by:
            query = query.order_by(order_by)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @staticmethod
    def get_by_id(app, model_class, id):
        """Get record by ID"""
        session = BaseEntity.get_db_session(app)
        return session.query(model_class).get(id)
    
    @staticmethod
    def create(app, model_class, data):
        """Create a new record"""
        session = BaseEntity.get_db_session(app)
        
        # Create instance of the model
        if isinstance(data, dict):
            instance = model_class(**data)
        else:
            instance = data
        
        session.add(instance)
        session.flush()  # Flush to get the ID
        session.commit()
        
        return instance
    
    @staticmethod
    def update(app, model_class, id, data):
        """Update an existing record"""
        session = BaseEntity.get_db_session(app)
        instance = session.query(model_class).get(id)
        
        if not instance:
            return None
        
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        
        session.commit()
        return instance
    
    @staticmethod
    def delete(app, model_class, id):
        """Delete a record"""
        session = BaseEntity.get_db_session(app)
        instance = session.query(model_class).get(id)
        
        if instance:
            session.delete(instance)
            session.commit()
            return True
        
        return False
    
    @staticmethod
    def count(app, model_class, filters=None):
        """Count records"""
        session = BaseEntity.get_db_session(app)
        query = session.query(model_class)
        
        if filters:
            query = query.filter_by(**filters)
        
        return query.count()
    
    @staticmethod
    def exists(app, model_class, filters):
        """Check if record exists based on filters"""
        return BaseEntity.count(app, model_class, filters) > 0