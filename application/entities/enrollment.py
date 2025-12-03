from application.entities.base_entity import BaseEntity

class Enrollment(BaseEntity):
    """Enrollment entity"""
    
    TABLE_NAME = "Enrollments"
    
    def __init__(self, enrollment_id=None, student_id=None, course_id=None,
                 academic_year=None, semester=None, enrollment_date=None,
                 status='active'):
        self.enrollment_id = enrollment_id
        self.student_id = student_id
        self.course_id = course_id
        self.academic_year = academic_year
        self.semester = semester
        self.enrollment_date = enrollment_date
        self.status = status
    
    @classmethod
    def create_table(cls, app):
        """Create enrollments table"""
        query = f"""
        CREATE TABLE IF NOT EXISTS {cls.TABLE_NAME} (
            enrollment_id INT PRIMARY KEY AUTO_INCREMENT,
            student_id INT NOT NULL,
            course_id INT NOT NULL,
            academic_year VARCHAR(9) NOT NULL,
            semester VARCHAR(20),
            enrollment_date DATE DEFAULT (CURRENT_DATE),
            status ENUM('active', 'dropped', 'completed') DEFAULT 'active',
            FOREIGN KEY (student_id) REFERENCES Students(student_id) ON DELETE CASCADE,
            FOREIGN KEY (course_id) REFERENCES Courses(course_id) ON DELETE CASCADE,
            UNIQUE KEY unique_enrollment (student_id, course_id, academic_year, semester),
            INDEX idx_enrollment_student (student_id),
            INDEX idx_enrollment_course (course_id)
        )
        """
        cls.execute_query(app, query)
    
    @classmethod
    def get_by_student(cls, app, student_id):
        """Get all enrollments for a student"""
        query = f"SELECT * FROM {cls.TABLE_NAME} WHERE student_id = %s"
        results = cls.execute_query(app, query, (student_id,), fetch_all=True)
        
        return [cls.from_db_result(result) for result in results] if results else []
    
    @classmethod
    def get_by_course(cls, app, course_id):
        """Get all enrollments for a course"""
        query = f"SELECT * FROM {cls.TABLE_NAME} WHERE course_id = %s"
        results = cls.execute_query(app, query, (course_id,), fetch_all=True)
        
        return [cls.from_db_result(result) for result in results] if results else []
    
    @classmethod
    def get_active_by_student(cls, app, student_id, academic_year=None, semester=None):
        """Get active enrollments for a student"""
        query = f"SELECT * FROM {cls.TABLE_NAME} WHERE student_id = %s AND status = 'active'"
        params = [student_id]
        
        if academic_year:
            query += " AND academic_year = %s"
            params.append(academic_year)
        
        if semester:
            query += " AND semester = %s"
            params.append(semester)
        
        results = cls.execute_query(app, query, tuple(params), fetch_all=True)
        return [cls.from_db_result(result) for result in results] if results else []
    
    @classmethod
    def get_by_student_and_course(cls, app, student_id, course_id):
        """Get enrollment for specific student and course"""
        query = f"SELECT * FROM {cls.TABLE_NAME} WHERE student_id = %s AND course_id = %s"
        result = cls.execute_query(app, query, (student_id, course_id), fetch_one=True)
        
        return cls.from_db_result(result) if result else None
    
    @classmethod
    def from_db_result(cls, db_result):
        """Create Enrollment object from database result"""
        return Enrollment(
            enrollment_id=db_result[0],
            student_id=db_result[1],
            course_id=db_result[2],
            academic_year=db_result[3],
            semester=db_result[4],
            enrollment_date=db_result[5],
            status=db_result[6]
        )