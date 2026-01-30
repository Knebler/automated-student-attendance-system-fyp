"""
Increase the face_encoding column size in facial_data table
Changes from BLOB (64KB) to MEDIUMBLOB (16MB)
"""
import os
from dotenv import load_dotenv
import mysql.connector

load_dotenv()

DB = {
    "host": os.getenv('DB_HOST'),
    "user": os.getenv('DB_USER'),
    "password": os.getenv('DB_PASSWORD'),
    "database": os.getenv('DB_NAME'),
    "port": int(os.getenv('DB_PORT', 3306))
}

if os.getenv('DB_SSL_ENABLED', 'false').lower() == 'true':
    ssl_ca = os.getenv('DB_SSL_CA', './combined-ca-certificates.pem')
    if os.path.exists(ssl_ca):
        DB['ssl_ca'] = ssl_ca
        DB['ssl_verify_cert'] = True

print("=" * 70)
print("🔧 DATABASE COLUMN SIZE UPGRADE")
print("=" * 70)

try:
    conn = mysql.connector.connect(**DB)
    cursor = conn.cursor()
    
    # Check current column type
    cursor.execute("""
        SELECT COLUMN_TYPE, CHARACTER_MAXIMUM_LENGTH, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s
        AND TABLE_NAME = 'facial_data'
        AND COLUMN_NAME = 'face_encoding'
    """, (DB['database'],))
    
    result = cursor.fetchone()
    
    if result:
        column_type, max_length, data_type = result
        
        # Decode bytes to string if needed
        if isinstance(column_type, bytes):
            column_type = column_type.decode('utf-8')
        if isinstance(data_type, bytes):
            data_type = data_type.decode('utf-8')
        
        print(f"\nCurrent column type: {column_type}")
        print(f"Data type: {data_type}")
        print(f"Max length: {max_length}")
        
        if 'longblob' in column_type.lower():
            print("\n✅ Column is already LONGBLOB (4GB max)")
            print("   No changes needed!")
        elif 'mediumblob' in column_type.lower():
            print("\n✅ Column is already MEDIUMBLOB (16MB max)")
            print("   This should be sufficient.")
            
            response = input("\n❓ Upgrade to LONGBLOB (4GB) anyway? (yes/no): ").strip().lower()
            if response == 'yes':
                print("\nUpgrading to LONGBLOB...")
                cursor.execute("ALTER TABLE facial_data MODIFY COLUMN face_encoding LONGBLOB")
                conn.commit()
                print("✅ Column upgraded to LONGBLOB!")
            else:
                print("\n✅ Keeping MEDIUMBLOB")
        else:
            print(f"\n⚠️  Column is {column_type}")
            print("   This is too small for facial recognition data!")
            
            response = input("\n❓ Upgrade to LONGBLOB (4GB)? (yes/no): ").strip().lower()
            
            if response == 'yes':
                print("\nUpgrading column...")
                cursor.execute("ALTER TABLE facial_data MODIFY COLUMN face_encoding LONGBLOB")
                conn.commit()
                print("✅ Column upgraded to LONGBLOB (4GB max)!")
                print("   You can now store larger facial recognition data.")
            else:
                print("\n❌ Cancelled - column not modified")
    else:
        print("\n❌ Column 'face_encoding' not found in table 'facial_data'")
    
    cursor.close()
    conn.close()
    print("=" * 70)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
