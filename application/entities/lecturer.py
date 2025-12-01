from application.entities.base_entity import BaseEntity

class Lecturer(BaseEntity):
    """Lecturer entity"""
    
    TABLE_NAME = "Lecturers"
    
    def __init__(self, lecturer_id=None, institution_id=None, email=None,
                 password_hash=None, full_name=None, department=None, is_active=True):
        self.lecturer_id = lecturer_id
        self.institution_id = institution_id
        self.email = email
        self.password_hash = password_hash
        self.full_name = full_name
        self.department = department
        self.is_active = is_active
    
    @classmethod
    def create_table(cls, app):
        """Create lecturers table"""
        query = f"""
        CREATE TABLE IF NOT EXISTS {cls.TABLE_NAME} (
            lecturer_id INT PRIMARY KEY AUTO_INCREMENT,
            institution_id INT NOT NULL,
            email VARCHAR(255) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(100) NOT NULL,
            department VARCHAR(100),
            is_active BOOLEAN DEFAULT TRUE,
            UNIQUE KEY unique_lecturer_email (institution_id, email),
            INDEX idx_lecturer_institution (institution_id)
        )
        """
        cls.execute_query(app, query)