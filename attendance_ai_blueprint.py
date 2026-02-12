"""
Attendance AI API Blueprint - CLEAN VERSION
============================================
Features:
- Upper face recognition (works with/without masks)
- Multiple face detection and recognition
- Auto-mark absent when class ends (handles 'unmarked' status)
- Early departure detection (anti-cheat)
- Browser webcam support
- Proper late detection based on class time

NO anti-spoofing code included.
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, date, timedelta
from sqlalchemy import text
import numpy as np
import cv2
import base64
import json
import zlib
import threading

attendance_ai_bp = Blueprint('attendance_ai', __name__)

# ==================== CONFIGURATION ====================

RECOGNITION_MODE = 'upper_face'
UPPER_FACE_RATIO = 0.5
FACE_WIDTH = 50
FACE_HEIGHT_FULL = 50
FACE_HEIGHT_UPPER = 25
PIXELS_FULL_FACE = 2500
PIXELS_UPPER_FACE = 1250
LATE_THRESHOLD_MINUTES = 30
AUTO_ABSENT_ENABLED = True
AUTO_ABSENT_DELAY_MINUTES = 5
EARLY_DEPARTURE_ENABLED = True
EARLY_DEPARTURE_THRESHOLD_MINUTES = 1
PRESENCE_CHECK_INTERVAL_MINUTES = 1
MULTI_FACE_ENABLED = True
MAX_FACES_PER_FRAME = 20
MIN_FACE_SIZE = 60
FACE_DETECTION_SCALE = 1.1
FACE_DETECTION_NEIGHBORS = 5

FACE_CASCADE = None
_model_cache = {
    'knn': None, 'labels': None, 'student_map': {}, 'last_loaded': None,
    'lock': threading.Lock(), 'skipped_students': [], 'mode': RECOGNITION_MODE,
    'class_id': None  # Track which class the model is for
}
_presence_tracker = {}
_presence_tracker_lock = threading.Lock()
_presence_check_threads = {}
_auto_absent_jobs = {}


def load_face_detector():
    global FACE_CASCADE
    if FACE_CASCADE is None:
        for path in [cv2.data.haarcascades + 'haarcascade_frontalface_default.xml', 'haarcascade_frontalface_default.xml']:
            try:
                cascade = cv2.CascadeClassifier(path)
                if not cascade.empty():
                    FACE_CASCADE = cascade
                    print(f"✅ Face detector loaded")
                    return FACE_CASCADE
            except:
                continue
    return FACE_CASCADE


def get_db_session():
    try:
        db = current_app.config.get('db')
        if db:
            return db.session
    except:
        pass
    return None


def detect_faces_in_frame(img, face_cascade, max_faces=None):
    if max_faces is None:
        max_faces = MAX_FACES_PER_FRAME
    if face_cascade is None:
        h, w = img.shape[:2]
        size = min(h, w) // 2
        cx, cy = w // 2, h // 2
        return [{'face': img[cy-size:cy+size, cx-size:cx+size], 'bbox': (cx-size, cy-size, size*2, size*2), 'face_id': 0}], True
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, FACE_DETECTION_SCALE, FACE_DETECTION_NEIGHBORS, minSize=(MIN_FACE_SIZE, MIN_FACE_SIZE))
    
    if len(faces) > 0:
        results = []
        faces_sorted = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
        for idx, (x, y, w, h) in enumerate(faces_sorted[:max_faces]):
            pad = int(0.1 * w)
            x1, y1 = max(0, x - pad), max(0, y - pad)
            x2, y2 = min(img.shape[1], x + w + pad), min(img.shape[0], y + h + pad)
            results.append({'face': img[y1:y2, x1:x2], 'bbox': (int(x), int(y), int(w), int(h)), 'face_id': idx})
        return results, True
    return [], False


def extract_features(face_img, mode='upper_face'):
    try:
        h, w = face_img.shape[:2]
        if min(h, w) < 10:
            return None
        if h != w:
            size = min(h, w)
            sh, sw = (h - size) // 2, (w - size) // 2
            face_img = face_img[sh:sh+size, sw:sw+size]
        if len(face_img.shape) == 3:
            gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = face_img
        
        if mode == 'upper_face':
            resized = cv2.resize(gray, (FACE_WIDTH, FACE_HEIGHT_FULL))
            upper = resized[0:FACE_HEIGHT_UPPER, :]
            enhanced = cv2.equalizeHist(upper.astype(np.uint8))
            return enhanced.flatten().reshape(1, -1)
        else:
            resized = cv2.resize(gray, (FACE_WIDTH, FACE_HEIGHT_FULL))
            enhanced = cv2.equalizeHist(resized.astype(np.uint8))
            return enhanced.flatten().reshape(1, -1)
    except:
        return None


def generate_augmented_samples(face_img, sample_count=100, mode='upper_face'):
    all_samples = []
    base_face = cv2.resize(face_img, (60, 60))
    if len(base_face.shape) == 2:
        base_face = cv2.cvtColor(base_face, cv2.COLOR_GRAY2BGR)
    
    for i in range(sample_count):
        aug = base_face.copy()
        scale = np.random.uniform(0.85, 1.15)
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
        brightness = np.random.randint(-30, 30)
        aug = np.clip(aug.astype(np.int16) + brightness, 0, 255).astype(np.uint8)
        if i % 4 == 0:
            aug = np.clip(np.random.uniform(0.8, 1.2) * aug, 0, 255).astype(np.uint8)
        if i % 3 == 0:
            M = cv2.getRotationMatrix2D((30, 30), np.random.uniform(-15, 15), 1.0)
            aug = cv2.warpAffine(aug, M, (60, 60), borderMode=cv2.BORDER_REPLICATE)
        if np.random.random() > 0.5:
            aug = cv2.flip(aug, 1)
        gray = cv2.cvtColor(aug, cv2.COLOR_BGR2GRAY)
        if mode == 'upper_face':
            resized = cv2.resize(gray, (FACE_WIDTH, FACE_HEIGHT_FULL))
            upper = resized[0:FACE_HEIGHT_UPPER, :]
            all_samples.append(cv2.equalizeHist(upper).flatten())
        else:
            resized = cv2.resize(gray, (FACE_WIDTH, FACE_HEIGHT_FULL))
            all_samples.append(cv2.equalizeHist(resized).flatten())
    return np.array(all_samples, dtype=np.uint8)


def load_or_get_model(class_id=None):
    from sklearn.neighbors import KNeighborsClassifier
    with _model_cache['lock']:
        # Check if we can reuse cached model for the same class
        if (_model_cache['knn'] is not None and 
            _model_cache['last_loaded'] and 
            _model_cache['class_id'] == class_id):
            if (datetime.now() - _model_cache['last_loaded']).total_seconds() < 300:
                return _model_cache['knn'], _model_cache['student_map']
        
        session = get_db_session()
        if not session:
            return None, {}
        
        try:
            # If class_id is provided, only load students enrolled in that class
            if class_id:
                # Get course_id and semester_id for the class
                class_info = session.execute(text("""
                    SELECT course_id, semester_id 
                    FROM classes 
                    WHERE class_id = :cid
                """), {'cid': class_id}).fetchone()
                
                if class_info and class_info[0] and class_info[1]:
                    course_id, semester_id = class_info
                    # Load only enrolled students' facial data
                    results = session.execute(text("""
                        SELECT fd.user_id, u.name, fd.face_encoding, fd.sample_count
                        FROM facial_data fd 
                        JOIN users u ON fd.user_id = u.user_id
                        JOIN course_users cu ON u.user_id = cu.user_id
                        WHERE fd.is_active = TRUE 
                        AND u.is_active = TRUE 
                        AND u.role = 'student'
                        AND cu.course_id = :cid 
                        AND cu.semester_id = :sid
                    """), {'cid': course_id, 'sid': semester_id}).fetchall()
                else:
                    # Fallback to all students if class info not found
                    results = session.execute(text("""
                        SELECT fd.user_id, u.name, fd.face_encoding, fd.sample_count
                        FROM facial_data fd JOIN users u ON fd.user_id = u.user_id
                        WHERE fd.is_active = TRUE AND u.is_active = TRUE AND u.role = 'student'
                    """)).fetchall()
            else:
                # No class specified - load all students (backward compatibility)
                results = session.execute(text("""
                    SELECT fd.user_id, u.name, fd.face_encoding, fd.sample_count
                    FROM facial_data fd JOIN users u ON fd.user_id = u.user_id
                    WHERE fd.is_active = TRUE AND u.is_active = TRUE AND u.role = 'student'
                """)).fetchall()
            
            if not results:
                return None, {}
            
            all_faces, all_labels, student_map = [], [], {}
            mode = RECOGNITION_MODE
            expected_pixels = PIXELS_UPPER_FACE if mode == 'upper_face' else PIXELS_FULL_FACE
            
            for row in results:
                user_id, name, face_encoding, sample_count = row
                if face_encoding is None:
                    continue
                try:
                    raw_data = face_encoding
                    rows = sample_count if sample_count else 100
                    cols = expected_pixels
                    if raw_data[:6] == b'SHAPE:':
                        try:
                            header_end = raw_data.index(b';')
                            rows, cols = map(int, raw_data[6:header_end].decode('utf-8').split(','))
                            compressed = raw_data[header_end + 1:]
                        except:
                            compressed = raw_data
                    else:
                        compressed = raw_data
                    try:
                        data = zlib.decompress(compressed)
                    except:
                        data = compressed
                    
                    actual_size = len(data)
                    valid_cols = [PIXELS_UPPER_FACE, PIXELS_FULL_FACE, 7500, 2500]
                    if cols not in valid_cols:
                        for try_cols in valid_cols:
                            if actual_size % try_cols == 0:
                                cols = try_cols
                                rows = actual_size // try_cols
                                break
                        else:
                            continue
                    if actual_size != rows * cols:
                        if actual_size % cols == 0:
                            rows = actual_size // cols
                        else:
                            continue
                    
                    faces_array = np.frombuffer(data, dtype=np.uint8).reshape(rows, cols)
                    loaded_count = 0
                    for face in faces_array:
                        try:
                            if cols == 7500:
                                face_2d = cv2.cvtColor(face.reshape(50, 50, 3), cv2.COLOR_BGR2GRAY)
                                if mode == 'upper_face':
                                    enhanced = cv2.equalizeHist(face_2d[0:FACE_HEIGHT_UPPER, :]).flatten()
                                else:
                                    enhanced = cv2.equalizeHist(face_2d).flatten()
                            elif cols == 2500:
                                gray = face.reshape(50, 50)
                                if mode == 'upper_face':
                                    enhanced = cv2.equalizeHist(gray[0:FACE_HEIGHT_UPPER, :].astype(np.uint8)).flatten()
                                else:
                                    enhanced = cv2.equalizeHist(gray.astype(np.uint8)).flatten()
                            elif cols == PIXELS_UPPER_FACE:
                                enhanced = cv2.equalizeHist(face.reshape(FACE_HEIGHT_UPPER, FACE_WIDTH).astype(np.uint8)).flatten()
                            else:
                                continue
                            all_faces.append(enhanced)
                            all_labels.append(name)
                            loaded_count += 1
                        except:
                            continue
                    if loaded_count > 0:
                        student_map[name] = {'user_id': user_id, 'student_id': user_id}
                except:
                    continue
            
            if not all_faces:
                return None, {}
            
            X = np.array(all_faces)
            y = np.array(all_labels)
            knn = KNeighborsClassifier(n_neighbors=min(5, len(X)), weights='distance')
            knn.fit(X, y)
            
            _model_cache['knn'] = knn
            _model_cache['student_map'] = student_map
            _model_cache['last_loaded'] = datetime.now()
            _model_cache['class_id'] = class_id
            class_info = f" for class {class_id}" if class_id else " (all students)"
            print(f"✅ Model trained: {len(X)} samples, {len(student_map)} students{class_info}")
            return knn, student_map
        except Exception as e:
            print(f"❌ Model error: {e}")
            return None, {}


def determine_attendance_status(class_start_time):
    now = datetime.now()
    if class_start_time is None:
        return 'present'
    try:
        if isinstance(class_start_time, datetime):
            start_dt = class_start_time
        elif hasattr(class_start_time, 'hour'):
            start_dt = datetime.combine(now.date(), class_start_time)
        else:
            for fmt in ['%H:%M:%S', '%H:%M', '%Y-%m-%d %H:%M:%S']:
                try:
                    parsed = datetime.strptime(str(class_start_time), fmt)
                    start_dt = parsed.replace(year=now.year, month=now.month, day=now.day) if fmt in ['%H:%M:%S', '%H:%M'] else parsed
                    break
                except:
                    continue
            else:
                return 'present'
        return 'present' if now <= start_dt + timedelta(minutes=LATE_THRESHOLD_MINUTES) else 'late'
    except:
        return 'present'


# ==================== AUTO-ABSENT (FIXED) ====================

def mark_absent_for_class(class_id, force=False):
    """
    Mark absent for students without records.
    Also UPDATE 'unmarked' status to 'absent'.
    """
    try:
        print(f"\n{'='*50}")
        print(f"📋 AUTO-ABSENT: Processing class {class_id}")
        print(f"{'='*50}")
        
        session = get_db_session()
        if not session:
            print("❌ No database session")
            return 0
        
        class_info = session.execute(text("SELECT course_id, semester_id, lecturer_id, status FROM classes WHERE class_id = :cid"), {'cid': class_id}).fetchone()
        if not class_info:
            print(f"❌ Class {class_id} not found")
            return 0
        
        course_id, semester_id, lecturer_id, status = class_info
        print(f"   Class status: {status}")
        
        if not force and status not in ['completed', 'ended', 'finished', 'active', 'in_progress', None]:
            print(f"⏳ Skipping - use force=True")
            return 0
        
        # Get enrolled students
        enrolled = []
        if course_id and semester_id:
            enrolled = session.execute(text("""
                SELECT cu.user_id, u.name FROM course_users cu JOIN users u ON cu.user_id = u.user_id
                WHERE cu.course_id = :cid AND cu.semester_id = :sid AND u.role = 'student' AND u.is_active = TRUE
            """), {'cid': course_id, 'sid': semester_id}).fetchall()
        if not enrolled:
            enrolled = session.execute(text("SELECT user_id, name FROM users WHERE role = 'student' AND is_active = TRUE")).fetchall()
        
        if not enrolled:
            print("⚠️ No students found")
            return 0
        
        print(f"   Enrolled students: {len(enrolled)}")
        
        # Get existing records with their status
        existing = {row[0]: row[1] for row in session.execute(text("SELECT student_id, status FROM attendance_records WHERE class_id = :cid"), {'cid': class_id}).fetchall()}
        print(f"   Existing records: {len(existing)}")
        
        inserted = 0
        updated = 0
        
        for student_id, name in enrolled:
            current_status = existing.get(student_id)
            
            if current_status is None:
                # No record - INSERT absent
                session.execute(text("""
                    INSERT INTO attendance_records (class_id, student_id, status, marked_by, lecturer_id, notes, recorded_at)
                    VALUES (:cid, :sid, 'absent', 'system_auto', :lid, 'Auto-marked absent', NOW())
                """), {'cid': class_id, 'sid': student_id, 'lid': lecturer_id})
                inserted += 1
                print(f"   📝 INSERT absent: {name}")
            
            elif current_status in ('unmarked', 'unknown', ''):
                # Has 'unmarked' - UPDATE to absent
                session.execute(text("""
                    UPDATE attendance_records SET status = 'absent', marked_by = 'system_auto',
                    notes = CONCAT(COALESCE(notes, ''), ' | Updated from unmarked')
                    WHERE class_id = :cid AND student_id = :sid
                """), {'cid': class_id, 'sid': student_id})
                updated += 1
                print(f"   🔄 UPDATE absent: {name} (was '{current_status}')")
        
        total = inserted + updated
        if total > 0:
            session.commit()
            print(f"\n✅ Done: {inserted} inserted, {updated} updated")
        else:
            print(f"\nℹ️ No changes needed")
        
        print(f"{'='*50}\n")
        return total
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 0


def update_student_presence(class_id, student_id, name=None):
    """Update last seen time for a student."""
    # Ensure types are consistent
    class_id = int(class_id)
    student_id = int(student_id)
    
    with _presence_tracker_lock:
        if class_id not in _presence_tracker:
            _presence_tracker[class_id] = {}
        _presence_tracker[class_id][student_id] = {'last_seen': datetime.now(), 'name': name}


def check_early_departures(class_id):
    """
    Check for students who left early (not seen on camera for X minutes).
    Changes status from 'present'/'late' to 'absent'.
    Only checks students who have been tracked by the camera.
    """
    class_id = int(class_id)
    
    if not EARLY_DEPARTURE_ENABLED:
        return 0
    
    departed_count = 0
    try:
        session = get_db_session()
        if not session:
            return 0
        
        now = datetime.now()
        threshold = timedelta(minutes=EARLY_DEPARTURE_THRESHOLD_MINUTES)
        
        print(f"\n👁️ Checking early departures for class {class_id}")
        print(f"   Threshold: {EARLY_DEPARTURE_THRESHOLD_MINUTES} minutes")
        
        # Get presence tracker data for this class
        with _presence_tracker_lock:
            class_tracker = _presence_tracker.get(class_id, {})
            tracked_students = dict(class_tracker)  # Copy to avoid lock issues
        
        print(f"   Tracked students: {len(tracked_students)}")
        
        if not tracked_students:
            print(f"   ⚠️ No students being tracked by camera")
            return 0
        
        # Check each tracked student
        for student_id, tracker_data in tracked_students.items():
            last_seen = tracker_data.get('last_seen')
            name = tracker_data.get('name', f'Student {student_id}')
            
            if not last_seen:
                continue
            
            time_since_seen = now - last_seen
            minutes_ago = int(time_since_seen.total_seconds() / 60)
            seconds_ago = int(time_since_seen.total_seconds()) % 60
            
            print(f"   👤 {name}: Last seen {minutes_ago}m {seconds_ago}s ago")
            
            if time_since_seen > threshold:
                # Student left - update to absent
                result = session.execute(text("""
                    UPDATE attendance_records 
                    SET status = 'absent',
                        marked_by = 'system',
                        notes = CONCAT(COALESCE(notes, ''), ' | Left early at ', :last_seen)
                    WHERE class_id = :cid AND student_id = :sid AND status IN ('present', 'late')
                """), {
                    'cid': class_id, 
                    'sid': student_id, 
                    'last_seen': last_seen.strftime('%H:%M:%S')
                })
                
                if result.rowcount > 0:
                    departed_count += 1
                    print(f"   🚪 {name}: CHANGED TO ABSENT (last seen: {last_seen.strftime('%H:%M:%S')})")
        
        if departed_count > 0:
            session.commit()
            print(f"\n⚠️ Early departure: {departed_count} student(s) changed to absent")
        else:
            print(f"   ✅ All tracked students still present")
        
        return departed_count
        
    except Exception as e:
        print(f"❌ Early departure check error: {e}")
        import traceback
        traceback.print_exc()
        return 0


def start_presence_monitoring(class_id):
    """Start monitoring student presence for early departure detection."""
    # Ensure class_id is int for consistency
    class_id = int(class_id)
    
    if not EARLY_DEPARTURE_ENABLED:
        print(f"⚠️ Early departure detection is DISABLED")
        return
    
    if class_id in _presence_check_threads:
        print(f"👁️ Monitoring already active for class {class_id}")
        return
    
    # Initialize the presence tracker for this class
    with _presence_tracker_lock:
        if class_id not in _presence_tracker:
            _presence_tracker[class_id] = {}
    
    def monitor():
        import time
        print(f"👁️ Started presence monitoring thread for class {class_id}")
        print(f"   Check interval: {PRESENCE_CHECK_INTERVAL_MINUTES} minutes")
        print(f"   Departure threshold: {EARLY_DEPARTURE_THRESHOLD_MINUTES} minutes")
        
        while class_id in _presence_check_threads:
            time.sleep(PRESENCE_CHECK_INTERVAL_MINUTES * 60)
            if class_id in _presence_check_threads:  # Check again after sleep
                check_early_departures(class_id)
        
        print(f"👁️ Stopped presence monitoring thread for class {class_id}")
    
    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    _presence_check_threads[class_id] = thread
    print(f"✅ Monitoring STARTED for class {class_id}")
    print(f"   Active threads: {list(_presence_check_threads.keys())}")


def stop_presence_monitoring(class_id):
    """Stop monitoring and do final early departure check."""
    # Ensure class_id is int for consistency
    class_id = int(class_id)
    
    print(f"🛑 Stopping presence monitoring for class {class_id}")
    
    if class_id in _presence_check_threads:
        del _presence_check_threads[class_id]
    
    # Final check for early departures
    check_early_departures(class_id)
    
    # Clear tracker
    with _presence_tracker_lock:
        if class_id in _presence_tracker:
            del _presence_tracker[class_id]
    
    print(f"✅ Monitoring STOPPED for class {class_id}")


# ==================== API ROUTES ====================

@attendance_ai_bp.route('/recognize-frame', methods=['POST'])
def recognize_frame():
    try:
        data = request.get_json(silent=True)
        if not data or 'frame' not in data:
            return jsonify({'success': False, 'error': 'No frame'}), 400
        
        frame_data = data['frame']
        session_id = data.get('session_id')
        
        if ',' in frame_data:
            frame_data = frame_data.split(',')[1]
        frame = cv2.imdecode(np.frombuffer(base64.b64decode(frame_data), np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            return jsonify({'success': False, 'error': 'Invalid image'}), 400
        
        # Load model with class filter to only recognize enrolled students
        knn, student_map = load_or_get_model(class_id=session_id)
        if knn is None:
            return jsonify({'success': False, 'error': 'No model'}), 400
        
        class_start_time = None
        if session_id:
            try:
                result = get_db_session().execute(text("SELECT start_time FROM classes WHERE class_id = :cid"), {'cid': session_id}).fetchone()
                if result:
                    class_start_time = result[0]
            except:
                pass
        
        status = determine_attendance_status(class_start_time)
        face_cascade = load_face_detector()
        face_results, found = detect_faces_in_frame(frame, face_cascade)
        
        if not found:
            return jsonify({'success': True, 'faces': [], 'face_count': 0})
        
        recognized = []
        for face_data in face_results:
            features = extract_features(face_data['face'], mode=RECOGNITION_MODE)
            if features is None:
                continue
            try:
                prediction = knn.predict(features)[0]
                confidence = float(np.max(knn.predict_proba(features)))
                if confidence < 0.5:
                    recognized.append({'name': 'Unknown', 'confidence': confidence, 'bbox': list(face_data['bbox']), 'face_id': face_data.get('face_id', 0)})
                    continue
                name = str(prediction)
                info = student_map.get(name, {})
                student_id = info.get('student_id')
                if session_id and student_id:
                    update_student_presence(session_id, student_id, name)
                recognized.append({'name': name, 'confidence': confidence, 'student_id': student_id, 'status': status, 'bbox': list(face_data['bbox']), 'face_id': face_data.get('face_id', 0)})
            except:
                continue
        
        return jsonify({'success': True, 'faces': recognized, 'face_count': len(face_results), 'recognized_count': len([f for f in recognized if f['name'] != 'Unknown'])})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@attendance_ai_bp.route('/ping', methods=['GET'])
def ping():
    return jsonify({'success': True, 'mode': RECOGNITION_MODE, 'mask_friendly': True})


@attendance_ai_bp.route('/health', methods=['GET'])
def health():
    db_ok = False
    try:
        session = get_db_session()
        if session:
            session.execute(text("SELECT 1"))
            db_ok = True
    except:
        pass
    return jsonify({'status': 'healthy' if db_ok else 'degraded', 'database': 'connected' if db_ok else 'error', 'model_loaded': _model_cache.get('knn') is not None})


@attendance_ai_bp.route('/model/reload', methods=['POST'])
def reload_model():
    data = request.get_json(silent=True) or {}
    class_id = data.get('class_id')
    with _model_cache['lock']:
        _model_cache['knn'] = None
        _model_cache['last_loaded'] = None
        _model_cache['class_id'] = None
    knn, student_map = load_or_get_model(class_id=class_id)
    return jsonify({'success': knn is not None, 'student_count': len(student_map), 'class_id': class_id})


@attendance_ai_bp.route('/sessions', methods=['GET'])
@attendance_ai_bp.route('/classes', methods=['GET'])
def get_sessions():
    try:
        session = get_db_session()
        if not session:
            return jsonify({'success': False}), 500
        results = session.execute(text("""
            SELECT c.class_id, c.course_id, c.start_time, c.end_time, c.status, co.code, co.name
            FROM classes c LEFT JOIN courses co ON c.course_id = co.course_id ORDER BY c.start_time DESC LIMIT 50
        """)).fetchall()
        return jsonify({'success': True, 'sessions': [{'session_id': r[0], 'class_id': r[0], 'start_time': str(r[2]) if r[2] else None, 'end_time': str(r[3]) if r[3] else None, 'status': r[4], 'course_code': r[5], 'course_name': r[6]} for r in results]})
    except:
        return jsonify({'success': False}), 500


@attendance_ai_bp.route('/students', methods=['GET'])
def get_students():
    try:
        session = get_db_session()
        if not session:
            return jsonify({'success': False}), 500
        results = session.execute(text("SELECT user_id, name, email FROM users WHERE role = 'student' AND is_active = TRUE")).fetchall()
        return jsonify({'success': True, 'students': [{'student_id': r[0], 'name': r[1], 'email': r[2]} for r in results]})
    except:
        return jsonify({'success': False}), 500


@attendance_ai_bp.route('/class/<int:class_id>/students', methods=['GET'])
def get_class_students(class_id):
    try:
        session = get_db_session()
        if not session:
            return get_students()
        info = session.execute(text("SELECT course_id, semester_id FROM classes WHERE class_id = :c"), {'c': class_id}).fetchone()
        if not info:
            return get_students()
        results = session.execute(text("""
            SELECT u.user_id, u.name, u.email FROM course_users cu JOIN users u ON cu.user_id = u.user_id
            WHERE cu.course_id = :cid AND cu.semester_id = :sid AND u.role = 'student'
        """), {'cid': info[0], 'sid': info[1]}).fetchall()
        if not results:
            return get_students()
        return jsonify({'success': True, 'students': [{'student_id': r[0], 'name': r[1], 'email': r[2]} for r in results]})
    except:
        return get_students()


@attendance_ai_bp.route('/attendance/mark', methods=['POST'])
def mark_attendance():
    try:
        data = request.json
        student_id = data.get('student_id')
        session_id = data.get('session_id') or data.get('class_id')
        status = data.get('status')
        if not student_id or not session_id:
            return jsonify({'success': False, 'error': 'Missing data'}), 400
        
        session = get_db_session()
        if not session:
            return jsonify({'success': False}), 500
        
        if not status:
            result = session.execute(text("SELECT start_time FROM classes WHERE class_id = :cid"), {'cid': session_id}).fetchone()
            status = determine_attendance_status(result[0] if result else None)
        if status not in ['present', 'late', 'absent', 'excused']:
            status = 'present'
        
        existing = session.execute(text("SELECT attendance_id, status FROM attendance_records WHERE student_id = :s AND class_id = :c"), {'s': student_id, 'c': session_id}).fetchone()
        if existing:
            if existing[1] == status:
                return jsonify({'success': True, 'already_present': True, 'status': existing[1]})
            session.execute(text("UPDATE attendance_records SET status = :st WHERE attendance_id = :a"), {'st': status, 'a': existing[0]})
            session.commit()
            return jsonify({'success': True, 'already_present': False, 'status': status})
        
        lecturer = session.execute(text("SELECT lecturer_id FROM classes WHERE class_id = :c"), {'c': session_id}).fetchone()
        session.execute(text("INSERT INTO attendance_records (class_id, student_id, status, marked_by, lecturer_id) VALUES (:c, :s, :st, 'system', :l)"),
                       {'c': session_id, 's': student_id, 'st': status, 'l': lecturer[0] if lecturer else None})
        session.commit()
        return jsonify({'success': True, 'already_present': False, 'status': status})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@attendance_ai_bp.route('/attendance/class/<int:sid>', methods=['GET'])
def get_class_attendance(sid):
    """Get attendance records for a class. Also triggers early departure check."""
    try:
        session = get_db_session()
        if not session:
            return jsonify({'success': False}), 500
        
        # Trigger early departure check if monitoring is active
        if sid in _presence_check_threads or sid in _presence_tracker:
            departed = check_early_departures(sid)
            if departed > 0:
                print(f"📋 Early departure check found {departed} students who left")
        
        records = session.execute(text("""
            SELECT ar.attendance_id, ar.student_id, u.name, ar.status, ar.recorded_at
            FROM attendance_records ar JOIN users u ON ar.student_id = u.user_id WHERE ar.class_id = :c
        """), {'c': sid}).fetchall()
        
        # Get presence info
        with _presence_tracker_lock:
            presence_data = _presence_tracker.get(sid, {})
        
        now = datetime.now()
        threshold = timedelta(minutes=EARLY_DEPARTURE_THRESHOLD_MINUTES)
        
        result_records = []
        for r in records:
            student_id = r[1]
            last_seen = presence_data.get(student_id, {}).get('last_seen')
            
            record = {
                'attendance_id': r[0],
                'student_id': student_id,
                'name': r[2],
                'status': r[3],
                'recorded_at': str(r[4]) if r[4] else None
            }
            
            # Add presence info
            if last_seen:
                minutes_ago = int((now - last_seen).total_seconds() / 60)
                record['last_seen'] = last_seen.strftime('%H:%M:%S')
                record['minutes_since_seen'] = minutes_ago
                record['is_still_present'] = minutes_ago <= EARLY_DEPARTURE_THRESHOLD_MINUTES
            
            result_records.append(record)
        
        return jsonify({
            'success': True,
            'records': result_records,
            'count': len(result_records),
            'monitoring_active': sid in _presence_check_threads,
            'early_departure_threshold': EARLY_DEPARTURE_THRESHOLD_MINUTES
        })
    except Exception as e:
        print(f"❌ Error getting attendance: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@attendance_ai_bp.route('/class/<int:class_id>/end', methods=['POST'])
def end_class(class_id):
    try:
        session = get_db_session()
        if not session:
            return jsonify({'success': False}), 500
        session.execute(text("UPDATE classes SET status = 'completed' WHERE class_id = :cid"), {'cid': class_id})
        session.commit()
        stop_presence_monitoring(class_id)
        absent_count = mark_absent_for_class(class_id, force=True)
        return jsonify({'success': True, 'absent_marked': absent_count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@attendance_ai_bp.route('/class/<int:class_id>/mark-absent', methods=['POST'])
def trigger_mark_absent(class_id):
    try:
        absent_count = mark_absent_for_class(class_id, force=True)
        return jsonify({'success': True, 'absent_marked': absent_count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@attendance_ai_bp.route('/auto-absent/test/<int:class_id>', methods=['POST'])
def test_auto_absent(class_id):
    try:
        session = get_db_session()
        if not session:
            return jsonify({'success': False}), 500
        
        enrolled = session.execute(text("SELECT user_id, name FROM users WHERE role = 'student' AND is_active = TRUE")).fetchall()
        existing = {row[0]: row[1] for row in session.execute(text("SELECT student_id, status FROM attendance_records WHERE class_id = :cid"), {'cid': class_id}).fetchall()}
        
        would_insert = [{'id': sid, 'name': name} for sid, name in enrolled if sid not in existing]
        would_update = [{'id': sid, 'name': name, 'was': existing[sid]} for sid, name in enrolled if existing.get(sid) in ('unmarked', 'unknown', '')]
        already_ok = [{'id': sid, 'name': name, 'status': existing[sid]} for sid, name in enrolled if existing.get(sid) in ('present', 'late', 'absent')]
        
        return jsonify({
            'success': True,
            'class_id': class_id,
            'enrolled': len(enrolled),
            'would_insert_absent': would_insert,
            'would_update_to_absent': would_update,
            'already_has_status': already_ok
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@attendance_ai_bp.route('/recognition/start', methods=['POST'])
def start_recognition():
    data = request.json or {}
    class_id = data.get('class_id') or data.get('session_id')
    if class_id:
        # Convert to int for consistency
        class_id = int(class_id)
        start_presence_monitoring(class_id)
    return jsonify({
        'success': True, 
        'mode': RECOGNITION_MODE, 
        'mask_friendly': True, 
        'early_departure_enabled': EARLY_DEPARTURE_ENABLED,
        'monitoring_active': class_id in _presence_check_threads if class_id else False
    })


@attendance_ai_bp.route('/recognition/stop', methods=['POST'])
def stop_recognition():
    data = request.json or {}
    class_id = data.get('class_id') or data.get('session_id')
    if class_id:
        # Convert to int for consistency
        class_id = int(class_id)
        stop_presence_monitoring(class_id)
        if data.get('mark_absent', True):
            mark_absent_for_class(class_id, force=True)
    return jsonify({'success': True})


@attendance_ai_bp.route('/presence/config', methods=['GET'])
def get_config():
    return jsonify({
        'success': True,
        'recognition_mode': RECOGNITION_MODE,
        'mask_friendly': True,
        'late_threshold_minutes': LATE_THRESHOLD_MINUTES,
        'early_departure_enabled': EARLY_DEPARTURE_ENABLED,
        'auto_absent_enabled': AUTO_ABSENT_ENABLED
    })


@attendance_ai_bp.route('/presence/status/<int:class_id>', methods=['GET'])
def get_presence_status(class_id):
    now = datetime.now()
    threshold = timedelta(minutes=EARLY_DEPARTURE_THRESHOLD_MINUTES)
    with _presence_tracker_lock:
        class_tracker = _presence_tracker.get(class_id, {})
    students = []
    for student_id, data in class_tracker.items():
        last_seen = data['last_seen']
        time_since = now - last_seen
        students.append({'student_id': student_id, 'name': data.get('name'), 'last_seen': last_seen.strftime('%H:%M:%S'), 'minutes_ago': int(time_since.total_seconds() / 60), 'is_present': time_since <= threshold})
    return jsonify({'success': True, 'class_id': class_id, 'students': students, 'monitoring_active': class_id in _presence_check_threads})


@attendance_ai_bp.route('/presence/check-early/<int:class_id>', methods=['POST'])
def manual_check_early_departures(class_id):
    """Manually trigger early departure check and return results."""
    try:
        departed_count = check_early_departures(class_id)
        return jsonify({
            'success': True,
            'departed_count': departed_count,
            'message': f'Found {departed_count} students who left early'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500