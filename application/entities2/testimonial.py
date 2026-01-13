from .base_entity import BaseEntity
from database.models import Testimonial

class TestimonialModel(BaseEntity[Testimonial]):
    """Specific entity for Testimonial model with custom methods"""
    
    def __init__(self, session):
        super().__init__(session, Testimonial)
    
    def get_by_institution(self, institution_id, status=None, limit=None, offset=0):
        """Get testimonials by institution, optionally filtered by status."""
        query = self.session.query(self.model).filter(
            self.model.institution_id == institution_id
        )
        
        if status:
            query = query.filter(self.model.status == status)
        
        query = query.order_by(self.model.date_submitted.desc())
        
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        
        return query.all()
    
    def get_by_institution_and_user(self, institution_id, user_id):
        """Get testimonial by institution and user (should be unique)."""
        return self.session.query(self.model).filter(
            self.model.institution_id == institution_id,
            self.model.user_id == user_id
        ).first()
    
    def get_approved_testimonials(self, institution_id=None, min_rating=4, limit=10):
        """Get approved testimonials, optionally filtered by institution and minimum rating."""
        query = self.session.query(self.model).filter(
            self.model.status == "approved",
            self.model.rating >= min_rating
        )
    
        if institution_id:
            query = query.filter(self.model.institution_id == institution_id)
    
        # Order by date_submitted descending to get latest testimonials first
        query = query.order_by(self.model.date_submitted.desc())
    
        if limit:
            query = query.limit(limit)
    
        return query.all()
    
    def count_by_institution(self, institution_id, status=None):
        """Count testimonials for an institution, optionally filtered by status."""
        query = self.session.query(self.model).filter(
            self.model.institution_id == institution_id
        )
        
        if status:
            query = query.filter(self.model.status == status)
        
        return query.count()
    
    def get_average_rating(self, institution_id=None):
        """Get average rating for approved testimonials, optionally filtered by institution."""
        from sqlalchemy import func
        
        query = self.session.query(func.avg(self.model.rating)).filter(
            self.model.status == "approved"
        )
        
        if institution_id:
            query = query.filter(self.model.institution_id == institution_id)
        
        result = query.scalar()
        return float(result) if result else None