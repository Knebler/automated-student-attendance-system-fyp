from .base_entity import BaseEntity
from database.models import Class, Course, Venue, User, CourseUser, AttendanceRecord, Semester, AttendanceAppeal
from datetime import date, datetime, timedelta
from sqlalchemy import func, extract, case
from sqlalchemy.orm import aliased
from collections import defaultdict
import calendar

class ClassModel(BaseEntity[Class]):
    """Specific entity for User model with custom methods"""
    
    def __init__(self, session):
        super().__init__(session, Class)

    def update_class_statuses(self, institution_id=None):
        """
        Update class statuses in the database based on current time.
        Also marks unmarked attendance as 'absent' for completed classes.
        Sends notifications to students when class is starting in 30 mins or has started.
        Returns number of classes updated.
        """
        from .notification import NotificationModel
        
        now = datetime.now()
        updated_count = 0
        notification_model = NotificationModel(self.session)
        
        # Build base query
        query = self.session.query(Class)
        
        # Filter by institution if provided
        if institution_id:
            query = query.join(Course, Class.course_id == Course.course_id).filter(
                Course.institution_id == institution_id
            )
        
        # Check for classes starting in 30 minutes (with 1 minute window)
        thirty_min_from_now = now + timedelta(minutes=30)
        thirty_one_min_from_now = now + timedelta(minutes=31)
        
        classes_starting_soon = query.filter(
            Class.start_time >= thirty_min_from_now,
            Class.start_time < thirty_one_min_from_now,
            Class.status == 'scheduled',
            Class.notification_30min_sent == False
        ).all()
        
        for cls in classes_starting_soon:
            # Get enrolled students
            enrolled_students = (
                self.session.query(User.user_id)
                .join(CourseUser, CourseUser.user_id == User.user_id)
                .filter(CourseUser.course_id == cls.course_id)
                .filter(CourseUser.semester_id == cls.semester_id)
                .filter(User.role == 'student')
                .all()
            )
            
            student_ids = [s[0] for s in enrolled_students]
            
            # Get course and venue names for notification
            course_venue_info = (
                self.session.query(Course.name, Venue.name)
                .join(Course, Course.course_id == cls.course_id)
                .join(Venue, Venue.venue_id == cls.venue_id)
                .first()
            )
            
            if course_venue_info and student_ids:
                course_name, venue_name = course_venue_info
                notification_content = f"⏰ Class starting soon: {course_name} begins in 30 minutes at {venue_name}"
                
                # Send notifications to all enrolled students
                notification_model.bulk_create_notifications(student_ids, notification_content)
                
                # Mark notification as sent
                cls.notification_30min_sent = True
                updated_count += 1
        
        # Update completed classes (end_time has passed and status is not 'completed' or 'cancelled')
        completed_classes = query.filter(
            Class.end_time < now,
            Class.status.notin_(['completed', 'cancelled'])
        ).all()
        
        for cls in completed_classes:
            cls.status = 'completed'
            updated_count += 1
            
            # Mark any unmarked attendance as 'absent' for this completed class
            # Get all students enrolled in this class
            enrolled_students = (
                self.session.query(User.user_id)
                .join(CourseUser, CourseUser.user_id == User.user_id)
                .filter(CourseUser.course_id == cls.course_id)
                .filter(CourseUser.semester_id == cls.semester_id)
                .filter(User.role == 'student')
                .all()
            )
            
            student_ids = [s[0] for s in enrolled_students]
            
            # Get students who already have attendance records
            existing_records = (
                self.session.query(AttendanceRecord.student_id)
                .filter(AttendanceRecord.class_id == cls.class_id)
                .all()
            )
            
            existing_student_ids = {r[0] for r in existing_records}
            
            # Create absent records for students without attendance
            for student_id in student_ids:
                if student_id not in existing_student_ids:
                    new_record = AttendanceRecord(
                        class_id=cls.class_id,
                        student_id=student_id,
                        status='absent',
                        marked_by='system'
                    )
                    self.session.add(new_record)
        
        # Update in_progress classes (started but not ended, and status is not 'in_progress', 'completed', or 'cancelled')
        in_progress_classes = query.filter(
            Class.start_time <= now,
            Class.end_time >= now,
            Class.status.notin_(['in_progress', 'completed', 'cancelled'])
        ).all()
        
        for cls in in_progress_classes:
            cls.status = 'in_progress'
            updated_count += 1
            
            # Send "class has started" notification if not already sent
            if not cls.notification_started_sent:
                # Get enrolled students
                enrolled_students = (
                    self.session.query(User.user_id)
                    .join(CourseUser, CourseUser.user_id == User.user_id)
                    .filter(CourseUser.course_id == cls.course_id)
                    .filter(CourseUser.semester_id == cls.semester_id)
                    .filter(User.role == 'student')
                    .all()
                )
                
                student_ids = [s[0] for s in enrolled_students]
                
                # Get course and venue names for notification
                course_venue_info = (
                    self.session.query(Course.name, Venue.name)
                    .join(Course, Course.course_id == cls.course_id)
                    .join(Venue, Venue.venue_id == cls.venue_id)
                    .first()
                )
                
                if course_venue_info and student_ids:
                    course_name, venue_name = course_venue_info
                    notification_content = f"🔔 Class started: {course_name} is now in progress at {venue_name}"
                    
                    # Send notifications to all enrolled students
                    notification_model.bulk_create_notifications(student_ids, notification_content)
                    
                    # Mark notification as sent
                    cls.notification_started_sent = True
        
        self.session.commit()
        return updated_count

    def get_today(self, institution_id):
        return (
            self.session
            .query(Class)
            .join(Course, Class.course_id == Course.course_id)
            .filter(Course.institution_id == institution_id)
            .filter(Class.start_time > date.today())
            .all()
        )
    
    def get_completed(self, course_id):
        return (
            self.session
            .query(Class.class_id, Class.start_time, Class.end_time, Venue.name, User.name)
            .join(User, User.user_id == Class.lecturer_id)
            .join(Venue, Class.venue_id == Venue.venue_id)
            .filter(Class.course_id == course_id)
            .filter(Class.end_time < datetime.now())
            .filter(User.role == "lecturer")
            .all()
        )

    def get_upcoming(self, course_id):
        return (
            self.session
            .query(Class.class_id, Class.start_time, Class.end_time, Venue.name, User.name)
            .join(User, User.user_id == Class.lecturer_id)
            .join(Venue, Class.venue_id == Venue.venue_id)
            .filter(Class.course_id == course_id)
            .filter(Class.start_time > datetime.now())
            .filter(User.role == "lecturer")
            .all()
        )

    def get_all_with_status(self, course_id, update_db=True):
        """
        Get all classes for a course with status (completed, in_progress, scheduled).
        
        Args:
            course_id: ID of the course
            update_db: If True, updates the database status before querying (default: True)
        
        Returns status from database, but also updates statuses automatically.
        """
        now = datetime.now()
        
        if update_db:
            # First, update any classes that need status changes
            # Get the institution_id for this course
            course = self.session.query(Course).filter(Course.course_id == course_id).first()
            if course:
                self.update_class_statuses(institution_id=course.institution_id)
        
        # Map database status to display status
        status_map = case(
            (Class.status == 'completed', 'completed'),
            (Class.status == 'in_progress', 'ongoing'),
            (Class.status == 'scheduled', 'upcoming'),
            (Class.status == 'cancelled', 'cancelled'),
            else_='upcoming'
        )
        
        return (
            self.session
            .query(
                Class.class_id, 
                Class.start_time, 
                Class.end_time, 
                Venue.name, 
                User.name,
                status_map.label('status')
            )
            .join(User, User.user_id == Class.lecturer_id)
            .join(Venue, Class.venue_id == Venue.venue_id)
            .filter(Class.course_id == course_id)
            .filter(User.role == "lecturer")
            .order_by(Class.start_time.desc())
            .all()
        )

    def admin_dashboard_classes_today(self, institution_id):
        cols = ["id", "module", "venue", "lecturer"]
        classes = (
            self.session
            .query(Class.class_id, Course.name, Venue.name, User.name)
            .select_from(Class)
            .join(Course, Class.course_id == Course.course_id)
            .join(User, Class.lecturer_id == User.user_id)
            .join(Venue, Class.venue_id == Venue.venue_id)
            .filter(Course.institution_id == institution_id)
            .filter(Class.start_time > date.today())
            .filter(Class.start_time < date.today() + timedelta(days=1))
            .all()
        )
        return self.add_headers(cols, classes)
    
    def admin_class_details(self, class_id):
        headers = ["start_time", "venue", "lecturer"]
        class_data = (
            self.session
            .query(Class.start_time, Venue.name, User.name)
            .join(Venue, Class.venue_id == Venue.venue_id)
            .join(User, Class.lecturer_id == User.user_id)
            .filter(Class.class_id == class_id)
            .one()
        )
        class_details: dict = dict(zip(headers, class_data))
        q_in_course = (
            self.session
            .query(func.count(User.user_id))
            .select_from(Class)
            .join(Course, Class.course_id == Course.course_id)
            .join(CourseUser, 
                  (CourseUser.course_id == Course.course_id) & 
                  (CourseUser.semester_id == Class.semester_id))
            .join(User, User.user_id == CourseUser.user_id)
            .filter(Class.class_id == class_id)
            .filter(User.role == "student")
        )
        q_total = q_in_course.scalar_subquery()
        q_attendance_exists = q_in_course.join(AttendanceRecord, 
                                               (AttendanceRecord.class_id == Class.class_id) & 
                                               (AttendanceRecord.student_id == User.user_id))
        q_present = q_attendance_exists.filter(AttendanceRecord.status == "present").scalar_subquery()
        q_late = q_attendance_exists.filter(AttendanceRecord.status == "late").scalar_subquery()
        q_excused = q_attendance_exists.filter(AttendanceRecord.status == "excused").scalar_subquery()
        q_absent = q_attendance_exists.filter(AttendanceRecord.status == "absent").scalar_subquery()

        cols = ["total", "present", "late", "excused", "absent"]
        row = self.session.query(q_total, q_present, q_late, q_excused, q_absent).one()

        class_details.update(dict(zip(cols, row)))
        class_details["marked"] = sum(row[1:])
        return class_details

    def student_attendance_absent_late(self, user_id):
        headers = [
            "class_id", "course_code", "course_name", "start_date", "venue", "lecturer", "attendance_id", "status"
        ]
        Lecturer = aliased(User)
        data = (
            self.session
            .query(Class.class_id, Course.code, Course.name, Class.start_time, Venue.name, Lecturer.name
                   , AttendanceRecord.attendance_id, func.coalesce(AttendanceRecord.status, "unmarked"))
            .select_from(Semester)
            .join(CourseUser, Semester.semester_id == CourseUser.semester_id)
            .join(User, CourseUser.user_id == User.user_id)
            .join(Course, CourseUser.course_id == Course.course_id)
            .join(Class, Class.course_id == Course.course_id)
            .join(Venue, Class.venue_id == Venue.venue_id)
            .join(Lecturer, Class.lecturer_id == Lecturer.user_id)
            .outerjoin(
                AttendanceRecord,
                (AttendanceRecord.class_id == Class.class_id) &
                (AttendanceRecord.student_id == user_id)
            )
            .outerjoin(
                AttendanceAppeal,
                AttendanceAppeal.attendance_id == AttendanceRecord.attendance_id
            )
            .filter((Semester.start_date <= func.now()) & (Semester.end_date >= func.now()))
            .filter(CourseUser.user_id == user_id)
            .filter(User.role == "student")
            .filter(AttendanceAppeal.attendance_id.is_(None)) # Exclude appealed records
            .distinct(Class.class_id)
            .all()
        )
        data = [d for d in data if d[-1] in ["absent", "late"]]
        return self.add_headers(headers, data)

    def student_attendance_monthly(self, user_id, num_months: int=4):
        n_months_ago = datetime.now() - timedelta(days=30 * num_months)
        cutoff_date = n_months_ago.replace(day=1)
        headers = ["year", "month", "total_classes", "p", "a", "l", "e"]
        return self.add_headers(headers, (
            self.session.query(
                extract('year', Class.start_time).label('year'),
                extract('month', Class.start_time).label('month'),
                func.count(Class.class_id).label('total_classes'),
                func.sum(case((AttendanceRecord.status == "present", 1), else_=0)).label('p'),
                func.sum(case((AttendanceRecord.status == "absent", 1), else_=0)).label('a'),
                func.sum(case((AttendanceRecord.status == "late", 1), else_=0)).label('l'),
                func.sum(case((AttendanceRecord.status == "excused", 1), else_=0)).label('e'),
            )
            .join(Class, AttendanceRecord.class_id == Class.class_id)
            .filter(AttendanceRecord.student_id == user_id)
            .filter(Class.start_time >= cutoff_date)
            # .filter(Class.start_time < datetime.now())
            .filter(Class.start_time < date(2026, 6,27))
            .group_by('year', 'month')
            .order_by('year', 'month')
        ))

    def get_attendance_records(self, class_id):
        headers = ["student_name", "student_id", "status"]
        records = (
            self.session
            .query(User.name, User.user_id, func.coalesce(AttendanceRecord.status, "unmarked"))
            .select_from(Class)
            .join(Course, Class.course_id == Course.course_id)
            .join(CourseUser, 
                  (CourseUser.course_id == Course.course_id) & 
                  (CourseUser.semester_id == Class.semester_id))
            .join(User, User.user_id == CourseUser.user_id)
            .outerjoin(AttendanceRecord, 
                       (AttendanceRecord.class_id == Class.class_id) & 
                       (AttendanceRecord.student_id == User.user_id))
            .filter(Class.class_id == class_id)
            .filter(User.role == "student")
            .all()
        )
        return self.add_headers(headers, records)

    def class_is_institution(self, class_id, institution_id) -> bool:
        return (
            self.session
            .query(Course.institution_id)
            .join(Class, Class.course_id == Course.course_id)
            .filter(Class.class_id == class_id)
            .filter(Course.institution_id == institution_id)
            .count() > 0
        )
    
    def get_course_name(self, class_id) -> str:
        result = (
            self.session
            .query(Course.name)
            .join(Class, Class.course_id == Course.course_id)
            .filter(Class.class_id == class_id)
            .one_or_none()
        )
        return result[0] if result else ""
    
    def get_today_classes_for_lecturer(self, lecturer_id, today_date):
        """Get today's classes for a specific lecturer"""
        return (
            self.session.query(Class)
            .filter(Class.lecturer_id == lecturer_id)
            .filter(func.date(Class.start_time) == today_date)
            .order_by(Class.start_time)
            .all()
        )

    def get_enrolled_students(self, class_id):
        """Get students enrolled in a specific class"""
        return (
            self.session.query(User)
            .join(CourseUser, CourseUser.user_id == User.user_id)
            .join(Course, Course.course_id == CourseUser.course_id)
            .join(Class, Class.course_id == Course.course_id)
            .filter(Class.class_id == class_id)
            .filter(User.role == 'student')
            .all()
        )

    def get_enrolled_count(self, class_id):
        """Get count of students enrolled in a class"""
        return (
            self.session.query(func.count(User.user_id))
            .join(CourseUser, CourseUser.user_id == User.user_id)
            .join(Course, Course.course_id == CourseUser.course_id)
            .join(Class, Class.course_id == Course.course_id)
            .filter(Class.class_id == class_id)
            .filter(User.role == 'student')
            .scalar() or 0
        )

    def get_attendance_statistics(self, course_id, lecturer_id, start_date, end_date):
        """Get attendance statistics for a course
        
        Args:
            course_id: ID of the course
            lecturer_id: ID of the lecturer
            start_date: Start date for statistics calculation
            end_date: End date for statistics calculation
            
        Returns:
            Dictionary containing:
            - attendance_trend: List of attendance percentages over time
            - trend_labels: Labels for the trend data points
            - distribution: Distribution of students by attendance performance
            - total_classes: Total number of classes in the period
            - total_attendance: Overall attendance percentage
            - total_students: Total number of students enrolled
        """
        # Get all classes for this course in the date range
        classes = (
            self.session.query(Class)
            .filter(Class.course_id == course_id)
            .filter(Class.lecturer_id == lecturer_id)
            .filter(Class.start_time >= datetime.combine(start_date, datetime.min.time()))
            .filter(Class.start_time <= datetime.combine(end_date, datetime.max.time()))
            .order_by(Class.start_time)
            .all()
        )
        
        if not classes:
            return {
                'attendance_trend': [],
                'trend_labels': [],
                'distribution': {'excellent': 0, 'good': 0, 'average': 0, 'bad': 0},
                'total_classes': 0,
                'total_attendance': 0,
                'total_students': 0
            }
        
        class_ids = [c.class_id for c in classes]
        
        # Get all attendance records for these classes
        attendance_records = (
            self.session.query(AttendanceRecord)
            .filter(AttendanceRecord.class_id.in_(class_ids))
            .all()
        )

        # Get all students enrolled in the course
        course_students = (
            self.session.query(CourseUser.user_id)
            .filter(CourseUser.course_id == course_id)
            .all()
        )

        student_ids = [s[0] for s in course_students]
        
        # Determine time period grouping based on date range
        days_diff = (end_date - start_date).days
        
        # Calculate attendance trend by period
        # For week: group by day, for month: group by week, for semester: group by month
        if days_diff <= 7:
            # Week view: group by day
            period_key_format = '%Y-%m-%d'
            max_periods = 7
        elif days_diff <= 35:
            # Month view: group by week
            period_key_format = '%Y-W%U'
            max_periods = 5
        else:
            # Semester view: group by month
            period_key_format = '%Y-%m'
            max_periods = 5
        
        # Calculate attendance trend by period
        # For each period, calculate: (students who attended / total possible attendances) * 100
        period_stats = defaultdict(lambda: {'total_possible': 0, 'present': 0})
        
        # Count total possible attendances per period (classes * students)
        for cls in classes:
            if days_diff <= 7:
                period_key = cls.start_time.strftime(period_key_format)
            elif days_diff <= 35:
                # Week number
                period_key = cls.start_time.strftime(period_key_format)
            else:
                period_key = cls.start_time.strftime(period_key_format)
            
            period_stats[period_key]['total_possible'] += len(student_ids) if student_ids else 0
        
        # Count actual attendances per period
        for record in attendance_records:
            if record.class_id in class_ids and record.student_id in student_ids:
                cls = next((c for c in classes if c.class_id == record.class_id), None)
                if cls and record.status in ['present', 'late']:
                    if days_diff <= 7:
                        period_key = cls.start_time.strftime(period_key_format)
                    elif days_diff <= 35:
                        period_key = cls.start_time.strftime(period_key_format)
                    else:
                        period_key = cls.start_time.strftime(period_key_format)
                    
                    period_stats[period_key]['present'] += 1
        
        # Build trend data
        trend_data = []
        trend_labels = []
        
        # Sort periods chronologically
        sorted_periods = sorted(period_stats.keys())
        
        # Get last N periods or all available
        periods_to_show = sorted_periods[-max_periods:] if len(sorted_periods) > max_periods else sorted_periods
        
        for period_key in periods_to_show:
            stats = period_stats[period_key]
            if stats['total_possible'] > 0:
                attendance_rate = (stats['present'] / stats['total_possible']) * 100
                trend_data.append(round(attendance_rate, 1))
                
                # Format label based on period type
                if days_diff <= 7:
                    # Day label (e.g., "Mon 15")
                    try:
                        period_date = datetime.strptime(period_key, '%Y-%m-%d').date()
                        trend_labels.append(period_date.strftime('%a %d'))
                    except:
                        trend_labels.append(period_key.split('-')[-1])
                elif days_diff <= 35:
                    # Week label (e.g., "W12")
                    try:
                        year, week = period_key.split('-W')
                        trend_labels.append(f"W{week}")
                    except:
                        trend_labels.append(period_key)
                else:
                    # Month label (e.g., "Jan")
                    try:
                        month_num = int(period_key.split('-')[1])
                        trend_labels.append(calendar.month_abbr[month_num])
                    except:
                        trend_labels.append(period_key)
            else:
                trend_data.append(0)
                # Add appropriate label even for zero data
                if days_diff <= 7:
                    try:
                        period_date = datetime.strptime(period_key, '%Y-%m-%d').date()
                        trend_labels.append(period_date.strftime('%a %d'))
                    except:
                        trend_labels.append('')
                elif days_diff <= 35:
                    try:
                        year, week = period_key.split('-W')
                        trend_labels.append(f"W{week}")
                    except:
                        trend_labels.append('')
                else:
                    try:
                        month_num = int(period_key.split('-')[1])
                        trend_labels.append(calendar.month_abbr[month_num])
                    except:
                        trend_labels.append('')
        
        # Calculate distribution: Get each student's attendance rate
        student_attendance = defaultdict(lambda: {'total': 0, 'present': 0})
        
        # Count attendance for each student
        for cls in classes:
            for student_id in student_ids:
                student_attendance[student_id]['total'] += 1
                # Check if student was present/late for this class
                record = None
                for r in attendance_records:
                    if r.class_id == cls.class_id and r.student_id == student_id:
                        record = r
                        break
                if record and record.status in ['present', 'late']:
                    student_attendance[student_id]['present'] += 1
        
        # Calculate distribution
        excellent_count = 0  # ≥90%
        good_count = 0       # 80-89%
        average_count = 0    # 70-79%
        bad_count = 0        # <70%
        
        for student_id, stats in student_attendance.items():
            if stats['total'] > 0:
                rate = (stats['present'] / stats['total']) * 100
                if rate >= 90:
                    excellent_count += 1
                elif rate >= 80:
                    good_count += 1
                elif rate >= 70:
                    average_count += 1
                else:
                    bad_count += 1
        
        total_students = len(student_attendance)
        if total_students > 0:
            excellent_pct = round((excellent_count / total_students) * 100)
            good_pct = round((good_count / total_students) * 100)
            average_pct = round((average_count / total_students) * 100)
            bad_pct = round((bad_count / total_students) * 100)
        else:
            excellent_pct = good_pct = average_pct = bad_pct = 0
        
        # Calculate overall attendance rate
        # Count only records for enrolled students
        total_present = sum(1 for r in attendance_records 
                           if r.status in ['present', 'late'] and r.student_id in student_ids)
        total_possible = len(classes) * len(student_ids) if student_ids and len(classes) > 0 else 0
        overall_attendance = (total_present / total_possible * 100) if total_possible > 0 else 0
        
        return {
            'attendance_trend': trend_data,
            'trend_labels': trend_labels,
            'distribution': {
                'excellent': excellent_pct,
                'good': good_pct,
                'average': average_pct,
                'bad': bad_pct
            },
            'total_classes': len(classes),
            'total_attendance': round(overall_attendance, 1),
            'total_students': total_students
        }

    def get_classes_for_course(self, course_id, lecturer_id):
        """Get classes for a specific course taught by a lecturer"""
        return (
            self.session.query(Class)
            .filter(Class.course_id == course_id)
            .filter(Class.lecturer_id == lecturer_id)
            .order_by(Class.start_time)
            .all()
        )

    def get_upcoming_classes_for_lecturer(self, lecturer_id, from_date, course_filter=None, class_type_filter=None):
        """Get upcoming classes for a lecturer"""
        query = (
            self.session.query(Class)
            .filter(Class.lecturer_id == lecturer_id)
            .filter(Class.start_time >= from_date)
            .order_by(Class.start_time)
        )
    
        if course_filter:
            query = query.join(Course).filter(Course.code == course_filter)
    
        if class_type_filter:
            query = query.filter(Class.class_type == class_type_filter)
    
        return query.all()

    def get_classes_for_lecturer_in_date_range(self, lecturer_id, start_date, end_date, course_filter=None, class_type_filter=None):
        """Get classes for a lecturer within a date range"""
        query = (
            self.session.query(Class)
            .join(Course, Class.course_id == Course.course_id)  # Join with Course
            .filter(Class.lecturer_id == lecturer_id)
            .filter(Class.start_time >= start_date)
            .filter(Class.start_time <= end_date)
            .order_by(Class.start_time)
        )
    
        if course_filter:
            query = query.join(Course).filter(Course.code == course_filter)
    
        if class_type_filter:
            query = query.filter(Class.class_type == class_type_filter)
    
        return query.all()
    
    def get_institution_classes_with_attendance_summary(self, institution_id):
        """Get classes with attendance summary for an institution"""
        return (
            self.session.query(Class)
            .join(Course, Class.course_id == Course.course_id)
            .filter(Course.institution_id == institution_id)
            .join(AttendanceRecord, Class.class_id == AttendanceRecord.class_id)
            .all()
        )
    
    def get_all_classes_with_attendance(self, institution_id):
        """Get all classes for an institution with attendance statistics"""
        headers = ["class_id", "module_name", "date", "venue", "lecturer", 
                   "total", "present", "absent", "late", "excused", "unmarked"]
        
        # Subqueries for attendance counts
        q_total = (
            self.session
            .query(func.count(User.user_id))
            .select_from(CourseUser)
            .join(User, User.user_id == CourseUser.user_id)
            .filter(CourseUser.course_id == Class.course_id)
            .filter(CourseUser.semester_id == Class.semester_id)
            .filter(User.role == "student")
            .correlate(Class)
            .scalar_subquery()
        )
        
        q_present = (
            self.session
            .query(func.count(AttendanceRecord.attendance_id))
            .filter(AttendanceRecord.class_id == Class.class_id)
            .filter(AttendanceRecord.status == "present")
            .correlate(Class)
            .scalar_subquery()
        )
        
        q_absent = (
            self.session
            .query(func.count(AttendanceRecord.attendance_id))
            .filter(AttendanceRecord.class_id == Class.class_id)
            .filter(AttendanceRecord.status == "absent")
            .correlate(Class)
            .scalar_subquery()
        )
        
        q_late = (
            self.session
            .query(func.count(AttendanceRecord.attendance_id))
            .filter(AttendanceRecord.class_id == Class.class_id)
            .filter(AttendanceRecord.status == "late")
            .correlate(Class)
            .scalar_subquery()
        )
        
        q_excused = (
            self.session
            .query(func.count(AttendanceRecord.attendance_id))
            .filter(AttendanceRecord.class_id == Class.class_id)
            .filter(AttendanceRecord.status == "excused")
            .correlate(Class)
            .scalar_subquery()
        )
        
        # Main query
        classes = (
            self.session
            .query(
                Class.class_id,
                Course.name,
                Class.start_time,
                Venue.name,
                User.name,
                q_total,
                func.coalesce(q_present, 0),
                func.coalesce(q_absent, 0),
                func.coalesce(q_late, 0),
                func.coalesce(q_excused, 0),
                (q_total - func.coalesce(q_present, 0) - func.coalesce(q_absent, 0) - 
                 func.coalesce(q_late, 0) - func.coalesce(q_excused, 0))
            )
            .join(Course, Class.course_id == Course.course_id)
            .join(Venue, Class.venue_id == Venue.venue_id)
            .join(User, Class.lecturer_id == User.user_id)
            .filter(Course.institution_id == institution_id)
            .order_by(Class.start_time.desc())
            .all()
        )
        
        return self.add_headers(headers, classes)