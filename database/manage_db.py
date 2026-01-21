from sqlalchemy import text, func
from datetime import datetime, date, timedelta
import os
import bcrypt
import random

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

def seed_subscription_plans():
    with get_session() as session:
        plans = [
            SubscriptionPlan(
                name="Starter Plan",
                description="Perfect for small institutions",
                price_per_cycle=99.99,
                billing_cycle="monthly",
                max_users=500,
                features='{"facial_recognition": true, "basic_reporting": true, "email_support": true}'
            ),
            SubscriptionPlan(
                name="Professional Plan",
                description="For growing institutions",
                price_per_cycle=199.99,
                billing_cycle="monthly",
                max_users=2000,
                features='{"facial_recognition": true, "advanced_reporting": true, "priority_support": true, "api_access": true}'
            ),
            SubscriptionPlan(
                name="Enterprise Plan",
                description="For large institutions",
                price_per_cycle=499.99,
                billing_cycle="annual",
                max_users=10000,
                features='{"facial_recognition": true, "custom_reporting": true, "24/7_support": true, "api_access": true, "custom_integrations": true}'
            )
        ]
        session.add_all(plans)
        session.commit()
    print(f"Added {len(plans)} subscription plans")

def seed_subscriptions():
    with get_session() as session:
        subs = [
            Subscription(
                plan_id=1,
                start_date=date(2023, 1, 1),
                end_date=date(2029, 1, 31),
                stripe_subscription_id="stripe_subscription_id_1"
            ),
            Subscription(
                plan_id=2,
                start_date=date(2023, 2, 1),
                end_date=date(2029, 2, 28),
                stripe_subscription_id="stripe_subscription_id_2"
            ),
            Subscription(
                plan_id=3,
                start_date=date(2023, 3, 1),
                end_date=date(2029, 3, 31),
                stripe_subscription_id="stripe_subscription_id_3"
            )
        ]
        session.add_all(subs)
        session.commit()
    print(f"Added {len(subs)} subscriptions")

def seed_institutions():
    with get_session() as session:
        insts = [
            Institution(
                name="University of Technology",
                address="123 Campus Road, Tech City",
                poc_name="Your Admin POC",
                poc_phone="89 54987 954",
                poc_email="https://utech.edu",
                subscription_id=1,
            ),
            Institution(
                name="City College",
                address="456 College Ave, Metro City",
                poc_name="My Admin POC",
                poc_phone="549832168",
                poc_email="https://citycollege.edu",
                subscription_id=2,
            ),
            Institution(
                name="University Test",
                address="789 Test Street, Test City",
                poc_name="Test Admin POC",
                poc_phone="4578 5668 12",
                poc_email="https://university.test.edu",
                subscription_id=3,
            )
        ]
        session.add_all(insts)
        session.commit()
    print(f"Added {len(insts)} institutions")

def seed_semesters(years: int, sem_per_year: int=4):
    with get_session() as session:
        num_inst = session.query(Institution).count()
    semesters = []
    for inst_id in range(1, num_inst+1):
        for year in range(date.today().year, date.today().year + years):
            months_per_sem = 12 // sem_per_year
            for q in range(1, sem_per_year + 1):
                semesters.append(Semester(
                    institution_id=inst_id,
                    name=f"{year}-{q}",
                    start_date=date(year, (q - 1) * months_per_sem + 1, 1),
                    end_date=date(year, q * months_per_sem, 28),
                ))
    with get_session() as session:
        session.add_all(semesters)
        session.commit()
    print(f"Added {len(semesters)} semesters")

