"""
Migration Script: Add Audit Fields to Attendance Records
Date: 2026-02-08
Description: Adds audit_status, audited_at, and audited_by fields to the attendance_records table
             to support attendance auditing using facial recognition
"""

from sqlalchemy import text
from datetime import datetime
import sys
import os

# Add parent directory to path to import base and models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from base import engine, get_session

def migrate_up():
    """Add audit fields to attendance_records table"""
    print("Starting migration: add_audit_fields_to_attendance_records")
    
    try:
        with engine.begin() as conn:
            # Check if columns already exist
            print("  Checking if audit columns already exist...")
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = DATABASE()
                AND table_name = 'attendance_records' 
                AND column_name IN ('audit_status', 'audited_at', 'audited_by')
            """))
            existing_columns = [row[0] for row in result]
            
            if 'audit_status' in existing_columns:
                print("  Audit columns already exist, skipping creation")
                return True
            
            # Add audit_status column (MySQL ENUM)
            print("  Adding audit_status column...")
            conn.execute(text("""
                ALTER TABLE attendance_records 
                ADD COLUMN audit_status ENUM('no_audit', 'pass', 'fail') NOT NULL DEFAULT 'no_audit'
            """))
            print("✓ Added audit_status column")
            
            # Add audited_at column
            print("  Adding audited_at column...")
            conn.execute(text("""
                ALTER TABLE attendance_records 
                ADD COLUMN audited_at DATETIME NULL
            """))
            print("✓ Added audited_at column")
            
            # Add audited_by column (references users table)
            print("  Adding audited_by column...")
            conn.execute(text("""
                ALTER TABLE attendance_records 
                ADD COLUMN audited_by INT NULL
            """))
            print("✓ Added audited_by column")
            
            # Add foreign key constraint
            print("  Adding foreign key constraint...")
            conn.execute(text("""
                ALTER TABLE attendance_records 
                ADD CONSTRAINT fk_audited_by 
                FOREIGN KEY (audited_by) 
                REFERENCES users(user_id) 
                ON DELETE CASCADE
            """))
            print("✓ Added foreign key constraint")
            
            # Create index on audit_status for faster queries
            print("  Creating index on audit_status...")
            conn.execute(text("""
                CREATE INDEX idx_attendance_audit_status 
                ON attendance_records(audit_status)
            """))
            print("✓ Created index on audit_status")
        
        print("✓ Migration completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def migrate_down():
    """Remove audit fields from attendance_records table (rollback)"""
    print("Rolling back migration: add_audit_fields_to_attendance_records")
    
    try:
        with engine.begin() as conn:
            # Drop the index
            print("  Dropping index idx_attendance_audit_status...")
            conn.execute(text("""
                DROP INDEX IF EXISTS idx_attendance_audit_status ON attendance_records
            """))
            print("✓ Dropped index")
            
            # Drop foreign key constraint
            print("  Dropping foreign key constraint...")
            conn.execute(text("""
                ALTER TABLE attendance_records 
                DROP FOREIGN KEY IF EXISTS fk_audited_by
            """))
            print("✓ Dropped foreign key constraint")
            
            # Drop columns
            print("  Dropping audit columns...")
            conn.execute(text("""
                ALTER TABLE attendance_records 
                DROP COLUMN IF EXISTS audit_status,
                DROP COLUMN IF EXISTS audited_at,
                DROP COLUMN IF EXISTS audited_by
            """))
            print("✓ Dropped audit columns")
        
        print("✓ Rollback completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Rollback failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate attendance records to add audit fields')
    parser.add_argument('--down', action='store_true', help='Rollback the migration')
    args = parser.parse_args()
    
    if args.down:
        success = migrate_down()
    else:
        success = migrate_up()
    
    sys.exit(0 if success else 1)
