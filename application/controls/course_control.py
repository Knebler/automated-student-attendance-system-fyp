from application.entities2.course import CourseModel
from database.base import get_session
from database.models import Course, CourseUser, User

class CourseControl:
    """Control class for course entity operations"""
    
    @staticmethod
    def get_course_by_id(course_id):
        """
        Get a course by its ID
        
        Args:
            course_id: The ID of the course to retrieve
            
        Returns:
            Dictionary with success status and course data or error message
        """
        try:
            with get_session() as session:
                course_model = CourseModel(session)
                course_obj = course_model.get_by_id(course_id)
                
                if not course_obj:
                    return {
                        'success': False,
                        'error': f'Course with ID {course_id} not found'
                    }
                
                # Convert course object to dictionary
                course_data = course_obj.as_sanitized_dict()
                
                return {
                    'success': True,
                    'course': course_data
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Error retrieving course: {str(e)}'
            }
    
    @staticmethod
    def get_students_by_course_id(course_id):
        """
        Get all students enrolled in a course
        
        Args:
            course_id: The ID of the course
            
        Returns:
            Dictionary with success status and list of students or error message
        """
        try:
            with get_session() as session:
                # Query to get all students enrolled in the course
                students = (
                    session.query(User)
                    .join(CourseUser, CourseUser.user_id == User.user_id)
                    .filter(CourseUser.course_id == course_id)
                    .filter(User.role == 'student')
                    .all()
                )
                
                # Convert students to list of dictionaries
                students_data = []
                for student in students:
                    students_data.append({
                        'user_id': student.user_id,
                        'name': student.name,
                        'email': student.email if hasattr(student, 'email') else '',
                        'id_number': getattr(student, 'student_code', None) or getattr(student, 'user_code', None) or str(student.user_id),
                        'role': student.role,
                        'institution_id': student.institution_id if hasattr(student, 'institution_id') else None,
                    })
                
                return {
                    'success': True,
                    'students': students_data
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Error retrieving students: {str(e)}',
                'students': []
            }


