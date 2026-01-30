"""
Delete corrupted facial data records
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

print("Connecting to database...")
conn = mysql.connector.connect(**DB)
cursor = conn.cursor()

# Find users with problematic names
print("\nFinding corrupted facial data...")
cursor.execute("""
    SELECT fd.facial_data_id, u.name, u.user_id
    FROM facial_data fd
    JOIN users u ON fd.user_id = u.user_id
    WHERE u.name IN ('Charlie Brown', 'Isabella Chen')
    AND fd.is_active = TRUE
""")

results = cursor.fetchall()

if results:
    print(f"\nFound {len(results)} corrupted records:")
    for facial_data_id, name, user_id in results:
        print(f"  - {name} (User ID: {user_id}, Facial Data ID: {facial_data_id})")
    
    confirm = input("\nDelete these corrupted records? (yes/no): ").strip().lower()
    
    if confirm == 'yes':
        for facial_data_id, name, user_id in results:
            cursor.execute("DELETE FROM facial_data WHERE facial_data_id = %s", (facial_data_id,))
            print(f"  ✅ Deleted facial data for {name}")
        
        conn.commit()
        print("\n✅ Corrupted facial data deleted!")
        print("   These students will need to re-upload their photos.")
    else:
        print("\n❌ Cancelled")
else:
    print("\n✅ No corrupted records found")

cursor.close()
conn.close()
