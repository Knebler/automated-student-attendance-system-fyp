import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def create_db():
    """Create database and all tables from schema.sql"""
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
        
        # Create database
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"Database '{db_name}' created or already exists")
        
        # Use the database
        cursor.execute(f"USE {db_name}")
        
        # Read and execute schema.sql
        schema_path = os.path.join(os.path.dirname(__file__), '../../database/schema.sql')
        
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                sql_script = f.read()
            
            # Split script into individual statements
            statements = sql_script.split(';')
            
            for statement in statements:
                statement = statement.strip()
                if statement:
                    try:
                        cursor.execute(statement)
                    except Exception as e:
                        print(f"Warning executing statement: {e}")
                        continue
            
            print("Schema created successfully!")
            
            # Populate with dummy data
            from .populate_dummy_data import populate_dummy_data
            populate_dummy_data(conn, cursor)
            
        else:
            print(f"Schema file not found at {schema_path}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Error creating database: {e}")
        return False