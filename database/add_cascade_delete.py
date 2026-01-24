"""
Migration script to add CASCADE delete to foreign key constraints.
Run this to update the database schema.
"""

from sqlalchemy import text
from base import engine

def add_cascade_constraints():
    """Add CASCADE delete to foreign key constraints"""
    
    with engine.connect() as conn:
        print("Starting migration to add CASCADE delete constraints...")
        
        try:
            # Drop existing foreign key constraints
            print("1. Dropping existing foreign key constraint on attendance_appeals...")
            conn.execute(text("""
                ALTER TABLE attendance_appeals 
                DROP FOREIGN KEY attendance_appeals_ibfk_1
            """))
            conn.commit()
            
            print("2. Dropping existing foreign key constraint on attendance_records...")
            conn.execute(text("""
                ALTER TABLE attendance_records 
                DROP FOREIGN KEY attendance_records_ibfk_1
            """))
            conn.commit()
            
            # Add new foreign key constraints with CASCADE
            print("3. Adding CASCADE constraint to attendance_records.class_id...")
            conn.execute(text("""
                ALTER TABLE attendance_records
                ADD CONSTRAINT attendance_records_ibfk_1 
                FOREIGN KEY (class_id) 
                REFERENCES classes(class_id) 
                ON DELETE CASCADE
            """))
            conn.commit()
            
            print("4. Adding CASCADE constraint to attendance_appeals.attendance_id...")
            conn.execute(text("""
                ALTER TABLE attendance_appeals
                ADD CONSTRAINT attendance_appeals_ibfk_1 
                FOREIGN KEY (attendance_id) 
                REFERENCES attendance_records(attendance_id) 
                ON DELETE CASCADE
            """))
            conn.commit()
            
            print("\n✅ Migration completed successfully!")
            print("Foreign keys now have CASCADE delete enabled:")
            print("  - attendance_records.class_id → classes.class_id (CASCADE)")
            print("  - attendance_appeals.attendance_id → attendance_records.attendance_id (CASCADE)")
            
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            print("\nNote: If constraints have different names, you may need to:")
            print("1. Check actual constraint names: SHOW CREATE TABLE attendance_appeals;")
            print("2. Update the constraint names in this script")
            raise

if __name__ == "__main__":
    add_cascade_constraints()