def seed_assign_courses():
    with get_session() as session:
        # Preload everything needed once
        semesters = session.query(Semester).all()
        courses = session.query(Course).all()
        users = session.query(User).all()

        # Group users by institution + role
        inst_lecturers = {}
        inst_students = {}
        inst_semesters = {}

        for user in users:
            if user.role == "lecturer":
                inst_lecturers.setdefault(user.institution_id, []).append(user)
            elif user.role == "student":
                inst_students.setdefault(user.institution_id, []).append(user)

        for sem in semesters:
            inst_semesters.setdefault(sem.institution_id, []).append(sem)

        bindings = []
        for course in courses:
            inst_id = course.institution_id

            course_lecturers: list[User] = inst_lecturers.get(inst_id, [])
            course_students: list[User] = inst_students.get(inst_id, [])
            course_semesters: list[Semester] = inst_semesters.get(inst_id, [])

            if not course_lecturers or not course_semesters:
                # Skip institution if incomplete data
                continue

            # Pick 1 lecturer in the same institution
            lecturer: User = random.choice(course_lecturers)

            for sem in course_semesters:
                # Add lecturer binding
                bindings.append(CourseUser(
                    course_id=course.course_id,
                    user_id=lecturer.user_id,
                    semester_id=sem.semester_id
                ))

                # Add students with 80% chance
                for student in course_students:
                    if random.random() < 0.8:
                        bindings.append(CourseUser(
                            course_id=course.course_id,
                            user_id=student.user_id,
                            semester_id=sem.semester_id
                        ))
        session.add_all(bindings)
        session.commit()
        print(f"Created {len(bindings)} course_user bindings created.")

def seed_classes(classes_per_sem: int=5):
    with get_session() as session:
        courses = session.query(Course).all()
        venues = session.query(Venue).all()

        # Group venues by institution
        inst_venues = {}
        for v in venues:
            inst_venues.setdefault(v.institution_id, []).append(v)

        def random_datetime_in_semester(semester: Semester):
            delta = semester.end_date - semester.start_date
            random_days = random.randint(0, delta.days)
            random_hour = random.randint(8, 18)
            random_minute = random.choice([0, 15, 30, 45])
            start_date: datetime = semester.as_dict()["start_date"]
            return start_date.replace(hour=random_hour, minute=random_minute, second=0, microsecond=0) + timedelta(days=random_days)

        classes = []
        for course in courses:
            inst_id = course.institution_id

            # Skip if institution has no lecturer or venue
            lecturers: list[User] = (
                session.query(User)
                .join(CourseUser)
                .filter(
                    User.institution_id == inst_id,
                    User.role == "lecturer", 
                    CourseUser.course_id == course.course_id
                )
                .all()
            )
            venue_list: list[Venue] = inst_venues.get(inst_id, [])
            semesters: list[Semester] = (
                session.query(Semester)
                .select_from(CourseUser)
                .join(Semester)
                .filter(
                    Semester.institution_id == inst_id,
                    CourseUser.course_id == course.course_id,
                )
                .all()
            )
            if not lecturers or not venue_list:
                continue
            lecturer = random.choice(lecturers)

            for sem in semesters:
                for _ in range(classes_per_sem):
                    start = random_datetime_in_semester(sem)
                    end = start + timedelta(hours=2)

                    cls = Class(
                        course_id=course.course_id,
                        semester_id=sem.semester_id,
                        venue_id=random.choice(venue_list).venue_id,
                        lecturer_id=lecturer.user_id,
                        start_time=start,
                        end_time=end,
                        status="scheduled",
                    )
                    classes.append(cls)
        session.add_all(classes)
        session.commit()
    print(f"{len(classes)} classes created.")

def seed_attendance():
    with get_session() as session:
        classes = session.query(Class).all()
        statuses = AttendanceStatusEnum.enums
        statuses.remove("unmarked")

        for cls in classes:
            # Get students who should be in this class
            enrolled_students = session.query(CourseUser).join(User).filter(
                CourseUser.course_id == cls.course_id,
                CourseUser.semester_id == cls.semester_id,
                User.role == "student",
            ).all()

            # Initialize attendance records list
            attendance_records = []

            for cu in enrolled_students:
                record = AttendanceRecord(
                    class_id=cls.class_id,
                    student_id=cu.user_id,
                    status=random.choice(statuses),
                    marked_by="lecturer",
                    lecturer_id=cls.lecturer_id
                )
                attendance_records.append(record)

            # Add all attendance records for this class at once
            session.add_all(attendance_records)

        session.commit()
        print(f"Created {len(attendance_records)} attendance records.")
        
