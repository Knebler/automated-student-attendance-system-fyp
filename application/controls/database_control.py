from application.entities.base_entity import BaseEntity
from application.entities.attendance_record import AttendanceRecord
from application.entities.institution import Institution
from application.entities.course import Course
from application.entities.lecturer import Lecturer
from application.entities.student import Student
from application.entities.enrollment import Enrollment
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
                Enrollment,
                Session,
                AttendanceRecord
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
            # prefer DB-API cursor via BaseEntity.get_db_connection
            try:
                cursor = BaseEntity.get_db_connection(app)
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                result = cursor.fetchone()
                # close if supported
                try:
                    cursor.close()
                except Exception:
                    pass
                if result:
                    # tuple-like
                    return int(result[0]) > 0
                return False
            except Exception:
                # fallback to raw mysql connector if present
                mysql = app.config.get('mysql')
                if mysql is None:
                    return False
                cursor = mysql.connection.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                cursor.close()
                return count > 0
        except Exception:
            return False

    @staticmethod
    def check_database_connection(app):
        """Check whether the configured database is reachable.

        Returns a dict { success: bool, message: str }.
        Tries SQLAlchemy engine (app.config['db']) first, then falls back to
        traditional mysql connector (app.config['mysql']) if present.
        """
        try:
            # prefer SQLAlchemy session/engine if available
            db = app.config.get('db')
            if db is not None:
                # run a lightweight query
                try:
                    session = db.session
                    session.execute('SELECT 1')
                    return {'success': True, 'message': 'ok'}
                except Exception as e:
                    return {'success': False, 'message': str(e)}

            # fallback to mysql connector
            mysql = app.config.get('mysql')
            if mysql is not None:
                try:
                    cursor = mysql.connection.cursor()
                    cursor.execute('SELECT 1')
                    cursor.close()
                    return {'success': True, 'message': 'ok'}
                except Exception as e:
                    return {'success': False, 'message': str(e)}

            return {'success': False, 'message': 'no-database-configured'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def insert_sample_data(app):
        """Insert sample data for testing"""
        # Prefer unified DBAPI cursor from BaseEntity so SQLAlchemy-backed apps will work
        cursor = None
        mysql = app.config.get('mysql')
        try:
            cursor = BaseEntity.get_db_connection(app)
        except Exception:
            cursor = None

        if cursor is None and mysql is not None:
            cursor = mysql.connection.cursor()
        
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
        
        # Commit depending on backend
        try:
            if mysql is not None and cursor is not None and getattr(mysql, 'connection', None):
                mysql.connection.commit()
            else:
                # session-backed wrapper - use BaseEntity.commit_changes
                BaseEntity.commit_changes(app)
        except Exception:
            pass

        try:
            cursor.close()
        except Exception:
            pass


# Dev actions expose database helpers for testing
try:
    # lazy import so this module still loads when dev_actions isn't available
    from application.boundaries.dev_actions import register_action

    register_action(
        'check_table_has_data',
        DatabaseControl.check_table_has_data,
        params=[{'name': 'table_name', 'label': 'Table name', 'placeholder': 'e.g. Students'}],
        description='Return whether a given table contains any rows (dev only)'
    )

    register_action(
        'insert_sample_data',
        DatabaseControl.insert_sample_data,
        params=[],
        description='Insert sample data into the database (dev only)'
    )
except Exception:
    # dev_actions may not be importable in production or tests — ignore
    pass