import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def delete_db():
    """Delete the database if it exists"""
    try:
        # Connect to MySQL without specifying a database
        conn = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', ''),
            port=int(os.getenv('MYSQL_PORT', '3306'))
        )
        
        cursor = conn.cursor()
        db_name = os.getenv('MYSQL_DB', 'attendance_system')
        
        # Drop database if it exists
        cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
        print(f"Database '{db_name}' deleted if it existed")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error deleting database: {e}")
        return False