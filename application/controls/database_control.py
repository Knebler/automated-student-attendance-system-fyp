from application.entities.user import User
from application.entities.attendance import Attendance
from application.entities.institution import Institution
from application.entities.course import Course
from application.entities.lecturer import Lecturer
from application.entities.student import Student
#from application.entities.enrollment import Enrollment
from application.entities.session import Session
from application.entities.platform_manager import PlatformManager
from application.entities.subscription_plan import SubscriptionPlan
from application.entities.subscription import Subscription
from application.entities.venue import Venue
from application.entities.timetable_slot import TimetableSlot

class DatabaseControl:
    """Control class for database initialization and maintenance"""
    
    @staticmethod
    def initialize_database(app):
        """Initialize all database tables according to schema"""
        try:
            # Create tables in order of dependencies
            tables = [
                PlatformManager,
                SubscriptionPlan,
                Subscription,
                Institution,
                Venue,
                TimetableSlot,
                Lecturer,
                Course,
                Student,
                #Enrollment,
                Session,
                Attendance
            ]
            
            for entity_class in tables:
                entity_class.create_table(app)
            
            # Insert sample data if needed
            if not DatabaseControl.check_table_has_data(app, 'Subscription_Plans'):
                DatabaseControl.insert_sample_data(app)
            
            return {
                'success': True,
                'message': 'Database initialized successfully',
                'tables_created': [entity_class.TABLE_NAME for entity_class in tables]
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def check_table_has_data(app, table_name):
        """Check if a table has any data"""
        try:
            cursor = app.config['mysql'].connection.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            cursor.close()
            return count > 0
        except:
            return False
    
    @staticmethod
    def insert_sample_data(app):
        """Insert sample data for testing"""
        cursor = app.config['mysql'].connection.cursor()
        
        # Insert sample subscription plan
        cursor.execute("""
        INSERT INTO Subscription_Plans (plan_name, description, price_per_cycle, billing_cycle, 
            max_students, max_courses, max_lecturers, features)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            'Starter Plan',
            'Perfect for small institutions getting started with automated attendance',
            99.99,
            'monthly',
            500,
            50,
            20,
            '{"facial_recognition": true, "basic_reporting": true, "email_support": true}'
        ))
        
        # Insert platform manager
        cursor.execute("""
        INSERT INTO Platform_Managers (email, password_hash, full_name)
        VALUES (%s, %s, %s)
        """, (
            'admin@attendanceplatform.com',
            '$2b$10$examplehash',
            'System Administrator'
        ))
        
        app.config['mysql'].connection.commit()
        cursor.close()