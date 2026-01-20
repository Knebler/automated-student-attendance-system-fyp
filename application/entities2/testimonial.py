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
    
    def get_pending_testimonials(self):
        """Get all pending testimonials for platform manager review"""
        headers = ["testimonial_id", "summary", "content", "rating", "date_submitted", "user_name", "user_email", "user_role", "institution_name", "institution_id"]
        data = (
            self.session
            .query(
                Testimonial.testimonial_id,
                Testimonial.summary,
                Testimonial.content,
                Testimonial.rating,
                Testimonial.date_submitted,
                User.name.label("user_name"),
                User.email.label("user_email"),
                User.role.label("user_role"),
                Institution.name.label("institution_name"),
                Institution.institution_id
            )
            .join(User, Testimonial.user_id == User.user_id)
            .join(Institution, User.institution_id == Institution.institution_id)
            .filter(Testimonial.status == 'pending')
            .order_by(Testimonial.date_submitted.asc())
            .all()
        )
        return self.add_headers(headers, data)
    
    def get_all_testimonials_with_status(self, status=None):
        """Get all testimonials, optionally filtered by status"""
        headers = ["testimonial_id", "summary", "content", "rating", "status", "date_submitted", "user_name", "user_email", "user_role", "institution_name", "institution_id"]
        query = (
            self.session
            .query(
                Testimonial.testimonial_id,
                Testimonial.summary,
                Testimonial.content,
                Testimonial.rating,
                Testimonial.status,
                Testimonial.date_submitted,
                User.name.label("user_name"),
                User.email.label("user_email"),
                User.role.label("user_role"),
                Institution.name.label("institution_name"),
                Institution.institution_id
            )
            .join(User, Testimonial.user_id == User.user_id)
            .join(Institution, User.institution_id == Institution.institution_id)
        )
        
        if status:
            query = query.filter(Testimonial.status == status)
        
        data = query.order_by(Testimonial.date_submitted.desc()).all()
        return self.add_headers(headers, data)
    
    def count_by_status(self, status):
        """Count testimonials by status"""
        return self.session.query(Testimonial).filter(Testimonial.status == status).count()
    
    def get_testimonials_by_status(self, status):
        """Get all testimonials with a specific status"""
        headers = ["testimonial_id", "summary", "content", "rating", "date_submitted", "user_name", "user_email", "user_role", "institution_name"]
        data = (
            self.session
            .query(
                Testimonial.testimonial_id,
                Testimonial.summary,
                Testimonial.content,
                Testimonial.rating,
                Testimonial.date_submitted,
                User.name.label("user_name"),
                User.email.label("user_email"),
                User.role.label("user_role"),
                Institution.name.label("institution_name")
            )
            .join(User, Testimonial.user_id == User.user_id)
            .join(Institution, User.institution_id == Institution.institution_id)
            .filter(Testimonial.status == status)
            .order_by(Testimonial.date_submitted.desc())
            .all()
        )
        return self.add_headers(headers, data)
    
    def update_status(self, testimonial_id, status):
        """Update testimonial status"""
        testimonial = self.get_by_id(testimonial_id)
        if testimonial:
            testimonial.status = status
            self.session.commit()
            return True
        return False