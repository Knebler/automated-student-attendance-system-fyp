#!/usr/bin/env python3
"""
Standalone script to populate the database with dummy data.
Updated for Azure MySQL with SSL support.
Run this separately from your Flask app.
"""

import ssl
import os
import mysql.connector
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

def get_ssl_context():
    """Create SSL context for Azure MySQL"""
    ssl_context = ssl.create_default_context(cafile='./combined-ca-certificates.pem')
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    return ssl_context

def load_dummy_data():
    """Load dummy data into the Azure MySQL database"""
    try:
        # Check if SSL certificate exists
        ssl_cert_path = os.getenv('DB_SSL_CA', './combined-ca-certificates.pem')
        if not os.path.exists(ssl_cert_path):
            print(f"SSL certificate not found at {ssl_cert_path}")
            print("Download it using: curl -o DigiCertGlobalRootCA.crt https://cacerts.digicert.com/DigiCertGlobalRootCA.crt")
            print("Download DigiCertGlobalRootG2.crt.pem from: https://www.digicert.com/CACerts/DigiCertGlobalRootG2.crt.pem")
            print("Download Microsoft RSA Root Certificate Authority 2017.crt from: https://aka.ms/MicrosoftRSA2017")
            print("Convert Microsoft RSA Root Certificate Authority 2017.crt to PEM format.")
            print("Then create combined-ca-certificates.pem by concatenating the downloaded certs.")
            return
        
        # Connect to Azure MySQL with SSL
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            port=int(os.getenv('DB_PORT')),
            database=os.getenv('DB_NAME'),
            ssl_ca=ssl_cert_path,
            ssl_verify_cert=True,
            ssl_disabled=False
        )
        
        cursor = conn.cursor()
        
        # Test connection
        cursor.execute("SELECT DATABASE(), VERSION()")
        db_info = cursor.fetchone()
        print(f"Connected to database: {db_info[0]}")
        print(f"MySQL Version: {db_info[1]}")
        
        # Check current table counts
        print("\n📋 Current table status:")
        cursor.execute("""
            SELECT table_name, table_rows 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE()
            ORDER BY table_name
        """)
        
        for table_name, row_count in cursor.fetchall():
            print(f"  {table_name}: {row_count} rows")
        
        # Clear existing data (optional - be careful!)
        clear_existing = input("\nClear existing data before loading? (y/n): ").lower() == 'y'
        
        if clear_existing:
            print("\nClearing existing data...")
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
                'Platform_Issues',  # New table
                'Reports',          # New table
                'Subscription_Plans',
                'Platform_Managers'
            ]
            
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            for table in tables:
                try:
                    cursor.execute(f"DELETE FROM {table}")
                    conn.commit()
                    cursor.execute(f"ALTER TABLE {table} AUTO_INCREMENT = 1")
                    print(f"Cleared {table}")
                except mysql.connector.Error as e:
                    print(f"Skipped {table}: {e.msg}")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            conn.commit()
        
        # Check if we need to populate basic data
        cursor.execute("SELECT COUNT(*) FROM Subscription_Plans")
        plan_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM Platform_Managers")
        mgr_count = cursor.fetchone()[0]
        
        if plan_count == 0 or mgr_count == 0:
            print("\nLoading basic configuration data...")
            
            # Insert basic subscription plans if none exist
            if plan_count == 0:
                cols = [
                    'plan_name', 'description', 'price_per_cycle', 'billing_cycle', 'max_students', 'max_courses', 'max_lecturers', 'features',
                ]
                subscription_plans = [
                    ('Starter Plan', 'Perfect for small institutions', 99.99, 'monthly', 500, 50, 20, 
                     '{"facial_recognition": true, "basic_reporting": true, "email_support": true}'),
                    ('Professional Plan', 'For growing institutions', 199.99, 'monthly', 2000, 200, 50,
                     '{"facial_recognition": true, "advanced_reporting": true, "priority_support": true, "api_access": true}'),
                    ('Enterprise Plan', 'For large institutions', 499.99, 'annual', 10000, 500, 200,
                     '{"facial_recognition": true, "custom_reporting": true, "24/7_support": true, "api_access": true, "custom_integrations": true}')
                ]
                
                cursor.executemany(f"""
                    INSERT INTO Subscription_Plans
                    ({", ".join(cols)})
                    VALUES ({", ".join(['%s'] * len(cols))})
                """, subscription_plans)
                print(f"Added {len(subscription_plans)} subscription plans")
            
            # Insert platform managers if none exist
            if mgr_count == 0:
                cursor.execute("""
                    INSERT INTO Platform_Managers (email, password_hash, full_name)
                    VALUES ('admin@attendanceplatform.com', '$2b$10$examplehash', 'System Administrator')
                """)
                print("Added platform manager")
            
            conn.commit()
        
        # Populate with comprehensive dummy data
        print("\nLoading comprehensive dummy data...")
        populate_comprehensive_data(conn, cursor)
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 50)
        print("DUMMY DATA LOADED SUCCESSFULLY!")
        print("=" * 50)
        
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

