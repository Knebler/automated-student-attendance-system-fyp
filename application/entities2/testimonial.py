from .base_entity import BaseEntity
from database.models import Testimonial, User, Institution
from datetime import datetime

class TestimonialModel(BaseEntity[Testimonial]):
    """Specific entity for Testimonial model with custom methods"""
    
    def __init__(self, session):
        super().__init__(session, Testimonial)
    
    def testimonials(self):
        """Get all approved testimonials with user and institution details"""
        headers = ["id", "summary", "content", "rating", "date_submitted", "user_name", "user_role", "institution_name"]
        data = (
            self.session
            .query(
                Testimonial.testimonial_id,
                Testimonial.summary,
                Testimonial.content,
                Testimonial.rating,
                Testimonial.date_submitted,
                User.name.label("user_name"),
                User.role.label("user_role"),
                Institution.name.label("institution_name")
            )
            .join(User, Testimonial.user_id == User.user_id)
            .join(Institution, User.institution_id == Institution.institution_id)
            .filter(Testimonial.status == 'approved')
            .order_by(Testimonial.date_submitted.desc())
            .limit(3)
            .all()
        )
        return self.add_headers(headers, data)
    
    def get_by_id(self, id):
        """Get a testimonial by its ID"""
        return self.session.query(Testimonial).filter(Testimonial.testimonial_id == id).first()
    
    def get_random_testimonials(self, exclude_id=None, limit=3):
        """Get random approved testimonials, optionally excluding a specific one"""
        from sqlalchemy import func
        headers = ["id", "summary", "content", "rating", "date_submitted", "user_name", "user_role", "institution_name"]
        query = (
            self.session
            .query(
                Testimonial.testimonial_id,
                Testimonial.summary,
                Testimonial.content,
                Testimonial.rating,
                Testimonial.date_submitted,
                User.name.label("user_name"),
                User.role.label("user_role"),
                Institution.name.label("institution_name")
            )
            .join(User, Testimonial.user_id == User.user_id)
            .join(Institution, User.institution_id == Institution.institution_id)
            .filter(Testimonial.status == 'approved')
        )
        
        if exclude_id:
            query = query.filter(Testimonial.testimonial_id != exclude_id)
        
        data = query.order_by(func.random()).limit(limit).all()
        return self.add_headers(headers, data)