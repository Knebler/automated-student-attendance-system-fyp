# face_recognition_api.py - Browser-Based Face Recognition API
from flask import Blueprint, request, jsonify, session, current_app
from datetime import datetime
import cv2
import numpy as np
from sklearn.neighbors import KNeighborsClassifier
import io
from PIL import Image
import zlib

face_recognition_api_bp = Blueprint('face_recognition_api', __name__)

def verify_auth():
    """Verify user is authenticated"""
    return 'user_id' in session and 'role' in session

@face_recognition_api_bp.route('/recognize-face', methods=['POST'])
def recognize_face():
    """
    Receive image from browser, perform facial recognition, mark attendance
    """
    if not verify_auth():
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    user_role = session.get('role')
    if user_role not in ['lecturer', 'admin']:
        return jsonify({'success': False, 'error': 'Permission denied'}), 403
    
    # Get class_id
    class_id = request.form.get('class_id')
    if not class_id:
        return jsonify({'success': False, 'error': 'class_id required'}), 400
    
    # Get image
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'No image provided'}), 400
    
    image_file = request.files['image']
    
    try:
        # Read image
        image_bytes = image_file.read()
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({'success': False, 'error': 'Invalid image'}), 400
        
        # Perform face recognition
        result = perform_face_recognition(frame, class_id)
        
        return jsonify({
            'success': True,
            'recognized': len(result['recognized']) > 0,
            'students': result['recognized'],
            'faces': result['faces'],
            'count': len(result['recognized']),
            'total_faces': len(result['faces'])
        })
        
    except Exception as e:
        current_app.logger.error(f"Face recognition error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Recognition failed: {str(e)}'
        }), 500


def perform_face_recognition(frame, class_id):
    """
    Perform face recognition on a frame
    Returns dict with recognized students and face boxes
    """
    from database.models import User
    from application.controls.attendance_control import AttendanceControl
    
    recognized = []
    all_faces = []  # All detected faces with coordinates
    
    # Load Haar Cascade
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Detect faces
    faces = face_cascade.detectMultiScale(gray, 1.2, 5, minSize=(80, 80))
    
    if len(faces) == 0:
        return {'recognized': recognized, 'faces': all_faces}
    
    # Load training data and model
    training_data = load_training_data_from_db()
    if not training_data:
        return recognized
    
    faces_data, labels, student_mapping = training_data
    
    # Train KNN
    n_neighbors = min(5, len(faces_data))
    knn = KNeighborsClassifier(n_neighbors=n_neighbors)
    knn.fit(faces_data, labels)
    
    # Process each detected face
    for (x, y, w, h) in faces:
        crop_img = frame[y:y+h, x:x+w]
        features = extract_features(crop_img)
        
        face_info = {
            'x': int(x),
            'y': int(y),
            'width': int(w),
            'height': int(h),
            'recognized': False,
            'name': 'Unknown',
            'confidence': 0.0
        }
        
        if features is None:
            all_faces.append(face_info)
            continue
        
        # Predict
        prediction = knn.predict(features)[0]
        proba = knn.predict_proba(features)
        confidence = np.max(proba)
        
        distances, _ = knn.kneighbors(features, n_neighbors=n_neighbors)
        avg_distance = np.mean(distances[0])
        
        # Strict thresholds
        CONFIDENCE_THRESHOLD = 0.85
        MAX_DISTANCE = 3500
        
        student_name = str(prediction)
        face_info['name'] = student_name
        face_info['confidence'] = float(confidence)
        
        if confidence >= CONFIDENCE_THRESHOLD and avg_distance <= MAX_DISTANCE:
            if student_name in student_mapping:
                student_info = student_mapping[student_name]
                student_id = student_info['student_id']
                
                face_info['recognized'] = True
                
                # Try to mark attendance
                result = AttendanceControl.mark_attendance(
                    current_app,
                    class_id=class_id,
                    student_id=student_id,
                    status='present',
                    marked_by='system',
                    lecturer_id=session.get('user_id')
                )
                
                if result.get('success') and not result.get('already_present'):
                    recognized.append({
                        'name': student_name,
                        'student_id': student_id,
                        'status': 'present',
                        'confidence': float(confidence),
                        'distance': float(avg_distance)
                    })
                    face_info['newly_marked'] = True
                elif result.get('already_present'):
                    face_info['already_marked'] = True
        
        all_faces.append(face_info)
    
    return {'recognized': recognized, 'faces': all_faces}


