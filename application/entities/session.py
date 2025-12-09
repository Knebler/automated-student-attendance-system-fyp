from application.entities.base_entity import BaseEntity
from datetime import date

class Session(BaseEntity):
    """Session entity as a SQLAlchemy model"""
    
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
            
            class SessionModel(db.Model, BaseEntity):
                """Actual SQLAlchemy model class"""
                __tablename__ = "Sessions"
                
                # Column definitions matching schema.sql
                session_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
                course_id = db.Column(db.Integer, db.ForeignKey('Courses.course_id', ondelete='CASCADE'), nullable=False)
                venue_id = db.Column(db.Integer, db.ForeignKey('Venues.venue_id', ondelete='CASCADE'), nullable=False)
                slot_id = db.Column(db.Integer, db.ForeignKey('TimeSlots.slot_id', ondelete='CASCADE'), nullable=False)
                lecturer_id = db.Column(db.Integer, db.ForeignKey('Lecturers.lecturer_id', ondelete='CASCADE'), nullable=False)
                session_date = db.Column(db.Date, nullable=False, default=date.today)
                session_topic = db.Column(db.String(255))
                status = db.Column(db.String(50), default='scheduled')
                cancellation_reason = db.Column(db.Text)
                
                # Table args with constraints and indexes
                __table_args__ = (
                    db.UniqueConstraint('venue_id', 'slot_id', 'session_date', name='unique_venue_booking'),
                    db.UniqueConstraint('course_id', 'session_date', 'slot_id', name='unique_course_session'),
                    db.Index('idx_session_course', 'course_id'),
                    db.Index('idx_session_venue', 'venue_id'),
                    db.Index('idx_session_lecturer', 'lecturer_id'),
                    db.Index('idx_session_date', 'session_date'),
                )
                
                def __init__(self, **kwargs):
                    # Set defaults
                    if 'session_date' not in kwargs:
                        kwargs['session_date'] = date.today()
                    if 'status' not in kwargs:
                        kwargs['status'] = 'scheduled'
                    super().__init__(**kwargs)
                
                def __repr__(self):
                    return f"<Session {self.session_id}: {self.session_date} - {self.session_topic}>"
                
                def to_dict(self):
                    """Convert to dictionary"""
                    return {
                        'session_id': self.session_id,
                        'course_id': self.course_id,
                        'venue_id': self.venue_id,
                        'slot_id': self.slot_id,
                        'lecturer_id': self.lecturer_id,
                        'session_date': self.session_date.isoformat() if self.session_date else None,
                        'session_topic': self.session_topic,
                        'status': self.status,
                        'cancellation_reason': self.cancellation_reason
                    }
                
                @classmethod
                def get_today_sessions(cls, app, lecturer_id=None, course_id=None):
                    """Get sessions for today"""
                    session = BaseEntity.get_db_session(app)
                    query = session.query(cls).filter(cls.session_date == date.today())
                    
                    if lecturer_id:
                        query = query.filter_by(lecturer_id=lecturer_id)
                    
                    if course_id:
                        query = query.filter_by(course_id=course_id)
                    
                    return query.all()

                @classmethod
                def get_all_sessions(cls, app, lecturer_id=None, course_id=None, start_date=None, end_date=None):
                    """Get all sessions (optionally within a date range).

                    By default this will return sessions up to today (end_date defaults to today)
                    so admins can view historical sessions.
                    """
                    session = BaseEntity.get_db_session(app)
                    query = session.query(cls)

                    # apply optional date range
                    if start_date:
                        query = query.filter(cls.session_date >= start_date)

                    if end_date:
                        query = query.filter(cls.session_date <= end_date)
                    else:
                        # Default: sessions up to today
                        query = query.filter(cls.session_date <= date.today())

                    if lecturer_id:
                        query = query.filter_by(lecturer_id=lecturer_id)

                    if course_id:
                        query = query.filter_by(course_id=course_id)

                    query = query.order_by(cls.session_date.desc(), cls.slot_id.asc())
                    return query.all()
                
                @classmethod
                def get_by_course(cls, app, course_id, start_date=None, end_date=None):
                    """Get all sessions for a course within a date range"""
                    session = BaseEntity.get_db_session(app)
                    query = session.query(cls).filter_by(course_id=course_id)
                    
                    if start_date:
                        query = query.filter(cls.session_date >= start_date)
                    
                    if end_date:
                        query = query.filter(cls.session_date <= end_date)
                    
                    query = query.order_by(cls.session_date.asc(), cls.slot_id.asc())
                    return query.all()
                
                @classmethod
                def get_by_lecturer(cls, app, lecturer_id, start_date=None, end_date=None):
                    """Get all sessions for a lecturer within a date range"""
                    session = BaseEntity.get_db_session(app)
                    query = session.query(cls).filter_by(lecturer_id=lecturer_id)
                    
                    if start_date:
                        query = query.filter(cls.session_date >= start_date)
                    
                    if end_date:
                        query = query.filter(cls.session_date <= end_date)
                    
                    query = query.order_by(cls.session_date.asc(), cls.slot_id.asc())
                    return query.all()
            
            cls._model_class = SessionModel
        
        return cls._model_class
    
    # Forward methods to the actual model
    @classmethod
    def get_today_sessions(cls, app, lecturer_id=None, course_id=None):
        """Get sessions for today"""
        return cls.get_model().get_today_sessions(app, lecturer_id, course_id)

    @classmethod
    def get_all_sessions(cls, app, lecturer_id=None, course_id=None, start_date=None, end_date=None):
        """Get all sessions (forward to model implementation)

        Defaults to returning sessions up to today when no end_date provided.
        """
        return cls.get_model().get_all_sessions(app, lecturer_id, course_id, start_date, end_date)
    
    @classmethod
    def get_by_course(cls, app, course_id, start_date=None, end_date=None):
        """Get all sessions for a course within a date range"""
        return cls.get_model().get_by_course(app, course_id, start_date, end_date)
    
    @classmethod
    def get_by_lecturer(cls, app, lecturer_id, start_date=None, end_date=None):
        """Get all sessions for a lecturer within a date range"""
        return cls.get_model().get_by_lecturer(app, lecturer_id, start_date, end_date)
    
    @classmethod
    def from_db_result(cls, result_tuple):
        """Backward compatibility method - convert tuple result to model instance"""
        if not result_tuple:
            return None
        
        # If it's already a model instance
        if hasattr(result_tuple, 'session_id'):
            return result_tuple
        
        # If it's a tuple from raw SQL
        model_class = cls.get_model()
        return model_class(
            session_id=result_tuple[0],
            course_id=result_tuple[1],
            venue_id=result_tuple[2],
            slot_id=result_tuple[3],
            lecturer_id=result_tuple[4],
            session_date=result_tuple[5] if len(result_tuple) > 5 else date.today(),
            session_topic=result_tuple[6] if len(result_tuple) > 6 else None,
            status=result_tuple[7] if len(result_tuple) > 7 else 'scheduled',
            cancellation_reason=result_tuple[8] if len(result_tuple) > 8 else None
        )
    
    @classmethod
    def create_table(cls, app):
        """Create sessions table - compatibility method for older code"""
        # With SQLAlchemy, tables are usually created via db.create_all()
        # This method is kept for compatibility but does nothing
        # as SQLAlchemy handles table creation
        pass