from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Float, Text,
    Enum, ForeignKey, UniqueConstraint, JSON, Index
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import text
from sqlalchemy.inspection import inspect

Base = declarative_base()

class BaseMixin:
    def as_dict(self):
        return {
            c.key: getattr(self, c.key)
            for c in inspect(self).mapper.column_attrs
        }

# =====================
# ENUM DEFINITIONS
# =====================
UserRoleEnum = Enum("student", "lecturer", "admin", name="user_role_enum")
BillingCycleEnum = Enum("monthly", "quarterly", "annual", name="billing_cycle_enum")
GenderEnum = Enum("male", "female", "other", name="gender_enum")
ClassStatusEnum = Enum("scheduled", "in_progress", "completed", "cancelled", name="class_status_enum")
AttendanceStatusEnum = Enum("unmarked", "present", "absent", "late", "excused", name="attendance_status_enum")
MarkedByEnum = Enum("system", "lecturer", name="marked_by_enum")
ReportScheduleEnum = Enum("one", "daily", "weekly", "monthly", name="report_schedule_enum")
TestimonialStatusEnum = Enum("pending", "approved", "rejected", name="testimonial_status_enum")

# =====================
# SUBSCRIPTION
# =====================
class SubscriptionPlan(Base, BaseMixin):
    __tablename__ = "subscription_plans"

    plan_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    price_per_cycle = Column(Float, nullable=False)
    billing_cycle = Column(BillingCycleEnum, nullable=False)
    max_users = Column(Integer, nullable=False)
    features = Column(JSON)
    is_active = Column(Boolean, server_default="1")
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class Subscription(Base, BaseMixin):
    __tablename__ = "subscriptions"

    subscription_id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey("subscription_plans.plan_id"), nullable=False)

    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)
    is_active = Column(Boolean, server_default="1")
    stripe_subscription_id = Column(String(255), unique=True)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    plan = relationship("SubscriptionPlan")
    institution = relationship("Institution", back_populates="subscription")

# =====================
# INSTITUTION
# =====================
class Institution(Base, BaseMixin):
    __tablename__ = "institutions"

    institution_id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    address = Column(Text)
    poc_name = Column(String(100))
    poc_phone = Column(String(30))
    poc_email = Column(String(150))
    subscription_id = Column(Integer, ForeignKey("subscriptions.subscription_id"), index=True)

    subscription = relationship("Subscription", back_populates="institution")
    users = relationship("User", back_populates="institution")
    courses = relationship("Course", back_populates="institution")
    venues = relationship("Venue", back_populates="institution")

# =====================
# USERS
# =====================
class User(Base, BaseMixin):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.institution_id"), nullable=False, index=True)

    role = Column(UserRoleEnum, nullable=False)
    name = Column(String(100), nullable=False)
    age = Column(Integer)
    gender = Column(GenderEnum)
    phone_number = Column(String(30))
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, server_default="1")
    date_joined = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    institution = relationship("Institution", back_populates="users")

    def as_sanitized_dict(self):
        data = self.as_dict()
        data.pop("password_hash")
        return data

# =====================
# ANNOUNCEMENTS
# =====================
class Announcement(Base, BaseMixin):
    __tablename__ = "announcements"

    announcement_id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.institution_id"), nullable=False, index=True)
    requested_by_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    date_posted = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

# =====================
# NOTIFICATIONS
# =====================
class Notification(Base, BaseMixin):
    __tablename__ = "notifications"

    notification_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    content = Column(Text, nullable=False)
    acknowledged = Column(Boolean, server_default="0")

# =====================
# REPORT SCHEDULE
# =====================
class Semester(Base, BaseMixin):
    __tablename__ = "semesters"

    semester_id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.institution_id"), nullable=False, index=True)

    name = Column(String(100), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)

# =====================
# COURSES
# =====================
class Course(Base, BaseMixin):
    __tablename__ = "courses"

    course_id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.institution_id"), nullable=False, index=True)

    code = Column(String(50), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    start_date = Column(DateTime, index=True)
    end_date = Column(DateTime, index=True)
    description = Column(Text)
    credits = Column(Integer)
    is_active = Column(Boolean, server_default="1")

    institution = relationship("Institution", back_populates="courses")

# =====================
# COURSE USERS (M2M)
# =====================
class CourseUser(Base, BaseMixin):
    __tablename__ = "course_users"
    table_args = (
        UniqueConstraint("course_id", "user_id", "semester_id", name="uq_course_user_year"),
    )

    course_id = Column(Integer, ForeignKey("courses.course_id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)
    semester_id = Column(Integer, ForeignKey("semesters.semester_id"), primary_key=True)

# =====================
# VENUE
# =====================
class Venue(Base, BaseMixin):
    __tablename__ = "venues"

    venue_id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.institution_id"), nullable=False, index=True)

    name = Column(String(100), nullable=False)
    capacity = Column(Integer)

    institution = relationship("Institution", back_populates="venues")

# =====================
# CLASSES
# =====================
class Class(Base, BaseMixin):
    __tablename__ = "classes"

    class_id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.course_id"), nullable=False, index=True)
    venue_id = Column(Integer, ForeignKey("venues.venue_id"), nullable=False, index=True)
    lecturer_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)

    status = Column(ClassStatusEnum, server_default="scheduled")
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)

# =====================
# ATTENDANCE RECORDS
# =====================
class AttendanceRecord(Base, BaseMixin):
    __tablename__ = "attendance_records"
    table_args = (
        UniqueConstraint("class_id", "student_id", name="uq_attendance_class_student"),
    )

    attendance_id = Column(Integer, primary_key=True)
    class_id = Column(Integer, ForeignKey("classes.class_id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)

    status = Column(AttendanceStatusEnum, nullable=False, index=True)
    marked_by = Column(MarkedByEnum, nullable=False)
    lecturer_id = Column(Integer, ForeignKey("users.user_id"), index=True)
    captured_image_id = Column(Integer)
    notes = Column(Text)
    recorded_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

# =====================
# REPORT SCHEDULE
# =====================
class ReportSchedule(Base, BaseMixin):
    __tablename__ = "reports_schedule"

    schedule_id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.institution_id"), nullable=False)
    requested_by_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    schedule_type = Column(ReportScheduleEnum, nullable=False)
    schedule_type = Column(ReportScheduleEnum, nullable=False)

# ====================
# TESTIMONIALS
# ====================
class Testimonial(Base, BaseMixin):
    __tablename__ = "testimonials"
    __table_args__ = (
        UniqueConstraint("institution_id", "user_id", name="uq_testimonial_institution_user"),
    )
    
    testimonial_id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.institution_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    rating = Column(Integer, nullable=False, default=5)  # 1 to 5
    status = Column(TestimonialStatusEnum, server_default="pending")  # Moderation status
    date_submitted = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    
    # Optional: Index for frequently filtered columns
    __table_args__ = (
        UniqueConstraint("institution_id", "user_id", name="uq_testimonial_institution_user"),
        Index("idx_testimonial_status", "status"),
        Index("idx_testimonial_institution_status", "institution_id", "status"),
        # CheckConstraint('rating >= 1 AND rating <= 5', name='rating_range_check')
    )
    
    # Relationships
    institution = relationship("Institution")
    user = relationship("User")
    
    # Validation method
    def validate_rating(self):
        if not 1 <= self.rating <= 5:
            raise ValueError("Rating must be between 1 and 5")
    
    # Helper method to check if testimonial is visible (approved)
    def is_visible(self):
        return self.status == "approved"