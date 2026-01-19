from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any
import app
from database.base import get_session
from application.entities2.classes import ClassModel
from application.entities2.course import CourseModel
from application.entities2.user import UserModel
from application.entities2.attendance_record import AttendanceRecordModel
from application.entities2.announcement import AnnouncementModel
from application.entities2.semester import SemesterModel
from application.entities2.venue import VenueModel

class LecturerControl:
    """Control class for lecturer business logic using ORM"""
    
    def get_dashboard_data(app, lecturer_id: int, institution_id: int) -> Dict[str, Any]:
        """Get data for lecturer dashboard"""
        try:
            with get_session() as db_session:
                user_model = UserModel(db_session)
                class_model = ClassModel(db_session)
                announcement_model = AnnouncementModel(db_session)
            
                # Get lecturer info
                lecturer = user_model.get_by_id(lecturer_id)
                if not lecturer:
                    return {'success': False, 'error': 'Lecturer not found'}
            
                # Get today's classes for the lecturer
                today = date.today()
                today_classes = class_model.get_today_classes_for_lecturer(lecturer_id, today)
            
                # Get recent announcements for the institution
                announcements = announcement_model.get_recent_announcements(institution_id, limit=3)
            
                # Prepare classes data (same as before)
                formatted_today_classes = []
                for class_obj in today_classes:
                    course = CourseModel(db_session).get_by_id(class_obj.course_id) if class_obj.course_id else None
                    venue = VenueModel(db_session).get_by_id(class_obj.venue_id) if class_obj.venue_id else None
                
                    formatted_today_classes.append({
                        'class_id': class_obj.class_id,
                        'course_code': course.code if course else 'N/A',
                        'course_name': course.name if course else 'N/A',
                        'start_time': class_obj.start_time.strftime('%I:%M %p') if class_obj.start_time else 'N/A',
                        'end_time': class_obj.end_time.strftime('%I:%M %p') if class_obj.end_time else 'N/A',
                        'venue': venue.name if venue else 'N/A',
                        'status': class_obj.status,
                        'student_count': class_model.get_enrolled_count(class_obj.class_id) if hasattr(class_model, 'get_enrolled_count') else 0
                    })
            
                # Prepare announcements in the format expected by the template
                formatted_announcements = []
                for announcement in announcements:
                    requested_by = user_model.get_by_id(announcement.requested_by_user_id) if announcement.requested_by_user_id else None
                
                    formatted_announcements.append({
                        'title': announcement.title,
                        'date': announcement.date_posted.strftime('%b %d, %Y') if announcement.date_posted else 'N/A',
                        'content': announcement.content
                    })
            
                return {
                    'success': True,
                    'lecturer_info': {
                        'lecturer_id': lecturer.user_id,
                        'name': lecturer.name,
                        'email': lecturer.email,
                        'role': lecturer.role
                    },
                    'today_classes': formatted_today_classes,
                    'announcements': formatted_announcements,  # Now in correct format
                    'statistics': {
                        'today_classes_count': len(today_classes),
                        'current_date': today.strftime('%d %B %Y'),
                        'current_time': datetime.now().strftime('%I:%M %p')
                    }
                }
            
        except Exception as e:
            app.logger.error(f"Error getting lecturer dashboard data: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    
    def get_lecturer_courses(app, lecturer_id: int) -> Dict[str, Any]:
        """Get all courses taught by a lecturer"""
        try:
            with get_session() as db_session:
                course_model = CourseModel(db_session)
                
                # Get courses for lecturer
                courses = course_model.get_by_user_id(lecturer_id)
                
                formatted_courses = []
                for course in courses:
                    # Get active classes for this course
                    class_model = ClassModel(db_session)
                    active_classes = class_model.get_active_classes_for_course(course.course_id, lecturer_id)
                    
                    formatted_courses.append({
                        'course_id': course.course_id,
                        'code': course.code,
                        'name': course.name,
                        'description': course.description,
                        'credits': course.credits,
                        'start_date': course.start_date.strftime('%Y-%m-%d') if course.start_date else None,
                        'end_date': course.end_date.strftime('%Y-%m-%d') if course.end_date else None,
                        'is_active': True,
                        'active_classes_count': len(active_classes)
                    })
                
                return {
                    'success': True,
                    'courses': formatted_courses,
                    'total_count': len(formatted_courses)
                }
                
        except Exception as e:
            app.logger.error(f"Error getting lecturer courses: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_lecturer_classes(app, lecturer_id: int, course_id: Optional[int] = None, 
                            status: Optional[str] = None) -> Dict[str, Any]:
        """Get classes for a lecturer with optional filters"""
        try:
            with get_session() as db_session:
                class_model = ClassModel(db_session)
                course_model = CourseModel(db_session)
                user_model = UserModel(db_session)
                venue_model = VenueModel(db_session)
                
                # Get classes for lecturer
                if course_id:
                    classes = class_model.get_classes_for_course(course_id, lecturer_id)
                else:
                    # Get all classes for lecturer
                    classes = class_model.get_classes_for_lecturer(lecturer_id)
                
                # Filter by status if provided
                if status:
                    classes = [c for c in classes if c.status == status]
                
                formatted_classes = []
                for class_obj in classes:
                    course = course_model.get_by_id(class_obj.course_id) if class_obj.course_id else None
                    venue = venue_model.get_by_id(class_obj.venue_id) if class_obj.venue_id else None
                    lecturer = user_model.get_by_id(class_obj.lecturer_id) if class_obj.lecturer_id else None
                    
                    # Get enrolled students count
                    student_count = class_model.get_enrolled_count(class_obj.class_id) if hasattr(class_model, 'get_enrolled_count') else 0
                    
                    # Get attendance summary
                    attendance_model = AttendanceRecordModel(db_session)
                    attendance_records = attendance_model.get_by_class(class_obj.class_id)
                    present_count = sum(1 for r in attendance_records if r.status == 'present')
                    
                    formatted_classes.append({
                        'class_id': class_obj.class_id,
                        'course_id': class_obj.course_id,
                        'course_code': course.code if course else 'N/A',
                        'course_name': course.name if course else 'N/A',
                        'start_time': class_obj.start_time,
                        'end_time': class_obj.end_time,
                        'date': class_obj.start_time.date().isoformat() if class_obj.start_time else None,
                        'time_display': f"{class_obj.start_time.strftime('%I:%M %p') if class_obj.start_time else 'N/A'} - {class_obj.end_time.strftime('%I:%M %p') if class_obj.end_time else 'N/A'}",
                        'venue_id': class_obj.venue_id,
                        'venue_name': venue.name if venue else 'N/A',
                        'venue_capacity': venue.capacity if venue else None,
                        'lecturer_id': class_obj.lecturer_id,
                        'lecturer_name': lecturer.name if lecturer else 'N/A',
                        'status': class_obj.status,
                        'student_count': student_count,
                        'attendance_present': present_count,
                        'attendance_rate': round((present_count / student_count * 100), 2) if student_count > 0 else 0
                    })
                
                # Sort by date (most recent first)
                formatted_classes.sort(key=lambda x: x['start_time'] if x['start_time'] else datetime.min, reverse=True)
                
                return {
                    'success': True,
                    'classes': formatted_classes,
                    'total_count': len(formatted_classes)
                }
                
        except Exception as e:
            app.logger.error(f"Error getting lecturer classes: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_class_details_for_attendance(app, class_id: int, lecturer_id: int) -> Dict[str, Any]:
        """Get detailed class information for attendance management"""
        try:
            with get_session() as db_session:
                class_model = ClassModel(db_session)
                course_model = CourseModel(db_session)
                user_model = UserModel(db_session)
                venue_model = VenueModel(db_session)
                attendance_model = AttendanceRecordModel(db_session)
                
                # Get class details
                class_obj = class_model.get_by_id(class_id)
                if not class_obj:
                    return {'success': False, 'error': 'Class not found'}
                
                # Verify lecturer authorization
                if class_obj.lecturer_id != lecturer_id:
                    return {'success': False, 'error': 'Unauthorized access to this class'}
                
                # Get related data
                course = course_model.get_by_id(class_obj.course_id) if class_obj.course_id else None
                venue = venue_model.get_by_id(class_obj.venue_id) if class_obj.venue_id else None
                lecturer = user_model.get_by_id(class_obj.lecturer_id) if class_obj.lecturer_id else None
                
                # Get enrolled students
                students = class_model.get_enrolled_students(class_id) if hasattr(class_model, 'get_enrolled_students') else []
                
                # Get attendance records
                attendance_records = attendance_model.get_by_class(class_id)
                attendance_status = {record.student_id: record for record in attendance_records}
                
                # Prepare student data
                formatted_students = []
                for student in students:
                    record = attendance_status.get(student.user_id)
                    formatted_students.append({
                        'student_id': student.user_id,
                        'name': student.name,
                        'email': student.email,
                        'phone_number': student.phone_number,
                        'initials': ''.join([name[0] for name in student.name.split()[:2]]).upper() if student.name else '',
                        'attendance_status': record.status if record else 'unmarked',
                        'attendance_id': record.attendance_id if record else None,
                        'marked_by': record.marked_by if record else None,
                        'notes': record.notes if record else None,
                        'recorded_at': record.recorded_at.isoformat() if record and record.recorded_at else None
                    })
                
                # Get attendance summary
                total_students = len(students)
                present_count = sum(1 for record in attendance_records if record.status == 'present')
                absent_count = sum(1 for record in attendance_records if record.status == 'absent')
                late_count = sum(1 for record in attendance_records if record.status == 'late')
                excused_count = sum(1 for record in attendance_records if record.status == 'excused')
                
                return {
                    'success': True,
                    'class_info': {
                        'class_id': class_obj.class_id,
                        'course_id': class_obj.course_id,
                        'course_code': course.code if course else 'N/A',
                        'course_name': course.name if course else 'N/A',
                        'start_time': class_obj.start_time,
                        'end_time': class_obj.end_time,
                        'date_display': class_obj.start_time.strftime('%B %d, %Y') if class_obj.start_time else 'N/A',
                        'time_display': f"{class_obj.start_time.strftime('%I:%M %p') if class_obj.start_time else 'N/A'} - {class_obj.end_time.strftime('%I:%M %p') if class_obj.end_time else 'N/A'}",
                        'venue_id': class_obj.venue_id,
                        'venue_name': venue.name if venue else 'N/A',
                        'lecturer_id': class_obj.lecturer_id,
                        'lecturer_name': lecturer.name if lecturer else 'N/A',
                        'status': class_obj.status
                    },
                    'students': formatted_students,
                    'attendance_summary': {
                        'total_students': total_students,
                        'present_count': present_count,
                        'absent_count': absent_count,
                        'late_count': late_count,
                        'excused_count': excused_count,
                        'unmarked_count': total_students - len(attendance_records),
                        'attendance_rate': round((present_count / total_students * 100), 2) if total_students > 0 else 0
                    }
                }
                
        except Exception as e:
            app.logger.error(f"Error getting class details for attendance: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_timetable_data(app, lecturer_id: int, view_type: str = 'monthly', 
                          target_date: Optional[date] = None) -> Dict[str, Any]:
        """Get timetable data for lecturer based on view type"""
        try:
            with get_session() as db_session:
                class_model = ClassModel(db_session)
                course_model = CourseModel(db_session)
                
                if not target_date:
                    target_date = date.today()
                
                if view_type == 'monthly':
                    # Generate monthly calendar
                    first_day = date(target_date.year, target_date.month, 1)
                    last_day = date(target_date.year, target_date.month, 
                                  (date(target_date.year, target_date.month + 1, 1) - timedelta(days=1)).day)
                    
                    classes = class_model.get_classes_for_lecturer_in_date_range(
                        lecturer_id, first_day, last_day
                    )
                    
                    # Group classes by date
                    classes_by_date = {}
                    for class_obj in classes:
                        if class_obj.start_time:
                            class_date = class_obj.start_time.date()
                            if class_date not in classes_by_date:
                                classes_by_date[class_date] = []
                            
                            course = course_model.get_by_id(class_obj.course_id) if class_obj.course_id else None
                            classes_by_date[class_date].append({
                                'class_id': class_obj.class_id,
                                'course_code': course.code if course else 'N/A',
                                'course_name': course.name if course else 'N/A',
                                'start_time': class_obj.start_time.strftime('%I:%M %p') if class_obj.start_time else 'N/A',
                                'end_time': class_obj.end_time.strftime('%I:%M %p') if class_obj.end_time else 'N/A',
                                'status': class_obj.status
                            })
                    
                    return {
                        'success': True,
                        'view_type': 'monthly',
                        'current_month': target_date.strftime('%B'),
                        'current_year': target_date.year,
                        'classes_by_date': classes_by_date
                    }
                    
                elif view_type == 'weekly':
                    # Generate weekly data
                    # Get start of week (Monday)
                    week_start = target_date - timedelta(days=target_date.weekday())
                    week_end = week_start + timedelta(days=6)
                    
                    classes = class_model.get_classes_for_lecturer_in_date_range(
                        lecturer_id, week_start, week_end
                    )
                    
                    # Group by day of week
                    week_days = {}
                    for i in range(7):
                        current_date = week_start + timedelta(days=i)
                        week_days[current_date] = []
                    
                    for class_obj in classes:
                        if class_obj.start_time:
                            class_date = class_obj.start_time.date()
                            if class_date in week_days:
                                course = course_model.get_by_id(class_obj.course_id) if class_obj.course_id else None
                                week_days[class_date].append({
                                    'class_id': class_obj.class_id,
                                    'course_code': course.code if course else 'N/A',
                                    'course_name': course.name if course else 'N/A',
                                    'start_time': class_obj.start_time,
                                    'end_time': class_obj.end_time,
                                    'status': class_obj.status
                                })
                    
                    # Convert to list format
                    formatted_week_days = []
                    for day_date, day_classes in sorted(week_days.items()):
                        formatted_week_days.append({
                            'date': day_date,
                            'day_name': day_date.strftime('%A'),
                            'day_short': day_date.strftime('%a'),
                            'classes': sorted(day_classes, key=lambda x: x['start_time'] if x['start_time'] else datetime.min)
                        })
                    
                    return {
                        'success': True,
                        'view_type': 'weekly',
                        'week_start': week_start.strftime('%Y-%m-%d'),
                        'week_end': week_end.strftime('%Y-%m-%d'),
                        'week_days': formatted_week_days
                    }
                    
                else:  # list view
                    # Get all upcoming classes
                    classes = class_model.get_upcoming_classes_for_lecturer(lecturer_id, target_date)
                    
                    formatted_classes = []
                    for class_obj in classes:
                        course = course_model.get_by_id(class_obj.course_id) if class_obj.course_id else None
                        formatted_classes.append({
                            'class_id': class_obj.class_id,
                            'course_code': course.code if course else 'N/A',
                            'course_name': course.name if course else 'N/A',
                            'date': class_obj.start_time.date().isoformat() if class_obj.start_time else 'N/A',
                            'start_time': class_obj.start_time.strftime('%I:%M %p') if class_obj.start_time else 'N/A',
                            'end_time': class_obj.end_time.strftime('%I:%M %p') if class_obj.end_time else 'N/A',
                            'status': class_obj.status
                        })
                    
                    return {
                        'success': True,
                        'view_type': 'list',
                        'upcoming_classes': formatted_classes
                    }
                
        except Exception as e:
            app.logger.error(f"Error getting timetable data: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_attendance_statistics(app, lecturer_id: int, course_id: Optional[int] = None, 
                                 start_date: Optional[date] = None, end_date: Optional[date] = None) -> Dict[str, Any]:
        """Get attendance statistics for lecturer's classes"""
        try:
            with get_session() as db_session:
                class_model = ClassModel(db_session)
                course_model = CourseModel(db_session)
                attendance_model = AttendanceRecordModel(db_session)
                
                # Set default date range if not provided
                if not end_date:
                    end_date = date.today()
                if not start_date:
                    start_date = end_date - timedelta(days=30)
                
                # Get classes for lecturer in date range
                classes = class_model.get_classes_for_lecturer_in_date_range(
                    lecturer_id, start_date, end_date
                )
                
                # Filter by course if specified
                if course_id:
                    classes = [c for c in classes if c.course_id == course_id]
                
                # Collect statistics
                statistics = {
                    'total_classes': len(classes),
                    'total_students': 0,
                    'attendance_summary': {
                        'present': 0,
                        'absent': 0,
                        'late': 0,
                        'excused': 0,
                        'unmarked': 0
                    },
                    'by_course': {},
                    'daily_attendance': {},
                    'overall_attendance_rate': 0
                }
                
                total_attendance_instances = 0
                total_possible_attendance = 0
                
                for class_obj in classes:
                    # Get course info
                    course = course_model.get_by_id(class_obj.course_id) if class_obj.course_id else None
                    course_key = f"{course.code if course else 'Unknown'}"
                    
                    if course_key not in statistics['by_course']:
                        statistics['by_course'][course_key] = {
                            'course_id': course.course_id if course else None,
                            'course_code': course.code if course else 'Unknown',
                            'course_name': course.name if course else 'Unknown',
                            'class_count': 0,
                            'attendance_summary': {
                                'present': 0,
                                'absent': 0,
                                'late': 0,
                                'excused': 0,
                                'unmarked': 0
                            },
                            'attendance_rate': 0
                        }
                    
                    statistics['by_course'][course_key]['class_count'] += 1
                    
                    # Get enrolled students count
                    student_count = class_model.get_enrolled_count(class_obj.class_id) if hasattr(class_model, 'get_enrolled_count') else 0
                    statistics['total_students'] += student_count
                    
                    # Get attendance records
                    attendance_records = attendance_model.get_by_class(class_obj.class_id)
                    
                    # Update course-level statistics
                    for record in attendance_records:
                        statistics['by_course'][course_key]['attendance_summary'][record.status] += 1
                        statistics['attendance_summary'][record.status] += 1
                    
                    # Calculate unmarked
                    marked_count = len(attendance_records)
                    unmarked_count = student_count - marked_count
                    statistics['by_course'][course_key]['attendance_summary']['unmarked'] += unmarked_count
                    statistics['attendance_summary']['unmarked'] += unmarked_count
                    
                    # Track for overall rate
                    present_count = sum(1 for r in attendance_records if r.status == 'present')
                    total_attendance_instances += present_count
                    total_possible_attendance += student_count
                    
                    # Track daily attendance
                    if class_obj.start_time:
                        date_key = class_obj.start_time.date().isoformat()
                        if date_key not in statistics['daily_attendance']:
                            statistics['daily_attendance'][date_key] = {
                                'date': date_key,
                                'classes_count': 0,
                                'present_count': 0,
                                'total_students': 0
                            }
                        
                        statistics['daily_attendance'][date_key]['classes_count'] += 1
                        statistics['daily_attendance'][date_key]['present_count'] += present_count
                        statistics['daily_attendance'][date_key]['total_students'] += student_count
                
                # Calculate rates
                for course_key in statistics['by_course']:
                    course_stats = statistics['by_course'][course_key]
                    total_marked = sum(course_stats['attendance_summary'].values()) - course_stats['attendance_summary']['unmarked']
                    present_count = course_stats['attendance_summary']['present']
                    
                    if total_marked > 0:
                        course_stats['attendance_rate'] = round((present_count / total_marked * 100), 2)
                
                # Calculate overall attendance rate
                if total_possible_attendance > 0:
                    statistics['overall_attendance_rate'] = round((total_attendance_instances / total_possible_attendance * 100), 2)
                
                # Convert daily attendance to list
                statistics['daily_attendance_list'] = sorted(
                    statistics['daily_attendance'].values(),
                    key=lambda x: x['date']
                )
                
                return {
                    'success': True,
                    'statistics': statistics,
                    'date_range': {
                        'start_date': start_date.isoformat(),
                        'end_date': end_date.isoformat()
                    }
                }
                
        except Exception as e:
            app.logger.error(f"Error getting attendance statistics: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_lecturer_class_access(app, lecturer_id: int, class_id: int) -> bool:
        """Verify that lecturer has access to a specific class"""
        try:
            with get_session() as db_session:
                class_model = ClassModel(db_session)
                class_obj = class_model.get_by_id(class_id)
                
                if not class_obj:
                    return False
                
                return class_obj.lecturer_id == lecturer_id
                
        except Exception as e:
            app.logger.error(f"Error verifying lecturer class access: {e}")
            return False