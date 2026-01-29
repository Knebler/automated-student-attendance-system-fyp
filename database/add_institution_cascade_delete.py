"""
Migration script to add CASCADE delete to all institution-related foreign key constraints.
This ensures that when an institution is deleted, all related data is automatically deleted.

Run this after updating models.py with cascade delete relationships.
"""

from sqlalchemy import text, inspect
from base import engine

def get_foreign_key_name(table_name, column_name):
    """Get the actual foreign key constraint name from the database"""
    inspector = inspect(engine)
    foreign_keys = inspector.get_foreign_keys(table_name)
    
    for fk in foreign_keys:
        if column_name in fk['constrained_columns']:
            return fk['name']
    return None

def add_cascade_to_foreign_key(conn, table_name, column_name, reference_table, reference_column, constraint_suffix=None):
    """Drop and recreate a foreign key with CASCADE delete"""
    try:
        # Get the actual constraint name
        fk_name = get_foreign_key_name(table_name, column_name)
        
        if not fk_name:
            print(f"  ⚠️  No foreign key found for {table_name}.{column_name}")
            return False
        
        print(f"  - Dropping constraint {fk_name} from {table_name}...")
        conn.execute(text(f"ALTER TABLE {table_name} DROP FOREIGN KEY {fk_name}"))
        conn.commit()
        
        print(f"  - Adding CASCADE constraint to {table_name}.{column_name}...")
        conn.execute(text(f"""
            ALTER TABLE {table_name}
            ADD CONSTRAINT {fk_name}
            FOREIGN KEY ({column_name}) 
            REFERENCES {reference_table}({reference_column}) 
            ON DELETE CASCADE
        """))
        conn.commit()
        
        print(f"  ✅ Updated {table_name}.{column_name}")
        return True
        
    except Exception as e:
        print(f"  ❌ Error with {table_name}.{column_name}: {e}")
        return False

def add_institution_cascade_constraints():
    """Add CASCADE delete to all institution-related foreign keys"""
    
    with engine.connect() as conn:
        print("=" * 70)
        print("Starting migration to add CASCADE delete for institutions...")
        print("=" * 70)
        print()
        
        success_count = 0
        total_count = 0
        
        # Define all foreign keys that need CASCADE delete
        foreign_keys = [
            # Direct institution relationships
            ("users", "institution_id", "institutions", "institution_id"),
            ("courses", "institution_id", "institutions", "institution_id"),
            ("venues", "institution_id", "institutions", "institution_id"),
            ("semesters", "institution_id", "institutions", "institution_id"),
            ("announcements", "institution_id", "institutions", "institution_id"),
            ("testimonials", "institution_id", "institutions", "institution_id"),
            ("platform_issues", "institution_id", "institutions", "institution_id"),
            ("reports_schedule", "institution_id", "institutions", "institution_id"),
            
            # User relationships (cascade from users)
            ("notifications", "user_id", "users", "user_id"),
            ("announcements", "requested_by_user_id", "users", "user_id"),
            ("testimonials", "user_id", "users", "user_id"),
            ("platform_issues", "user_id", "users", "user_id"),
            ("reports_schedule", "requested_by_user_id", "users", "user_id"),
            ("facial_data", "user_id", "users", "user_id"),
            
            # Course relationships
            ("course_users", "course_id", "courses", "course_id"),
            ("course_users", "user_id", "users", "user_id"),
            ("course_users", "semester_id", "semesters", "semester_id"),
            
            # Class relationships
            ("classes", "course_id", "courses", "course_id"),
            ("classes", "semester_id", "semesters", "semester_id"),
            ("classes", "venue_id", "venues", "venue_id"),
            ("classes", "lecturer_id", "users", "user_id"),
            
            # Attendance relationships
            ("attendance_records", "class_id", "classes", "class_id"),
            ("attendance_records", "student_id", "users", "user_id"),
            ("attendance_records", "lecturer_id", "users", "user_id"),
            
            # Attendance appeal relationships
            ("attendance_appeals", "attendance_id", "attendance_records", "attendance_id"),
            ("attendance_appeals", "student_id", "users", "user_id"),
        ]
        
        print(f"Found {len(foreign_keys)} foreign keys to update\n")
        
        for table, column, ref_table, ref_column in foreign_keys:
            total_count += 1
            print(f"[{total_count}/{len(foreign_keys)}] Processing {table}.{column}...")
            
            if add_cascade_to_foreign_key(conn, table, column, ref_table, ref_column):
                success_count += 1
            print()
        
        print("=" * 70)
        print(f"Migration completed: {success_count}/{total_count} foreign keys updated")
        print("=" * 70)
        print()
        
        if success_count == total_count:
            print("✅ All foreign keys successfully updated with CASCADE delete!")
            print()
            print("What this means:")
            print("  - Deleting an institution will automatically delete:")
            print("    • All users in that institution")
            print("    • All courses in that institution")
            print("    • All venues in that institution")
            print("    • All semesters in that institution")
            print("    • All classes in that institution")
            print("    • All attendance records for those classes")
            print("    • All notifications for those users")
            print("    • All announcements for that institution")
            print("    • All testimonials from that institution")
            print("    • All platform issues from that institution")
            print("    • And more!")
        else:
            print(f"⚠️  Warning: Only {success_count} out of {total_count} updates succeeded")
            print("Please check the errors above and run again if needed")

if __name__ == "__main__":
    try:
        add_institution_cascade_constraints()
    except Exception as e:
        print(f"\n❌ Migration failed with error: {e}")
        print("\nPlease check the database connection and try again")
        raise
