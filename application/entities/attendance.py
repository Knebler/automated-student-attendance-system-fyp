from application.entities.base_entity import BaseEntity
from datetime import datetime, date

class Attendance(BaseEntity):
    """Attendance entity representing attendance records"""
    
    TABLE_NAME = "attendance"
    
    def __init__(self, user_id=None, date=None, status='absent', 
                 check_in_time=None, check_out_time=None, notes=None, id=None):
        self.id = id
        self.user_id = user_id
        self.date = date or datetime.now().date()
        self.status = status  # 'present', 'absent', 'late', 'excused'
        self.check_in_time = check_in_time
        self.check_out_time = check_out_time
        self.notes = notes
    
    @classmethod
    def create_table(cls, app):
        """Create attendance table if it doesn't exist"""
        query = f"""
        CREATE TABLE IF NOT EXISTS {cls.TABLE_NAME} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            date DATE NOT NULL,
            status ENUM('present', 'absent', 'late', 'excused') DEFAULT 'absent',
            check_in_time TIME,
            check_out_time TIME,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE KEY unique_attendance (user_id, date),
            INDEX idx_date (date),
            INDEX idx_user_id (user_id),
            INDEX idx_status (status)
        )
        """
        cls.execute_query(app, query)
    
    @classmethod
    def mark_attendance(cls, app, attendance_data):
        """Mark attendance for a user"""
        query = f"""
        INSERT INTO {cls.TABLE_NAME} (user_id, date, status, check_in_time, notes)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            status = VALUES(status),
            check_in_time = VALUES(check_in_time),
            notes = VALUES(notes),
            updated_at = CURRENT_TIMESTAMP
        """
        
        params = (
            attendance_data.get('user_id'),
            attendance_data.get('date', date.today()),
            attendance_data.get('status', 'present'),
            attendance_data.get('check_in_time'),
            attendance_data.get('notes')
        )
        
        cursor = cls.get_db_connection(app)
        cursor.execute(query, params)
        attendance_id = cursor.lastrowid
        cursor.close()
        cls.commit_changes(app)
        
        return attendance_id
    
    @classmethod
    def get_by_user_and_date(cls, app, user_id, date):
        """Get attendance record for a user on a specific date"""
        query = f"SELECT * FROM {cls.TABLE_NAME} WHERE user_id = %s AND date = %s"
        result = cls.execute_query(app, query, (user_id, date), fetch_one=True)
        
        if result:
            return cls.from_db_result(result)
        return None
    
    @classmethod
    def get_user_attendance(cls, app, user_id, start_date=None, end_date=None):
        """Get all attendance records for a user within a date range"""
        query = f"SELECT * FROM {cls.TABLE_NAME} WHERE user_id = %s"
        params = [user_id]
        
        if start_date and end_date:
            query += " AND date BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        elif start_date:
            query += " AND date >= %s"
            params.append(start_date)
        elif end_date:
            query += " AND date <= %s"
            params.append(end_date)
        
        query += " ORDER BY date DESC"
        
        results = cls.execute_query(app, query, tuple(params), fetch_all=True)
        return [cls.from_db_result(result) for result in results] if results else []
    
    @classmethod
    def from_db_result(cls, db_result):
        """Create Attendance object from database result"""
        return Attendance(
            id=db_result[0],
            user_id=db_result[1],
            date=db_result[2],
            status=db_result[3],
            check_in_time=db_result[4],
            check_out_time=db_result[5],
            notes=db_result[6]
        )
    
    def to_dict(self):
        """Convert attendance object to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'date': self.date.isoformat() if isinstance(self.date, date) else str(self.date),
            'status': self.status,
            'check_in_time': str(self.check_in_time) if self.check_in_time else None,
            'check_out_time': str(self.check_out_time) if self.check_out_time else None,
            'notes': self.notes
        }