def seed_appeals():
    with get_session() as session:
        attendance_records = (
            session.query(AttendanceRecord)
            .filter(AttendanceRecord.status.in_(["absent", "late"]))
            .all()
        )
        appeal_reasons = [
            "I was sick that day.",
            "There was a family emergency.",
            "I had technical issues with the attendance system.",
            "I was attending a university-approved event.",
            "I had a valid excuse from my lecturer."
        ]

        appeals = []
        for record in attendance_records:
            if random.random() < 0.25:  # 25% chance to create an appeal
                appeal = AttendanceAppeal(
                    attendance_id=record.attendance_id,
                    student_id=record.student_id,
                    reason=random.choice(appeal_reasons),
                    status="pending",
                )
                appeals.append(appeal)

        session.add_all(appeals)
        session.commit()
        print(f"Created {len(appeals)} appeals.")

def seed_testimonials():
    with get_session() as session:
        testimonials = []
        
        testimonial_data = [
            (1, 4, "The automated attendance system has revolutionized how we track student participation. It's accurate, fast, and saves us countless hours of manual work.", "Revolutionary attendance tracking", 5, "approved"),
            (1, 11, "The automated attendance system has significantly improved how attendance is handled in our classes. Compared to manual roll calls or sign-in sheets, the process is much faster and reduces disruption during lessons. Most of the time, students are marked correctly without any intervention, which helps both lecturers and students focus more on learning rather than administration.\n\nThat said, there are occasional challenges, particularly when classes are held in rooms with poor or inconsistent lighting. In those situations, facial recognition may take slightly longer or require repositioning. While this does not happen often, it can be noticeable during early morning or evening sessions.\n\nOverall, despite these minor issues, the system is a huge improvement over traditional methods. The benefits in efficiency, accuracy, and time savings far outweigh the occasional inconvenience, and with further optimization, it has the potential to be nearly flawless.",
            "Works great with minor issues", 4, "approved"),
            (2, 16, "The system delivers exactly what it promises in terms of core functionality. Attendance marking is reliable, and the facial recognition works consistently across most environments. From a practical standpoint, it has reduced administrative workload and eliminated many common attendance-related disputes.\n\nOne area that could be improved is the user interface. While it is functional and easy to understand, the design feels somewhat dated compared to newer platforms. A more modern layout and visual enhancements would improve the overall user experience, especially for students who interact with the system frequently.\n\nDespite this, the strength of the platform lies in its performance and stability. It rarely experiences downtime, handles large class sizes well, and provides accurate records. For institutions prioritizing reliability over aesthetics, this system performs exceptionally well.",
            "Solid functionality", 4, "approved"),
            (3, 18, "Overall, the attendance system performs reliably and meets our expectations for daily academic operations. Facial recognition is generally accurate, and attendance records are updated correctly without requiring manual corrections. This has greatly reduced errors compared to older attendance methods.\n\nDuring peak hours, such as when multiple large classes start at the same time, the system can become slightly slower. Processing may take a few extra seconds, which can be noticeable but does not disrupt classes significantly. These delays are infrequent and usually resolve quickly.\n\nIn summary, the system is dependable and effective for regular use. The minor performance slowdowns during peak periods are manageable and do not overshadow the overall advantages. With improved scalability, the system could easily support even larger institutions without issue.",
            "Works well with minor delays", 4, "approved"),
            
            
        ]
        
        users = session.query(User).all()
        for user in users:
            if random.random() < 0.3:  # Only 30% of users get testimonials
                testimonial = Testimonial(
                    institution_id=user.institution_id,
                    user_id=user.user_id,
                    content=random.choice(testimonial_data)[2],
                    summary=random.choice(testimonial_data)[3],
                    rating=random.choice(testimonial_data)[4],
                    status=random.choice(testimonial_data)[5],
                )
                testimonials.append(testimonial)
            
        
        
        session.add_all(testimonials)
        session.commit()
        print(f"Added {len(testimonials)} testimonials")