def populate_comprehensive_data(conn, cursor):
    """Populate database with comprehensive dummy data"""
    from datetime import datetime, timedelta, date
    import random
    import bcrypt
    
    print("Populating Institutions and Users...")
    now = datetime.now()
    
    # Hash password for all test accounts
    test_password = "password"
    password_hash = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # 1. Create unregistered users
    cols = [
        'email', 'full_name', 'institution_name', 'institution_address',
        'phone_number', 'message', 'selected_plan_id', 'status',
        'reviewed_by', 'reviewed_at', 'response_message', 'applied_at',
    ]
    unregistered_users = [
        ('john.doe@university.edu', 'John Doe', 'University of Technology', '123 Campus Road', '1234567890', 
         'Interested in Starter Plan', 1, 'approved', 1, now, 'Approved for trial', now),
        ('jane.smith@college.edu', 'Jane Smith', 'City College', '456 College Ave', '0987654321',
         'Need Professional Plan for our campus', 2, 'approved', 1, now, 'Approved', now),
        ('admin@university.edu', 'University Admin', 'University Test', '789 Test Street', '5551234567',
         'Test institution setup', 1, 'approved', 1, now, 'Test account approved', now),
    ]
    
    cursor.executemany(f"""
        INSERT INTO Unregistered_Users 
        ({", ".join(cols)})
        VALUES ({", ".join(['%s'] * len(cols))})
    """, unregistered_users)
    conn.commit()
    print(f"Added {len(unregistered_users)} unregistered users")
    
    # 2. Create subscriptions
    cursor.execute("""
        INSERT INTO Subscriptions (unreg_user_id, plan_id, start_date, end_date, status)
        VALUES 
        (1, 1, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 1 YEAR), 'active'),
        (2, 2, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 1 YEAR), 'active'),
        (3, 1, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 1 YEAR), 'active')
    """)
    conn.commit()
    print("Added subscriptions")
    
    # 3. Create assignments
    cursor.execute("""
        INSERT INTO Assignments (platform_mgr_id, unreg_user_id, subscription_id, notes)
        VALUES (1, 1, 1, 'Initial setup for University of Technology'),
               (1, 2, 2, 'Professional setup for City College'),
               (1, 3, 3, 'Test institution setup')
    """)
    conn.commit()
    print("Added assignments")
    
    # 4. Create institutions
    cols = ['name', 'address', 'website', 'subscription_id']
    institutions = [
        ('University of Technology', '123 Campus Road, Tech City', 'https://utech.edu', 1),
        ('City College', '456 College Ave, Metro City', 'https://citycollege.edu', 2),
        ('University Test', '789 Test Street, Test City', 'https://university.test.edu', 3)
    ]
    
    cursor.executemany(f"""
        INSERT INTO Institutions ({", ".join(cols)})
        VALUES ({", ".join(['%s'] * len(cols))})
    """, institutions)
    conn.commit()
    print(f"Added {len(institutions)} institutions")
    
    # 5. Create institution admins - INCLUDING TESTER ACCOUNT
    cursor.execute("""
        INSERT INTO Institution_Admins (email, password_hash, full_name, institution_id)
        VALUES 
        ('admin@utech.edu', %s, 'Dr. Robert Chen', 1),
        ('admin@citycollege.edu', %s, 'Prof. Sarah Johnson', 2),
        ('admin@university.edu', %s, 'University Admin', 3)  -- TESTER ACCOUNT
    """, (password_hash, password_hash, password_hash))
    conn.commit()
    print("Added institution admins")
    
    print("Populating Academic Structure...")

    # 6. Create venues for all institutions
    cols = ['institution_id', 'venue_name', 'building', 'capacity', 'facilities']
    venues_data = [
        (1, 'Lecture Hall A', 'Science Building', 200, '{"projector": true, "ac": true, "whiteboard": true}'),
        (1, 'Lab 101', 'Computer Building', 40, '{"computers": 40, "projector": true, "ac": true}'),
        (1, 'Seminar Room 3', 'Business Building', 50, '{"projector": true, "ac": true}'),
        (2, 'Main Auditorium', 'Central Building', 300, '{"projector": true, "sound_system": true, "ac": true}'),
        (2, 'Computer Lab', 'IT Center', 60, '{"computers": 60, "projector": true}'),
        (3, 'Main Hall', 'Test Building', 150, '{"projector": true, "ac": true, "whiteboard": true}'),  # Test institution
        (3, 'Lab 201', 'Tech Building', 30, '{"computers": 30, "projector": true}'),  # Test institution
    ]
    
    cursor.executemany(f"""
        INSERT INTO Venues ({", ".join(cols)})
        VALUES ({", ".join(['%s'] * len(cols))})
    """, venues_data)
    conn.commit()
    print(f"Added {len(venues_data)} venues")
    
    # 7. Create timetable slots for all institutions
    cols = ['institution_id', 'day_of_week', 'start_time', 'end_time', 'slot_name']
    timetable_slots = [
        (1, 1, '09:00:00', '10:30:00', 'Morning Slot 1'),
        (1, 1, '11:00:00', '12:30:00', 'Morning Slot 2'),
        (1, 2, '14:00:00', '15:30:00', 'Afternoon Slot 1'),
        (2, 1, '10:00:00', '11:30:00', 'Morning Session'),
        (2, 2, '13:00:00', '14:30:00', 'Afternoon Session'),
        (3, 1, '08:30:00', '10:00:00', 'Early Morning'),  # Test institution
        (3, 1, '10:30:00', '12:00:00', 'Late Morning'),   # Test institution
    ]
    
    cursor.executemany(f"""
        INSERT INTO Timetable_Slots ({", ".join(cols)})
        VALUES ({", ".join(['%s'] * len(cols))})
    """, timetable_slots)
    conn.commit()
    print(f"Added {len(timetable_slots)} timetable slots")
    
    # 8. Create lecturers - INCLUDING TESTER ACCOUNT
    cols = ['institution_id', 'age', 'gender', 'phone_number',
            'email', 'password_hash', 'full_name', 'department', 'year_joined',]
    lecturers = [
        (1, 30, 'Male', '1234567890', 'prof.zhang@utech.edu', password_hash, 'Professor Zhang Wei', 'Computer Science', 2022),
        (1, 25, 'Female', '9876543210', 'dr.lee@utech.edu', password_hash, 'Dr. Lee Min Ho', 'Mathematics', 2021),
        (2, 28, 'Male', '5555555555', 'mr.jones@citycollege.edu', password_hash, 'Mr. David Jones', 'Business Studies', 2020),
        (2, 31, 'Female', '1111111111', 'ms.garcia@citycollege.edu', password_hash, 'Ms. Maria Garcia', 'Information Technology', 2010),
        (3, 32, 'Male', '9999999999', 'prof.smith@university.edu', password_hash, 'Professor John Smith', 'Computer Science', 2023),  # TESTER ACCOUNT
        (3, 27, 'Female', '8888888888', 'dr.jones@university.edu', password_hash, 'Dr. Emily Jones', 'Mathematics', 2025),  # Test institution
    ]
    
    cursor.executemany(f"""
        INSERT INTO Lecturers ({", ".join(cols)})
        VALUES ({", ".join(['%s'] * len(cols))})
    """, lecturers)
    conn.commit()
    print(f"Added {len(lecturers)} lecturers")
    
    # 9. Create courses
    cols = ['institution_id', 'course_code', 'course_name', 'description', 'credits', 'start_date', 'end_date']
    courses = [
        (1, 'CS101', 'Introduction to Programming', 'Basic programming concepts using Python', 3, date(2023, 1, 1), date(2023, 6, 30)),
        (1, 'MATH201', 'Calculus I', 'Differential and integral calculus', 4, date(2023, 7, 1), date(2023, 12, 31)),
        (1, 'CS301', 'Database Systems', 'Relational database design and SQL', 3, date(2023, 1, 1), date(2023, 6, 30)),
        (2, 'BUS101', 'Business Fundamentals', 'Introduction to business concepts', 3, date(2023, 1, 1), date(2023, 6, 30)),
        (2, 'IT102', 'Web Development', 'HTML, CSS, and JavaScript fundamentals', 3, date(2023, 7, 1), date(2023, 12, 31)),
        (3, 'TEST101', 'Test Course 1', 'Introduction to Testing', 3, date(2023, 1, 1), date(2023, 6, 30)),  # Test institution
        (3, 'TEST201', 'Test Course 2', 'Advanced Testing Methods', 4, date(2023, 7, 1), date(2023, 12, 31)),  # Test institution
    ]
    
    cursor.executemany(f"""
        INSERT INTO Courses ({", ".join(cols)})
        VALUES ({", ".join(['%s'] * len(cols))})
    """, courses)
    conn.commit()
    print(f"Added {len(courses)} courses")
    
    # 10. Assign lecturers to courses
    for course_id, course in enumerate(courses):
        possible_lecturers = [idx for idx, lecturer in enumerate(lecturers) if lecturer[0] == course[0]]
        chosen_lecturer_idx = random.choice(possible_lecturers)
        cursor.execute("""
            INSERT INTO Course_Lecturers (course_id, lecturer_id)
            VALUES (%s, %s)
        """, (course_id+1, chosen_lecturer_idx+1))
        # Randomly assigns a lecturer from the same institution
    conn.commit()
    print(f"Assigned lecturers to {len(courses)} courses")
    
    print("Populating Students and Enrollments...")
    
    # 11. Create students for all institutions - INCLUDING TESTER ACCOUNT
    cols = ['institution_id', 'student_code', 'age', 'gender',
            'phone_number', 'email', 'password_hash', 'full_name', 'enrollment_year']
    students_data = [
        # Institution 1
        (1, 'S001', 22, 'female', '91234567', 'alice.wong@utech.edu', password_hash, 'Alice Wong', 2023),
        (1, 'S002', 24, 'male', '12345678', 'bob.smith@utech.edu', password_hash, 'Bob Smith', 2023),
        (1, 'S003', 25, 'male', '85432298', 'charlie.brown@utech.edu', password_hash, 'Charlie Brown', 2022),
        (1, 'S004', 21, 'other', '84564569', 'diana.ross@utech.edu', password_hash, 'Diana Ross', 2022),
        # Institution 2
        (2, 'CC001', 23, 'female', '96546548', 'emma.johnson@citycollege.edu', password_hash, 'Emma Johnson', 2023),
        (2, 'CC002', 24, 'male', '98765432', 'frank.miller@citycollege.edu', password_hash, 'Frank Miller', 2023),
        (2, 'CC003', 25, 'female', '87654321', 'grace.williams@citycollege.edu', password_hash, 'Grace Williams', 2022),
        # Institution 3 (Test) - INCLUDING TESTER ACCOUNT
        (3, 'TEST001', 21, 'male', '96546548', 'student1@university.edu', password_hash, 'Test Student 1', 2023),  # TESTER ACCOUNT
        (3, 'TEST002', 21, 'female', '+010 731 96 8318', 'student2@university.edu', password_hash, 'Test Student 2', 2023),
        (3, 'TEST003', 21, 'other', '+65 98765432', 'student3@university.edu', password_hash, 'Test Student 3', 2022),
    ]
    
    cursor.executemany(f"""
        INSERT INTO Students ({", ".join(cols)})
        VALUES ({", ".join(['%s'] * len(cols))})
    """, students_data)
    conn.commit()
    print(f"Added {len(students_data)} students")

    # 11b. Assigning students to courses
    for student_id, student in enumerate(students_data):
        possible_course_ids = [idx for idx, course in enumerate(courses) if course[0] == student[0]]
        chance_of_assigning = 0.8  # 80% chance of assigning a course from the same institution
        for course_id in possible_course_ids:
            if random.random() > chance_of_assigning:
                continue
            cursor.execute(f"""
                INSERT INTO Course_Students (course_id, student_id)
                VALUES (%s, %s)
            """, (course_id+1, student_id+1,))
        # Student has 80% chance of attending the course in the same institution
    conn.commit()
    print(f"Assigned students to {len(students_data)} courses")

    # 12. Create enrollments
    cols = ['student_id', 'course_id', 'academic_year', 'semester', 'status']
    enrollments = [
        # Institution 1
        (1, 1, '2023-2024', 'Fall', 'active'),   # Alice in CS101
        (1, 2, '2023-2024', 'Fall', 'active'),   # Alice in MATH201
        (2, 1, '2023-2024', 'Fall', 'active'),   # Bob in CS101
        (2, 3, '2023-2024', 'Fall', 'active'),   # Bob in CS301
        (3, 2, '2023-2024', 'Fall', 'active'),   # Charlie in MATH201
        # Institution 2
        (5, 4, '2023-2024', 'Fall', 'active'),   # Emma in BUS101
        (6, 5, '2023-2024', 'Fall', 'active'),   # Frank in IT102
        (7, 5, '2023-2024', 'Fall', 'active'),   # Grace in IT102
        # Institution 3 (Test) - TESTER STUDENT enrolled in TESTER LECTURER's course
        (8, 6, '2023-2024', 'Fall', 'active'),   # Test Student 1 in TEST101 (Prof. Smith's course)
        (8, 7, '2023-2024', 'Fall', 'active'),   # Test Student 1 in TEST201
        (9, 6, '2023-2024', 'Fall', 'active'),   # Test Student 2 in TEST101
        (10, 6, '2023-2024', 'Fall', 'active'),  # Test Student 3 in TEST101
    ]
    
    cursor.executemany(f"""
        INSERT INTO Enrollments ({", ".join(cols)})
        VALUES ({", ".join(['%s'] * len(cols))})
    """, enrollments)
    conn.commit()
    print(f"Added {len(enrollments)} enrollments")
    
    print("Populating Sessions and Attendance...")
    
    # 13. Create sessions for the past week
    today = datetime.now().date()
    dates = [(today - timedelta(days=i)) for i in range(7)]
    
    sessions = []
    # Track venue-date usage to avoid duplicates
    venue_date_usage = set()
    
    # Create sessions for each course on different days
    for course_id in range(1, 8):  # 7 courses total
        institution_id = 1 if course_id <= 3 else (2 if course_id <= 5 else 3)
        
        # Get available venues for this institution
        cursor.execute("SELECT venue_id FROM Venues WHERE institution_id = %s ORDER BY venue_id", (institution_id,))
        available_venues = [row[0] for row in cursor.fetchall()]
        
        for i, date in enumerate(dates[:2]):  # First 2 days for each course
            # Try each venue until we find an available one
            for venue_id in available_venues:
                if (venue_id, date) not in venue_date_usage:
                    venue_date_usage.add((venue_id, date))
                    # Determine lecturer_id based on course_id
                    if course_id == 1 or course_id == 3:
                        lecturer_id = 1
                    elif course_id == 2:
                        lecturer_id = 2
                    elif course_id == 4:
                        lecturer_id = 3
                    elif course_id == 5:
                        lecturer_id = 4
                    elif course_id == 6:
                        lecturer_id = 5  # Prof. Smith (TESTER)
                    elif course_id == 7:
                        lecturer_id = 6
                    
                    # Get slot based on institution and day
                    slot_id = 1 if i == 0 else 2
                    # Adjust slot for different institutions
                    if institution_id == 2:
                        slot_id = 4 if i == 0 else 5  # Slots 4-5 for institution 2
                    elif institution_id == 3:
                        slot_id = 6 if i == 0 else 7  # Slots 6-7 for institution 3
                    
                    sessions.append((
                        course_id, venue_id, slot_id, lecturer_id, date,
                        f'Lecture {i+1}: Course Introduction' if i == 0 else f'Lecture {i+1}: Advanced Topics',
                        'completed'
                    ))
                    break
    
    if sessions:
        cursor.executemany("""
            INSERT INTO Sessions (course_id, venue_id, slot_id, lecturer_id, session_date, session_topic, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, sessions)
        conn.commit()
        print(f"Created {len(sessions)} sessions")
    
    # 14. Create attendance records
    if sessions:
        attendance_records = []
        
        # Get all sessions
        cursor.execute("SELECT session_id, course_id FROM Sessions ORDER BY session_id")
        all_sessions = cursor.fetchall()
        
        # For each session, mark attendance for enrolled students
        for session_id, course_id in all_sessions:
            # Get students enrolled in this course
            cursor.execute("SELECT student_id FROM Enrollments WHERE course_id = %s", (course_id,))
            enrolled_students = [row[0] for row in cursor.fetchall()]
            
            for student_id in enrolled_students:
                # Random attendance status (80% present, 10% late, 5% absent, 5% excused)
                rand = random.random()
                if rand < 0.80:
                    status = 'present'
                elif rand < 0.90:
                    status = 'late'
                elif rand < 0.95:
                    status = 'absent'
                else:
                    status = 'excused'
                
                # Determine lecturer_id based on course_id
                lecturer_id_map = {
                    1: 1, 2: 2, 3: 1, 4: 3, 5: 4, 6: 5, 7: 6
                }
                lecturer_id = lecturer_id_map.get(course_id, 1)
                
                # Generate attendance time based on status
                attendance_time = None
                if status == 'present':
                    attendance_time = '09:15:00'
                elif status == 'late':
                    attendance_time = '09:45:00'
                
                attendance_records.append((
                    session_id, student_id, status, 'system', lecturer_id,
                    None, attendance_time,
                    'Auto-generated attendance'
                ))
        
        if attendance_records:
            cursor.executemany("""
                INSERT INTO Attendance_Records 
                (session_id, student_id, status, marked_by, lecturer_id, captured_image_path, attendance_time, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, attendance_records)
            conn.commit()
            print(f"Created {len(attendance_records)} attendance records")
    
    print("Populating Reports and Platform Issues...")
    
    # Update the Platform_Managers table with tester account FIRST (before any other operations)
    # This ensures the platform manager exists before being referenced
    print("Updating Platform Manager tester account...")
    
    # First, check if the platform manager already exists
    cursor.execute("SELECT COUNT(*) FROM Platform_Managers WHERE email = 'admin@attendanceplatform.com'")
    if cursor.fetchone()[0] == 0:
        # Insert the platform manager if not exists
        cursor.execute("""
            INSERT INTO Platform_Managers (email, password_hash, full_name)
            VALUES ('admin@attendanceplatform.com', %s, 'System Administrator')
        """, (password_hash,))
        conn.commit()
        print("Added platform manager tester account")
    else:
        # Update the password hash if exists
        cursor.execute("""
            UPDATE Platform_Managers 
            SET password_hash = %s 
            WHERE email = 'admin@attendanceplatform.com'
        """, (password_hash,))
        conn.commit()
        print("Updated platform manager tester account password")
    
    # 15. Create sample reports (simplified - without UUID)
    # Calculate dates
    seven_days_ago = datetime.now() - timedelta(days=7)
    thirty_days_ahead = datetime.now() + timedelta(days=30)
    seven_days_ahead = datetime.now() + timedelta(days=7)
    ninety_days_ahead = datetime.now() + timedelta(days=90)
    now = datetime.now()
    
    reports = [
        (
            'Attendance Summary Q1 2024',
            'Quarterly attendance report for all courses',
            'attendance_summary',
            1,
            'admin@utech.edu',
            'admin',
            '{"summary": {"total_sessions": 45, "attendance_rate": 85.5}, "details": []}',
            '{"date_range": "2024-01-01 to 2024-03-31"}',
            'pdf',
            'completed',
            120,
            2048000,
            '/reports/attendance_q1.pdf',
            'https://storage.example.com/reports/attendance_q1.pdf',
            'https://app.example.com/reports/preview/123',
            'once',
            '{}',
            None,
            seven_days_ago,
            thirty_days_ahead,
            None,
            None,
            False,
            None,
            '[]'
        ),
        
        (
            'Test Institution Weekly Report',
            'Weekly attendance for test courses',
            'course_attendance',
            3,
            'admin@university.edu',  # TESTER ADMIN
            'admin',
            '{"courses": ["TEST101", "TEST201"], "attendance_rate": 95.5, "students": []}',
            '{"week": 12}',
            'html',
            'completed',
            45,
            1024000,
            None,
            None,
            'https://app.example.com/reports/preview/125',
            'weekly',
            '{"day": "monday", "time": "08:00"}',
            seven_days_ahead,
            now,
            ninety_days_ahead,
            now,
            None,
            True,
            'test123',
            '[]'
        ),
    ]
    
    cursor.executemany("""
        INSERT INTO Reports 
        (title, description, report_type, institution_id, reporter_email, reporter_role,
         report_data, parameters, format, status, generation_time, file_size_bytes,
         file_path, storage_url, preview_url, schedule_type, schedule_config, next_scheduled_run,
         generated_at, expires_at, viewed_at, deleted_at, is_public, access_code, allowed_viewers)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, reports)
    conn.commit()
    
    # 16. Create sample platform issues
    print("Creating sample platform issues...")
    now = datetime.now()
    two_days_ago = now - timedelta(days=2)
    three_days_ago = now - timedelta(days=3)
    seven_days_ahead = now + timedelta(days=7)
    
    platform_issues = [
        (
            'student', 1, 'student1@university.edu', 1, 'Attendance not marked correctly',
            'My attendance was marked as absent when I was present in class yesterday.',
            'bug', 'attendance', 'high', 'major', 'Attendance Marking', '/attendance/mark',
            '{"browser": "Chrome", "version": "120.0", "os": "Windows 11"}', 'desktop',
            '/uploads/screenshots/issue1.png', None, '[]', 'new', None, None, None, None, None,
            None, None, now, now, None, None, None, False, None, None
        ),
    
        (   
            'lecturer', 1, 'prof.smith@university.edu', 1, 'Feature request: Bulk attendance marking',
            'Can we have a feature to mark attendance for multiple students at once?',
            'feature_request', 'attendance', 'medium', 'minor', 'Attendance Interface',
            '/lecturer/attendance', '{"browser": "Firefox", "version": "121.0", "os": "macOS"}', 'desktop',
            None, None, '[]', 'acknowledged', 1, now, None, None, None, None, None,
            now, now, now, None, None, False, None, None
        ),
    
        (
            'admin', 1, 'admin@university.edu', 1, 'Report generation slow',
            'Generating monthly reports takes more than 5 minutes.',
            'performance', 'reports', 'high', 'major', 'Reporting Module', '/reports/generate',
            '{"browser": "Safari", "version": "17.0", "os": "macOS"}', 'desktop',
            None, '/logs/report_slow.log', '[]', 'investigating', 1, two_days_ago,
            None, None, 2.0, 1.5, None,
            three_days_ago, now, None, None, None, False, 
            'Looks like a database query optimization issue', None
        ),
    ]
    
    cursor.executemany("""
        INSERT INTO Platform_Issues 
        (reporter_type, reporter_id, reporter_email, institution_id, title, description,
         issue_type, category, priority, severity, module, page_url, browser_info, device_type,
         screenshot_path, log_file_path, additional_files, status, assigned_to, assigned_at,
         resolution, resolution_notes, fix_version, estimated_hours, actual_hours, due_date,
         created_at, acknowledged_at, resolved_at, closed_at,
         reporter_notified, reporter_feedback, reporter_rating)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, platform_issues)
    conn.commit()
    
    print("\nTester Accounts Created:")
    print("  Platform Manager: admin@attendanceplatform.com / password")
    print("  Institution Admin: admin@university.edu / password")
    print("  Lecturer: prof.smith@university.edu / password")
    print("  Student: student1@university.edu / password")
    
    print("\nData Summary:")
    print("  • 3 Institutions (including Test Institution)")
    print("  • 3 Institution Admins")
    print("  • 6 Lecturers (including Prof. Smith)")
    print("  • 7 Courses")
    print("  • 10 Students (including Test Student 1)")
    print("  • 12 Enrollments")
    print(f"  • {len(sessions) if sessions else 0} Sessions")
    print(f"  • {len(attendance_records) if attendance_records else 0} Attendance Records")
    print("  • 2 Reports")
    print("  • 3 Platform Issues")

if __name__ == '__main__':
    print("=" * 60)
    print("ATTENDANCE SYSTEM - AZURE DUMMY DATA LOADER")
    print("=" * 60)
    
    print("\nIMPORTANT:")
    print("1. Ensure combined-ca-certificates.pem is in the current directory")
    print("2. Your .env file should contain Azure MySQL credentials")
    print("3. Database 'attendance_system' must exist in Azure")
    print("4. This script requires mysql-connector-python package")
    
    confirm = input("\nLoad dummy data into Azure MySQL? (y/n): ").lower()
    
    if confirm == 'y':
        # Install required packages if not present
        try:
            import mysql.connector
        except ImportError:
            print("Installing mysql-connector-python...")
            os.system("pip install mysql-connector-python")
        
        load_dummy_data()
    else:
        print("Operation cancelled.")