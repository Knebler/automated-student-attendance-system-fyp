from application.entities.base_entity import BaseEntity

class Student(BaseEntity):
    """Student entity"""
    
    TABLE_NAME = "Students"
    
    def __init__(self, student_id=None, institution_id=None, student_code=None,
                 email=None, password_hash=None, full_name=None, 
                 enrollment_year=None, is_active=True):
        self.student_id = student_id
        self.institution_id = institution_id
        self.student_code = student_code
        self.email = email
        self.password_hash = password_hash
        self.full_name = full_name
        self.enrollment_year = enrollment_year
        self.is_active = is_active
    
    @classmethod
    def create_table(cls, app):
        """Create students table"""
        query = f"""
        CREATE TABLE IF NOT EXISTS {cls.TABLE_NAME} (
            student_id INT PRIMARY KEY AUTO_INCREMENT,
            institution_id INT NOT NULL,
            student_code VARCHAR(50) NOT NULL,
            email VARCHAR(255) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(100) NOT NULL,
            enrollment_year INT,
            is_active BOOLEAN DEFAULT TRUE,
            UNIQUE KEY unique_student_code (institution_id, student_code),
            UNIQUE KEY unique_student_email (institution_id, email),
            INDEX idx_student_institution (institution_id)
        )
        """
        cls.execute_query(app, query)
    
    @classmethod
    def get_by_institution(cls, app, institution_id):
        """Get all students for an institution"""
        query = f"SELECT * FROM {cls.TABLE_NAME} WHERE institution_id = %s AND is_active = TRUE"
        results = cls.execute_query(app, query, (institution_id,), fetch_all=True)
        
        return [cls.from_db_result(result) for result in results] if results else []