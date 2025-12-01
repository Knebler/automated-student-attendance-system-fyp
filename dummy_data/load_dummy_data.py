#!/usr/bin/env python3
"""
Standalone script to populate the database with dummy data.
Run this separately from your Flask app.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def load_dummy_data():
    """Load dummy data into the database"""
    try:
        # Connect to MySQL
        conn = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', ''),
            port=int(os.getenv('MYSQL_PORT', '3306')),
            database=os.getenv('MYSQL_DB', 'attendance_system')
        )
        
        cursor = conn.cursor()
        
        # Import the populate function
        from helper.db.populate_dummy_data import populate_dummy_data
        
        # Clear existing data (optional - be careful!)
        clear_existing = input("Clear existing data before loading? (y/n): ").lower() == 'y'
        
        if clear_existing:
            print("Clearing existing data...")
            # Get all tables in reverse order of dependencies
            tables = [
                'Attendance_Records',
                'Sessions',
                'Enrollments',
                'Course_Lecturers',
                'Students',
                'Lecturers',
                'Courses',
                'Timetable_Slots',
                'Venues',
                'Institution_Admins',
                'Institutions',
                'Assignments',
                'Subscriptions',
                'Unregistered_Users',
                'Subscription_Plans',
                'Platform_Managers'
            ]
            
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            for table in tables:
                try:
                    cursor.execute(f"TRUNCATE TABLE {table}")
                    print(f"  Cleared {table}")
                except:
                    print(f"  Skipped {table} (might not exist)")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        
        # Populate with dummy data
        populate_dummy_data(conn, cursor)
        
        cursor.close()
        conn.close()
        
        print("\nDummy data loaded successfully!")
        
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    print("=" * 50)
    print("ATTENDANCE SYSTEM - DUMMY DATA LOADER")
    print("=" * 50)
    
    confirm = input("This will populate the database with dummy data. Continue? (y/n): ")
    
    if confirm.lower() == 'y':
        load_dummy_data()
    else:
        print("Operation cancelled.")