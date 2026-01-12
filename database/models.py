from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Float, Text,
    Enum, ForeignKey, UniqueConstraint, JSON, Index
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import text

Base = declarative_base()

# =====================
# ENUM DEFINITIONS
# =====================
UserRoleEnum = Enum("student", "lecturer", "admin", name="user_role_enum")
BillingCycleEnum = Enum("monthly", "quarterly", "annual", name="billing_cycle_enum")
GenderEnum = Enum("male", "female", "other", name="gender_enum")
ClassStatusEnum = Enum("scheduled", "completed", "cancelled", name="class_status_enum")
AttendanceStatusEnum = Enum("present", "absent", "late", "excused", name="attendance_status_enum")
MarkedByEnum = Enum("system", "lecturer", name="marked_by_enum")
ReportScheduleEnum = Enum("one", "daily", "weekly", "monthly", name="report_schedule_enum")

# =====================
# SUBSCRIPTION
# =====================
class SubscriptionPlan(Base):
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


class Subscription(Base):
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
class Institution(Base):
    __tablename__ = "institutions"

    institution_id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    address = Column(Text)
    poc_name = Column(String(100))
    poc_phone = Column(String(30))
    poc_email = Column(String(150))
    subscription_id = Column(Integer, ForeignKey("subscriptions.subscription_id"))

    subscription = relationship("Subscription", back_populates="institution")
    users = relationship("User", back_populates="institution")
    courses = relationship("Course", back_populates="institution")
    venues = relationship("Venue", back_populates="institution")

# =====================
# USERS
# =====================
class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.institution_id"), nullable=False)

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
        data = self.__dict__.copy()
        data.pop("password_hash")
        return data

# =====================
# ANNOUNCEMENTS
# =====================
class Announcement(Base):
    __tablename__ = "announcements"

    announcement_id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.institution_id"), nullable=False)
    requested_by_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    date_posted = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

# =====================
# NOTIFICATIONS
# =====================
class Notification(Base):
    __tablename__ = "notifications"

    notification_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    content = Column(Text, nullable=False)
    acknowledged = Column(Boolean, server_default="0")

# =====================
# COURSES
# =====================
class Course(Base):
    __tablename__ = "courses"

    course_id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.institution_id"), nullable=False)

    code = Column(String(50), nullable=False)
    name = Column(String(150), nullable=False)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    description = Column(Text)
    credits = Column(Integer)
    is_active = Column(Boolean, server_default="1")

    institution = relationship("Institution", back_populates="courses")

# =====================
# COURSE USERS (M2M)
# =====================
class CourseUser(Base):
    __tablename__ = "course_users"
    table_args = (
        UniqueConstraint("course_id", "user_id", "academic_year", name="uq_course_user_year"),
    )

    course_id = Column(Integer, ForeignKey("courses.course_id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)
    academic_year = Column(String(20), primary_key=True)

# =====================
# VENUE
# =====================
class Venue(Base):
    __tablename__ = "venues"

    venue_id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.institution_id"), nullable=False)

    name = Column(String(100), nullable=False)
    capacity = Column(Integer)

    institution = relationship("Institution", back_populates="venues")

# =====================
# CLASSES
# =====================
class Class(Base):
    __tablename__ = "classes"

    class_id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.course_id"), nullable=False)
    venue_id = Column(Integer, ForeignKey("venues.venue_id"), nullable=False)
    lecturer_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    status = Column(ClassStatusEnum, server_default="scheduled")
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)

# =====================
# ATTENDANCE RECORDS
# =====================
class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    table_args = (
        UniqueConstraint("class_id", "student_id", name="uq_attendance_class_student"),
    )

    attendance_id = Column(Integer, primary_key=True)
    class_id = Column(Integer, ForeignKey("classes.class_id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    status = Column(AttendanceStatusEnum, nullable=False)
    marked_by = Column(MarkedByEnum, nullable=False)
    lecturer_id = Column(Integer, ForeignKey("users.user_id"))
    captured_image_id = Column(Integer)
    notes = Column(Text)
    recorded_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

# =====================
# REPORT SCHEDULE
# =====================
class ReportSchedule(Base):
    __tablename__ = "reports_schedule"

    schedule_id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.institution_id"), nullable=False)
    requested_by_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    schedule_type = Column(ReportScheduleEnum, nullable=False)