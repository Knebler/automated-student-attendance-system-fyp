"""
Attendance AI API Blueprint - BROWSER WEBCAM VERSION (FIXED)
============================================================
Fixed to handle corrupted/incompatible facial data gracefully.
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, date
from sqlalchemy import text
import numpy as np
import cv2
import base64
import json
import zlib
import threading

attendance_ai_bp = Blueprint('attendance_ai', __name__)

FACE_CASCADE = None
_model_cache = {
    'knn': None,
    'labels': None,
    'student_map': {},
    'last_loaded': None,
    'lock': threading.Lock(),
    'skipped_students': []
}


def load_face_detector():
    global FACE_CASCADE
    if FACE_CASCADE is None:
        paths = [
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml',
            'data/haarcascade_frontalface_default.xml',
        ]
        for path in paths:
            try:
                cascade = cv2.CascadeClassifier(path)
                if not cascade.empty():
                    FACE_CASCADE = cascade
                    print(f"✅ Face detector loaded: {path}")
                    return FACE_CASCADE
            except:
                continue
        print("⚠️ Face detector not found")
    return FACE_CASCADE


def get_db_session():
    try:
        db = current_app.config.get('db')
        if db:
            return db.session
    except:
        pass
    return None


def detect_faces_in_frame(img, face_cascade):
    """Detect faces in an image frame."""
    if face_cascade is None:
        # No cascade - return center crop as fallback
        h, w = img.shape[:2]
        size = min(h, w) // 2
        cx, cy = w // 2, h // 2
        return [{'face': img[cy-size:cy+size, cx-size:cx+size], 'bbox': (cx-size, cy-size, size*2, size*2)}], True
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))
    
    if len(faces) > 0:
        results = []
        for (x, y, w, h) in faces:
            pad = int(0.1 * w)
            x1, y1 = max(0, x - pad), max(0, y - pad)
            x2, y2 = min(img.shape[1], x + w + pad), min(img.shape[0], y + h + pad)
            results.append({'face': img[y1:y2, x1:x2], 'bbox': (int(x), int(y), int(w), int(h))})
        return results, True
    return [], False


def extract_features(face_img):
    """Extract features from a face image for KNN matching."""
    try:
        h, w = face_img.shape[:2]
        if min(h, w) < 10:
            return None
        
        # Make square
        if h != w:
            size = min(h, w)
            sh, sw = (h - size) // 2, (w - size) // 2
            face_img = face_img[sh:sh+size, sw:sw+size]
        
        # Resize to 50x50
        face_resized = cv2.resize(face_img, (50, 50))
        
        # Convert to grayscale
        if len(face_resized.shape) == 3:
            gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
        else:
            gray = face_resized
        
        # Enhance contrast
        enhanced = cv2.equalizeHist(gray.astype(np.uint8))
        return enhanced.flatten().reshape(1, -1)
    except Exception as e:
        print(f"Feature extraction error: {e}")
        return None


def generate_augmented_samples(face_img, sample_count=100):
    """Generate augmented training samples from a face image."""
    all_faces = []
    base_face = cv2.resize(face_img, (60, 60))
    
    for i in range(sample_count):
        aug = base_face.copy()
        
        # Random scale
        scale = np.random.uniform(0.8, 1.2)
        new_size = int(60 * scale)
        if new_size > 20:
            scaled = cv2.resize(aug, (new_size, new_size))
            if new_size >= 60:
                s = (new_size - 60) // 2
                aug = scaled[s:s+60, s:s+60]
            else:
                p = (60 - new_size) // 2
                aug = cv2.copyMakeBorder(scaled, p, p, p, p, cv2.BORDER_REPLICATE)
                aug = cv2.resize(aug, (60, 60))
        
        # Random brightness
        brightness = np.random.randint(-30, 30)
        aug = np.clip(aug.astype(np.int16) + brightness, 0, 255).astype(np.uint8)
        
        # Random rotation
        if i % 3 == 0:
            angle = np.random.uniform(-15, 15)
            M = cv2.getRotationMatrix2D((30, 30), angle, 1.0)
            aug = cv2.warpAffine(aug, M, (60, 60), borderMode=cv2.BORDER_REPLICATE)
        
        # Random flip
        if np.random.random() > 0.5:
            aug = cv2.flip(aug, 1)
        
        final = cv2.resize(aug, (50, 50))
        all_faces.append(final.flatten())
    
    return np.array(all_faces, dtype=np.uint8)


def load_or_get_model():
    """
    Load KNN model from database.
    FIXED: Properly handles corrupted/incompatible facial data.
    """
    from sklearn.neighbors import KNeighborsClassifier
    
    with _model_cache['lock']:
        # Check cache
        if _model_cache['knn'] is not None and _model_cache['last_loaded']:
            age = (datetime.now() - _model_cache['last_loaded']).total_seconds()
            if age < 300:
                return _model_cache['knn'], _model_cache['student_map']
        
        session = get_db_session()
        if not session:
            print("❌ No database session")
            return None, {}
        
        try:
            query = text("""
                SELECT fd.user_id, u.name, fd.face_encoding, fd.sample_count
                FROM facial_data fd
                JOIN users u ON fd.user_id = u.user_id
                WHERE fd.is_active = TRUE AND u.is_active = TRUE
            """)
            results = session.execute(query).fetchall()
            
            if not results:
                print("❌ No facial data in database")
                return None, {}
            
            all_faces = []
            all_labels = []
            student_map = {}
            skipped = []
            
            print(f"📊 Processing {len(results)} facial data records...")
            
            for row in results:
                user_id, name, face_encoding, sample_count = row
                
                if face_encoding is None:
                    skipped.append(f"{name}: No data")
                    continue
                
                try:
                    raw_data = face_encoding
                    rows = sample_count if sample_count else 100
                    cols = 7500  # Default: 50x50x3
                    
                    # Check for SHAPE header
                    if raw_data[:6] == b'SHAPE:':
                        try:
                            header_end = raw_data.index(b';')
                            shape_str = raw_data[6:header_end].decode('utf-8')
                            rows, cols = map(int, shape_str.split(','))
                            compressed = raw_data[header_end + 1:]
                        except:
                            compressed = raw_data
                    else:
                        compressed = raw_data
                    
                    # Decompress
                    try:
                        data = zlib.decompress(compressed)
                    except zlib.error:
                        data = compressed
                    
                    actual_size = len(data)
                    
                    # Validate data size
                    if cols not in [7500, 2500]:
                        # Try to auto-detect format
                        if actual_size % 7500 == 0:
                            cols = 7500
                            rows = actual_size // 7500
                        elif actual_size % 2500 == 0:
                            cols = 2500
                            rows = actual_size // 2500
                        else:
                            skipped.append(f"{name}: Invalid format ({actual_size} bytes)")
                            print(f"⚠️ Skipping {name}: {actual_size} bytes - incompatible format")
                            print(f"   → Re-import this student using the fixed import page")
                            continue
                    
                    expected_size = rows * cols
                    
                    if actual_size != expected_size:
                        # Try to find correct dimensions
                        if actual_size % 7500 == 0:
                            rows = actual_size // 7500
                            cols = 7500
                        elif actual_size % 2500 == 0:
                            rows = actual_size // 2500
                            cols = 2500
                        else:
                            skipped.append(f"{name}: Size mismatch ({actual_size} bytes)")
                            print(f"⚠️ Skipping {name}: Cannot reshape {actual_size} bytes")
                            continue
                    
                    # Now reshape
                    faces_array = np.frombuffer(data, dtype=np.uint8).reshape(rows, cols)
                    
                    # Process each sample
                    loaded_count = 0
                    for face in faces_array:
                        try:
                            if cols == 7500:
                                face_2d = face.reshape(50, 50, 3)
                                gray = cv2.cvtColor(face_2d, cv2.COLOR_BGR2GRAY)
                            else:
                                gray = face.reshape(50, 50)
                            
                            enhanced = cv2.equalizeHist(gray.astype(np.uint8)).flatten()
                            all_faces.append(enhanced)
                            all_labels.append(name)
                            loaded_count += 1
                        except:
                            continue
                    
                    if loaded_count > 0:
                        student_map[name] = {'user_id': user_id, 'student_id': user_id}
                        print(f"✅ {name}: Loaded {loaded_count} samples")
                    
                except Exception as e:
                    skipped.append(f"{name}: {str(e)}")
                    print(f"❌ Error loading {name}: {e}")
                    continue
            
            _model_cache['skipped_students'] = skipped
            
            if not all_faces:
                print("❌ No valid facial data found!")
                print("   Skipped students:", skipped)
                return None, {}
            
            # Train KNN
            X = np.array(all_faces)
            y = np.array(all_labels)
            n_neighbors = min(5, len(X))
            
            knn = KNeighborsClassifier(n_neighbors=n_neighbors)
            knn.fit(X, y)
            
            # Cache
            _model_cache['knn'] = knn
            _model_cache['student_map'] = student_map
            _model_cache['last_loaded'] = datetime.now()
            
            print(f"✅ Model trained: {len(X)} samples, {len(student_map)} students")
            if skipped:
                print(f"⚠️ Skipped {len(skipped)} records - re-import these students")
            
            return knn, student_map
            
        except Exception as e:
            print(f"❌ Model loading error: {e}")
            import traceback
            traceback.print_exc()
            return None, {}


# ==================== BROWSER WEBCAM RECOGNITION ====================

@attendance_ai_bp.route('/recognize-frame', methods=['POST'])
def recognize_frame():
    """Receive frame from browser, return recognition results."""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'JSON required'}), 400
        
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'success': False, 'error': 'Invalid JSON'}), 400
        
        frame_data = data.get('frame')
        if not frame_data:
            return jsonify({'success': False, 'error': 'No frame'}), 400
        
        # Decode image
        try:
            if ',' in frame_data:
                frame_data = frame_data.split(',')[1]
            img_bytes = base64.b64decode(frame_data)
            frame = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                return jsonify({'success': False, 'error': 'Invalid image'}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': f'Decode error: {e}'}), 400
        
        # Load model
        knn, student_map = load_or_get_model()
        
        if knn is None:
            skipped = _model_cache.get('skipped_students', [])
            return jsonify({
                'success': False, 
                'error': 'No valid facial data. Please re-import students using the fixed import page.',
                'skipped_students': skipped,
                'hint': 'Visit /api/debug/facial-data to see data status'
            }), 400
        
        # Detect faces
        face_cascade = load_face_detector()
        face_results, found = detect_faces_in_frame(frame, face_cascade)
        
        if not found:
            return jsonify({'success': True, 'faces': []})
        
        # Recognize
        recognized = []
        for face_data in face_results:
            features = extract_features(face_data['face'])
            if features is None:
                continue
            
            try:
                prediction = knn.predict(features)[0]
                proba = knn.predict_proba(features)
                confidence = float(np.max(proba))
                
                if confidence < 0.5:
                    recognized.append({
                        'name': 'Unknown',
                        'confidence': confidence,
                        'student_id': None,
                        'bbox': list(face_data['bbox'])
                    })
                    continue
                
                name = str(prediction)
                info = student_map.get(name, {})
                
                now = datetime.now()
                status = 'late' if now.hour > 9 or (now.hour == 9 and now.minute > 30) else 'present'
                
                recognized.append({
                    'name': name,
                    'confidence': confidence,
                    'student_id': info.get('student_id'),
                    'status': status,
                    'bbox': list(face_data['bbox'])
                })
            except:
                continue
        
        return jsonify({'success': True, 'faces': recognized})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@attendance_ai_bp.route('/model/reload', methods=['POST'])
def reload_model():
    """Force reload the model."""
    with _model_cache['lock']:
        _model_cache['knn'] = None
        _model_cache['last_loaded'] = None
    
    knn, student_map = load_or_get_model()
    skipped = _model_cache.get('skipped_students', [])
    
    return jsonify({
        'success': knn is not None,
        'student_count': len(student_map),
        'skipped': skipped
    })


# ==================== HEALTH ====================

@attendance_ai_bp.route('/ping', methods=['GET'])
def ping():
    return jsonify({'success': True, 'message': 'pong', 'mode': 'browser_webcam'})


@attendance_ai_bp.route('/health', methods=['GET'])
def health_check():
    db_ok = False
    try:
        session = get_db_session()
        if session:
            session.execute(text("SELECT 1"))
            db_ok = True
    except:
        pass
    
    return jsonify({
        'status': 'healthy' if db_ok else 'degraded',
        'database': 'connected' if db_ok else 'error',
        'model_loaded': _model_cache.get('knn') is not None,
        'mode': 'browser_webcam'
    })


# ==================== SESSIONS ====================

@attendance_ai_bp.route('/sessions', methods=['GET'])
@attendance_ai_bp.route('/classes', methods=['GET'])
def get_sessions():
    try:
        session = get_db_session()
        if not session:
            return jsonify({'success': False, 'error': 'No database'}), 500
        
        results = session.execute(text("""
            SELECT c.class_id, c.course_id, c.start_time, c.status,
                   co.code, co.name, v.name, u.name
            FROM classes c
            LEFT JOIN courses co ON c.course_id = co.course_id
            LEFT JOIN venues v ON c.venue_id = v.venue_id
            LEFT JOIN users u ON c.lecturer_id = u.user_id
            ORDER BY c.start_time DESC LIMIT 50
        """)).fetchall()
        
        sessions = [{
            'session_id': r[0], 'class_id': r[0], 'course_id': r[1],
            'start_time': str(r[2]) if r[2] else None, 'status': r[3],
            'course_code': r[4] or 'N/A', 'course_name': r[5] or 'N/A',
            'venue_name': r[6] or 'N/A', 'lecturer_name': r[7] or 'N/A'
        } for r in results]
        
        return jsonify({'success': True, 'sessions': sessions})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== STUDENTS ====================

@attendance_ai_bp.route('/students', methods=['GET'])
def get_students():
    try:
        session = get_db_session()
        if not session:
            return jsonify({'success': False, 'error': 'No database'}), 500
        
        results = session.execute(text(
            "SELECT user_id, name, email FROM users WHERE role = 'student' AND is_active = TRUE"
        )).fetchall()
        
        return jsonify({
            'success': True,
            'students': [{'student_id': r[0], 'user_id': r[0], 'name': r[1], 'email': r[2]} for r in results]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@attendance_ai_bp.route('/students/training-data', methods=['GET'])
def get_training_data():
    """Get training data for desktop client (if needed)."""
    try:
        session = get_db_session()
        if not session:
            return jsonify({'success': False, 'error': 'No database'}), 500
        
        results = session.execute(text("""
            SELECT fd.user_id, u.name, fd.face_encoding, fd.sample_count
            FROM facial_data fd JOIN users u ON fd.user_id = u.user_id
            WHERE fd.is_active = TRUE AND u.is_active = TRUE
        """)).fetchall()
        
        all_faces, all_labels = [], []
        skipped = []
        
        for row in results:
            user_id, name, face_encoding, sample_count = row
            if not face_encoding:
                continue
            
            try:
                raw = face_encoding
                if raw[:6] == b'SHAPE:':
                    header_end = raw.index(b';')
                    shape_str = raw[6:header_end].decode()
                    rows, cols = map(int, shape_str.split(','))
                    compressed = raw[header_end + 1:]
                else:
                    rows, cols = sample_count or 100, 7500
                    compressed = raw
                
                try:
                    data = zlib.decompress(compressed)
                except:
                    data = compressed
                
                if len(data) % 7500 == 0:
                    rows, cols = len(data) // 7500, 7500
                elif len(data) % 2500 == 0:
                    rows, cols = len(data) // 2500, 2500
                else:
                    skipped.append(name)
                    continue
                
                faces = np.frombuffer(data, dtype=np.uint8).reshape(rows, cols)
                for face in faces:
                    all_faces.append(face.tolist())
                    all_labels.append(name)
            except:
                skipped.append(name)
        
        return jsonify({
            'success': True,
            'faces': all_faces,
            'labels': all_labels,
            'total_samples': len(all_labels),
            'skipped': skipped if skipped else None
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@attendance_ai_bp.route('/students/import', methods=['POST'])
def import_students():
    """Import students with facial data."""
    try:
        data = request.json
        students_data = data.get('students', [])
        institution_id = data.get('institution_id', 1)
        
        if not students_data:
            return jsonify({'success': False, 'error': 'No students'}), 400
        
        session = get_db_session()
        if not session:
            return jsonify({'success': False, 'error': 'No database'}), 500
        
        face_cascade = load_face_detector()
        imported, faces_detected = 0, 0
        names = []
        
        for info in students_data:
            name = info.get('name')
            user_id = info.get('user_id')
            photo = info.get('photo')
            sample_count = info.get('sample_count', 100)
            
            # Get or create user
            if user_id:
                result = session.execute(
                    text("SELECT user_id, name FROM users WHERE user_id = :uid"),
                    {'uid': user_id}
                ).fetchone()
                if result:
                    user_id, name = result[0], result[1] or name
                else:
                    continue
            else:
                email = info.get('email') or f"{name.lower().replace(' ', '.')}@student.edu"
                result = session.execute(
                    text("SELECT user_id FROM users WHERE email = :email"),
                    {'email': email}
                ).fetchone()
                
                if result:
                    user_id = result[0]
                else:
                    import bcrypt
                    pwd = bcrypt.hashpw('password'.encode(), bcrypt.gensalt()).decode()
                    session.execute(text(
                        "INSERT INTO users (institution_id, role, name, email, password_hash, is_active) VALUES (:i, 'student', :n, :e, :p, TRUE)"
                    ), {'i': institution_id, 'n': name, 'e': email, 'p': pwd})
                    session.commit()
                    user_id = session.execute(text("SELECT user_id FROM users WHERE email = :e"), {'e': email}).fetchone()[0]
            
            # Process photo
            if photo and user_id:
                try:
                    if ',' in photo:
                        photo = photo.split(',')[1]
                    img = cv2.imdecode(np.frombuffer(base64.b64decode(photo), np.uint8), cv2.IMREAD_COLOR)
                    
                    if img is not None:
                        faces, found = detect_faces_in_frame(img, face_cascade)
                        if found and faces:
                            face_img = faces[0]['face']
                            faces_detected += 1
                        else:
                            h, w = img.shape[:2]
                            s = min(h, w)
                            face_img = img[(h-s)//2:(h+s)//2, (w-s)//2:(w+s)//2]
                        
                        samples = generate_augmented_samples(face_img, sample_count)
                        compressed = zlib.compress(samples.tobytes())
                        full_data = f"SHAPE:{samples.shape[0]},{samples.shape[1]};".encode() + compressed
                        
                        existing = session.execute(text("SELECT 1 FROM facial_data WHERE user_id = :u"), {'u': user_id}).fetchone()
                        if existing:
                            session.execute(text("UPDATE facial_data SET face_encoding = :d, sample_count = :c, is_active = TRUE WHERE user_id = :u"),
                                          {'d': full_data, 'c': sample_count, 'u': user_id})
                        else:
                            session.execute(text("INSERT INTO facial_data (user_id, face_encoding, sample_count, is_active) VALUES (:u, :d, :c, TRUE)"),
                                          {'u': user_id, 'd': full_data, 'c': sample_count})
                        session.commit()
                        
                        # Clear model cache to force reload
                        with _model_cache['lock']:
                            _model_cache['knn'] = None
                        
                        print(f"✅ Imported {name}: {sample_count} samples")
                except Exception as e:
                    print(f"❌ Photo error for {name}: {e}")
            
            imported += 1
            names.append(name)
        
        return jsonify({
            'success': True, 
            'message': f'Imported {imported}', 
            'students': names, 
            'faces_detected': faces_detected
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@attendance_ai_bp.route('/class/<int:class_id>/students', methods=['GET'])
def get_class_students(class_id):
    try:
        session = get_db_session()
        if not session:
            return jsonify({'success': False, 'error': 'No database'}), 500
        
        info = session.execute(text("SELECT course_id, semester_id FROM classes WHERE class_id = :c"), {'c': class_id}).fetchone()
        if not info:
            return get_students()
        
        results = session.execute(text("""
            SELECT u.user_id, u.name, u.email FROM course_users cu
            JOIN users u ON cu.user_id = u.user_id
            WHERE cu.course_id = :cid AND cu.semester_id = :sid AND u.role = 'student'
        """), {'cid': info[0], 'sid': info[1]}).fetchall()
        
        if not results:
            return get_students()
        
        return jsonify({
            'success': True,
            'students': [{'student_id': r[0], 'name': r[1], 'email': r[2]} for r in results]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== ATTENDANCE ====================

@attendance_ai_bp.route('/attendance/mark', methods=['POST'])
def mark_attendance():
    try:
        data = request.json
        student_id = data.get('student_id')
        session_id = data.get('session_id') or data.get('class_id')
        status = data.get('status', 'present')
        recognition_data = data.get('recognition_data', {})
        
        if not student_id or not session_id:
            return jsonify({'success': False, 'error': 'Missing student_id or session_id'}), 400
        
        session = get_db_session()
        if not session:
            return jsonify({'success': False, 'error': 'No database'}), 500
        
        existing = session.execute(
            text("SELECT attendance_id, status FROM attendance_records WHERE student_id = :s AND class_id = :c"),
            {'s': student_id, 'c': session_id}
        ).fetchone()
        
        if existing:
            if existing[1] == status or (existing[1] in ['present', 'late'] and status == 'absent'):
                return jsonify({'success': True, 'already_present': True, 'attendance_id': existing[0]})
            
            session.execute(text("UPDATE attendance_records SET status = :st WHERE attendance_id = :a"),
                          {'st': status, 'a': existing[0]})
            session.commit()
            return jsonify({'success': True, 'already_present': False, 'attendance_id': existing[0]})
        
        lecturer = session.execute(text("SELECT lecturer_id FROM classes WHERE class_id = :c"), {'c': session_id}).fetchone()
        
        session.execute(text("""
            INSERT INTO attendance_records (class_id, student_id, status, marked_by, lecturer_id, notes)
            VALUES (:c, :s, :st, 'system', :l, :n)
        """), {
            'c': session_id, 's': student_id, 'st': status, 
            'l': lecturer[0] if lecturer else None,
            'n': json.dumps(recognition_data) if recognition_data else None
        })
        session.commit()
        
        result = session.execute(text("SELECT attendance_id FROM attendance_records WHERE student_id = :s AND class_id = :c"),
                                {'s': student_id, 'c': session_id}).fetchone()
        
        return jsonify({'success': True, 'already_present': False, 'attendance_id': result[0] if result else None})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@attendance_ai_bp.route('/attendance/session/<int:sid>', methods=['GET'])
@attendance_ai_bp.route('/attendance/class/<int:sid>', methods=['GET'])
def get_class_attendance(sid):
    try:
        session = get_db_session()
        if not session:
            return jsonify({'success': False, 'error': 'No database'}), 500
        
        results = session.execute(text("""
            SELECT ar.attendance_id, ar.student_id, u.name, ar.status, ar.recorded_at
            FROM attendance_records ar JOIN users u ON ar.student_id = u.user_id
            WHERE ar.class_id = :c
        """), {'c': sid}).fetchall()
        
        records = [{
            'attendance_id': r[0], 'student_id': r[1], 'name': r[2], 'status': r[3],
            'recorded_at': r[4].strftime('%H:%M:%S') if r[4] else None
        } for r in results]
        
        return jsonify({'success': True, 'records': records, 'count': len(records)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== RECOGNITION CONTROL ====================

@attendance_ai_bp.route('/recognition/start', methods=['POST'])
def start_recognition():
    return jsonify({'success': True, 'mode': 'browser_webcam'})


@attendance_ai_bp.route('/recognition/stop', methods=['POST'])
def stop_recognition():
    return jsonify({'success': True, 'status': 'stopped'})


@attendance_ai_bp.route('/recognition/status', methods=['GET'])
def get_recognition_status():
    return jsonify({'success': True, 'mode': 'browser_webcam'})


# ==================== DEBUG ====================

@attendance_ai_bp.route('/debug/facial-data', methods=['GET'])
def debug_facial_data():
    """Check facial data status - helps diagnose import issues."""
    try:
        session = get_db_session()
        if not session:
            return jsonify({'success': False, 'error': 'No database'}), 500
        
        results = session.execute(text("""
            SELECT fd.facial_data_id, fd.user_id, u.name, fd.sample_count, 
                   LENGTH(fd.face_encoding) as size, fd.is_active
            FROM facial_data fd 
            LEFT JOIN users u ON fd.user_id = u.user_id
        """)).fetchall()
        
        records = []
        for r in results:
            size = r[4] or 0
            
            # Determine status based on size
            if size < 1000:
                status = "❌ INVALID - Too small (likely face-api.js embeddings)"
                fix = "Re-import using fixed import page"
            elif size < 50000:
                status = "⚠️ SUSPICIOUS - May be corrupted"
                fix = "Consider re-importing"
            else:
                status = "✅ VALID"
                fix = None
            
            records.append({
                'id': r[0],
                'user_id': r[1],
                'name': r[2],
                'sample_count': r[3],
                'data_size_bytes': size,
                'status': status,
                'fix': fix,
                'is_active': r[5]
            })
        
        # Summary
        valid = sum(1 for r in records if '✅' in r['status'])
        invalid = sum(1 for r in records if '❌' in r['status'])
        
        return jsonify({
            'success': True,
            'summary': {
                'total': len(records),
                'valid': valid,
                'invalid': invalid,
                'model_loaded': _model_cache.get('knn') is not None
            },
            'records': records,
            'help': 'Invalid records need to be re-imported using the fixed import page that sends raw images to server'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500