def seed_features():
    with get_session() as session:
        features_data = [
            {
                'slug': 'ai-face-recognition',
                'icon': '🤖',
                'title': 'AI-Powered Face Recognition',
                'description': 'Automatically identify and mark attendance using advanced facial recognition technology with 99.8% accuracy. No more manual check-ins or proxy attendance.',
                'details': '''Our advanced facial recognition system revolutionizes attendance tracking with unparalleled accuracy and efficiency.

<h4>Key Features:</h4>
<ul>
    <li>99.8% accuracy rate with deep learning algorithms</li>
    <li>Real-time face detection and recognition</li>
    <li>Works in various lighting conditions</li>
    <li>Anti-spoofing technology to prevent fraud</li>
    <li>Privacy-focused with encrypted face data</li>
</ul>

<h4>How It Works:</h4>
Students simply look at the camera during class entry. The system instantly identifies them and marks attendance automatically. The entire process takes less than 2 seconds per student.''',
                'try_url': '/auth/register',
                'is_advanced': False,
                'display_order': 1
            },
            {
                'slug': 'qr-mobile-checkins',
                'icon': '📱',
                'title': 'QR Code & Mobile Check-ins',
                'description': 'Quick QR code scanning for fast check-ins. Students and staff can mark attendance with a simple scan using our mobile app or web interface.',
                'details': '''Streamline attendance with quick QR code scanning and mobile check-ins for maximum flexibility.

<h4>Benefits:</h4>
<ul>
    <li>Instant check-in via QR code scanning</li>
    <li>Works on any smartphone or tablet</li>
    <li>No special hardware required</li>
    <li>Offline mode for areas with poor connectivity</li>
    <li>Unique codes generated for each session</li>
</ul>

<h4>Perfect For:</h4>
Large lecture halls, outdoor events, remote learning scenarios, and hybrid classrooms where facial recognition may not be practical.''',
                'try_url': '/demo/qr-checkin',
                'is_advanced': False,
                'display_order': 2
            },
            {
                'slug': 'real-time-analytics',
                'icon': '📊',
                'title': 'Real-time Analytics Dashboard',
                'description': 'Monitor attendance patterns, trends, and statistics in real-time. Generate instant reports and identify at-risk students with predictive analytics.',
                'details': '''Transform raw attendance data into actionable insights with our powerful analytics platform.

<h4>Analytics Features:</h4>
<ul>
    <li>Live attendance tracking across all classes</li>
    <li>Historical trend analysis and comparisons</li>
    <li>Customizable reports and exports</li>
    <li>Visual charts and graphs for easy interpretation</li>
    <li>Automatic alerts for attendance issues</li>
</ul>

<h4>Insights You'll Get:</h4>
Identify patterns like frequent absences, peak attendance times, course popularity, and early warning signs for students who may need additional support.''',
                'try_url': '/demo/analytics',
                'is_advanced': False,
                'display_order': 3
            },
            {
                'slug': 'automated-notifications',
                'icon': '🔔',
                'title': 'Automated Notifications',
                'description': 'Send automatic alerts to students, parents, and staff about attendance status, upcoming classes, and important announcements via email or SMS.',
                'details': '''Keep everyone informed with automated, customizable notification system.

<h4>Notification Types:</h4>
<ul>
    <li>Absence alerts sent to students and parents</li>
    <li>Class reminders and schedule changes</li>
    <li>Low attendance warnings</li>
    <li>Custom announcements and updates</li>
    <li>Weekly/monthly attendance summaries</li>
</ul>

<h4>Delivery Options:</h4>
Choose from email, SMS, push notifications, or in-app alerts. Set up custom rules for when and who receives notifications based on your institution's needs.''',
                'try_url': '/demo/notifications',
                'is_advanced': False,
                'display_order': 4
            },
            {
                'slug': 'advanced-security',
                'icon': '🔒',
                'title': 'Advanced Security & Compliance',
                'description': 'Enterprise-grade security with data encryption, role-based access control, and GDPR compliance. Your data is protected with bank-level security.',
                'details': '''Enterprise-grade security measures to protect sensitive attendance data.

<h4>Security Features:</h4>
<ul>
    <li>End-to-end encryption for all data</li>
    <li>Role-based access control (RBAC)</li>
    <li>Two-factor authentication (2FA)</li>
    <li>Regular security audits and updates</li>
    <li>GDPR, FERPA, and SOC 2 compliance</li>
</ul>

<h4>Privacy Protection:</h4>
We take data privacy seriously. All biometric data is encrypted, stored securely, and never shared with third parties. Students and staff have full control over their personal information.''',
                'try_url': '/demo/security',
                'is_advanced': False,
                'display_order': 5
            },
            {
                'slug': 'seamless-integrations',
                'icon': '🔄',
                'title': 'Seamless Integrations',
                'description': 'Connect with existing systems like Google Classroom, Microsoft Teams, LMS platforms, and student information systems through our powerful API.',
                'details': '''Connect AttendAI with your existing systems for a unified workflow.

<h4>Integration Options:</h4>
<ul>
    <li>Google Classroom and Microsoft Teams</li>
    <li>Popular LMS platforms (Canvas, Moodle, Blackboard)</li>
    <li>Student Information Systems (SIS)</li>
    <li>Calendar applications (Google Calendar, Outlook)</li>
    <li>Custom integrations via REST API</li>
</ul>

<h4>Benefits:</h4>
Sync attendance data automatically, reduce duplicate data entry, and create a seamless experience across all your educational technology tools.''',
                'try_url': '/demo/integrations',
                'is_advanced': False,
                'display_order': 6
            },
            {
                'slug': 'predictive-analytics',
                'icon': '🎯',
                'title': 'Predictive Analytics',
                'description': 'AI algorithms predict student performance based on attendance patterns, helping educators identify at-risk students early and intervene proactively.',
                'details': '''Use AI to predict student outcomes based on attendance patterns.

<h4>Predictive Capabilities:</h4>
<ul>
    <li>Early identification of at-risk students</li>
    <li>Performance prediction based on attendance</li>
    <li>Intervention recommendations</li>
    <li>Success probability scoring</li>
    <li>Trend forecasting for future semesters</li>
</ul>

<h4>Impact:</h4>
Studies show that early intervention based on attendance patterns can improve student retention by up to 25% and increase overall academic performance significantly.''',
                'try_url': '/demo/predictive-analytics',
                'is_advanced': True,
                'display_order': 7
            },
            {
                'slug': 'geolocation-tracking',
                'icon': '🌐',
                'title': 'Geolocation Tracking',
                'description': 'Verify attendance based on location for remote or hybrid learning. Ensure students are in the right place at the right time with geofencing technology.',
                'details': '''Verify attendance location for remote and hybrid learning environments.

<h4>Location Features:</h4>
<ul>
    <li>GPS-based location verification</li>
    <li>Geofencing for specific areas</li>
    <li>Configurable radius settings</li>
    <li>Privacy-conscious location tracking</li>
    <li>Works for field trips and off-campus events</li>
</ul>

<h4>Use Cases:</h4>
Perfect for hybrid learning, field trips, internships, practical sessions, and ensuring students attend the correct physical location for in-person requirements.''',
                'try_url': '/demo/geolocation',
                'is_advanced': True,
                'display_order': 8
            }
        ]
        
        for feature_data in features_data:
            feature = Feature(**feature_data)
            session.add(feature)
        
        session.commit()
        print(f"Added {len(features_data)} features")

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
        seed_subscription_plans()

    if row_count("Subscriptions") == 0:
        seed_subscriptions()

    if row_count("Institutions") == 0:
        seed_institutions()

    if row_count("Semesters") == 0:
        seed_semesters(years=1, sem_per_year=2)

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
            'institution_id', 'code', 'name', 'description', 'credits'
        ]
        courses = [
            (1, 'CS101', 'Introduction to Programming', 'Basic programming concepts using Python', 3),
            (1, 'MATH201', 'Calculus I', 'Differential and integral calculus', 4),
            (1, 'CS301', 'Database Systems', 'Relational database design and SQL', 3),
            (2, 'BUS101', 'Business Fundamentals', 'Introduction to business concepts', 3),
            (2, 'ECON101', 'Microeconomic Theory', 'Basic concepts of microeconomics', 3),
            (2, 'ECON201', 'Macroeconomic Theory', 'Basic concepts of macroeconomics', 3),
            (3, 'PHYS101', 'Physics I', 'Basic concepts of physics', 3),
            (3, 'CHEM101', 'Chemistry I', 'Basic concepts of chemistry', 3),
            (3, 'BIO101', 'Biology I', 'Basic concepts of biology', 3),
        ]
        push_data(f"INSERT INTO Courses ({comma_join(cols)}) VALUES ({colon_join(cols)})", zip_dict(cols, courses))
        print(f"Added {len(courses)} courses")
    
    seed_assign_courses()

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
        seed_classes(10)
    
    if row_count("Attendance_Records") == 0:
        seed_attendance()
    
    if row_count("Attendance_Appeals") == 0:
        seed_appeals()
    
    if row_count("Testimonials") == 0:
        seed_testimonials()
    
    if row_count("Features") == 0:
        seed_features()

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