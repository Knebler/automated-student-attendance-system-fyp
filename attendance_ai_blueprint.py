"""
Attendance AI API Blueprint - FIXED VERSION
============================================
This blueprint contains all the API endpoints for the attendance system.

Fixes:
- Updated /recognition/start to accept session_id from request body
- No duplicate endpoint functions
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, date, timedelta
from sqlalchemy import text
import numpy as np
import cv2
import base64
import json
import subprocess
import sys
import os
import signal
import zlib
import pickle

# Create blueprint
attendance_ai_bp = Blueprint('attendance_ai', __name__)

# Global variable to track recognition process
recognition_process = None

# Face cascade for face detection during import
FACE_CASCADE = None


def load_face_detector():
    """Load the face detector cascade"""
    global FACE_CASCADE
    if FACE_CASCADE is None:
        cascade_paths = [
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml',
            'data/haarcascade_frontalface_default.xml',
            'haarcascade_frontalface_default.xml',
            './AttendanceAI/data/haarcascade_frontalface_default.xml'
        ]
        
        for path in cascade_paths:
            try:
                cascade = cv2.CascadeClassifier(path)
                if not cascade.empty():
                    FACE_CASCADE = cascade
                    print(f"✅ Face detector loaded from: {path}")
                    return FACE_CASCADE
            except:
                continue
        
        print("⚠️ Warning: Could not load face detector")
    return FACE_CASCADE


def get_db_session():
    """Get database session from app config"""
    try:
        db = current_app.config.get('db')
        if db:
            return db.session
    except Exception as e:
        print(f"Error getting db session: {e}")
    return None


def get_db():
    """Get the SQLAlchemy db instance"""
    return current_app.config.get('db')


def detect_and_crop_face(img, face_cascade):
    """Detect face in image and return cropped face region."""
    if face_cascade is None:
        h, w = img.shape[:2]
        size = min(h, w)
        start_h = (h - size) // 2
        start_w = (w - size) // 2
        return img[start_h:start_h+size, start_w:start_w+size], False
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3, minSize=(30, 30))
    
    if len(faces) > 0:
        largest_face = max(faces, key=lambda f: f[2] * f[3])
        x, y, w, h = largest_face
        padding_w = int(0.05 * w)
        padding_h = int(0.05 * h)
        x = max(0, x - padding_w)
        y = max(0, y - padding_h)
        w = min(img.shape[1] - x, w + 2 * padding_w)
        h = min(img.shape[0] - y, h + 2 * padding_h)
        face_img = img[y:y+h, x:x+w]
        return face_img, True
    else:
        h, w = img.shape[:2]
        margin_h = int(h * 0.2)
        margin_w = int(w * 0.2)
        return img[margin_h:h-margin_h, margin_w:w-margin_w], False


def generate_augmented_samples(face_img, sample_count=100):
    """Generate augmented training samples from a single face image."""
    all_faces = []
    base_face = cv2.resize(face_img, (60, 60))
    
    for i in range(sample_count):
        augmented = base_face.copy()
        
        # Multi-scale augmentation
        scale = np.random.uniform(0.7, 1.3)
        new_size = int(60 * scale)
        
        if new_size > 20:
            scaled = cv2.resize(augmented, (new_size, new_size))
            if new_size >= 60:
                start = (new_size - 60) // 2
                augmented = scaled[start:start+60, start:start+60]
            else:
                pad = (60 - new_size) // 2
                augmented = cv2.copyMakeBorder(scaled, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
                augmented = cv2.resize(augmented, (60, 60))
        
        # Random brightness
        brightness = np.random.randint(-40, 40)
        augmented = np.clip(augmented.astype(np.int16) + brightness, 0, 255).astype(np.uint8)
        
        # Random contrast
        if i % 4 == 0:
            alpha = np.random.uniform(0.7, 1.3)
            augmented = np.clip(alpha * augmented, 0, 255).astype(np.uint8)
        
        # Random rotation
        if i % 3 == 0:
            angle = np.random.uniform(-20, 20)
            h, w = augmented.shape[:2]
            M = cv2.getRotationMatrix2D((w/2, h/2), angle, 1.0)
            augmented = cv2.warpAffine(augmented, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        
        # Random flip
        if np.random.random() > 0.5:
            augmented = cv2.flip(augmented, 1)
        
        # Random translation
        if i % 5 == 0:
            tx = np.random.randint(-5, 5)
            ty = np.random.randint(-5, 5)
            M = np.float32([[1, 0, tx], [0, 1, ty]])
            augmented = cv2.warpAffine(augmented, M, (augmented.shape[1], augmented.shape[0]), borderMode=cv2.BORDER_REPLICATE)
        
        # Random blur
        if i % 6 == 0:
            ksize = np.random.choice([3, 5])
            augmented = cv2.GaussianBlur(augmented, (ksize, ksize), 0)
        
        final = cv2.resize(augmented, (50, 50))
        flattened = final.flatten()
        all_faces.append(flattened)
    
    return np.array(all_faces, dtype=np.uint8)


# ==================== HEALTH CHECK ====================

@attendance_ai_bp.route('/ping', methods=['GET'])
def ping():
    """Simple ping endpoint - no database required"""
    return jsonify({
        'success': True,
        'message': 'pong',
        'timestamp': datetime.now().isoformat()
    })


@attendance_ai_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        db_status = 'Unknown'
        
        try:
            db = current_app.config.get('db')
            if db:
                db.session.execute(text("SELECT 1"))
                db_status = 'Connected'
            else:
                db_status = 'No db instance'
        except Exception as db_err:
            db_status = f'Error: {str(db_err)}'
        
        return jsonify({
            'status': 'healthy',
            'success': True,
            'database': db_status,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'success': False,
            'database': 'Error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


# ==================== SESSIONS ====================

@attendance_ai_bp.route('/sessions/debug', methods=['GET'])
def debug_sessions():
    """Debug endpoint to see all sessions in database"""
    try:
        session = get_db_session()
        if not session:
            return jsonify({'success': False, 'error': 'No database session'}), 500
        
        now = datetime.now()
        today = date.today()
        
        query = text("""
            SELECT c.class_id, c.course_id, c.venue_id, c.lecturer_id,
                   c.start_time, c.end_time, c.status,
                   co.code as course_code, co.name as course_name
            FROM classes c
            LEFT JOIN courses co ON c.course_id = co.course_id
            ORDER BY c.start_time DESC
            LIMIT 20
        """)
        results = session.execute(query).fetchall()
        
        sessions_list = []
        for row in results:
            start_time = row[4]
            end_time = row[5]
            
            sessions_list.append({
                'class_id': row[0],
                'course_id': row[1],
                'start_time_raw': str(start_time),
                'start_time_type': str(type(start_time)),
                'end_time_raw': str(end_time),
                'status': row[6],
                'course_code': row[7]
            })
        
        return jsonify({
            'success': True,
            'current_datetime': now.isoformat(),
            'current_date': str(today),
            'total_sessions_found': len(sessions_list),
            'sessions': sessions_list
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@attendance_ai_bp.route('/sessions', methods=['GET'])
@attendance_ai_bp.route('/classes', methods=['GET'])
def get_sessions():
    """Get today's classes (sessions)"""
    try:
        session = get_db_session()
        if not session:
            return jsonify({'success': False, 'error': 'No database session'}), 500
        
        date_str = request.args.get('date')
        show_all = request.args.get('all', 'false').lower() == 'true'
        
        if date_str:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            target_date = date.today()
        
        print(f"[DEBUG] Querying sessions for date: {target_date}, show_all: {show_all}")
        
        if show_all:
            query = text("""
                SELECT c.class_id, c.course_id, c.venue_id, c.lecturer_id,
                       c.start_time, c.end_time, c.status,
                       co.code as course_code, co.name as course_name,
                       v.name as venue_name, u.name as lecturer_name
                FROM classes c
                LEFT JOIN courses co ON c.course_id = co.course_id
                LEFT JOIN venues v ON c.venue_id = v.venue_id
                LEFT JOIN users u ON c.lecturer_id = u.user_id
                ORDER BY c.start_time
            """)
            results = session.execute(query).fetchall()
        else:
            start_of_day = datetime.combine(target_date, datetime.min.time())
            end_of_day = datetime.combine(target_date, datetime.max.time())
            
            query = text("""
                SELECT c.class_id, c.course_id, c.venue_id, c.lecturer_id,
                       c.start_time, c.end_time, c.status,
                       co.code as course_code, co.name as course_name,
                       v.name as venue_name, u.name as lecturer_name
                FROM classes c
                LEFT JOIN courses co ON c.course_id = co.course_id
                LEFT JOIN venues v ON c.venue_id = v.venue_id
                LEFT JOIN users u ON c.lecturer_id = u.user_id
                WHERE c.start_time >= :start_day
                  AND c.start_time <= :end_day
                ORDER BY c.start_time
            """)
            results = session.execute(query, {'start_day': start_of_day, 'end_day': end_of_day}).fetchall()
        
        sessions_list = []
        for row in results:
            start_time = row[4]
            end_time = row[5]
            
            if isinstance(start_time, datetime):
                start_time_str = start_time.strftime('%H:%M:%S')
                date_str = start_time.strftime('%Y-%m-%d')
            else:
                start_time_str = str(start_time) if start_time else '00:00:00'
                date_str = str(target_date)
            
            if isinstance(end_time, datetime):
                end_time_str = end_time.strftime('%H:%M:%S')
            else:
                end_time_str = str(end_time) if end_time else '23:59:59'
            
            sessions_list.append({
                'session_id': row[0],
                'class_id': row[0],
                'course_id': row[1],
                'venue_id': row[2],
                'lecturer_id': row[3],
                'start_time': start_time_str,
                'end_time': end_time_str,
                'date': date_str,
                'status': row[6],
                'course_code': row[7] or 'N/A',
                'course_name': row[8] or 'N/A',
                'venue_name': row[9] or 'N/A',
                'lecturer_name': row[10] or 'N/A'
            })
        
        return jsonify({
            'success': True,
            'sessions': sessions_list,
            'classes': sessions_list,
            'count': len(sessions_list),
            'query_date': str(target_date)
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'sessions': [],
            'classes': []
        }), 500


# ==================== STUDENTS ====================

@attendance_ai_bp.route('/students', methods=['GET'])
def get_students():
    """Get all students with facial data"""
    try:
        session = get_db_session()
        if not session:
            return jsonify({'success': False, 'error': 'No database session'}), 500
        
        query = text("""
            SELECT u.user_id, u.name, u.email, u.is_active
            FROM users u
            WHERE u.role = 'student' AND u.is_active = TRUE
        """)
        results = session.execute(query).fetchall()
        
        students_list = []
        for row in results:
            students_list.append({
                'student_id': row[0],
                'user_id': row[0],
                'name': row[1],
                'email': row[2],
                'facial_data_id': row[0],
                'is_active': row[3]
            })
        
        return jsonify({
            'success': True,
            'students': students_list,
            'count': len(students_list)
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@attendance_ai_bp.route('/students/training-data', methods=['GET'])
def get_training_data():
    """Get all facial training data for KNN model from database"""
    try:
        session = get_db_session()
        if not session:
            return jsonify({'success': False, 'error': 'No database session'}), 500
        
        query = text("""
            SELECT fd.user_id, u.name, fd.face_encoding, fd.sample_count
            FROM facial_data fd
            JOIN users u ON fd.user_id = u.user_id
            WHERE fd.is_active = TRUE AND u.is_active = TRUE
        """)
        results = session.execute(query).fetchall()
        
        all_faces = []
        all_labels = []
        student_count = 0
        
        for row in results:
            try:
                user_id, name, face_encoding, sample_count = row
                
                if face_encoding[:6] == b'SHAPE:':
                    header_end = face_encoding.index(b';')
                    shape_str = face_encoding[6:header_end].decode('utf-8')
                    rows, cols = map(int, shape_str.split(','))
                    compressed_data = face_encoding[header_end + 1:]
                else:
                    rows = sample_count if sample_count else 100
                    cols = 7500
                    compressed_data = face_encoding
                
                try:
                    decompressed = zlib.decompress(compressed_data)
                except zlib.error:
                    decompressed = compressed_data
                
                faces_array = np.frombuffer(decompressed, dtype=np.uint8).reshape(rows, cols)
                
                for face in faces_array:
                    all_faces.append(face.tolist())
                    all_labels.append(name)
                student_count += 1
                
            except Exception as row_error:
                print(f"Error processing row for {name}: {row_error}")
                continue
        
        if not all_faces:
            return jsonify({
                'success': True,
                'faces': [],
                'labels': [],
                'student_count': 0,
                'total_samples': 0,
                'message': 'No training data found'
            })
        
        return jsonify({
            'success': True,
            'faces': all_faces,
            'labels': all_labels,
            'student_count': student_count,
            'total_samples': len(all_labels)
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@attendance_ai_bp.route('/students/import', methods=['POST'])
def import_students():
    """Import students with their facial training data"""
    try:
        data = request.json
        students_data = data.get('students', [])
        institution_id = data.get('institution_id', 1)
        
        if not students_data:
            return jsonify({'success': False, 'error': 'No students provided'}), 400
        
        session = get_db_session()
        if not session:
            return jsonify({'success': False, 'error': 'No database session'}), 500
        
        face_cascade = load_face_detector()
        imported_count = 0
        student_names = []
        faces_detected = 0
        
        for student_info in students_data:
            name = student_info.get('name')
            email = student_info.get('email', f"{name.lower().replace(' ', '.')}@student.edu")
            photo_base64 = student_info.get('photo')
            sample_count = student_info.get('sample_count', 100)
            
            if not name:
                continue
            
            import bcrypt
            result = session.execute(
                text("SELECT user_id FROM users WHERE email = :email AND institution_id = :inst"),
                {'email': email, 'inst': institution_id}
            ).fetchone()
            
            if result:
                user_id = result[0]
            else:
                password_hash = bcrypt.hashpw('password'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                session.execute(
                    text("""
                        INSERT INTO users (institution_id, role, name, email, password_hash, is_active)
                        VALUES (:inst, 'student', :name, :email, :pwd, TRUE)
                    """),
                    {'inst': institution_id, 'name': name, 'email': email, 'pwd': password_hash}
                )
                session.commit()
                
                result = session.execute(
                    text("SELECT user_id FROM users WHERE email = :email"),
                    {'email': email}
                ).fetchone()
                user_id = result[0]
            
            if photo_base64 and user_id:
                try:
                    if ',' in photo_base64:
                        photo_base64 = photo_base64.split(',')[1]
                    
                    img_data = base64.b64decode(photo_base64)
                    img_array = np.frombuffer(img_data, dtype=np.uint8)
                    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                    
                    if img is not None:
                        face_img, face_found = detect_and_crop_face(img, face_cascade)
                        if face_found:
                            faces_detected += 1
                        
                        faces_array = generate_augmented_samples(face_img, sample_count)
                        
                        faces_bytes = faces_array.tobytes()
                        compressed_data = zlib.compress(faces_bytes)
                        shape_str = f"SHAPE:{faces_array.shape[0]},{faces_array.shape[1]};".encode('utf-8')
                        full_data = shape_str + compressed_data
                        
                        existing = session.execute(
                            text("SELECT facial_data_id FROM facial_data WHERE user_id = :uid"),
                            {'uid': user_id}
                        ).fetchone()
                        
                        if existing:
                            session.execute(
                                text("UPDATE facial_data SET face_encoding = :data, sample_count = :count WHERE user_id = :uid"),
                                {'data': full_data, 'count': sample_count, 'uid': user_id}
                            )
                        else:
                            session.execute(
                                text("INSERT INTO facial_data (user_id, face_encoding, sample_count) VALUES (:uid, :data, :count)"),
                                {'uid': user_id, 'data': full_data, 'count': sample_count}
                            )
                        
                        session.commit()
                except Exception as photo_error:
                    print(f"Photo error for {name}: {photo_error}")
            
            imported_count += 1
            student_names.append(name)
        
        return jsonify({
            'success': True,
            'message': f'Successfully imported {imported_count} students',
            'students': student_names,
            'faces_detected': faces_detected
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== CLASS STUDENTS ====================

@attendance_ai_bp.route('/class/<int:class_id>/students', methods=['GET'])
def get_class_students(class_id):
    """Get students enrolled in a specific class"""
    try:
        session = get_db_session()
        if not session:
            return jsonify({'success': False, 'error': 'No database session'}), 500
        
        class_info = session.execute(
            text("SELECT course_id, semester_id FROM classes WHERE class_id = :cid"),
            {'cid': class_id}
        ).fetchone()
        
        if not class_info:
            return jsonify({'success': False, 'error': 'Class not found'}), 404
        
        course_id, semester_id = class_info
        
        query = text("""
            SELECT u.user_id, u.name, u.email
            FROM course_users cu
            JOIN users u ON cu.user_id = u.user_id
            WHERE cu.course_id = :course_id
              AND cu.semester_id = :semester_id
              AND u.role = 'student'
              AND u.is_active = TRUE
        """)
        results = session.execute(query, {'course_id': course_id, 'semester_id': semester_id}).fetchall()
        
        students_list = []
        for row in results:
            students_list.append({
                'student_id': row[0],
                'user_id': row[0],
                'name': row[1],
                'email': row[2],
                'facial_data_id': row[0]
            })
        
        if len(students_list) == 0:
            print(f"⚠️ No students enrolled in class #{class_id}, returning all students")
            return get_students()
        
        return jsonify({
            'success': True,
            'students': students_list,
            'count': len(students_list),
            'class_id': class_id
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@attendance_ai_bp.route('/class/<int:class_id>/students/assign', methods=['POST'])
def assign_students_to_class(class_id):
    """Assign students to a class"""
    try:
        data = request.json
        student_ids = data.get('student_ids', [])
        
        if not student_ids:
            return jsonify({'success': False, 'error': 'No student IDs provided'}), 400
        
        session = get_db_session()
        if not session:
            return jsonify({'success': False, 'error': 'No database session'}), 500
        
        class_info = session.execute(
            text("SELECT course_id, semester_id FROM classes WHERE class_id = :cid"),
            {'cid': class_id}
        ).fetchone()
        
        if not class_info:
            return jsonify({'success': False, 'error': 'Class not found'}), 404
        
        course_id, semester_id = class_info
        assigned_count = 0
        
        for student_id in student_ids:
            existing = session.execute(
                text("""
                    SELECT 1 FROM course_users 
                    WHERE course_id = :cid AND user_id = :uid AND semester_id = :sid
                """),
                {'cid': course_id, 'uid': student_id, 'sid': semester_id}
            ).fetchone()
            
            if not existing:
                session.execute(
                    text("""
                        INSERT INTO course_users (course_id, user_id, semester_id)
                        VALUES (:cid, :uid, :sid)
                    """),
                    {'cid': course_id, 'uid': student_id, 'sid': semester_id}
                )
                assigned_count += 1
        
        session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Assigned {assigned_count} students to class',
            'assigned_count': assigned_count
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== ATTENDANCE ====================

@attendance_ai_bp.route('/attendance/mark', methods=['POST'])
def mark_attendance():
    """Mark student attendance"""
    try:
        data = request.json
        student_id = data.get('student_id')
        session_id = data.get('session_id', data.get('class_id'))
        status = data.get('status', 'present')
        recognition_data = data.get('recognition_data', {})
        
        if status not in ['present', 'late', 'absent', 'excused', 'unmarked']:
            status = 'present'
        
        if not student_id or not session_id:
            return jsonify({'success': False, 'error': 'student_id and session_id required'}), 400
        
        session = get_db_session()
        if not session:
            return jsonify({'success': False, 'error': 'No database session'}), 500
        
        # Check if already marked
        existing = session.execute(
            text("SELECT attendance_id, status FROM attendance_records WHERE student_id = :sid AND class_id = :cid"),
            {'sid': student_id, 'cid': session_id}
        ).fetchone()
        
        if existing:
            existing_id, existing_status = existing[0], existing[1]
            
            if existing_status == status:
                return jsonify({
                    'success': True,
                    'message': f'Already marked as {existing_status}',
                    'already_present': True,
                    'attendance_id': existing_id
                })
            
            if existing_status in ['present', 'late'] and status == 'absent':
                return jsonify({
                    'success': True,
                    'message': f'Already marked as {existing_status} (not changing to absent)',
                    'already_present': True,
                    'attendance_id': existing_id
                })
            
            # Update existing record
            session.execute(
                text("""
                    UPDATE attendance_records 
                    SET status = :status, 
                        recorded_at = CURRENT_TIMESTAMP,
                        notes = :notes
                    WHERE attendance_id = :aid
                """),
                {
                    'status': status,
                    'notes': json.dumps(recognition_data) if recognition_data else None,
                    'aid': existing_id
                }
            )
            session.commit()
            
            print(f"✅ Updated attendance: student {student_id} changed from {existing_status} → {status}")
            
            return jsonify({
                'success': True,
                'message': f'Attendance updated from {existing_status} to {status}',
                'already_present': False,
                'updated': True,
                'attendance_id': existing_id,
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })
        
        # Get lecturer_id from class
        class_info = session.execute(
            text("SELECT lecturer_id FROM classes WHERE class_id = :cid"),
            {'cid': session_id}
        ).fetchone()
        lecturer_id = class_info[0] if class_info else None
        
        # Create new attendance record
        session.execute(
            text("""
                INSERT INTO attendance_records (class_id, student_id, status, marked_by, lecturer_id, notes)
                VALUES (:cid, :sid, :status, 'system', :lid, :notes)
            """),
            {
                'cid': session_id,
                'sid': student_id,
                'status': status,
                'lid': lecturer_id,
                'notes': json.dumps(recognition_data) if recognition_data else None
            }
        )
        session.commit()
        
        result = session.execute(
            text("SELECT attendance_id FROM attendance_records WHERE student_id = :sid AND class_id = :cid"),
            {'sid': student_id, 'cid': session_id}
        ).fetchone()
        
        print(f"✅ New attendance: student {student_id} marked as {status}")
        
        return jsonify({
            'success': True,
            'message': f'Attendance marked as {status}',
            'already_present': False,
            'attendance_id': result[0] if result else None,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@attendance_ai_bp.route('/attendance/unmark', methods=['POST'])
def unmark_attendance():
    """Update attendance to absent"""
    try:
        data = request.json
        student_id = data.get('student_id')
        session_id = data.get('session_id', data.get('class_id'))
        
        if not student_id or not session_id:
            return jsonify({'success': False, 'error': 'student_id and session_id required'}), 400
        
        session = get_db_session()
        if not session:
            return jsonify({'success': False, 'error': 'No database session'}), 500
        
        session.execute(
            text("UPDATE attendance_records SET status = 'absent' WHERE student_id = :sid AND class_id = :cid"),
            {'sid': student_id, 'cid': session_id}
        )
        session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Student marked absent'
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@attendance_ai_bp.route('/attendance/session/<int:session_id>', methods=['GET'])
@attendance_ai_bp.route('/attendance/class/<int:session_id>', methods=['GET'])
def get_class_attendance(session_id):
    """Get attendance records for a specific class"""
    try:
        session = get_db_session()
        if not session:
            return jsonify({'success': False, 'error': 'No database session'}), 500
        
        query = text("""
            SELECT ar.attendance_id, ar.student_id, u.name, ar.status, ar.recorded_at, ar.marked_by
            FROM attendance_records ar
            JOIN users u ON ar.student_id = u.user_id
            WHERE ar.class_id = :cid
        """)
        results = session.execute(query, {'cid': session_id}).fetchall()
        
        records = []
        for row in results:
            records.append({
                'attendance_id': row[0],
                'student_id': row[1],
                'name': row[2],
                'status': row[3],
                'recorded_at': row[4].strftime('%H:%M:%S') if row[4] else None,
                'marked_by': row[5]
            })
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'class_id': session_id,
            'records': records,
            'count': len(records)
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== RECOGNITION CONTROL ====================

def find_attendance_client():
    """Find the attendance_client.py file"""
    server_dir = os.path.dirname(os.path.abspath(__file__))
    
    possible_names = ['attendance_client.py', 'attendance_client_cnn.py']
    possible_locations = [
        server_dir,
        os.getcwd(),
        os.path.join(server_dir, '..'),
        os.path.join(server_dir, 'AttendanceAI'),
    ]
    
    for location in possible_locations:
        for name in possible_names:
            path = os.path.join(location, name)
            if os.path.exists(path):
                return os.path.abspath(path)
    
    return None


@attendance_ai_bp.route('/recognition/start', methods=['POST'])
def start_recognition():
    """Start the attendance recognition client with session_id"""
    global recognition_process
    
    try:
        # Check if already running
        if recognition_process is not None and recognition_process.poll() is None:
            return jsonify({
                'success': False,
                'error': 'Recognition is already running',
                'status': 'running',
                'pid': recognition_process.pid
            })
        
        # Get session_id from request body
        data = request.get_json() or {}
        session_id = data.get('session_id') or data.get('class_id')
        
        script_path = find_attendance_client()
        
        if script_path is None:
            return jsonify({
                'success': False,
                'error': 'attendance_client.py not found'
            }), 404
        
        # Build command with session_id if provided
        cmd = [sys.executable, script_path]
        if session_id:
            cmd.extend(['--session', str(session_id)])
        
        print(f"🚀 Starting recognition: {' '.join(cmd)}")
        
        # Start the process
        if sys.platform == 'win32':
            recognition_process = subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=os.path.dirname(script_path)
            )
        else:
            recognition_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.path.dirname(script_path),
                start_new_session=True
            )
        
        return jsonify({
            'success': True,
            'message': 'Recognition started successfully',
            'status': 'running',
            'pid': recognition_process.pid,
            'script_path': script_path,
            'session_id': session_id
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@attendance_ai_bp.route('/recognition/stop', methods=['POST'])
def stop_recognition():
    """Stop the attendance recognition client"""
    global recognition_process
    
    try:
        if recognition_process is None or recognition_process.poll() is not None:
            recognition_process = None
            return jsonify({
                'success': True,
                'message': 'Recognition is not running',
                'status': 'stopped'
            })
        
        pid = recognition_process.pid
        
        if sys.platform == 'win32':
            try:
                recognition_process.terminate()
            except:
                os.system(f'taskkill /F /PID {pid}')
        else:
            try:
                os.kill(pid, signal.SIGTERM)
            except:
                os.kill(pid, signal.SIGKILL)
        
        try:
            recognition_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            if sys.platform == 'win32':
                os.system(f'taskkill /F /PID {pid}')
            else:
                os.kill(pid, signal.SIGKILL)
        
        recognition_process = None
        
        return jsonify({
            'success': True,
            'message': 'Recognition stopped successfully',
            'status': 'stopped'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@attendance_ai_bp.route('/recognition/status', methods=['GET'])
def get_recognition_status():
    """Check the status of the recognition client"""
    global recognition_process
    
    if recognition_process is None:
        return jsonify({
            'success': True,
            'status': 'stopped',
            'running': False
        })
    
    poll_result = recognition_process.poll()
    
    if poll_result is None:
        return jsonify({
            'success': True,
            'status': 'running',
            'running': True,
            'pid': recognition_process.pid
        })
    else:
        recognition_process = None
        return jsonify({
            'success': True,
            'status': 'stopped',
            'running': False,
            'exit_code': poll_result
        })


@attendance_ai_bp.route('/recognition/check-script', methods=['GET'])
def check_script():
    """Debug endpoint to check if attendance_client.py exists"""
    script_path = find_attendance_client()
    server_dir = os.path.dirname(os.path.abspath(__file__))
    cwd = os.getcwd()
    
    return jsonify({
        'success': True,
        'script_found': script_path is not None,
        'script_path': script_path,
        'server_directory': server_dir,
        'current_directory': cwd,
        'python_executable': sys.executable,
        'platform': sys.platform
    })


# ==================== DEBUG ====================

@attendance_ai_bp.route('/debug/facial-data', methods=['GET'])
def debug_facial_data():
    """Check what's in the facial_data table"""
    try:
        session = get_db_session()
        if not session:
            return jsonify({'success': False, 'error': 'No database session'}), 500
        
        query = text("""
            SELECT fd.facial_data_id, fd.user_id, u.name, fd.sample_count,
                   LENGTH(fd.face_encoding) as data_size, fd.is_active, fd.created_at
            FROM facial_data fd
            LEFT JOIN users u ON fd.user_id = u.user_id
        """)
        results = session.execute(query).fetchall()
        
        records = []
        for r in results:
            records.append({
                'facial_data_id': r[0],
                'user_id': r[1],
                'name': r[2],
                'sample_count': r[3],
                'data_size_bytes': r[4],
                'is_active': r[5],
                'created_at': str(r[6]) if r[6] else None
            })
        
        return jsonify({
            'success': True,
            'total_records': len(records),
            'records': records
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500