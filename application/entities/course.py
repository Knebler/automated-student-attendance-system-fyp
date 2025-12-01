from application.entities.base_entity import BaseEntity

class Course(BaseEntity):
    """Course entity"""
    
    TABLE_NAME = "Courses"
    
    def __init__(self, course_id=None, institution_id=None, course_code=None,
                 course_name=None, description=None, credits=None, is_active=True):
        self.course_id = course_id
        self.institution_id = institution_id
        self.course_code = course_code
        self.course_name = course_name
        self.description = description
        self.credits = credits
        self.is_active = is_active
    
    @classmethod
    def create_table(cls, app):
        """Create courses table"""
        query = f"""
        CREATE TABLE IF NOT EXISTS {cls.TABLE_NAME} (
            course_id INT PRIMARY KEY AUTO_INCREMENT,
            institution_id INT NOT NULL,
            course_code VARCHAR(50) NOT NULL,
            course_name VARCHAR(255) NOT NULL,
            description TEXT,
            credits INT,
            is_active BOOLEAN DEFAULT TRUE,
            UNIQUE KEY unique_course_code (institution_id, course_code),
            INDEX idx_course_institution (institution_id)
        )
        """
        cls.execute_query(app, query)
    
    @classmethod
    def get_by_institution(cls, app, institution_id):
        """Get all courses for an institution"""
        query = f"SELECT * FROM {cls.TABLE_NAME} WHERE institution_id = %s AND is_active = TRUE"
        results = cls.execute_query(app, query, (institution_id,), fetch_all=True)
        
        return [cls.from_db_result(result) for result in results] if results else []
    
    @classmethod
    def from_db_result(cls, db_result):
        """Create Course object from database result"""
        return Course(
            course_id=db_result[0],
            institution_id=db_result[1],
            course_code=db_result[2],
            course_name=db_result[3],
            description=db_result[4],
            credits=db_result[5],
            is_active=bool(db_result[6])
        )