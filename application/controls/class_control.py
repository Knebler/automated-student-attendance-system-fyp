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
                class_data = class_obj.as_sanitized_dict()
                
                return {
                    'success': True,
                    'class': class_data
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Error retrieving class: {str(e)}'
            }

