from application.entities.base_entity import BaseEntity
from datetime import date

class Session(BaseEntity):
    """Session entity for class sessions"""
    
    TABLE_NAME = "Sessions"
    
    def __init__(self, session_id=None, course_id=None, venue_id=None,
                 slot_id=None, lecturer_id=None, session_date=None,
                 session_topic=None, status='scheduled', cancellation_reason=None):
        self.session_id = session_id
        self.course_id = course_id
        self.venue_id = venue_id
        self.slot_id = slot_id
        self.lecturer_id = lecturer_id
        self.session_date = session_date or date.today()
        self.session_topic = session_topic
        self.status = status
        self.cancellation_reason = cancellation_reason
    
    @classmethod
    def create_table(cls, app):
        """Create sessions table"""
        query = f"""
        CREATE TABLE IF NOT EXISTS {cls.TABLE_NAME} (
            session_id INT PRIMARY KEY AUTO_INCREMENT,
            course_id INT NOT NULL,
            venue_id INT NOT NULL,
            slot_id INT NOT NULL,
            lecturer_id INT NOT NULL,
            session_date DATE NOT NULL,
            session_topic VARCHAR(255),
            status ENUM('scheduled', 'completed', 'cancelled', 'rescheduled') DEFAULT 'scheduled',
            cancellation_reason TEXT,
            UNIQUE KEY unique_venue_booking (venue_id, slot_id, session_date),
            UNIQUE KEY unique_course_session (course_id, session_date, slot_id),
            INDEX idx_session_course (course_id),
            INDEX idx_session_venue (venue_id),
            INDEX idx_session_lecturer (lecturer_id),
            INDEX idx_session_date (session_date)
        )
        """
        cls.execute_query(app, query)
    
    @classmethod
    def get_today_sessions(cls, app, lecturer_id=None, course_id=None):
        """Get sessions for today"""
        query = f"SELECT * FROM {cls.TABLE_NAME} WHERE session_date = CURDATE()"
        params = []
        
        if lecturer_id:
            query += " AND lecturer_id = %s"
            params.append(lecturer_id)
        
        if course_id:
            query += " AND course_id = %s"
            params.append(course_id)
        
        results = cls.execute_query(app, query, tuple(params) if params else None, fetch_all=True)
        return [cls.from_db_result(result) for result in results] if results else []