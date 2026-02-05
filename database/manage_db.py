from sqlalchemy import text, func
from datetime import datetime, date, timedelta
import os
import bcrypt
import random

from base import root_engine, engine, get_session
from models import *

# Import the new models
from models import Feature, HeroFeature, Stat, AboutIntro, AboutStory, AboutMissionVision, TeamMember, AboutValue, HomepageFeatureCard, FeaturesPageContent, FeaturesComparison, FAQ

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
                price_per_cycle=100,
                billing_cycle="monthly",
                max_users=500,
                features='{"facial_recognition": true, "basic_reporting": true, "email_support": true}'
            ),
            SubscriptionPlan(
                name="Professional Plan",
                description="For growing institutions",
                price_per_cycle=200,
                billing_cycle="monthly",
                max_users=2000,
                features='{"facial_recognition": true, "advanced_reporting": true, "priority_support": true, "api_access": true}'
            ),
            SubscriptionPlan(
                name="Enterprise Plan",
                description="For large institutions",
                price_per_cycle=500,
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
        # Create a copy of statuses to avoid modifying the original enum
        statuses = list(AttendanceStatusEnum.enums)
        statuses.remove("unmarked")

        # Track all attendance records to count them
        all_attendance_records = []
        # Track unique class-student pairs to prevent duplicates
        seen_pairs = set()

        for cls in classes:
            # Get students who should be in this class
            enrolled_students = session.query(CourseUser).join(User).filter(
                CourseUser.course_id == cls.course_id,
                CourseUser.semester_id == cls.semester_id,
                User.role == "student",
            ).all()

            for cu in enrolled_students:
                # Create unique key for this class-student pair
                pair_key = (cls.class_id, cu.user_id)
                
                # Skip if we've already created a record for this pair
                if pair_key in seen_pairs:
                    continue
                
                record = AttendanceRecord(
                    class_id=cls.class_id,
                    student_id=cu.user_id,
                    status=random.choice(statuses),
                    marked_by="lecturer",
                    lecturer_id=cls.lecturer_id
                )
                all_attendance_records.append(record)
                seen_pairs.add(pair_key)

        # Add all attendance records at once
        session.add_all(all_attendance_records)
        session.commit()
        print(f"Created {len(all_attendance_records)} attendance records.")
        
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

def seed_hero_features():
    with get_session() as session:
        hero_features_data = [
            {
                'title': 'AI-Powered Face Recognition',
                'description': '99.8% accuracy for automatic attendance marking',
                'summary': 'Automatically identify and mark attendance using advanced facial recognition technology.',
                'icon': '🤖',
                'bg_image': 'https://images.unsplash.com/photo-1677442136019-21780ecad995?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1200&q=80',
                'display_order': 1,
                'is_active': True
            },
            {
                'title': 'QR Code & Mobile Check-ins',
                'description': 'Fast and convenient attendance marking',
                'summary': 'Quick QR code scanning for fast check-ins using mobile app or web interface.',
                'icon': '📱',
                'bg_image': 'https://images.unsplash.com/photo-1611224923853-80b023f02d71?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1200&q=80',
                'display_order': 2,
                'is_active': True
            },
            {
                'title': 'Real-time Analytics Dashboard',
                'description': 'Monitor patterns and generate instant reports',
                'summary': 'Monitor attendance patterns, trends, and statistics with predictive analytics.',
                'icon': '📊',
                'bg_image': 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1200&q=80',
                'display_order': 3,
                'is_active': True
            },
            {
                'title': 'Automated Notifications',
                'description': 'Alerts via email or SMS',
                'summary': 'Send automatic alerts about attendance status and upcoming classes.',
                'icon': '🔔',
                'bg_image': 'https://images.unsplash.com/photo-1552664730-d307ca884978?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1200&q=80',
                'display_order': 4,
                'is_active': True
            },
            {
                'title': 'Advanced Security & Compliance',
                'description': 'Enterprise-grade security with data encryption',
                'summary': 'Bank-level security with GDPR compliance and role-based access control.',
                'icon': '🔒',
                'bg_image': 'https://images.unsplash.com/photo-1554224155-6726b3ff858f?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1200&q=80',
                'display_order': 5,
                'is_active': True
            },
            {
                'title': 'Seamless Integrations',
                'description': 'Connect with Google Classroom, Microsoft Teams, and LMS',
                'summary': 'Powerful API for connecting with existing systems and platforms.',
                'icon': '🔄',
                'bg_image': 'https://images.unsplash.com/photo-1522071820081-009f0129c71c?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1200&q=80',
                'display_order': 6,
                'is_active': True
            }
        ]
        
        for hero_data in hero_features_data:
            hero_feature = HeroFeature(**hero_data)
            session.add(hero_feature)
        
        session.commit()
        print(f"Added {len(hero_features_data)} hero features")

def seed_stats():
    with get_session() as session:
        stats_data = [
            {
                'value': '500+',
                'label': 'Educational Institutions',
                'display_order': 1,
                'is_active': True
            },
            {
                'value': '98%',
                'label': 'Customer Satisfaction',
                'display_order': 2,
                'is_active': True
            },
            {
                'value': '250K+',
                'label': 'Students & Employees',
                'display_order': 3,
                'is_active': True
            },
            {
                'value': '85%',
                'label': 'Time Savings',
                'display_order': 4,
                'is_active': True
            }
        ]
        
        for stat_data in stats_data:
            stat = Stat(**stat_data)
            session.add(stat)
        
        session.commit()
        print(f"Added {len(stats_data)} stats")

def seed_about_intro():
    with get_session() as session:
        intro = AboutIntro(
            title='About AttendAI',
            description="We're revolutionizing attendance management with AI-powered solutions that make tracking, reporting, and analytics seamless for educational institutions and businesses worldwide.",
            is_active=True
        )
        session.add(intro)
        session.commit()
        print("Added about intro")

def seed_about_story():
    with get_session() as session:
        story = AboutStory(
            title='Our Story',
            content="Founded in 2025, AttendAI began as a student project at a leading technology university. Our team recognized the inefficiencies in traditional attendance tracking systems and set out to create a smarter solution. Today, we serve over 500 institutions across 30 countries, helping them save thousands of hours annually while improving accuracy and insights.",
            is_active=True
        )
        session.add(story)
        session.commit()
        print("Added about story")

def seed_about_mission_vision():
    with get_session() as session:
        mission_vision_data = [
            {
                'type': 'mission',
                'title': 'Our Mission',
                'content': 'To revolutionize attendance management through innovative AI technology, making it effortless for organizations to track, analyze, and optimize participation while providing actionable insights for better decision-making.',
                'is_active': True
            },
            {
                'type': 'vision',
                'title': 'Our Vision',
                'content': 'To become the global standard in attendance management systems, empowering every educational and corporate institution with smart, seamless, and scalable solutions that enhance productivity and engagement.',
                'is_active': True
            }
        ]
        
        for mv_data in mission_vision_data:
            mission_vision = AboutMissionVision(**mv_data)
            session.add(mission_vision)
        
        session.commit()
        print(f"Added {len(mission_vision_data)} mission/vision items")

def seed_team_members():
    import json
    with get_session() as session:
        team_data = [
            {
                'name': 'CHONG YE HAN',
                'role': 'AI & Documentation Lead',
                'description': 'Leads the AI development and comprehensive documentation efforts for AttendAI.',
                'contributions': json.dumps([
                    'Wireframe Development',
                    'Project Requirement Document',
                    'System Requirement Document',
                    'Facial Recognition AI Training',
                    'Technical Design Manual',
                    'Technical Design Document',
                    'System Requirement Specification'
                ]),
                'skills': json.dumps(['AI Development', 'Technical Documentation', 'System Architecture', 'Project Planning']),
                'display_order': 1,
                'is_active': True
            },
            {
                'name': 'GOH CHING FONG',
                'role': 'Project Lead',
                'description': 'Manages frontend development and project workflow using Kanban methodology.',
                'contributions': json.dumps([
                    'Wireframe Development',
                    'Project Requirement Document',
                    'Technical Design Document',
                    'Frontend Prototype Code',
                    'Preliminary User Manual',
                    'Technical Design Manual',
                    'Debugging',
                    'System Requirement Specification',
                    'User Manual',
                    'Kanban Master',
                    'Presentation Slides'
                ]),
                'skills': json.dumps(['Frontend Development', 'Project Management', 'UI/UX Design', 'Documentation']),
                'display_order': 2,
                'is_active': True
            },
            {
                'name': 'AARON JED FUSANA BERNARDO',
                'role': 'Developer',
                'description': 'Develops both frontend and backend components with a focus on system integration.',
                'contributions': json.dumps([
                    'Wireframe Development',
                    'Project Requirement Document',
                    'Backend Prototype Code',
                    'Frontend Prototype Code',
                    'Debugging',
                    'System Requirement Specification',
                    'Kanban Contributor'
                ]),
                'skills': json.dumps(['Full Stack Development', 'Backend Architecture', 'Debugging', 'System Integration']),
                'display_order': 3,
                'is_active': True
            },
            {
                'name': 'WU JINGHAN',
                'role': 'UI/UX & Documentation',
                'description': 'Focuses on user interface design and creating comprehensive user documentation.',
                'contributions': json.dumps([
                    'Wireframe Development',
                    'Project Requirement Document',
                    'Preliminary User Manual',
                    'Presentation Slides'
                ]),
                'skills': json.dumps(['UI/UX Design', 'User Documentation', 'Presentation Design', 'Wireframing']),
                'display_order': 4,
                'is_active': True
            },
            {
                'name': 'LI JING YOUNG',
                'role': 'Technical Documentation',
                'description': 'Creates detailed technical documentation and design specifications.',
                'contributions': json.dumps([
                    'Wireframe Development',
                    'Project Requirement Document',
                    'Technical Design Manual',
                    'Technical Design Document',
                    'Presentation Slides',
                    'System Requirement Specification'
                ]),
                'skills': json.dumps(['Technical Writing', 'System Design', 'Documentation', 'Presentation']),
                'display_order': 5,
                'is_active': True
            }
        ]
        
        for member_data in team_data:
            team_member = TeamMember(**member_data)
            session.add(team_member)
        
        session.commit()
        print(f"Added {len(team_data)} team members")

def seed_about_values():
    with get_session() as session:
        values_data = [
            {
                'title': 'Innovation',
                'description': 'Constantly pushing boundaries with AI and machine learning to deliver cutting-edge solutions.',
                'display_order': 1,
                'is_active': True
            },
            {
                'title': 'Reliability',
                'description': '99.9% uptime guarantee with robust, secure systems you can trust.',
                'display_order': 2,
                'is_active': True
            },
            {
                'title': 'User-Centric',
                'description': 'Designed with real users in mind for intuitive, frictionless experiences.',
                'display_order': 3,
                'is_active': True
            }
        ]
        
        for value_data in values_data:
            value = AboutValue(**value_data)
            session.add(value)
        
        session.commit()
        print(f"Added {len(values_data)} values")

def seed_feature_cards():
    with get_session() as session:
        feature_cards_data = [
            {
                'title': 'Our Team',
                'description': 'Learn more about AttendAI and the dedicated team behind our innovative solutions',
                'icon': '👥',
                'bg_image': 'https://images.unsplash.com/photo-1522071820081-009f0129c71c?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=800&q=80',
                'link_url': '/about',
                'link_text': 'Learn More',
                'display_order': 1,
                'is_active': True
            },
            {
                'title': 'Testimonials',
                'description': 'Read glowing reviews from educational institutions and businesses using AttendAI',
                'icon': '⭐',
                'bg_image': 'https://images.unsplash.com/photo-1552664730-d307ca884978?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w-800&q=80',
                'link_url': '/testimonials',
                'link_text': 'Read Stories',
                'display_order': 2,
                'is_active': True
            },
            {
                'title': 'Affordable Plans',
                'description': 'Choose from our range of subscription plans designed to suit institutions of all sizes',
                'icon': '💳',
                'bg_image': 'https://images.unsplash.com/photo-1554224155-6726b3ff858f?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=800&q=80',
                'link_url': '/subscriptions',
                'link_text': 'View Plans',
                'display_order': 3,
                'is_active': True
            },
            {
                'title': 'AI Powered',
                'description': 'Leverage artificial intelligence for facial recognition and predictive analytics',
                'icon': '🤖',
                'bg_image': 'https://images.unsplash.com/photo-1677442136019-21780ecad995?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=800&q=80',
                'link_url': '/features',
                'link_text': 'Explore Features',
                'display_order': 4,
                'is_active': True
            },
            {
                'title': 'Real-time Reports',
                'description': 'Generate comprehensive attendance reports and analytics instantly',
                'icon': '📊',
                'bg_image': 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=800&q=80',
                'link_url': '/features',
                'link_text': 'See Analytics',
                'display_order': 5,
                'is_active': True
            },
            {
                'title': 'Easy Tracking',
                'description': 'Mark attendance with a single click using QR codes or facial recognition',
                'icon': '📱',
                'bg_image': 'https://images.unsplash.com/photo-1611224923853-80b023f02d71?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=800&q=80',
                'link_url': '/features',
                'link_text': 'Learn How',
                'display_order': 6,
                'is_active': True
            }
        ]
        
        for card_data in feature_cards_data:
            feature_card = HomepageFeatureCard(**card_data)
            session.add(feature_card)
        
        session.commit()
        print(f"Added {len(feature_cards_data)} homepage feature cards")

def seed_features_page_content():
    with get_session() as session:
        # Check if content already exists
        existing_count = session.query(FeaturesPageContent).count()
        if existing_count > 0:
            print(f"Features page content already exists ({existing_count} records), skipping seed")
            return
        
        content_data = [
            {
                'section': 'header',
                'title': 'Powerful Features for Modern Attendance Management',
                'content': 'Discover how AttendAI revolutionizes attendance tracking with AI-powered features designed for efficiency, accuracy, and ease of use.',
                'is_active': True
            },
            {
                'section': 'hero',
                'title': 'Why Choose AttendAI?',
                'content': 'Traditional attendance methods are time-consuming, error-prone, and lack insights. AttendAI transforms this process with intelligent automation, real-time analytics, and seamless integration - saving you hours of administrative work while providing valuable data-driven insights.',
                'is_active': True
            }
        ]
        
        for content in content_data:
            page_content = FeaturesPageContent(**content)
            session.add(page_content)
        
        session.commit()
        print(f"Added {len(content_data)} features page content items")

def seed_features_comparison():
    """Seed features comparison table with default data"""
    with get_session() as session:
        # Check if content already exists
        existing_count = session.query(FeaturesComparison).count()
        if existing_count > 0:
            print(f"Features comparison items already exist ({existing_count} records), skipping seed")
            return
        
        comparison_data = [
            {
                'feature_text': 'Manual roll calls',
                'traditional_has': True,
                'attendai_has': False,
                'display_order': 1,
                'is_active': True
            },
            {
                'feature_text': 'Automated attendance marking',
                'traditional_has': False,
                'attendai_has': True,
                'display_order': 2,
                'is_active': True
            },
            {
                'feature_text': 'Paper-based tracking',
                'traditional_has': True,
                'attendai_has': False,
                'display_order': 3,
                'is_active': True
            },
            {
                'feature_text': 'Digital tracking system',
                'traditional_has': False,
                'attendai_has': True,
                'display_order': 4,
                'is_active': True
            },
            {
                'feature_text': 'Time-consuming data entry',
                'traditional_has': True,
                'attendai_has': False,
                'display_order': 5,
                'is_active': True
            },
            {
                'feature_text': 'Instant data processing',
                'traditional_has': False,
                'attendai_has': True,
                'display_order': 6,
                'is_active': True
            },
            {
                'feature_text': 'Human errors common',
                'traditional_has': True,
                'attendai_has': False,
                'display_order': 7,
                'is_active': True
            },
            {
                'feature_text': '99.8% accuracy rate',
                'traditional_has': False,
                'attendai_has': True,
                'display_order': 8,
                'is_active': True
            },
            {
                'feature_text': 'No real-time insights',
                'traditional_has': True,
                'attendai_has': False,
                'display_order': 9,
                'is_active': True
            },
            {
                'feature_text': 'Real-time dashboards',
                'traditional_has': False,
                'attendai_has': True,
                'display_order': 10,
                'is_active': True
            },
            {
                'feature_text': 'Difficult to analyze trends',
                'traditional_has': True,
                'attendai_has': False,
                'display_order': 11,
                'is_active': True
            },
            {
                'feature_text': 'Advanced analytics',
                'traditional_has': False,
                'attendai_has': True,
                'display_order': 12,
                'is_active': True
            },
            {
                'feature_text': 'No automated reporting',
                'traditional_has': True,
                'attendai_has': False,
                'display_order': 13,
                'is_active': True
            },
            {
                'feature_text': 'Automated report generation',
                'traditional_has': False,
                'attendai_has': True,
                'display_order': 14,
                'is_active': True
            },
            {
                'feature_text': 'Limited accessibility',
                'traditional_has': True,
                'attendai_has': False,
                'display_order': 15,
                'is_active': True
            },
            {
                'feature_text': 'Access anywhere, anytime',
                'traditional_has': False,
                'attendai_has': True,
                'display_order': 16,
                'is_active': True
            }
        ]
        
        for comparison in comparison_data:
            comparison_item = FeaturesComparison(**comparison)
            session.add(comparison_item)
        
        session.commit()
        print(f"Added {len(comparison_data)} features comparison items")

def seed_platform_issues():
    """Seed platform issues table with realistic dummy data"""
    with get_session() as session:
        # Get users and institutions for creating realistic issues
        users = session.query(User).filter(User.role.in_(["student", "lecturer", "admin"])).all()
        institutions = session.query(Institution).all()
        
        # Issue categories
        categories = [
            "technical",
            "billing", 
            "feature_request",
            "bug",
            "account",
            "performance", 
            "ui_ux",
            "other"
        ]
        
        # Create realistic issue descriptions based on categories
        issue_descriptions = {
            "technical": [
                "Facial recognition not working properly in classroom lighting conditions",
                "System crashes when trying to mark attendance for large classes"
            ],
            "billing": [
                "Incorrect billing amount charged for monthly subscription",
                "Payment gateway integration not working for international cards"
            ],
            "feature_request": [
                "Request for bulk attendance import from CSV files",
                "Need custom report templates for different departments",
                "Advanced analytics dashboard with predictive insights"
            ],
            "bug": [
                "Attendance marked twice for the same student in system records",
                "Date/time display incorrect in semester reports (off by 1 day)",
                "Password reset emails containing expired links"
            ],
            "account": [
                "Cannot reset password - reset emails not being received",
                "Account access suddenly revoked without notification"
            ],
            "performance": [
                "Dashboard loading extremely slow during morning peak hours (8-9 AM)",
                "Attendance marking taking 5+ seconds per student in classes of 50+",
                "Memory usage climbing steadily without garbage collection"
            ],
            "ui_ux": [
                "Attendance marking interface confusing for new lecturers - needs simplification"
            ],
            "other": [
                "General feedback about platform usability and user experience",
                "General inquiry about platform scalability and future roadmap"
            ]
        }
        
        # Generate issues
        issues = []
        num_issues = 50  # Number of issues to create
        
        for i in range(num_issues):
            # Select random user and institution
            user = random.choice(users)
            
            # Make sure user's institution is used
            user_institution = next((inst for inst in institutions if inst.institution_id == user.institution_id), institutions[0])
            
            # Select random category
            category = random.choice(categories)
            
            # Create description from category-specific templates
            description = random.choice(issue_descriptions[category])
            
            # Add some variability and details to descriptions
            details = []
            
            # Add frequency/occurrence
            if random.random() < 0.4:
                frequencies = ["daily", "multiple times per week", "every Monday", "during peak hours", "randomly"]
                details.append(f"Occurs {random.choice(frequencies)}.")
            
            # Add impact statement
            if random.random() < 0.3:
                impacts = [
                    "This affects all students in my classes.",
                    "This creates extra work for our IT department."
                ]
                details.append(f"Impact: {random.choice(impacts)}")
            
            # Add attempted solutions
            if random.random() < 0.25:
                solutions = [
                    "Tried clearing cache and cookies.",
                    "Checked system requirements and all are met."
                ]
                details.append(f"Attempted: {random.choice(solutions)}")
            
            # Add urgency if needed
            if random.random() < 0.2:
                urgencies = [
                    "Need resolution before end of semester.",
                    "Preventing new staff onboarding."
                ]
                details.append(f"Urgency: {random.choice(urgencies)}")
            
            # Combine description with details
            if details:
                description += "\n\n" + "\n".join(details)
            
            # Add device/browser info (30% chance)
            if random.random() < 0.3:
                devices = [
                    "Device: Windows 10, Chrome 120",
                    "Device: Windows 11, Edge 119"
                ]
                description += f"\n\n{random.choice(devices)}"
            
            # Set created_at date - issues from last 90 days
            days_ago = random.randint(0, 90)
            created_at = datetime.now() - timedelta(days=days_ago)
            
            # For some issues, set deleted_at (soft delete simulation)
            deleted_at = None
            if random.random() < 0.1 and days_ago > 0:  # 10% of issues are "deleted"
                deleted_days = random.randint(1, days_ago)
                deleted_at = created_at + timedelta(days=deleted_days)
            
            # Create the issue (matching your actual model)
            issue = PlatformIssue(
                user_id=user.user_id,
                institution_id=user_institution.institution_id,
                description=description,
                category=category,
                created_at=created_at,
                deleted_at=deleted_at
            )
            
            issues.append(issue)
        
        # Add all issues to session
        session.add_all(issues)
        session.commit()
        print(f"Total Issues Created: {len(issues)}")


def seed_faqs():
    """Seed FAQs table with default data"""
    with get_session() as session:
        faqs = [
            # General FAQs
            FAQ(
                category="general",
                question="What is AttendAI and how does it work?",
                answer="""AttendAI is an AI-powered attendance management system that revolutionizes how educational institutions and businesses track attendance. Our system uses multiple verification methods including facial recognition, QR code scanning, and mobile check-ins to accurately record attendance in real-time.

The platform processes attendance data through our secure cloud infrastructure, providing administrators with real-time dashboards, predictive analytics, and comprehensive reporting tools. Everything is designed to be user-friendly while maintaining enterprise-grade security and reliability.""",
                display_order=1,
                is_active=True
            ),
            FAQ(
                category="general",
                question="Is there a free trial available?",
                answer="""Yes! We offer a 14-day free trial for all our plans. During the trial period, you'll have access to all features of the Professional plan, including AI face recognition, real-time analytics, and up to 500 student capacity. No credit card is required to start your trial.

Our support team will help you set up the system and provide training materials to ensure you get the most out of your trial period.""",
                display_order=2,
                is_active=True
            ),
            FAQ(
                category="general",
                question="How accurate is the facial recognition technology?",
                answer="""Our AI-powered facial recognition system achieves 99.8% accuracy in optimal conditions. The system uses advanced machine learning algorithms that continuously improve with use. Key features include:

• Works in various lighting conditions
• Adapts to different angles and distances
• Handles accessories like glasses and masks
• Protects against spoofing attempts
• Processes recognition in under 2 seconds

We also provide multiple fallback methods (QR codes, PINs) to ensure reliability in all situations.""",
                display_order=3,
                is_active=True
            ),
            
            # Features FAQs
            FAQ(
                category="features",
                question="Does AttendAI integrate with existing school management systems?",
                answer="""Yes, AttendAI offers seamless integration with popular school management systems including:

• Google Classroom and Microsoft Teams
• Popular LMS platforms (Canvas, Moodle, Blackboard)
• Student Information Systems (SIS)
• Human Resource Management Systems (HRMS)

We provide comprehensive API documentation for custom integrations, and our technical team can assist with implementation to ensure smooth data synchronization.""",
                display_order=1,
                is_active=True
            ),
            FAQ(
                category="features",
                question="Can parents or guardians receive attendance notifications?",
                answer="""Absolutely. AttendAI includes a comprehensive notification system that can alert parents and guardians via:

• Email notifications for daily, weekly, or monthly attendance reports
• SMS alerts for immediate attendance concerns
• Mobile app notifications through our dedicated parent portal
• Customizable alert thresholds (e.g., notify when attendance drops below 90%)

Parents can also access a secure portal to view their child's attendance history, patterns, and receive automated alerts about upcoming parent-teacher meetings.""",
                display_order=2,
                is_active=True
            ),
            
            # Pricing FAQs
            FAQ(
                category="pricing",
                question="What payment methods do you accept?",
                answer="""We accept all major payment methods for your convenience:

• Credit and debit cards (Visa, MasterCard, American Express)
• PayPal for quick online payments
• Bank transfers for enterprise customers
• Annual billing with 15% discount
• Purchase orders for educational institutions

All payments are processed through secure, PCI-compliant payment gateways to ensure your financial information is protected.""",
                display_order=1,
                is_active=True
            ),
            FAQ(
                category="pricing",
                question="Can I upgrade or downgrade my plan later?",
                answer="""Yes, you can change your plan at any time. When upgrading, the new features become available immediately, and you'll be charged the prorated difference for the remainder of your billing cycle. When downgrading, the changes take effect at the start of your next billing cycle.

Our system automatically handles data migration between plans, so you don't need to worry about losing any attendance records or settings when changing plans.""",
                display_order=2,
                is_active=True
            ),
            
            # Technical FAQs (placeholder for future)
            FAQ(
                category="technical",
                question="What are the system requirements for AttendAI?",
                answer="""AttendAI is a cloud-based solution with minimal system requirements:

• Web Browser: Chrome, Firefox, Safari, or Edge (latest versions)
• Internet Connection: Minimum 5 Mbps for smooth operation
• For facial recognition: Any device with a camera (720p or higher recommended)
• Mobile App: iOS 12+ or Android 8+

No special hardware or installation is required. The system works on desktops, laptops, tablets, and smartphones.""",
                display_order=1,
                is_active=True
            ),
            
            # Implementation FAQs (placeholder for future)
            FAQ(
                category="implementation",
                question="How long does it take to set up AttendAI?",
                answer="""The setup process is quick and straightforward:

• Initial Setup: 1-2 hours to configure your institution details
• User Import: Bulk import students and staff via CSV (5-10 minutes)
• Training: 2-hour training session for administrators
• Facial Data Collection: Students can register in 30 seconds each
• Go Live: Most institutions are fully operational within 1-3 days

Our dedicated onboarding team guides you through every step and provides ongoing support.""",
                display_order=1,
                is_active=True
            ),
        ]
        
        session.add_all(faqs)
        session.commit()
        print(f"Added {len(faqs)} FAQs")


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
    
    if row_count("Hero_Features") == 0:
        seed_hero_features()
    
    if row_count("Stats") == 0:
        seed_stats()
    
    if row_count("About_Intro") == 0:
        seed_about_intro()
    
    if row_count("About_Story") == 0:
        seed_about_story()
    
    if row_count("About_Mission_Vision") == 0:
        seed_about_mission_vision()
    
    if row_count("Team_Members") == 0:
        seed_team_members()
    
    if row_count("About_Values") == 0:
        seed_about_values()
    
    if row_count("Homepage_Feature_Cards") == 0:
        seed_feature_cards()
    
    if row_count("Features_Page_Content") == 0:
        seed_features_page_content()
    
    if row_count("Features_Comparison") == 0:
        seed_features_comparison()

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

    if row_count("Platform_Issues") == 0:
        seed_platform_issues()

    if row_count("FAQs") == 0:
        seed_faqs()

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