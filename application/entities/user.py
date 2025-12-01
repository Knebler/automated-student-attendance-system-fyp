from application.entities.base_entity import BaseEntity
from datetime import datetime

class User(BaseEntity):
    """User entity representing users in the system"""
    
    TABLE_NAME = "users"
    
    def __init__(self, firebase_uid=None, email=None, name=None, 
                 role='student', created_at=None, updated_at=None, id=None):
        self.id = id
        self.firebase_uid = firebase_uid
        self.email = email
        self.name = name
        self.role = role
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
    
    @classmethod
    def create_table(cls, app):
        """Create users table if it doesn't exist"""
        query = f"""
        CREATE TABLE IF NOT EXISTS {cls.TABLE_NAME} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            firebase_uid VARCHAR(255) UNIQUE NOT NULL,
            email VARCHAR(255) NOT NULL,
            name VARCHAR(255),
            role ENUM('student', 'teacher', 'admin') DEFAULT 'student',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_firebase_uid (firebase_uid),
            INDEX idx_email (email)
        )
        """
        cls.execute_query(app, query)
    
    @classmethod
    def create(cls, app, user_data):
        """Create a new user"""
        query = f"""
        INSERT INTO {cls.TABLE_NAME} (firebase_uid, email, name, role)
        VALUES (%s, %s, %s, %s)
        """
        params = (
            user_data.get('firebase_uid'),
            user_data.get('email'),
            user_data.get('name'),
            user_data.get('role', 'student')
        )
        
        cursor = cls.get_db_connection(app)
        cursor.execute(query, params)
        user_id = cursor.lastrowid
        cursor.close()
        cls.commit_changes(app)
        
        return user_id
    
    @classmethod
    def get_by_firebase_uid(cls, app, firebase_uid):
        """Get user by Firebase UID"""
        query = f"SELECT * FROM {cls.TABLE_NAME} WHERE firebase_uid = %s"
        result = cls.execute_query(app, query, (firebase_uid,), fetch_one=True)
        
        if result:
            return cls.from_db_result(result)
        return None
    
    @classmethod
    def get_by_email(cls, app, email):
        """Get user by email"""
        query = f"SELECT * FROM {cls.TABLE_NAME} WHERE email = %s"
        result = cls.execute_query(app, query, (email,), fetch_one=True)
        
        if result:
            return cls.from_db_result(result)
        return None
    
    @classmethod
    def from_db_result(cls, db_result):
        """Create User object from database result"""
        return User(
            id=db_result[0],
            firebase_uid=db_result[1],
            email=db_result[2],
            name=db_result[3],
            role=db_result[4],
            created_at=db_result[5],
            updated_at=db_result[6]
        )
    
    def to_dict(self):
        """Convert user object to dictionary"""
        return {
            'id': self.id,
            'firebase_uid': self.firebase_uid,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }