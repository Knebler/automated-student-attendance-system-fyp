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

print('\n' + '='*70)
print('COURSE ENROLLMENTS FOR STUDENTS WITH FACIAL DATA')
print('='*70)

cursor.execute('''
    SELECT u.user_id, u.name, co.code, co.name as course_name, s.name as semester
    FROM users u
    LEFT JOIN course_users cu ON u.user_id = cu.user_id
    LEFT JOIN courses co ON cu.course_id = co.course_id
    LEFT JOIN semesters s ON cu.semester_id = s.semester_id
    WHERE u.user_id IN (17, 18, 19)
    ORDER BY u.user_id, co.code
''')

rows = cursor.fetchall()
print(f"{'ID':<5} {'Name':<20} {'Course':<15} {'Course Name':<30} {'Semester':<15}")
print('-'*70)

for row in rows:
    user_id, name, code, course_name, semester = row
    code_str = code if code else 'NOT ENROLLED'
    course_str = course_name if course_name else '-'
    sem_str = semester if semester else '-'
    print(f'{user_id:<5} {name:<20} {code_str:<15} {course_str:<30} {sem_str:<15}')

print('='*70)
print('\n💡 NOTE: Grace Kim (ID: 17) needs to be enrolled in the same course')
print('   as Henry Lee and Isabella Chen for all 3 to appear in facial recognition.')
print('='*70 + '\n')

cursor.close()
conn.close()
