from application.entities.base_entity import BaseEntity
from datetime import datetime

class AttendanceRecord(BaseEntity):
    """Attendance Record entity as a SQLAlchemy model"""
    
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
            
            class AttendanceRecordModel(db.Model, BaseEntity):
                """Actual SQLAlchemy model class matching Attendance_Records table"""
                __tablename__ = "Attendance_Records"
                
                # Column definitions matching schema.sql
                attendance_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
                session_id = db.Column(
                    db.Integer, 
                    db.ForeignKey('Sessions.session_id', ondelete='CASCADE'), 
                    nullable=False
                )
                student_id = db.Column(
                    db.Integer, 
                    db.ForeignKey('Students.student_id', ondelete='CASCADE'), 
                    nullable=False
                )
                status = db.Column(
                    db.Enum('present', 'absent', 'late', 'excused'), 
                    default='absent'
                )
                marked_by = db.Column(
                    db.Enum('system', 'lecturer'), 
                    nullable=False
                )
                lecturer_id = db.Column(
                    db.Integer, 
                    db.ForeignKey('Lecturers.lecturer_id')
                )
                captured_image_path = db.Column(db.String(500))
                attendance_time = db.Column(db.Time)
                notes = db.Column(db.Text)
                recorded_at = db.Column(
                    db.DateTime, 
                    default=db.func.current_timestamp()
                )
                
                # Relationships
                session = db.relationship('Session', backref='attendance_records')
                student = db.relationship('Student', backref='attendance_records')
                lecturer = db.relationship('Lecturer', backref='marked_attendance')
                
                # Unique constraints
                __table_args__ = (
                    db.UniqueConstraint('session_id', 'student_id', name='unique_session_attendance'),
                    db.Index('idx_attendance_session', 'session_id'),
                    db.Index('idx_attendance_student', 'student_id'),
                    db.Index('idx_attendance_lecturer', 'lecturer_id'),
                    db.Index('idx_attendance_recorded', 'recorded_at'),
                )
                
                def __repr__(self):
                    return f"<AttendanceRecord session:{self.session_id} student:{self.student_id} status:{self.status}>"
                
                def to_dict(self):
                    """Convert to dictionary"""
                    return {
                        'attendance_id': self.attendance_id,
                        'session_id': self.session_id,
                        'student_id': self.student_id,
                        'status': self.status,
                        'marked_by': self.marked_by,
                        'lecturer_id': self.lecturer_id,
                        'captured_image_path': self.captured_image_path,
                        'attendance_time': str(self.attendance_time) if self.attendance_time else None,
                        'notes': self.notes,
                        'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None
                    }
                
                @classmethod
                def get_by_session_and_student(cls, app, session_id, student_id):
                    """Get attendance record for specific session and student"""
                    try:
                        session = BaseEntity.get_db_session(app)
                        record = session.query(cls).filter_by(
                            session_id=session_id,
                            student_id=student_id
                        ).first()
                        return record
                    except Exception as e:
                        app.logger.error(f"Error getting attendance by session and student: {e}")
                        return None
                
                @classmethod
                def get_by_session(cls, app, session_id):
                    """Get all attendance records for a session"""
                    try:
                        filters = {'session_id': session_id}
                        return BaseEntity.get_all(app, cls, filters=filters) or []
                    except Exception as e:
                        app.logger.error(f"Error getting attendance by session: {e}")
                        return []
                
                @classmethod
                def get_by_student(cls, app, student_id, start_date=None, end_date=None):
                    """Get attendance records for a student within date range"""
                    try:
                        from sqlalchemy import and_
                        
                        session = BaseEntity.get_db_session(app)
                        query = session.query(cls).join(
                            'session'  # Join with Session table via relationship
                        ).filter(
                            cls.student_id == student_id
                        )
                        
                        if start_date:
                            query = query.filter(cls.session.has(session_date=start_date))
                        if end_date:
                            query = query.filter(cls.session.has(session_date=end_date))
                        
                        return query.all()
                    except Exception as e:
                        app.logger.error(f"Error getting attendance by student: {e}")
                        return []
                
                @classmethod
                def mark_attendance(cls, app, attendance_data):
                    """Mark attendance for a session and student"""
                    try:
                        return BaseEntity.create(app, cls, attendance_data)
                    except Exception as e:
                        app.logger.error(f"Error marking attendance: {e}")
                        BaseEntity.rollback_changes(app)
                        return None
                
                @classmethod
                def update_attendance(cls, app, attendance_id, update_data):
                    """Update attendance record"""
                    try:
                        return BaseEntity.update(app, cls, attendance_id, update_data)
                    except Exception as e:
                        app.logger.error(f"Error updating attendance: {e}")
                        BaseEntity.rollback_changes(app)
                        return None
            
            cls._model_class = AttendanceRecordModel
        
        return cls._model_class
    
    # Forward methods to the actual model
    @classmethod
    def get_by_session_and_student(cls, app, session_id, student_id):
        """Get attendance record for specific session and student"""
        return cls.get_model().get_by_session_and_student(app, session_id, student_id)
    
    @classmethod
    def get_by_session(cls, app, session_id):
        """Get all attendance records for a session"""
        return cls.get_model().get_by_session(app, session_id)
    
    @classmethod
    def get_by_student(cls, app, student_id, start_date=None, end_date=None):
        """Get attendance records for a student within date range"""
        return cls.get_model().get_by_student(app, student_id, start_date, end_date)
    
    @classmethod
    def mark_attendance(cls, app, attendance_data):
        """Mark attendance for a session and student"""
        return cls.get_model().mark_attendance(app, attendance_data)
    
    @classmethod
    def update_attendance(cls, app, attendance_id, update_data):
        """Update attendance record"""
        return cls.get_model().update_attendance(app, attendance_id, update_data)
    
    @classmethod
    def get_by_id(cls, app, attendance_id):
        """Get attendance record by ID"""
        try:
            model = cls.get_model()
            return BaseEntity.get_by_id(app, model, attendance_id)
        except Exception as e:
            app.logger.error(f"Error getting attendance by ID: {e}")
            return None
    
    @classmethod
    def from_db_result(cls, result_tuple):
        """Backward compatibility method"""
        if not result_tuple:
            return None
        
        # If it's already a model instance
        if hasattr(result_tuple, 'attendance_id'):
            return result_tuple
        
        # If it's a tuple from raw SQL
        return cls.get_model()(
            attendance_id=result_tuple[0],
            session_id=result_tuple[1],
            student_id=result_tuple[2],
            status=result_tuple[3],
            marked_by=result_tuple[4],
            lecturer_id=result_tuple[5] if len(result_tuple) > 5 else None,
            captured_image_path=result_tuple[6] if len(result_tuple) > 6 else None,
            attendance_time=result_tuple[7] if len(result_tuple) > 7 else None,
            notes=result_tuple[8] if len(result_tuple) > 8 else None,
            recorded_at=result_tuple[9] if len(result_tuple) > 9 else None
        )
    
    @classmethod
    def create_table(cls, app):
        """Create attendance records table (for backward compatibility)"""
        query = """
        CREATE TABLE IF NOT EXISTS Attendance_Records (
            attendance_id INT PRIMARY KEY AUTO_INCREMENT,
            session_id INT NOT NULL,
            student_id INT NOT NULL,
            status ENUM('present', 'absent', 'late', 'excused') DEFAULT 'absent',
            marked_by ENUM('system', 'lecturer') NOT NULL,
            lecturer_id INT NULL,
            captured_image_path VARCHAR(500) NULL,
            attendance_time TIME NULL,
            notes TEXT,
            recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES Sessions(session_id) ON DELETE CASCADE,
            FOREIGN KEY (student_id) REFERENCES Students(student_id) ON DELETE CASCADE,
            FOREIGN KEY (lecturer_id) REFERENCES Lecturers(lecturer_id),
            UNIQUE KEY unique_session_attendance (session_id, student_id),
            INDEX idx_attendance_session (session_id),
            INDEX idx_attendance_student (student_id),
            INDEX idx_attendance_lecturer (lecturer_id),
            INDEX idx_attendance_recorded (recorded_at)
        )
        """
        cls.execute_query(app, query)