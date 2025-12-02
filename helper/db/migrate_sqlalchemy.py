import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

def migrate_schema():
    """Apply SQL schema from database/schema.sql using SQLAlchemy engine.

    This script is a small helper to create the application's schema using the
    same DB credentials the app uses. It is intended for development and
    CI scenarios where the schema needs to be created through SQLAlchemy.
    """
    user = os.getenv('MYSQL_USER', 'root')
    password = os.getenv('MYSQL_PASSWORD', '')
    host = os.getenv('MYSQL_HOST', 'localhost')
    port = os.getenv('MYSQL_PORT', '3306')
    db_name = os.getenv('MYSQL_DB', 'attendance_system')

    uri = f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}"

    engine = create_engine(uri)

    schema_path = os.path.join(os.path.dirname(__file__), '../../database/schema.sql')
    if not os.path.exists(schema_path):
        print(f"Schema file not found at {schema_path}")
        return False

    with open(schema_path, 'r', encoding='utf-8') as f:
        sql_script = f.read()

    # Split on semicolons - simple but effective for this repo's schema
    statements = [s.strip() for s in sql_script.split(';') if s.strip()]

    with engine.begin() as conn:
        for stmt in statements:
            try:
                conn.exec_driver_sql(stmt)
            except Exception as e:
                # Print warning but continue; many statements may be idempotent
                print(f"Warning executing statement: {e}")

    print("Schema applied via SQLAlchemy engine.")
    return True

if __name__ == '__main__':
    migrate_schema()
