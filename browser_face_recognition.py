"""
Browser-Based Face Recognition Module
======================================
This module handles facial recognition from browser-captured frames
using WebRTC instead of server-side camera access.

This allows the system to work on cloud platforms like Render.
"""

import cv2
import numpy as np
import base64
from sklearn.neighbors import KNeighborsClassifier
from datetime import datetime, timedelta
import time
from collections import defaultdict


class BrowserFaceRecognizer:
    """
    Handles face recognition from browser-captured video frames
    """
    
    def __init__(self):
        self.knn_model = None
        self.student_map = {}
        self.face_cascade = None
        self.eye_cascade = None
        self.session_id = None
        self.session_start_time = None
        self.attendance_records = {}
        self.track_data = defaultdict(lambda: {
            'count': 0,
            'name': None,
            'marked': False,
            'last_seen': 0
        })
        
        # Recognition settings
        self.CONFIDENCE_THRESHOLD = 0.70
        self.MIN_MATCH_DISTANCE = 4000
        self.FRAME_CONFIRMATION = 5
        self.LATE_THRESHOLD_MINUTES = 30
        
        self._load_cascades()
    
    def _load_cascades(self):
        """Load face and eye detection cascades"""
        import os
        
        cascade_paths = [
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml',
            'data/haarcascade_frontalface_default.xml',
            './AttendanceAI/data/haarcascade_frontalface_default.xml'
        ]
        
        for path in cascade_paths:
            if os.path.exists(path):
                self.face_cascade = cv2.CascadeClassifier(path)
                if not self.face_cascade.empty():
                    print(f"✅ Face cascade loaded: {path}")
                    break
        
        if self.face_cascade is None or self.face_cascade.empty():
            print("⚠️ Warning: Face cascade not loaded")
        
        # Load eye cascade
        try:
            self.eye_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_eye.xml'
            )
        except:
            print("⚠️ Warning: Eye cascade not loaded")
    
    def initialize_session(self, session_id, student_map, faces, labels):
        """
        Initialize a recognition session
        
        Args:
            session_id: The class/session ID
            student_map: Dictionary mapping names to student IDs
            faces: NumPy array of training face features
            labels: NumPy array of student name labels
        """
        self.session_id = session_id
        self.student_map = student_map
        self.session_start_time = datetime.now().time()
        self.attendance_records = {}
        self.track_data.clear()
        
        # Train KNN model
        if faces is not None and labels is not None and len(faces) > 0:
            n_neighbors = min(5, len(set(labels)))
            self.knn_model = KNeighborsClassifier(
                n_neighbors=n_neighbors,
                weights='distance',
                algorithm='ball_tree',
                metric='manhattan'
            )
            self.knn_model.fit(faces, labels)
            print(f"✅ Model trained with {len(faces)} samples, {len(set(labels))} students")
            return True
        
        print("❌ No training data available")
        return False
    
    def process_frame(self, frame_data):
        """
        Process a single frame from the browser
        
        Args:
            frame_data: Base64 encoded image data
            
        Returns:
            Dictionary with recognition results
        """
        try:
            # Decode base64 image
            if ',' in frame_data:
                frame_data = frame_data.split(',')[1]
            
            img_bytes = base64.b64decode(frame_data)
            img_array = np.frombuffer(img_bytes, dtype=np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            if frame is None:
                return {'success': False, 'error': 'Invalid frame data'}
            
            # Convert to grayscale for detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.2,
                minNeighbors=5,
                minSize=(60, 60)
            )
            
            results = []
            
            for (x, y, w, h) in faces:
                result = self._process_face(frame, gray, x, y, w, h)
                if result:
                    results.append(result)
            
            return {
                'success': True,
                'faces_detected': len(faces),
                'recognitions': results,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error processing frame: {e}")
            return {'success': False, 'error': str(e)}
    
    def _process_face(self, frame, gray, x, y, w, h):
        """Process a detected face region"""
        try:
            # Extract face region
            face_roi = frame[y:y+h, x:x+w]
            
            if face_roi.size == 0:
                return None
            
            # Extract features
            features = self._extract_features(face_roi)
            if features is None:
                return None
            
            # Predict using KNN
            prediction = self.knn_model.predict(features)[0]
            probabilities = self.knn_model.predict_proba(features)
            confidence = np.max(probabilities)
            
            distances, _ = self.knn_model.kneighbors(features, n_neighbors=min(5, len(self.knn_model.classes_)))
            avg_distance = np.mean(distances[0])
            
            # Check thresholds
            if confidence < self.CONFIDENCE_THRESHOLD or avg_distance > self.MIN_MATCH_DISTANCE:
                return {
                    'name': 'Unknown',
                    'confidence': float(confidence),
                    'distance': float(avg_distance),
                    'bbox': [int(x), int(y), int(w), int(h)],
                    'status': 'low_confidence'
                }
            
            # Track this person
            track_key = f"{x//30}_{y//30}"
            track = self.track_data[track_key]
            track['count'] += 1
            track['name'] = prediction
            track['last_seen'] = time.time()
            
            # Check if we should mark attendance
            marked = False
            status = None
            student_id = None
            
            if track['count'] >= self.FRAME_CONFIRMATION and not track['marked']:
                # Mark attendance
                student_info = self.student_map.get(prediction, {})
                student_id = student_info.get('student_id')
                
                if student_id and prediction not in self.attendance_records:
                    status = self._determine_status()
                    self.attendance_records[prediction] = {
                        'student_id': student_id,
                        'status': status,
                        'confidence': float(confidence),
                        'distance': float(avg_distance),
                        'time': datetime.now().isoformat()
                    }
                    track['marked'] = True
                    marked = True
            
            return {
                'name': prediction,
                'confidence': float(confidence),
                'distance': float(avg_distance),
                'bbox': [int(x), int(y), int(w), int(h)],
                'track_count': track['count'],
                'marked': marked,
                'status': status,
                'student_id': student_id
            }
            
        except Exception as e:
            print(f"Error in _process_face: {e}")
            return None
    
    def _extract_features(self, face_img):
        """Extract features from face image"""
        try:
            # Resize to standard size
            resized = cv2.resize(face_img, (50, 50))
            
            # Convert to grayscale if needed
            if len(resized.shape) == 3:
                gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
            else:
                gray = resized
            
            # Flatten
            features = gray.flatten().reshape(1, -1)
            return features
            
        except Exception as e:
            print(f"Error extracting features: {e}")
            return None
    
    def _determine_status(self):
        """Determine if student is present or late"""
        if self.session_start_time is None:
            return 'present'
        
        now = datetime.now()
        session_start_dt = datetime.combine(now.date(), self.session_start_time)
        late_cutoff = session_start_dt + timedelta(minutes=self.LATE_THRESHOLD_MINUTES)
        
        return 'late' if now > late_cutoff else 'present'
    
    def get_session_stats(self):
        """Get current session statistics"""
        present_count = sum(1 for r in self.attendance_records.values() if r['status'] == 'present')
        late_count = sum(1 for r in self.attendance_records.values() if r['status'] == 'late')
        
        return {
            'total_marked': len(self.attendance_records),
            'present': present_count,
            'late': late_count,
            'records': self.attendance_records
        }
    
    def cleanup_old_tracks(self):
        """Remove stale tracking data"""
        now = time.time()
        stale_keys = [k for k, v in self.track_data.items() if now - v['last_seen'] > 5]
        for key in stale_keys:
            del self.track_data[key]
    
    def reset(self):
        """Reset the recognizer state"""
        self.session_id = None
        self.session_start_time = None
        self.attendance_records.clear()
        self.track_data.clear()


# Global recognizer instance
browser_recognizer = BrowserFaceRecognizer()
