import os
from dotenv import load_dotenv
import mysql.connector

load_dotenv()

DB = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME'),
    'port': int(os.getenv('DB_PORT', 3306))
}

if os.getenv('DB_SSL_ENABLED', 'false').lower() == 'true':
    ssl_ca = os.getenv('DB_SSL_CA', './combined-ca-certificates.pem')
    if os.path.exists(ssl_ca):
        DB['ssl_ca'] = ssl_ca
        DB['ssl_verify_cert'] = True

conn = mysql.connector.connect(**DB)
cursor = conn.cursor()

# Get all active students first
print('\n' + '='*70)
print('ALL ACTIVE STUDENTS IN DATABASE')
print('='*70)

cursor.execute('''
    SELECT u.user_id, u.name, u.email,
           CASE WHEN fd.facial_data_id IS NOT NULL THEN 'YES' ELSE 'NO' END as has_facial_data,
           fd.sample_count
    FROM users u
    LEFT JOIN facial_data fd ON u.user_id = fd.user_id AND fd.is_active = TRUE
    WHERE u.role = 'student' AND u.is_active = TRUE
    ORDER BY u.user_id
''')

all_students = cursor.fetchall()
print(f"{'ID':<5} {'Name':<25} {'Email':<30} {'Has Data':<10} {'Samples':<10}")
print('-'*70)
for row in all_students:
    user_id, name, email, has_data, samples = row
    samples_str = str(samples) if samples else 'N/A'
    print(f'{user_id:<5} {name:<25} {email:<30} {has_data:<10} {samples_str:<10}')

print('='*70)
print(f'Total: {len(all_students)} active students')
print('='*70)

# Check facial data for enrolled students
print('\n' + '='*70)
print('FACIAL DATA STATUS FOR SPECIFIC STUDENTS (18, 19)')
print('='*70)

cursor.execute('''
    SELECT u.user_id, u.name, 
           CASE WHEN fd.facial_data_id IS NOT NULL THEN 'YES' ELSE 'NO' END as has_facial_data,
           fd.sample_count,
           fd.updated_at
    FROM users u
    LEFT JOIN facial_data fd ON u.user_id = fd.user_id AND fd.is_active = TRUE
    WHERE u.user_id IN (18, 19)
    ORDER BY u.user_id
''')

print('\n' + '='*70)
print('FACIAL DATA STATUS FOR ENROLLED STUDENTS')
print('='*70)
print(f"{'ID':<5} {'Name':<20} {'Has Data':<12} {'Samples':<10} {'Last Updated':<20}")
print('-'*70)

for row in cursor.fetchall():
    user_id, name, has_data, samples, updated = row
    samples_str = str(samples) if samples else 'N/A'
    updated_str = str(updated) if updated else 'Never'
    print(f'{user_id:<5} {name:<20} {has_data:<12} {samples_str:<10} {updated_str:<20}')

print('='*70)
print('\n⚠️  SOLUTION: The student with NO facial data needs to:')
print('  1. Log in to the student portal')
print('  2. Go to Profile > Facial Recognition Retrain')
print('  3. Capture their face photos (5-10 photos recommended)')
print('  4. Click "Save Training Data"')
print('='*70 + '\n')

cursor.close()
conn.close()
