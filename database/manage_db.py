from sqlalchemy import text
from datetime import datetime, date, timedelta
import os
import bcrypt

from base import root_engine, engine, get_session
from models import *

def drop_database():
    with root_engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {os.environ['DB_NAME']}"))
    print(f"Database {os.environ['DB_NAME']} dropped")

def create_database():
    with root_engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {os.environ['DB_NAME']}"))
    print(f"Database {os.environ['DB_NAME']} created")

def seed_database():
    import random
    zip_dict = lambda keys, list_of_values: [dict(zip(keys, values)) for values in list_of_values]
    comma_join = lambda l: ", ".join(l)
    colon_join = lambda l: ", ".join(f":{e}" for e in l)
    def row_count(s):
        with get_session() as session:
            return session.execute(text(f"SELECT COUNT(*) FROM {s}")).fetchone()[0]
    def push_data(s, data):
        with get_session() as session:
            session.execute(text(s), data)

    test_password = "password"
    password_hash = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    with get_session() as s:
        db_name, version = s.execute(text("SELECT DATABASE(), VERSION()")).fetchone()
    print(f"Connected to mySQL database: {db_name}")
    print(f"Version: {version}")
    
    if row_count("Subscription_Plans") == 0:
        cols = [
            'name', 'description', 'price_per_cycle', 'billing_cycle', 'max_users', 'features'
        ]
        subscription_plans = [
            ('Starter Plan', 'Perfect for small institutions', 99.99, 'monthly', 500,
                '{"facial_recognition": true, "basic_reporting": true, "email_support": true}'),
            ('Professional Plan', 'For growing institutions', 199.99, 'monthly', 2000,
                '{"facial_recognition": true, "advanced_reporting": true, "priority_support": true, "api_access": true}'),
            ('Enterprise Plan', 'For large institutions', 499.99, 'annual', 10000,
                '{"facial_recognition": true, "custom_reporting": true, "24/7_support": true, "api_access": true, "custom_integrations": true}')
        ]
        push_data(f"INSERT INTO Subscription_Plans ({comma_join(cols)}) VALUES ({colon_join(cols)})", zip_dict(cols, subscription_plans))
        print(f"Added {len(subscription_plans)} subscription plans")

    if row_count("Subscriptions") == 0:
        cols = [
            'plan_id', 'start_date', 'end_date', 'stripe_subscription_id'
        ]
        subscriptions = [
            (1, date(2023, 1, 1), date(2023, 1, 31), "stripe_subscription_id_1"),
            (2, date(2023, 2, 1), date(2023, 2, 28), "stripe_subscription_id_2"),
            (3, date(2023, 3, 1), date(2023, 3, 31), "stripe_subscription_id_3")
        ]
        push_data(f"INSERT INTO Subscriptions ({comma_join(cols)}) VALUES ({colon_join(cols)})", zip_dict(cols, subscriptions))
        print(f"Added {len(subscriptions)} subscriptions")

    if row_count("Institutions") == 0:
        cols = [
            "name", "address", "poc_name", "poc_phone", "poc_email", "subscription_id"
        ]
        institutions = [
            ('University of Technology', '123 Campus Road, Tech City', 'Your Admin POC', '89 54987 954', 'https://utech.edu', 1),
            ('City College', '456 College Ave, Metro City', 'My Admin POC', '549832168', 'https://citycollege.edu', 2),
            ('University Test', '789 Test Street, Test City', 'Test Admin POC', '4578 5668 12', 'https://university.test.edu', 3)
        ]
        push_data(f"INSERT INTO Institutions ({comma_join(cols)}) VALUES ({colon_join(cols)})", zip_dict(cols, institutions))
        print(f"Added {len(institutions)} institutions")

    if row_count("Users") == 0:
        cols = [
            "institution_id", "role", "name", "age", "gender", "phone_number", "email", "password_hash"
        ]
        users = [
            (1, "admin", 'Dr. Robert Chen', 40, 'male', '1234567890', 'admin@utech.edu', password_hash),
            (2, "admin", 'Prof. Sarah Johnson', 35, 'female', '9876543210', 'admin@citycollege.edu', password_hash),
            (3, "admin", 'University Admin', 45, 'male', '5551234567', 'admin@university.edu', password_hash),

            (1, "lecturer", 'Professor Zhang Wei', 30, 'male', '1234567890', 'prof.zhang@utech.edu', password_hash),
            (1, "lecturer", 'Dr. Lee Min Ho', 25, 'female', '9876543210', 'dr.lee@utech.edu', password_hash),
            (2, "lecturer", 'Mr. David Jones', 28, 'male', '5555555555', 'mr.jones@citycollege.edu', password_hash),
            (2, "lecturer", 'Ms. Maria Garcia', 31, 'female', '1111111111', 'ms.garcia@citycollege.edu', password_hash),
            (3, "lecturer", 'Professor John Smith', 32, 'male', '9999999999', 'prof.smith@university.edu', password_hash),
            (3, "lecturer", 'Dr. Emily Jones', 27, 'female', '8888888888', 'dr.jones@university.edu', password_hash),

            (1, "student", 'Alice Wong', 22, 'female', '91234567', 'alice.wong@utech.edu', password_hash),
            (1, "student", 'Bob Smith', 24, 'male', '12345678', 'bob.smith@utech.edu', password_hash),
            (1, "student", 'Charlie Brown', 25, 'male', '85432298', 'charlie.brown@utech.edu', password_hash),
            (1, "student", 'Diana Ross', 21, 'other', '84564569', 'diana.ross@utech.edu', password_hash),
            (2, "student", 'Emma Johnson', 23, 'female', '96546548', 'emma.johnson@citycollege.edu', password_hash),
            (2, "student", 'Frank Miller', 24, 'male', '98765432', 'frank.miller@citycollege.edu', password_hash),
            (2, "student", 'Grace Williams', 24, 'other', '98765432', 'grace.williams@citycollege.edu', password_hash),
            (3, "student", 'Grace Kim', 26, 'female', '87654321', 'grace.kim@university.edu', password_hash),
            (3, "student", 'Henry Lee', 23, 'male', '76543210', 'henry.lee@university.edu', password_hash),
            (3, "student", 'Isabella Chen', 25, 'other', '65432109', 'isabella.chen@university.edu', password_hash),
        ]
        push_data(f"INSERT INTO Users ({comma_join(cols)}) VALUES ({colon_join(cols)})", zip_dict(cols, users))
        print(f"Added {len(users)} users")

    if row_count("Courses") == 0:
        cols = [
            'institution_id', 'code', 'name', 'description', 'credits', 'start_date', 'end_date'
        ]
        courses = [
            (1, 'CS101', 'Introduction to Programming', 'Basic programming concepts using Python', 3, date(2023, 1, 1), date(2023, 6, 30)),
            (1, 'MATH201', 'Calculus I', 'Differential and integral calculus', 4, date(2023, 7, 1), date(2023, 12, 31)),
            (1, 'CS301', 'Database Systems', 'Relational database design and SQL', 3, date(2023, 1, 1), date(2023, 6, 30)),
            (2, 'BUS101', 'Business Fundamentals', 'Introduction to business concepts', 3, date(2023, 1, 1), date(2023, 6, 30)),
            (2, 'ECON101', 'Microeconomic Theory', 'Basic concepts of microeconomics', 3, date(2023, 7, 1), date(2023, 12, 31)),
            (2, 'ECON201', 'Macroeconomic Theory', 'Basic concepts of macroeconomics', 3, date(2023, 1, 1), date(2023, 6, 30)),
            (3, 'PHYS101', 'Physics I', 'Basic concepts of physics', 3, date(2023, 1, 1), date(2023, 6, 30)),
            (3, 'CHEM101', 'Chemistry I', 'Basic concepts of chemistry', 3, date(2023, 7, 1), date(2023, 12, 31)),
            (3, 'BIO101', 'Biology I', 'Basic concepts of biology', 3, date(2023, 1, 1), date(2023, 6, 30)),
        ]
        push_data(f"INSERT INTO Courses ({comma_join(cols)}) VALUES ({colon_join(cols)})", zip_dict(cols, courses))
        print(f"Added {len(courses)} courses")
    
    # Assigning users to courses
    course_lecturer_map = {}
    with get_session() as s:
        for course_id, course in enumerate(courses, 1):
            institution_id = course[0]
            possible_students = [user_id for user_id, user in enumerate(users, 1) if user[0] == institution_id and user[1] == "student"]
            possible_lecturers = [user_id for user_id, user in enumerate(users, 1) if user[0] == institution_id and user[1] == "lecturer"]

            cols = [
                'course_id', 'user_id', 'academic_year'
            ]
            # 80% chance student enrolls
            chance_of_assignment = 0.8
            for student_id in possible_students:
                if random.random() > chance_of_assignment:
                    continue
                s.execute(text(f"INSERT INTO Course_Users ({comma_join(cols)}) VALUES ({colon_join(cols)})"), zip_dict(cols, [(course_id, student_id, 2023)]))
            # Random lecturer assigned
            lecturer_id = random.choice(possible_lecturers)
            course_lecturer_map[course_id] = lecturer_id
            s.execute(text(f"INSERT INTO Course_Users ({comma_join(cols)}) VALUES ({colon_join(cols)})"), zip_dict(cols, [(course_id, lecturer_id, 2023)]))

    if row_count("Venues") == 0:
        cols = [
            'institution_id', 'name', 'capacity'
        ]
        venues = [
            (1, 'Building A Room 101', 50),
            (1, 'Building B Room 201', 30),
            (1, 'Building C Room 301', 20),
            (2, 'Building D Room 401', 40),
            (2, 'Building E Room 501', 25),
            (2, 'Building F Room 601', 15),
            (3, 'Building G Room 701', 60),
            (3, 'Building H Room 801', 35),
            (3, 'Building I Room 901', 10),
        ]
        push_data(f"INSERT INTO Venues ({comma_join(cols)}) VALUES ({colon_join(cols)}) ", zip_dict(cols, venues))
        print(f"Added {len(venues)} venues")

    if row_count("Classes") == 0:
        cols = [
            'course_id', 'venue_id', 'lecturer_id', 'start_time', 'end_time'
        ]
        classes = []
        for course_id, course in enumerate(courses, 1):
            institution_id = course[0]
            possible_venues = [venue_id for venue_id, venue in enumerate(venues, 1) if venue[0] == institution_id]

            for _ in range(5):
                start_time = datetime(2023, random.randint(1, 12), random.randint(1, 28), random.randint(8, 18), 0, 0)
                end_time = start_time + timedelta(hours=2)
                lecturer_id = course_lecturer_map[course_id]
                classes.append((course_id, random.choice(possible_venues), lecturer_id, start_time, end_time))
        
        push_data(f"INSERT INTO Classes ({comma_join(cols)}) VALUES ({colon_join(cols)}) ", zip_dict(cols, classes))
        print(f"Added {len(classes)} classes")
    
    if row_count("Attendance_Records") == 0:
        pass # TODO: Have to pull and coordinate information

    if row_count("Announcements") == 0:
        cols = [
            'institution_id', 'requested_by_user_id', 'title', 'content', 'date_posted'
        ]
        announcements = [
            (1, 1, 'Happy 105th Anniversary!', 'Celebrate the schools 105th anniversary with special events!', datetime.now()),
            (1, 1, 'System Maintenance', 'Portal will be down on 14th January due to planned maintenance.', datetime.now()),
            (2, 2, 'Happy 105th Anniversary!', 'Celebrate the schools 105th anniversary with special events!', datetime.now()),
            (2, 2, 'System Maintenance', 'Portal will be down on 14th January due to planned maintenance.', datetime.now()),
            (3, 3, 'Happy 105th Anniversary!', 'Celebrate the schools 105th anniversary with special events!', datetime.now()),
            (3, 3, 'System Maintenance', 'Portal will be down on 14th January due to planned maintenance.', datetime.now()),
        ]
        push_data(f"INSERT INTO Announcements ({comma_join(cols)}) VALUES ({colon_join(cols)}) ", zip_dict(cols, announcements))
        print(f"Added {len(announcements)} announcements")

    # Notifications just spam, supposed to have a lifespan of 30 days
    with get_session() as s:
        for user_id in range(1, len(users) + 1):
            for _ in range(5):
                content = f"Notification {random.randint(1, 100)} for user {user_id}"
                s.execute(text(f"INSERT INTO Notifications (user_id, content) VALUES ({user_id}, '{content}')"))
    print(f"Added 5 notifications to each user")
    print("Database seeded, models created")

def reset_database():
    drop_database()
    create_database()
    with engine.begin() as conn:
        Base.metadata.create_all(bind=conn)
    print("Database reset, models created")

if __name__ == "__main__":
    reset_database()
    seed_database()