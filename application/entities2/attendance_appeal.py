from .base_entity import BaseEntity
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from sqlalchemy.orm import aliased
from database.models import *

class AttendanceAppealModel(BaseEntity[AttendanceAppeal]):
    """Entity for AttendanceAppeal model with custom methods"""
    
    def __init__(self, session):
        super().__init__(session, AttendanceAppeal)
    
    def student_appeals(self, student_id: int) -> List[Dict[str, Any]]:
        """Get all appeals for a student with detailed information"""
        results = (
            self.session
            .query(
                AttendanceAppeal.appeal_id,
                AttendanceAppeal.status,
                AttendanceAppeal.reason,
                AttendanceAppeal.created_at,
                AttendanceRecord.attendance_id,
                Course.code.label('course_code'),
                Course.name.label('course_name'),
                Class.start_time,
                Class.end_time
            )
            .join(AttendanceRecord, AttendanceRecord.attendance_id == AttendanceAppeal.attendance_id)
            .join(Class, AttendanceRecord.class_id == Class.class_id)
            .join(Course, Class.course_id == Course.course_id)
            .filter(AttendanceAppeal.student_id == student_id)
            .order_by(AttendanceAppeal.created_at.desc())
            .all()
        )
        
        appeals = []
        for appeal in results:
            appeals.append({
                'id': appeal.appeal_id,
                'appeal_id': appeal.appeal_id,
                'attendance_id': appeal.attendance_id,
                'course_code': appeal.course_code,
                'course_name': appeal.course_name,
                'module': f"{appeal.course_code} - {appeal.course_name}",
                'class_date': appeal.start_time.date() if appeal.start_time else None,
                'class_date_str': appeal.start_time.strftime("%d %b %Y") if appeal.start_time else "N/A",
                'start_time': appeal.start_time.strftime("%H:%M") if appeal.start_time else "N/A",
                'end_time': appeal.end_time.strftime("%H:%M") if appeal.end_time else "N/A",
                'reason': appeal.reason,
                'status': appeal.status,
                'created_at': appeal.created_at.strftime("%d %b %Y %H:%M") if appeal.created_at else "N/A"
            })
        
        return appeals
    
    def admin_appeal_details(self, institution_id: int, **filters):
        """Get all appeals with detailed information for admin"""
        Lecturers = aliased(User)
        headers = [
            "id", "status", "reason", "created_at", "lecturer",
            "student_id", "student_email", "course_code", "course_name", "class_date"
        ]
        data = (
            self.session
            .query(
                AttendanceAppeal.appeal_id, 
                AttendanceAppeal.status,
                AttendanceAppeal.reason,
                AttendanceAppeal.created_at,
                Lecturers.name,
                User.user_id,
                User.email,
                Course.code,
                Course.name,
                Class.start_time,
            )
            .select_from(AttendanceAppeal)
            .join(AttendanceRecord, AttendanceRecord.attendance_id == AttendanceAppeal.attendance_id)
            .join(Class, AttendanceRecord.class_id == Class.class_id)
            .join(Course, Class.course_id == Course.course_id)
            .join(User, AttendanceAppeal.student_id == User.user_id)
            .join(Lecturers, Lecturers.user_id == Class.lecturer_id)
            .filter(User.institution_id == institution_id)
            .filter_by(**filters)
            .all()
        )
        return self.add_headers(headers, data)

    def get_one(self, attendance_id: Optional[int] = None, appeal_id: Optional[int] = None) -> Optional[AttendanceAppeal]:
        """Get an appeal by attendance_id or appeal_id"""
        if attendance_id:
            return self.session.query(AttendanceAppeal).filter(
                AttendanceAppeal.attendance_id == attendance_id
            ).first()
        elif appeal_id:
            return self.session.query(AttendanceAppeal).filter(
                AttendanceAppeal.appeal_id == appeal_id
            ).first()
        return None
    
    def get_by_id(self, appeal_id: int) -> Optional[AttendanceAppeal]:
        """Get appeal by its ID"""
        return self.session.query(AttendanceAppeal).filter(
            AttendanceAppeal.appeal_id == appeal_id
        ).first()
    
    def create(self, attendance_id: int, student_id: int, reason: str, status: str = 'pending') -> AttendanceAppeal:
        """Create a new attendance appeal"""
        appeal = AttendanceAppeal(
            attendance_id=attendance_id,
            student_id=student_id,
            reason=reason,
            status=status,
            created_at=datetime.now()
        )
        self.session.add(appeal)
        self.session.commit()
        return appeal
    
    def delete(self, appeal_id: int) -> bool:
        """Delete an appeal by ID"""
        appeal = self.get_by_id(appeal_id)
        if appeal:
            self.session.delete(appeal)
            self.session.commit()
            return True
        return False
    
    def update_status(self, appeal_id: int, status: str) -> bool:
        """Update the status of an appeal"""
        appeal = self.get_by_id(appeal_id)
        if appeal:
            appeal.status = status
            self.session.commit()
            return True
        return False
    
    def get_appeals_by_status(self, student_id: int, status: str) -> List[Dict[str, Any]]:
        """Get appeals for a student filtered by status"""
        all_appeals = self.student_appeals(student_id)
        return [appeal for appeal in all_appeals if appeal['status'] == status]
    
    def get_pending_appeals(self, student_id: int) -> List[Dict[str, Any]]:
        """Get pending appeals for a student"""
        return self.get_appeals_by_status(student_id, 'pending')
    
    def get_approved_appeals(self, student_id: int) -> List[Dict[str, Any]]:
        """Get approved appeals for a student"""
        return self.get_appeals_by_status(student_id, 'approved')
    
    def get_rejected_appeals(self, student_id: int) -> List[Dict[str, Any]]:
        """Get rejected appeals for a student"""
        return self.get_appeals_by_status(student_id, 'rejected')
    
    def get_appeal_with_details(self, appeal_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific appeal"""
        result = (
            self.session
            .query(
                AttendanceAppeal,
                AttendanceRecord,
                Class,
                Course,
                User.name.label('student_name'),
                User.email.label('student_email')
            )
            .join(AttendanceRecord, AttendanceRecord.attendance_id == AttendanceAppeal.attendance_id)
            .join(Class, AttendanceRecord.class_id == Class.class_id)
            .join(Course, Class.course_id == Course.course_id)
            .join(User, AttendanceAppeal.student_id == User.user_id)
            .filter(AttendanceAppeal.appeal_id == appeal_id)
            .first()
        )
        
        if result:
            appeal, record, class_obj, course, student_name, student_email = result
            return {
                'appeal_id': appeal.appeal_id,
                'status': appeal.status,
                'reason': appeal.reason,
                'created_at': appeal.created_at.strftime("%d %b %Y %H:%M") if appeal.created_at else "N/A",
                'attendance_id': record.attendance_id,
                'attendance_status': record.status,
                'class_id': class_obj.class_id,
                'course_code': course.code,
                'course_name': course.name,
                'class_date': class_obj.start_time.date() if class_obj.start_time else None,
                'class_date_str': class_obj.start_time.strftime("%d %b %Y") if class_obj.start_time else "N/A",
                'start_time': class_obj.start_time.strftime("%H:%M") if class_obj.start_time else "N/A",
                'end_time': class_obj.end_time.strftime("%H:%M") if class_obj.end_time else "N/A",
                'student_name': student_name,
                'student_email': student_email
            }
        return None
    
    def get_institution_appeals(self, institution_id: int) -> List[Dict[str, Any]]:
        """Get all appeals for an institution with detailed information"""
        results = (
            self.session
            .query(
                AttendanceAppeal.appeal_id,
                AttendanceAppeal.status,
                AttendanceAppeal.reason,
                AttendanceAppeal.created_at,
                AttendanceRecord.attendance_id,
                User.name.label('student_name'),
                User.user_id.label('student_id'),
                Course.code.label('course_code'),
                Course.name.label('course_name'),
                Class.class_id,
                Class.start_time,
                Class.end_time
            )
            .join(AttendanceRecord, AttendanceRecord.attendance_id == AttendanceAppeal.attendance_id)
            .join(Class, AttendanceRecord.class_id == Class.class_id)
            .join(Course, Class.course_id == Course.course_id)
            .join(User, AttendanceAppeal.student_id == User.user_id)
            .filter(Course.institution_id == institution_id)
            .order_by(AttendanceAppeal.created_at.desc())
            .all()
        )
        
        appeals = []
        for appeal in results:
            appeals.append({
                'appeal_id': appeal.appeal_id,
                'student_name': appeal.student_name,
                'student_id': appeal.student_id,
                'course_code': appeal.course_code,
                'course_name': appeal.course_name,
                'class_id': appeal.class_id,
                'class_name': f"{appeal.course_code} - {appeal.course_name} - {appeal.class_id}",
                'class_date': appeal.start_time.date() if appeal.start_time else None,
                'class_date_str': appeal.start_time.strftime("%b %d, %Y") if appeal.start_time else "N/A",
                'start_time': appeal.start_time.strftime("%H:%M") if appeal.start_time else "N/A",
                'end_time': appeal.end_time.strftime("%H:%M") if appeal.end_time else "N/A",
                'reason': appeal.reason,
                'status': appeal.status,
                'created_at': appeal.created_at.strftime("%b %d, %Y %H:%M") if appeal.created_at else "N/A"
            })
        
        return appeals