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

    # Compatibility wrapper used by older entity modules
    @staticmethod
    def execute_query(app, query, params=None, fetch_one=False, fetch_all=False):
        """Compatibility wrapper - delegates to execute_raw_query but accepts
        tuple/list params the older code uses.
        """
        # If params is a tuple/list convert to dict expected by SQLAlchemy text
        # We will pass params through directly; SQLAlchemy supports positional
        # style parameters only with certain drivers, but our helper also
        # supports raw DBAPI cursors via get_db_connection for legacy code.
        return BaseEntity.execute_raw_query(app, query, params, fetch_one=fetch_one, fetch_all=fetch_all)
    
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

    @staticmethod
    def get_db_connection(app):
        """Return a DB-API like cursor for compatibility with older entity code.

        - If a mysql connector is configured at app.config['mysql'], return
          its cursor directly.
        - If SQLAlchemy is available at app.config['db'], return a small
          wrapper that mimics a cursor for execute/fetchone/fetchall and
          exposes lastrowid. The wrapper does not auto-commit; callers
          should call BaseEntity.commit_changes(app) when needed.
        """
        # If a raw mysql connector exists, return a DBAPI cursor
        mysql = app.config.get('mysql')
        if mysql is not None:
            try:
                return mysql.connection.cursor()
            except Exception:
                # fall through to SQLAlchemy cursor
                pass

        # Use SQLAlchemy session as a lightweight cursor-wrapper
        db = app.config.get('db')
        if db is None:
            raise RuntimeError('No database configured')

        session = db.session

        class _SA_Cursor:
            def __init__(self, session):
                self._session = session
                self._last_result = None
                self.lastrowid = None

            def execute(self, sql, params=None):
                # Keep last result to support fetchone/fetchall
                from sqlalchemy import text
                if params is None:
                    self._last_result = self._session.execute(text(sql))
                else:
                    try:
                        self._last_result = self._session.execute(text(sql), params)
                    except Exception:
                        # try positional parameter style
                        self._last_result = self._session.execute(text(sql), params)

                # Try to extract lastrowid if present
                try:
                    self.lastrowid = getattr(self._last_result, 'lastrowid', None)
                except Exception:
                    self.lastrowid = None

            def fetchone(self):
                if not self._last_result:
                    return None
                return self._last_result.fetchone()

            def fetchall(self):
                if not self._last_result:
                    return []
                return self._last_result.fetchall()

            def close(self):
                # no-op for SQLAlchemy session-based wrapper
                return None

        return _SA_Cursor(session)