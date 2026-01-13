# testimonial_control.py
from application.entities2.user import UserModel
from application.entities2.testimonial import TestimonialModel  # Updated import name
from application.entities2.institution import InstitutionModel
from database.base import get_session
from sqlalchemy import text
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TestimonialControl:
    """Control class for testimonial business logic"""
    
    @staticmethod
    def create_testimonial(app, user_id, institution_id, title, description, rating, status="pending"):
        """
        Create a new testimonial.
        
        Args:
            app: Flask application instance
            user_id: ID of the user creating the testimonial
            institution_id: ID of the institution
            title: Testimonial title
            description: Testimonial description/content
            rating: Rating (1-5)
            status: Initial status (default: "pending")
            
        Returns:
            dict: {'success': bool, 'message': str, 'testimonial_id': int or None}
        """
        try:
            # Validate rating range
            if not 1 <= rating <= 5:
                return {'success': False, 'error': 'Rating must be between 1 and 5'}
            
            # Check if user has already submitted a testimonial for this institution
            with get_session() as session:
                testimonial_model = TestimonialModel(session)
                existing = testimonial_model.get_by_institution_and_user(institution_id, user_id)
                if existing:
                    return {
                        'success': False, 
                        'error': 'You have already submitted a testimonial for this institution'
                    }
                
                # Verify user exists and belongs to the institution
                user_model = UserModel(session)
                user = user_model.get_by_id(user_id)
                if not user or getattr(user, 'institution_id') != institution_id:
                    return {'success': False, 'error': 'User not found or does not belong to this institution'}
                
                # Verify institution exists
                institution_model = InstitutionModel(session)
                institution = institution_model.get_by_id(institution_id)
                if not institution:
                    return {'success': False, 'error': 'Institution not found'}
                
                # Create the testimonial
                testimonial = testimonial_model.create(
                    institution_id=institution_id,
                    user_id=user_id,
                    title=title,
                    description=description,
                    rating=rating,
                    status=status
                )
                
                return {
                    'success': True,
                    'message': 'Testimonial submitted successfully',
                    'testimonial_id': testimonial.testimonial_id
                }
                
        except Exception as e:
            logger.error(f"Error creating testimonial: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_testimonial_by_id(app, testimonial_id):
        """
        Get a testimonial by its ID.
        
        Args:
            app: Flask application instance
            testimonial_id: ID of the testimonial
            
        Returns:
            dict: {'success': bool, 'testimonial': dict or None, 'error': str or None}
        """
        try:
            with get_session() as session:
                testimonial_model = TestimonialModel(session)
                testimonial = testimonial_model.get_by_id(testimonial_id)
                
                if not testimonial:
                    return {'success': False, 'error': 'Testimonial not found'}
                
                # Convert to dict with additional user info if needed
                testimonial_dict = testimonial.as_dict()
                
                # Add user information
                user_model = UserModel(session)
                user = user_model.get_by_id(testimonial.user_id)
                if user:
                    testimonial_dict['user_name'] = user.name
                    testimonial_dict['user_email'] = user.email
                    testimonial_dict['user_role'] = user.role
                
                return {
                    'success': True,
                    'testimonial': testimonial_dict
                }
                
        except Exception as e:
            logger.error(f"Error getting testimonial by ID: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_testimonials_by_institution(app, institution_id, status=None, limit=None, offset=0):
        """
        Get testimonials for a specific institution, optionally filtered by status.
        
        Args:
            app: Flask application instance
            institution_id: ID of the institution
            status: Optional status filter ("pending", "approved", "rejected")
            limit: Optional limit for pagination
            offset: Optional offset for pagination
            
        Returns:
            dict: {'success': bool, 'testimonials': list, 'total': int, 'error': str or None}
        """
        try:
            with get_session() as session:
                testimonial_model = TestimonialModel(session)
                
                # Get testimonials with filters
                testimonials = testimonial_model.get_by_institution(
                    institution_id=institution_id,
                    status=status,
                    limit=limit,
                    offset=offset
                )
                
                # Get total count for pagination
                total = testimonial_model.count_by_institution(institution_id, status)
                
                # Convert to dicts with user info
                testimonial_list = []
                for testimonial in testimonials:
                    testimonial_dict = testimonial.as_dict()
                    
                    # Add user information
                    user_model = UserModel(session)
                    user = user_model.get_by_id(testimonial.user_id)
                    if user:
                        testimonial_dict['user_name'] = user.name
                        testimonial_dict['user_email'] = user.email
                        testimonial_dict['user_role'] = user.role
                    
                    testimonial_list.append(testimonial_dict)
                
                return {
                    'success': True,
                    'testimonials': testimonial_list,
                    'total': total
                }
                
        except Exception as e:
            logger.error(f"Error getting testimonials by institution: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_public_testimonials(app, institution_id=None, limit=10, min_rating=4):
        """
        Get approved testimonials for public display, optionally filtered by institution.
        
        Args:
            app: Flask application instance
            institution_id: Optional institution ID filter
            limit: Maximum number of testimonials to return
            min_rating: Minimum rating to include (default: 4)
            
        Returns:
            dict: {'success': bool, 'testimonials': list, 'error': str or None}
        """
        try:
            with get_session() as session:
                testimonial_model = TestimonialModel(session)
                
                # Get approved testimonials with rating filter
                testimonials = testimonial_model.get_approved_testimonials(
                    institution_id=institution_id,
                    min_rating=min_rating,
                    limit=limit
                )
                
                # Convert to dicts with user info
                testimonial_list = []
                for testimonial in testimonials:
                    testimonial_dict = testimonial.as_dict()
                    
                    # Add user information
                    user_model = UserModel(session)
                    user = user_model.get_by_id(testimonial.user_id)
                    if user:
                        testimonial_dict['user_name'] = user.name
                        # Only show first name and last initial for privacy
                        if user.name:
                            name_parts = user.name.split()
                            if len(name_parts) > 1:
                                testimonial_dict['display_name'] = f"{name_parts[0]} {name_parts[-1][0]}."
                            else:
                                testimonial_dict['display_name'] = user.name
                    
                    testimonial_list.append(testimonial_dict)
                
                return {
                    'success': True,
                    'testimonials': testimonial_list
                }
                
        except Exception as e:
            logger.error(f"Error getting public testimonials: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def update_testimonial_status(app, testimonial_id, new_status, reviewer_id=None, review_notes=None):
        """
        Update the status of a testimonial (e.g., approve, reject).
        
        Args:
            app: Flask application instance
            testimonial_id: ID of the testimonial to update
            new_status: New status ("pending", "approved", "rejected")
            reviewer_id: Optional ID of the user performing the review
            review_notes: Optional notes about the review
            
        Returns:
            dict: {'success': bool, 'message': str, 'error': str or None}
        """
        try:
            # Validate status
            valid_statuses = ["pending", "approved", "rejected"]
            if new_status not in valid_statuses:
                return {'success': False, 'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}
            
            with get_session() as session:
                testimonial_model = TestimonialModel(session)
                
                # Get the testimonial
                testimonial = testimonial_model.get_by_id(testimonial_id)
                if not testimonial:
                    return {'success': False, 'error': 'Testimonial not found'}
                
                # Update the status
                updated = testimonial_model.update(
                    testimonial_id=testimonial_id,
                    status=new_status
                )
                
                if not updated:
                    return {'success': False, 'error': 'Failed to update testimonial'}
                
                # Log the review action (optional - you could create a separate review log table)
                if reviewer_id or review_notes:
                    # Here you could add logic to log the review action
                    pass
                
                return {
                    'success': True,
                    'message': f'Testimonial status updated to {new_status}'
                }
                
        except Exception as e:
            logger.error(f"Error updating testimonial status: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def update_testimonial(app, testimonial_id, user_id, title=None, description=None, rating=None):
        """
        Update testimonial content (only allowed for the original user).
        
        Args:
            app: Flask application instance
            testimonial_id: ID of the testimonial to update
            user_id: ID of the user attempting the update (must be the original author)
            title: Optional new title
            description: Optional new description
            rating: Optional new rating (1-5)
            
        Returns:
            dict: {'success': bool, 'message': str, 'error': str or None}
        """
        try:
            # Validate rating if provided
            if rating is not None and not 1 <= rating <= 5:
                return {'success': False, 'error': 'Rating must be between 1 and 5'}
            
            with get_session() as session:
                testimonial_model = TestimonialModel(session)
                
                # Get the testimonial
                testimonial = testimonial_model.get_by_id(testimonial_id)
                if not testimonial:
                    return {'success': False, 'error': 'Testimonial not found'}
                
                # Verify user is the author
                if testimonial.user_id != user_id:
                    return {'success': False, 'error': 'You can only edit your own testimonials'}
                
                # Check if testimonial is approved (editing approved testimonials might reset status)
                if testimonial.status == "approved":
                    # Option 1: Reset to pending after edit
                    # Option 2: Keep approved status
                    # Here we'll reset to pending for re-review
                    status = "pending"
                else:
                    status = testimonial.status
                
                # Prepare update data
                update_data = {'status': status}
                if title is not None:
                    update_data['title'] = title
                if description is not None:
                    update_data['description'] = description
                if rating is not None:
                    update_data['rating'] = rating
                
                # Update the testimonial
                updated = testimonial_model.update(testimonial_id, **update_data)
                
                if not updated:
                    return {'success': False, 'error': 'Failed to update testimonial'}
                
                return {
                    'success': True,
                    'message': 'Testimonial updated successfully'
                }
                
        except Exception as e:
            logger.error(f"Error updating testimonial: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def delete_testimonial(app, testimonial_id, user_id, is_admin=False):
        """
        Delete a testimonial.
        
        Args:
            app: Flask application instance
            testimonial_id: ID of the testimonial to delete
            user_id: ID of the user attempting the deletion
            is_admin: Whether the user is an admin (admins can delete any testimonial)
            
        Returns:
            dict: {'success': bool, 'message': str, 'error': str or None}
        """
        try:
            with get_session() as session:
                testimonial_model = TestimonialModel(session)
                
                # Get the testimonial
                testimonial = testimonial_model.get_by_id(testimonial_id)
                if not testimonial:
                    return {'success': False, 'error': 'Testimonial not found'}
                
                # Check permissions
                user_model = UserModel(session)
                user = user_model.get_by_id(user_id)
                
                if not is_admin and testimonial.user_id != user_id:
                    return {'success': False, 'error': 'You can only delete your own testimonials'}
                
                # Delete the testimonial
                deleted = testimonial_model.delete(testimonial_id)
                
                if not deleted:
                    return {'success': False, 'error': 'Failed to delete testimonial'}
                
                return {
                    'success': True,
                    'message': 'Testimonial deleted successfully'
                }
                
        except Exception as e:
            logger.error(f"Error deleting testimonial: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_testimonial_stats(app, institution_id=None):
        """
        Get statistics about testimonials.
        
        Args:
            app: Flask application instance
            institution_id: Optional institution ID filter
            
        Returns:
            dict: {'success': bool, 'stats': dict, 'error': str or None}
        """
        try:
            with get_session() as session:
                testimonial_model = TestimonialModel(session)
                
                # Get counts by status
                stats = {}
                
                if institution_id:
                    # Get institution-specific stats
                    for status in ["pending", "approved", "rejected"]:
                        count = testimonial_model.count_by_institution(institution_id, status)
                        stats[f"{status}_count"] = count
                    
                    # Get total and average rating
                    total = testimonial_model.count_by_institution(institution_id)
                    stats["total_count"] = total
                    
                    # Get average rating for approved testimonials only
                    avg_rating = testimonial_model.get_average_rating(institution_id)
                    stats["average_rating"] = avg_rating if avg_rating else 0
                else:
                    # Get platform-wide stats
                    with session.execute(
                        text("""
                            SELECT status, COUNT(*) as count 
                            FROM testimonials 
                            GROUP BY status
                        """)
                    ) as result:
                        for row in result:
                            stats[f"{row.status}_count"] = row.count
                    
                    # Get total count
                    stats["total_count"] = sum(
                        stats.get(f"{status}_count", 0) 
                        for status in ["pending", "approved", "rejected"]
                    )
                    
                    # Get average rating for approved testimonials
                    with session.execute(
                        text("""
                            SELECT AVG(rating) as avg_rating 
                            FROM testimonials 
                            WHERE status = 'approved'
                        """)
                    ) as result:
                        row = result.fetchone()
                        stats["average_rating"] = float(row.avg_rating) if row.avg_rating else 0
                
                return {
                    'success': True,
                    'stats': stats
                }
                
        except Exception as e:
            logger.error(f"Error getting testimonial stats: {e}")
            return {'success': False, 'error': str(e)}