def load_training_data_from_db():
    """Load facial training data from database using same method as training-data API"""
    from sqlalchemy import text
    import zlib
    
    try:
        db_session = current_app.extensions['sqlalchemy'].db.session
        
        query = text("""
            SELECT fd.user_id, u.name, fd.face_encoding, fd.sample_count
            FROM facial_data fd
            JOIN users u ON fd.user_id = u.user_id
            WHERE fd.is_active = TRUE AND u.is_active = TRUE AND u.role = 'student'
        """)
        results = db_session.execute(query).fetchall()
        
        all_faces = []
        all_labels = []
        student_mapping = {}
        
        for row in results:
            try:
                user_id, name, face_encoding, sample_count = row
                
                # Parse header if exists
                if face_encoding[:6] == b'SHAPE:':
                    header_end = face_encoding.index(b';')
                    shape_str = face_encoding[6:header_end].decode('utf-8')
                    rows, cols = map(int, shape_str.split(','))
                    compressed_data = face_encoding[header_end + 1:]
                else:
                    rows = sample_count if sample_count else 100
                    cols = 7500
                    compressed_data = face_encoding
                
                # Decompress
                try:
                    decompressed = zlib.decompress(compressed_data)
                except zlib.error:
                    decompressed = compressed_data
                
                # Reshape to (samples, 7500)
                faces_array = np.frombuffer(decompressed, dtype=np.uint8).reshape(rows, cols)
                
                # Process each sample
                for face_data in faces_array:
                    # Convert from 7500 to enhanced 2500 features
                    try:
                        if len(face_data) == 7500:
                            # Reshape to 50x50x3 RGB
                            face_rgb = face_data.reshape(50, 50, 3)
                            # Convert to grayscale
                            face_gray = cv2.cvtColor(face_rgb.astype(np.uint8), cv2.COLOR_BGR2GRAY)
                        elif len(face_data) == 2500:
                            # Already grayscale 50x50
                            face_gray = face_data.reshape(50, 50).astype(np.uint8)
                        else:
                            current_app.logger.warning(f"Unexpected face data size: {len(face_data)}")
                            continue
                        
                        # Equalize histogram and flatten
                        face_enhanced = cv2.equalizeHist(face_gray).flatten()
                        all_faces.append(face_enhanced)
                        all_labels.append(name)
                        
                    except Exception as face_error:
                        current_app.logger.error(f"Error processing face sample: {face_error}")
                        continue
                
                # Add to student mapping
                student_mapping[name] = {
                    'student_id': user_id,
                    'user_id': user_id,
                    'facial_data_id': user_id
                }
                
            except Exception as row_error:
                current_app.logger.error(f"Error processing row for user {user_id}: {row_error}")
                continue
        
        if not all_faces:
            current_app.logger.warning("No facial training data found")
            return None
        
        current_app.logger.info(f"Loaded {len(all_faces)} face samples from {len(student_mapping)} students")
        return (np.array(all_faces), np.array(all_labels), student_mapping)
        
    except Exception as e:
        current_app.logger.error(f"Error loading training data: {e}")
        import traceback
        traceback.print_exc()
        return None


def extract_features(face_img):
    """Extract features from face image"""
    try:
        h, w = face_img.shape[:2]
        
        if min(h, w) < 30:
            scale = 50 / min(h, w)
            face_img = cv2.resize(face_img, (int(w * scale), int(h * scale)))
            h, w = face_img.shape[:2]
        
        if h != w:
            size = min(h, w)
            start_h, start_w = (h - size) // 2, (w - size) // 2
            face_img = face_img[start_h:start_h+size, start_w:start_w+size]
        
        face_resized = cv2.resize(face_img, (50, 50))
        
        if len(face_resized.shape) == 3:
            gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
        else:
            gray = face_resized
        
        gray = cv2.equalizeHist(gray.astype(np.uint8))
        return gray.flatten().reshape(1, -1)
    except:
        return None
