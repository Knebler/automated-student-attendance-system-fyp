# application/entities/report.py
from application.entities.base_entity import BaseEntity
import uuid

class Report(BaseEntity):
    """Report entity as a SQLAlchemy model"""
    
    @classmethod
    def get_model(cls):
        db = cls._get_db()  # Your existing method
        
        if not hasattr(cls, '_model_class'):
            class ReportModel(db.Model, BaseEntity):
                __tablename__ = "Reports"
                
                # Column definitions matching the schema above
                report_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
                report_uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
                title = db.Column(db.String(255), nullable=False)
                description = db.Column(db.Text)
                report_type = db.Column(db.String(50), nullable=False)
                
                # Reporter info (using your suggested approach)
                institution_id = db.Column(
                    db.Integer, 
                    db.ForeignKey('Institutions.institution_id', ondelete='CASCADE'),
                    nullable=False
                )
                reporter_email = db.Column(db.String(255), nullable=False)
                reporter_role = db.Column(
                    db.Enum('admin', 'lecturer', 'system'),
                    nullable=False
                )
                
                # Content
                report_data = db.Column(db.JSON, nullable=False)
                parameters = db.Column(db.JSON)
                format = db.Column(
                    db.Enum('pdf', 'csv', 'html', 'json', 'excel'),
                    default='html'
                )
                
                # Status
                status = db.Column(
                    db.Enum('generating', 'completed', 'failed', 'scheduled'),
                    default='generating'
                )
                generation_time = db.Column(db.Integer)  # seconds
                file_size_bytes = db.Column(db.Integer)
                
                # Storage
                file_path = db.Column(db.String(500))
                storage_url = db.Column(db.String(500))
                preview_url = db.Column(db.String(500))
                
                # Schedule
                schedule_type = db.Column(
                    db.Enum('once', 'daily', 'weekly', 'monthly', 'quarterly', 'yearly'),
                    default='once'
                )
                schedule_config = db.Column(db.JSON)
                next_scheduled_run = db.Column(db.DateTime)
                
                # Timestamps
                generated_at = db.Column(db.DateTime, default=db.func.current_timestamp())
                expires_at = db.Column(db.DateTime)
                viewed_at = db.Column(db.DateTime)
                deleted_at = db.Column(db.DateTime)
                
                # Access
                is_public = db.Column(db.Boolean, default=False)
                access_code = db.Column(db.String(100))
                allowed_viewers = db.Column(db.JSON)
                
                # Relationships
                institution = db.relationship('Institution', backref='reports')
                
                # Indexes
                __table_args__ = (
                    db.Index('idx_reports_institution', 'institution_id'),
                    db.Index('idx_reports_reporter', 'reporter_email'),
                    db.Index('idx_reports_type', 'report_type'),
                    db.Index('idx_reports_status', 'status'),
                    db.Index('idx_reports_generated', 'generated_at'),
                    db.Index('idx_reports_composite', 'institution_id', 'reporter_email', 'report_type'),
                )
                
                def get_reporter_info(self, app):
                    """Get reporter details from appropriate table"""
                    from application.entities.institution_admin import InstitutionAdmin
                    from application.entities.lecturer import Lecturer
                    
                    if self.reporter_role == 'admin':
                        return InstitutionAdmin.get_by_email_and_institution(
                            app, self.reporter_email, self.institution_id
                        )
                    elif self.reporter_role == 'lecturer':
                        return Lecturer.get_by_email_and_institution(
                            app, self.reporter_email, self.institution_id
                        )
                    return None  # System-generated
                
                def to_dict(self):
                    """Convert to dictionary with reporter info"""
                    data = {
                        'report_id': self.report_id,
                        'report_uuid': self.report_uuid,
                        'title': self.title,
                        'description': self.description,
                        'report_type': self.report_type,
                        'institution_id': self.institution_id,
                        'reporter_email': self.reporter_email,
                        'reporter_role': self.reporter_role,
                        'format': self.format,
                        'status': self.status,
                        'generated_at': self.generated_at.isoformat() if self.generated_at else None,
                        'expires_at': self.expires_at.isoformat() if self.expires_at else None,
                        'is_public': self.is_public,
                        'preview_url': self.preview_url,
                        'storage_url': self.storage_url,
                        'file_size_bytes': self.file_size_bytes,
                    }
                    
                    # Add reporter info if needed
                    if hasattr(self, '_reporter_info'):
                        data['reporter_info'] = self._reporter_info
                    
                    return data
            
            cls._model_class = ReportModel
        
        return cls._model_class