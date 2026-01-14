from application.entities2.classes import ClassModel
from database.base import get_session

class ClassControl:
    """Control class for class entity operations"""
    
    @staticmethod
    def get_class_by_id(class_id):
        """
        Get a class by its ID
        
        Args:
            class_id: The ID of the class to retrieve
            
        Returns:
            Dictionary with success status and class data or error message
        """
        try:
            with get_session() as session:
                class_model = ClassModel(session)
                class_obj = class_model.get_by_id(class_id)
                
                if not class_obj:
                    return {
                        'success': False,
                        'error': f'Class with ID {class_id} not found'
                    }
                
                # Convert class object to dictionary
                class_data = {
                    'class_id': class_obj.class_id,
                    'course_id': class_obj.course_id,
                    'venue_id': class_obj.venue_id,
                    'lecturer_id': class_obj.lecturer_id,
                    'status': class_obj.status.value if hasattr(class_obj.status, 'value') else str(class_obj.status),
                    'start_time': class_obj.start_time.isoformat() if class_obj.start_time else None,
                    'end_time': class_obj.end_time.isoformat() if class_obj.end_time else None,
                    'created_at': class_obj.created_at.isoformat() if hasattr(class_obj, 'created_at') and class_obj.created_at else None,
                    'updated_at': class_obj.updated_at.isoformat() if hasattr(class_obj, 'updated_at') and class_obj.updated_at else None,
                }
                
                return {
                    'success': True,
                    'class': class_data
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Error retrieving class: {str(e)}'
            }

