# Institution Cascade Delete Implementation

## Overview
This implementation ensures that when an institution is deleted, all related data in the system is automatically deleted through database-level cascade constraints and SQLAlchemy ORM relationships.

## Changes Made

### 1. Database Models (`database/models.py`)

#### SQLAlchemy Relationship Updates
Added `cascade="all, delete-orphan"` to the Institution model relationships:

```python
class Institution(Base, BaseMixin):
    # ...
    users = relationship("User", back_populates="institution", cascade="all, delete-orphan")
    courses = relationship("Course", back_populates="institution", cascade="all, delete-orphan")
    venues = relationship("Venue", back_populates="institution", cascade="all, delete-orphan")
```

#### Foreign Key Constraint Updates
Added `ondelete="CASCADE"` to all relevant foreign keys:

**Direct Institution References:**
- `users.institution_id`
- `courses.institution_id`
- `venues.institution_id`
- `semesters.institution_id`
- `announcements.institution_id`
- `testimonials.institution_id`
- `platform_issues.institution_id`
- `reports_schedule.institution_id`

**User References (cascade through users):**
- `notifications.user_id`
- `announcements.requested_by_user_id`
- `testimonials.user_id`
- `platform_issues.user_id`
- `reports_schedule.requested_by_user_id`
- `facial_data.user_id`
- `attendance_records.student_id`
- `attendance_records.lecturer_id`
- `attendance_appeals.student_id`

**Course & Class References:**
- `course_users.course_id`
- `course_users.user_id`
- `course_users.semester_id`
- `classes.course_id`
- `classes.semester_id`
- `classes.venue_id`
- `classes.lecturer_id`
- `attendance_records.class_id`
- `attendance_appeals.attendance_id`

### 2. Institution Entity (`application/entities2/institution.py`)

Added a `delete()` method to the `InstitutionModel` class:

```python
def delete(self, institution_id: int) -> bool:
    """Delete an institution and all related data (cascade delete).
    
    This will automatically delete:
    - All users associated with the institution
    - All courses associated with the institution
    - All venues associated with the institution
    - All semesters associated with the institution
    - All announcements associated with the institution
    - All testimonials associated with the institution
    - All platform issues associated with the institution
    - All report schedules associated with the institution
    - And all nested relationships (classes, attendance records, etc.)
    
    Args:
        institution_id: The ID of the institution to delete
        
    Returns:
        True if deletion was successful, False if institution not found
    """
    institution = self.get_by_id(institution_id)
    if not institution:
        return False
    
    try:
        self.session.delete(institution)
        self.session.commit()
        return True
    except Exception as e:
        self.session.rollback()
        raise e
```

### 3. Database Migration Script

Created `database/add_institution_cascade_delete.py` to apply the CASCADE constraints to existing databases.

## Cascade Delete Chain

When an institution is deleted, the following happens automatically:

```
Institution (deleted)
├── Users (all deleted)
│   ├── Notifications (all deleted)
│   ├── Facial Data (all deleted)
│   ├── Course Enrollments (all deleted)
│   ├── Attendance Records (as student, all deleted)
│   │   └── Attendance Appeals (all deleted)
│   └── Classes (as lecturer, all deleted)
│       └── Attendance Records (all deleted)
│           └── Attendance Appeals (all deleted)
├── Courses (all deleted)
│   ├── Course Enrollments (all deleted)
│   └── Classes (all deleted)
│       └── Attendance Records (all deleted)
│           └── Attendance Appeals (all deleted)
├── Venues (all deleted)
│   └── Classes (all deleted)
│       └── Attendance Records (all deleted)
│           └── Attendance Appeals (all deleted)
├── Semesters (all deleted)
│   ├── Course Enrollments (all deleted)
│   └── Classes (all deleted)
│       └── Attendance Records (all deleted)
│           └── Attendance Appeals (all deleted)
├── Announcements (all deleted)
├── Testimonials (all deleted)
├── Platform Issues (all deleted)
└── Report Schedules (all deleted)
```

## How to Use

### In Python Code

```python
from database.base import get_session
from application.entities2.institution import InstitutionModel

with get_session() as session:
    institution_model = InstitutionModel(session)
    
    # Delete an institution and all its data
    success = institution_model.delete(institution_id=123)
    
    if success:
        print("Institution and all related data deleted successfully")
    else:
        print("Institution not found")
```

### Applying to Existing Database

Run the migration script to update foreign key constraints in your existing database:

```bash
python database/add_institution_cascade_delete.py
```

This script will:
1. Identify all foreign key constraints that need CASCADE delete
2. Drop the existing constraints
3. Recreate them with CASCADE delete
4. Report success/failure for each constraint

## Important Notes

1. **Data Loss Warning**: Once an institution is deleted, ALL related data is permanently removed. This operation cannot be undone.

2. **Transaction Safety**: The delete operation is wrapped in a transaction. If any error occurs during deletion, the entire operation is rolled back.

3. **Database Level**: CASCADE delete works at the database level, so even direct SQL DELETE statements will trigger the cascade.

4. **Testing**: Always test cascade delete in a development/staging environment before applying to production.

5. **Backup**: Ensure you have recent backups before performing bulk deletions.

## Testing

To test the cascade delete functionality:

```python
# Create a test institution with related data
with get_session() as session:
    institution_model = InstitutionModel(session)
    user_model = UserModel(session)
    course_model = CourseModel(session)
    
    # Create institution
    institution = institution_model.create(
        name="Test Institution",
        address="123 Test St"
    )
    
    # Create users
    user = user_model.create(
        institution_id=institution.institution_id,
        name="Test User",
        email="test@test.com",
        role="student"
    )
    
    # Create course
    course = course_model.create(
        institution_id=institution.institution_id,
        code="TEST101",
        name="Test Course"
    )
    
    # Verify data exists
    assert user_model.count_by_institution(institution.institution_id) > 0
    
    # Delete institution
    institution_model.delete(institution.institution_id)
    
    # Verify cascade: users should be gone
    assert user_model.count_by_institution(institution.institution_id) == 0
```

## Related Files Modified

1. `database/models.py` - Added CASCADE constraints to all foreign keys
2. `application/entities2/institution.py` - Added delete() method
3. `database/add_institution_cascade_delete.py` - New migration script

## Migration Checklist

- [x] Update SQLAlchemy models with cascade relationships
- [x] Add ondelete="CASCADE" to all foreign key constraints
- [x] Implement delete() method in InstitutionModel
- [x] Create database migration script
- [ ] Run migration script on development database
- [ ] Test cascade delete with sample data
- [ ] Run migration script on staging database
- [ ] Test on staging environment
- [ ] Create database backup before production deployment
- [ ] Run migration script on production database
- [ ] Monitor for any issues after deployment
