import random
from datetime import datetime, timedelta
import json

def populate_dummy_data(conn, cursor):
    """Populate database with realistic dummy data"""
    print("Populating database with dummy data...")
    
    try:
        # =============================================
        # 1. Platform Managers
        # =============================================
        print("Adding Platform Managers...")
        platform_managers = [
            ('admin@attendanceplatform.com', '$2b$10$examplehash', 'System Administrator'),
            ('manager@attendanceplatform.com', '$2b$10$examplehash2', 'John Manager')
        ]
        
        for email, password_hash, full_name in platform_managers:
            cursor.execute(
                "INSERT IGNORE INTO Platform_Managers (email, password_hash, full_name) VALUES (%s, %s, %s)",
                (email, password_hash, full_name)
            )
        
        platform_mgr_id = 1  # Assuming first manager
        
        # =============================================
        # 2. Subscription Plans
        # =============================================
        print("Adding Subscription Plans...")
        subscription_plans = [
            ('Starter Plan', 'Perfect for small institutions', 99.99, 'monthly', 500, 50, 20,
             '{"facial_recognition": true, "basic_reporting": true, "email_support": true}'),
            
            ('Pro Plan', 'For medium-sized institutions', 199.99, 'monthly', 2000, 200, 50,
             '{"facial_recognition": true, "advanced_reporting": true, "priority_support": true, "api_access": true}'),
            
            ('Enterprise Plan', 'For large institutions', 499.99, 'annual', 10000, 500, 200,
             '{"facial_recognition": true, "custom_reporting": true, "24/7_support": true, "api_access": true, "custom_integrations": true}')
        ]
        
        plan_ids = []
        for plan in subscription_plans:
            cursor.execute(
                """INSERT IGNORE INTO Subscription_Plans 
                (plan_name, description, price_per_cycle, billing_cycle, max_students, max_courses, max_lecturers, features) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                plan
            )
            plan_ids.append(cursor.lastrowid)
        
        # =============================================
        # 3. Unregistered Users (Institution Applications)
        # =============================================
        print("Adding Unregistered Users...")
        unregistered_users = [
            ('dean@university.edu', 'Dr. James Wilson', 'University of Technology', 
             '123 Education St, City', '+1234567890', 'Interested in Starter Plan', 1, 'approved', 1),
            
            ('principal@college.edu', 'Ms. Sarah Johnson', 'City College', 
             '456 Learning Ave, Town', '+0987654321', 'Need Pro Plan for 1500 students', 2, 'pending', None)
        ]
        
        unreg_user_ids = []
        for user in unregistered_users:
            cursor.execute(
                """INSERT IGNORE INTO Unregistered_Users 
                (email, full_name, institution_name, institution_address, phone_number, message, selected_plan_id, status, reviewed_by) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                user
            )
            unreg_user_ids.append(cursor.lastrowid)
        
        # =============================================
        # 4. Subscriptions
        # =============================================
        print("Adding Subscriptions...")
        subscriptions = [
            (unreg_user_ids[0], plan_ids[0], '2024-01-01', '2024-12-31', 'active', 'sub_123456789'),
            (unreg_user_ids[1], plan_ids[1], '2024-02-01', '2025-01-31', 'pending_payment', None)
        ]
        
        subscription_ids = []
        for sub in subscriptions:
            cursor.execute(
                """INSERT IGNORE INTO Subscriptions 
                (unreg_user_id, plan_id, start_date, end_date, status, stripe_subscription_id) 
                VALUES (%s, %s, %s, %s, %s, %s)""",
                sub
            )
            subscription_ids.append(cursor.lastrowid)
        
        # =============================================
        # 5. Assignments
        # =============================================
        print("Adding Assignments...")
        assignments = [
            (platform_mgr_id, unreg_user_ids[0], subscription_ids[0], 'Approved for Starter Plan'),
            (platform_mgr_id, unreg_user_ids[1], subscription_ids[1], 'Pending payment verification')
        ]
        
        for assignment in assignments:
            cursor.execute(
                """INSERT IGNORE INTO Assignments 
                (platform_mgr_id, unreg_user_id, subscription_id, notes) 
                VALUES (%s, %s, %s, %s)""",
                assignment
            )
        
        # =============================================
        # 6. Institutions
        # =============================================
        print("Adding Institutions...")
        institutions = [
            ('University of Technology', '123 Education St, City', 'https://university.edu', subscription_ids[0], True),
            ('City College', '456 Learning Ave, Town', 'https://citycollege.edu', subscription_ids[1], True)
        ]
        
        institution_ids = []
        for inst in institutions:
            cursor.execute(
                """INSERT IGNORE INTO Institutions 
                (name, address, website, subscription_id, is_active) 
                VALUES (%s, %s, %s, %s, %s)""",
                inst
            )
            institution_ids.append(cursor.lastrowid)
        
        # =============================================
        # 7. Institution Admins
        # =============================================
        print("Adding Institution Admins...")
        institution_admins = [
            ('admin@university.edu', '$2b$10$examplehash', 'Dr. James Wilson', institution_ids[0]),
            ('admin@college.edu', '$2b$10$examplehash', 'Ms. Sarah Johnson', institution_ids[1])
        ]
        
        for admin in institution_admins:
            cursor.execute(
                """INSERT IGNORE INTO Institution_Admins 
                (email, password_hash, full_name, institution_id) 
                VALUES (%s, %s, %s, %s)""",
                admin
            )
        
        # =============================================
        # 8. Venues
        # =============================================
        print("Adding Venues...")
        venues = [
            (institution_ids[0], 'Lecture Hall A', 'Main Building', 200, '{"projector": true, "ac": true, "whiteboard": true}'),
            (institution_ids[0], 'Lab 101', 'Science Building', 50, '{"computers": 50, "projector": true, "lab_equipment": true}'),
            (institution_ids[1], 'Room 201', 'Academic Block', 80, '{"projector": true, "speakers": true}')
        ]
        
        venue_ids = []
        for venue in venues:
            cursor.execute(
                """INSERT IGNORE INTO Venues 
                (institution_id, venue_name, building, capacity, facilities) 
                VALUES (%s, %s, %s, %s, %s)""",
                venue
            )
            venue_ids.append(cursor.lastrowid)
        
        # =============================================
        # 9. Timetable Slots
        # =============================================
        print("Adding Timetable Slots...")
        timetable_slots = [
            (institution_ids[0], 1, '08:30:00', '10:00:00', 'Morning Slot 1'),
            (institution_ids[0], 1, '10:15:00', '11:45:00', 'Morning Slot 2'),
            (institution_ids[0], 1, '13:00:00', '14:30:00', 'Afternoon Slot 1'),
            (institution_ids[1], 2, '09:00:00', '10:30:00', 'Tuesday Morning')
        ]
        
        slot_ids = []
        for slot in timetable_slots:
            cursor.execute(
                """INSERT IGNORE INTO Timetable_Slots 
                (institution_id, day_of_week, start_time, end_time, slot_name) 
                VALUES (%s, %s, %s, %s, %s)""",
                slot
            )
            slot_ids.append(cursor.lastrowid)
        
        # =============================================
        # 10. Lecturers
        # =============================================
        print("Adding Lecturers...")
        lecturers = [
            (institution_ids[0], 'prof.smith@university.edu', '$2b$10$examplehash', 'Professor Smith', 'Computer Science'),
            (institution_ids[0], 'dr.jones@university.edu', '$2b$10$examplehash', 'Dr. Jones', 'Mathematics'),
            (institution_ids[1], 'mr.brown@college.edu', '$2b$10$examplehash', 'Mr. Brown', 'Physics')
        ]
        
        lecturer_ids = []
        for lecturer in lecturers:
            cursor.execute(
                """INSERT IGNORE INTO Lecturers 
                (institution_id, email, password_hash, full_name, department) 
                VALUES (%s, %s, %s, %s, %s)""",
                lecturer
            )
            lecturer_ids.append(cursor.lastrowid)
        
        # =============================================
        # 11. Courses
        # =============================================
        print("Adding Courses...")
        courses = [
            (institution_ids[0], 'CS101', 'Introduction to Computer Science', 'Basic computer science concepts', 3),
            (institution_ids[0], 'MATH201', 'Calculus II', 'Advanced calculus topics', 4),
            (institution_ids[1], 'PHY101', 'General Physics', 'Fundamental physics principles', 3)
        ]
        
        course_ids = []
        for course in courses:
            cursor.execute(
                """INSERT IGNORE INTO Courses 
                (institution_id, course_code, course_name, description, credits) 
                VALUES (%s, %s, %s, %s, %s)""",
                course
            )
            course_ids.append(cursor.lastrowid)
        
        # =============================================
        # 12. Course Lecturers
        # =============================================
        print("Linking Courses to Lecturers...")
        course_lecturers = [
            (course_ids[0], lecturer_ids[0]),  # CS101 -> Professor Smith
            (course_ids[1], lecturer_ids[1]),  # MATH201 -> Dr. Jones
            (course_ids[2], lecturer_ids[2])   # PHY101 -> Mr. Brown
        ]
        
        for cl in course_lecturers:
            cursor.execute(
                "INSERT IGNORE INTO Course_Lecturers (course_id, lecturer_id) VALUES (%s, %s)",
                cl
            )
        
        # =============================================
        # 13. Students
        # =============================================
        print("Adding Students...")
        students = [
            (institution_ids[0], 'S001', 'student1@university.edu', '$2b$10$examplehash', 'John Doe', 2023),
            (institution_ids[0], 'S002', 'student2@university.edu', '$2b$10$examplehash', 'Jane Smith', 2023),
            (institution_ids[0], 'S003', 'student3@university.edu', '$2b$10$examplehash', 'Bob Johnson', 2024),
            (institution_ids[1], 'C001', 'student4@college.edu', '$2b$10$examplehash', 'Alice Williams', 2023),
            (institution_ids[1], 'C002', 'student5@college.edu', '$2b$10$examplehash', 'Charlie Brown', 2024)
        ]
        
        student_ids = []
        for student in students:
            cursor.execute(
                """INSERT IGNORE INTO Students 
                (institution_id, student_code, email, password_hash, full_name, enrollment_year) 
                VALUES (%s, %s, %s, %s, %s, %s)""",
                student
            )
            student_ids.append(cursor.lastrowid)
        
        # =============================================
        # 14. Enrollments
        # =============================================
        print("Enrolling Students in Courses...")
        enrollments = [
            # University students in CS101 and MATH201
            (student_ids[0], course_ids[0], '2023-2024', 'Spring', 'active'),
            (student_ids[0], course_ids[1], '2023-2024', 'Spring', 'active'),
            (student_ids[1], course_ids[0], '2023-2024', 'Spring', 'active'),
            (student_ids[1], course_ids[1], '2023-2024', 'Spring', 'active'),
            (student_ids[2], course_ids[0], '2024-2025', 'Fall', 'active'),
            # College students in PHY101
            (student_ids[3], course_ids[2], '2023-2024', 'Spring', 'active'),
            (student_ids[4], course_ids[2], '2024-2025', 'Fall', 'active')
        ]
        
        for enrollment in enrollments:
            cursor.execute(
                """INSERT IGNORE INTO Enrollments 
                (student_id, course_id, academic_year, semester, status) 
                VALUES (%s, %s, %s, %s, %s)""",
                enrollment
            )
        
        # =============================================
        # 15. Sessions
        # =============================================
        print("Creating Class Sessions...")
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        
        sessions = [
            (course_ids[0], venue_ids[0], slot_ids[0], lecturer_ids[0], yesterday, 'Introduction to Programming', 'completed'),
            (course_ids[0], venue_ids[0], slot_ids[0], lecturer_ids[0], today, 'Variables and Data Types', 'scheduled'),
            (course_ids[1], venue_ids[1], slot_ids[1], lecturer_ids[1], today, 'Integration Techniques', 'scheduled'),
            (course_ids[2], venue_ids[2], slot_ids[3], lecturer_ids[2], tomorrow, 'Newton\'s Laws', 'scheduled')
        ]
        
        session_ids = []
        for session in sessions:
            cursor.execute(
                """INSERT IGNORE INTO Sessions 
                (course_id, venue_id, slot_id, lecturer_id, session_date, session_topic, status) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                session
            )
            session_ids.append(cursor.lastrowid)
        
        # =============================================
        # 16. Attendance Records
        # =============================================
        print("Creating Attendance Records...")
        
        # For yesterday's completed session
        attendance_records = [
            # CS101 yesterday - 3 students
            (session_ids[0], student_ids[0], 'present', 'system', None, None, '09:00:00', 'On time'),
            (session_ids[0], student_ids[1], 'late', 'lecturer', lecturer_ids[0], None, '09:15:00', 'Arrived 15 min late'),
            (session_ids[0], student_ids[2], 'absent', 'system', None, None, None, 'Not present'),
            
            # CS101 today - 2 students (session ongoing)
            (session_ids[1], student_ids[0], 'present', 'system', None, None, '08:30:00', 'Present'),
            (session_ids[1], student_ids[1], 'present', 'system', None, None, '08:35:00', 'Present'),
            
            # MATH201 today - 2 students
            (session_ids[2], student_ids[0], 'present', 'lecturer', lecturer_ids[1], None, '10:20:00', 'Attended'),
            (session_ids[2], student_ids[1], 'excused', 'lecturer', lecturer_ids[1], None, None, 'Medical leave')
        ]
        
        for record in attendance_records:
            cursor.execute(
                """INSERT IGNORE INTO Attendance_Records 
                (session_id, student_id, status, marked_by, lecturer_id, captured_image_path, attendance_time, notes) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                record
            )
        
        conn.commit()
        print("Dummy data populated successfully!")
        print(f"\nData Summary:")
        print(f"- Institutions: {len(institution_ids)}")
        print(f"- Courses: {len(course_ids)}")
        print(f"- Lecturers: {len(lecturer_ids)}")
        print(f"- Students: {len(student_ids)}")
        print(f"- Sessions: {len(session_ids)}")
        print(f"- Attendance Records: {len(attendance_records)}")
        
        # Print login credentials for testing
        print(f"\nTest Credentials:")
        print(f"Platform Manager: admin@attendanceplatform.com / password")
        print(f"Institution Admin: admin@university.edu / password")
        print(f"Lecturer: prof.smith@university.edu / password")
        print(f"Student: student1@university.edu / password")
        
    except Exception as e:
        print(f"Error populating dummy data: {e}")
        conn.rollback()
        raise