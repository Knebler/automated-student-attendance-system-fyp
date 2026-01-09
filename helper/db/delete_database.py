import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def delete_db():
    """Delete the database if it exists"""
    try:
        # Connect to MySQL without specifying a database
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            port=int(os.getenv('DB_PORT'))
        )
        
        cursor = conn.cursor()
        db_name = os.getenv('DB_NAME', 'attendance_system')
        
        # Drop database if it exists
        cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
        print(f"Database '{db_name}' deleted if it existed")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error deleting database: {e}")
        return False
    
if __name__ == "__main__":
    delete_db()