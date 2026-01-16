from .base_entity import BaseEntity
from database.models import AttendanceRecord, Class, User, Course
from typing import List, Optional, Dict
from datetime import datetime, date

class AttendanceRecordModel(BaseEntity[AttendanceRecord]):
    """Entity for AttendanceRecord model with custom methods"""
    
    def __init__(self, session):
        super().__init__(session, AttendanceRecord)
    
    def get_by_class(self, class_id: int) -> List[AttendanceRecord]:
        """Get all attendance records for a specific class"""
        return self.session.query(AttendanceRecord)\
            .filter(AttendanceRecord.class_id == class_id)\
            .all()
    
    def get_by_student(self, student_id: int) -> List[AttendanceRecord]:
        """Get all attendance records for a specific student"""
        return self.session.query(AttendanceRecord)\
            .filter(AttendanceRecord.student_id == student_id)\
            .order_by(AttendanceRecord.recorded_at.desc())\
            .all()
    
    def get_student_class_attendance(self, student_id: int, class_id: int) -> Optional[AttendanceRecord]:
        """Get attendance record for a specific student in a specific class"""
        return self.session.query(AttendanceRecord)\
            .filter(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.class_id == class_id
            )\
            .first()
    
    def mark_attendance(self, class_id: int, student_id: int, status: str, 
                       marked_by: str, lecturer_id: Optional[int] = None,
                       notes: Optional[str] = None) -> AttendanceRecord:
        """Mark attendance for a student"""
        attendance = AttendanceRecord(
            class_id=class_id,
            student_id=student_id,
            status=status,
            marked_by=marked_by,
            lecturer_id=lecturer_id,
            notes=notes,
            recorded_at=datetime.utcnow()
        )
        self.session.add(attendance)
        self.session.commit()
        return attendance
    
    def get_attendance_summary(self, student_id: int, start_date: date, 
                              end_date: date) -> Dict[str, int]:
        """Get attendance summary for a student within a date range"""
        records = self.session.query(AttendanceRecord)\
            .join(Class, AttendanceRecord.class_id == Class.class_id)\
            .filter(
                AttendanceRecord.student_id == student_id,
                Class.start_time >= start_date,
                Class.start_time <= end_date
            )\
            .all()
        
        summary = {
            "present": 0,
            "absent": 0,
            "late": 0,
            "excused": 0,
            "total": len(records)
        }
        
        for record in records:
            summary[record.status] = summary.get(record.status, 0) + 1
        
        return summary
    
    def bulk_mark_attendance(self, class_id: int, attendance_data: List[Dict]) -> List[AttendanceRecord]:
        """Bulk mark attendance for multiple students"""
        records = []
        for data in attendance_data:
            record = AttendanceRecord(
                class_id=class_id,
                student_id=data['student_id'],
                status=data['status'],
                marked_by=data['marked_by'],
                lecturer_id=data.get('lecturer_id'),
                notes=data.get('notes'),
                recorded_at=datetime.utcnow()
            )
            records.append(record)
            self.session.add(record)
        
        self.session.commit()
        return records
    
    def student_get_attendance_for_appeal(self, attendance_record_id: int):
        """Get attendance record details for appeal"""
        headers = ["student_id", "student_name", "course_name", "course_code", "class_id"]
        data = (
            self.session.query(User.user_id, User.name, Course.name, Course.code, Class.class_id)
            .select_from(AttendanceRecord)
            .join(Class, AttendanceRecord.class_id == Class.class_id)
            .join(Course, Class.course_id == Course.course_id)
            .join(User, AttendanceRecord.student_id == User.user_id)
            .filter(AttendanceRecord.attendance_id == attendance_record_id)
            .one()
        )
        return dict(zip(headers, data))