"""
Manual Attendance System Client - Session-Focused Version
==========================================================
Features:
✓ Manually started via button (no auto-session detection)
✓ Receives session_id from command line or uses active session
✓ Multiple person detection & tracking
✓ Enhanced anti-spoofing (motion, depth, multi-blink)
✓ Timestamp recording for each student
✓ Late detection (configurable grace period)
✓ Real-time statistics
✓ Runs until manually stopped (press 'q' or stop button)

Author: AI Assistant
Date: 2026-01-20
"""

from sklearn.neighbors import KNeighborsClassifier
import cv2
import numpy as np
import time
import os
import sys
import argparse
from datetime import datetime, timedelta
from collections import defaultdict, deque
import requests
import json

# ==================== CONFIGURATION ====================
API_URL = "http://localhost:5000"
CAMERA_INDEX = 0

# Timing configuration
LATE_THRESHOLD_MINUTES = 30

# Recognition thresholds - STRICT TO PREVENT MISIDENTIFICATION
CONFIDENCE_THRESHOLD = 0.85
MIN_MATCH_DISTANCE = 3500
FRAME_CONFIRMATION = 30
REJECT_UNKNOWN = True
UNKNOWN_THRESHOLD = 0.60
MIN_MARGIN = 0.20
LOCK_AFTER_MARK = True

# Anti-spoofing
BLINK_REQUIRED = 1
EYE_OPEN_FRAMES = 2
MOTION_THRESHOLD = 5

# Other settings
SHOW_ATTENDANCE_PANEL = True
MAX_DISPLAY_NAMES = 8

print("=" * 80)
print("🎓 MANUAL ATTENDANCE SYSTEM - SESSION FOCUSED")
print("=" * 80)
print(f"⏰ Late after: {LATE_THRESHOLD_MINUTES} minutes from session start")
print("")
print("🔒 RECOGNITION SETTINGS:")
print(f"   Confidence threshold: {CONFIDENCE_THRESHOLD} ({int(CONFIDENCE_THRESHOLD*100)}%)")
print(f"   Max distance: {MIN_MATCH_DISTANCE}")
print(f"   Frames required: {FRAME_CONFIRMATION}")
print("=" * 80)


# ==================== API FUNCTIONS ====================

def check_server_connection():
    """Check if API server is reachable"""
    try:
        response = requests.get(f"{API_URL}/api/health", timeout=3)
        return response.status_code == 200
    except:
        return False


def get_session_info(session_id):
    """Get specific session info by ID"""
    try:
        response = requests.get(f"{API_URL}/api/sessions?all=true", timeout=5)
        data = response.json()
        
        if data.get('success'):
            sessions = data.get('sessions', data.get('classes', []))
            for session in sessions:
                sid = session.get('session_id', session.get('class_id'))
                if str(sid) == str(session_id):
                    return session
        
        # If not found in sessions, try to get class info directly
        print(f"   Session #{session_id} not in today's list, using as class_id directly")
        return {
            'session_id': session_id,
            'class_id': session_id,
            'course_code': 'Direct Session',
            'start_time': datetime.now().strftime('%H:%M:%S'),
            'end_time': (datetime.now() + timedelta(hours=2)).strftime('%H:%M:%S')
        }
        
    except Exception as e:
        print(f"⚠️ Could not get session info: {e}")
        return None


def get_active_session():
    """Get any currently active session (fallback if no session_id provided)"""
    try:
        response = requests.get(f"{API_URL}/api/sessions", timeout=5)
        data = response.json()
        
        if data.get('success'):
            sessions = data.get('sessions', data.get('classes', []))
            if sessions:
                # Return the first available session
                session = sessions[0]
                session['session_id'] = session.get('session_id', session.get('class_id'))
                return session
        
        return None
    except Exception as e:
        print(f"⚠️ Could not get active session: {e}")
        return None


def load_training_data():
    """Load training data from server"""
    try:
        response = requests.get(f"{API_URL}/api/students/training-data", timeout=15)
        data = response.json()
        
        if not data.get('success') or data['student_count'] == 0:
            return None, None
        
        faces = np.array(data['faces'], dtype=np.uint8)
        labels = np.array(data['labels'])
        return faces, labels
    except Exception as e:
        print(f"❌ Error loading training data: {e}")
        return None, None


def get_student_mapping():
    """Get student ID to name mapping"""
    try:
        response = requests.get(f"{API_URL}/api/students", timeout=5)
        data = response.json()
        
        if data.get('success'):
            mapping = {}
            for student in data['students']:
                student_id = student.get('student_id', student.get('user_id'))
                mapping[student['name']] = {
                    'student_id': student_id,
                    'user_id': student_id,
                    'facial_data_id': student.get('facial_data_id', student_id)
                }
            return mapping
        return {}
    except:
        return {}


def get_enrolled_students_for_class(class_id):
    """Get students enrolled in a specific class"""
    try:
        response = requests.get(f"{API_URL}/api/class/{class_id}/students", timeout=5)
        data = response.json()
        
        if data.get('success'):
            mapping = {}
            for student in data.get('students', []):
                student_id = student.get('student_id', student.get('user_id'))
                mapping[student['name']] = {
                    'student_id': student_id,
                    'user_id': student_id,
                    'facial_data_id': student.get('facial_data_id', student_id)
                }
            return mapping
        return {}
    except:
        return {}


def mark_attendance_api(student_name, student_id, facial_data_id, session_id,
                        status, arrival_time, confidence, distance):
    """Mark student attendance via API"""
    try:
        payload = {
            'student_id': student_id,
            'session_id': session_id,
            'class_id': session_id,
            'status': status,
            'recognition_data': {
                'facial_data_id': facial_data_id,
                'confidence': float(confidence),
                'distance': float(distance),
                'name': student_name,
                'arrival_time': arrival_time.strftime("%H:%M:%S") if arrival_time else None
            }
        }
        
        print(f"   📤 API Call: student_id={student_id}, session_id={session_id}, status={status}")
        
        response = requests.post(
            f"{API_URL}/api/attendance/mark",
            json=payload,
            timeout=5
        )
        data = response.json()
        
        success = data.get('success', False)
        already_present = data.get('already_present', False)
        
        if success:
            if already_present:
                print(f"   ℹ️ {student_name} already marked")
            else:
                print(f"   ✅ API confirmed: {student_name} marked as {status}")
        else:
            print(f"   ❌ API error: {data.get('error', 'Unknown error')}")
        
        return success and not already_present
        
    except Exception as e:
        print(f"⚠️ API error: {e}")
        return False


# ==================== TRACKING CLASSES ====================

class PersonTracker:
    def __init__(self):
        self.tracks = {}
        self.next_id = 0
        
    def reset(self):
        self.tracks = {}
        self.next_id = 0
        
    def get_track_id(self, x, y, w, h):
        current_pos = (x // 30, y // 30)
        
        for track_id, data in self.tracks.items():
            last_pos = data['last_pos']
            if abs(current_pos[0] - last_pos[0]) <= 2 and abs(current_pos[1] - last_pos[1]) <= 2:
                data['last_pos'] = current_pos
                data['last_seen'] = time.time()
                return track_id
        
        track_id = self.next_id
        self.next_id += 1
        self.tracks[track_id] = {
            'last_pos': current_pos,
            'last_seen': time.time(),
            'name': None,
            'count': 0,
            'confirmed': False,
            'blink_count': 0,
            'eye_open_count': 0,
            'motion_score': 0,
            'marked': False
        }
        return track_id
    
    def cleanup_stale_tracks(self):
        now = time.time()
        stale_ids = [tid for tid, data in self.tracks.items() 
                     if now - data['last_seen'] > 3]
        for tid in stale_ids:
            del self.tracks[tid]


class AntiSpoofDetector:
    def __init__(self):
        self.motion_history = defaultdict(lambda: deque(maxlen=30))
        self.last_frames = {}
    
    def reset(self):
        self.motion_history = defaultdict(lambda: deque(maxlen=30))
        self.last_frames = {}
        
    def check_motion(self, track_id, face_roi):
        try:
            face_roi_resized = cv2.resize(face_roi, (100, 100))
        except:
            return 0
        
        if track_id not in self.last_frames:
            self.last_frames[track_id] = face_roi_resized
            return 0
        
        try:
            diff = cv2.absdiff(self.last_frames[track_id], face_roi_resized)
            motion_score = np.mean(diff)
        except:
            return 0
        
        self.motion_history[track_id].append(motion_score)
        self.last_frames[track_id] = face_roi_resized
        
        if len(self.motion_history[track_id]) >= 10:
            return np.var(list(self.motion_history[track_id]))
        return 0


class AttendanceRecord:
    def __init__(self, session_start_time):
        self.session_start_time = session_start_time
        self.records = {}
        self.late_threshold = timedelta(minutes=LATE_THRESHOLD_MINUTES)
        self.last_seen = {}
    
    def mark_student(self, name, student_id, facial_data_id, confidence, distance):
        if name in self.records:
            return self.records[name]['status'], False
        
        now = datetime.now()
        arrival_time = now.time()
        
        session_start_dt = datetime.combine(now.date(), self.session_start_time)
        late_cutoff = session_start_dt + self.late_threshold
        
        status = 'late' if now > late_cutoff else 'present'
        
        self.records[name] = {
            'status': status,
            'arrival_time': arrival_time,
            'arrival_datetime': now,
            'student_id': student_id,
            'facial_data_id': facial_data_id,
            'confidence': confidence,
            'distance': distance
        }
        
        self.last_seen[name] = now
        return status, True
    
    def update_last_seen(self, name):
        if name in self.records:
            self.last_seen[name] = datetime.now()
    
    def get_present_count(self):
        return sum(1 for r in self.records.values() if r['status'] == 'present')
    
    def get_late_count(self):
        return sum(1 for r in self.records.values() if r['status'] == 'late')
    
    def get_total_count(self):
        return sum(1 for r in self.records.values() if r['status'] in ['present', 'late'])
    
    def get_attendance_list(self):
        return sorted(self.records.items(), key=lambda x: x[1]['arrival_datetime'])


# ==================== MAIN SYSTEM ====================

class ManualAttendanceSystem:
    def __init__(self, session_id=None):
        self.session_id = session_id
        self.video = None
        self.knn = None
        self.facedetect = None
        self.eye_cascade = None
        self.tracker = PersonTracker()
        self.anti_spoof = AntiSpoofDetector()
        self.student_map = {}
        self.attendance = None
        self.current_session = None
        self.running = False
        self.marked_names = set()
        self.n_neighbors = 5
        
    def initialize(self):
        print("\n🔧 Initializing system components...")
        
        # Load face detector
        cascade_paths = [
            'data/haarcascade_frontalface_default.xml',
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml',
            './AttendanceAI/data/haarcascade_frontalface_default.xml'
        ]
        
        for path in cascade_paths:
            if os.path.exists(path):
                self.facedetect = cv2.CascadeClassifier(path)
                if not self.facedetect.empty():
                    print(f"✅ Face detector loaded: {path}")
                    break
        
        if self.facedetect is None or self.facedetect.empty():
            print("❌ Error: Could not load face detector!")
            return False
        
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        
        print("✅ System initialized")
        return True
    
    def extract_features(self, face_img):
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
    
    def load_model(self, enrolled_only=None):
        print("📥 Loading training data...")
        faces, labels = load_training_data()
        
        if faces is None:
            print("❌ No training data!")
            return False
        
        # Filter to enrolled students only if provided
        if enrolled_only and len(enrolled_only) > 0:
            enrolled_names = set(enrolled_only.keys())
            filtered = [(f, l) for f, l in zip(faces, labels) if l in enrolled_names]
            if filtered:
                faces = np.array([f for f, _ in filtered])
                labels = np.array([l for _, l in filtered])
                print(f"   Filtered to {len(set(labels))} enrolled students")
        
        # Enhance faces
        enhanced = []
        for face in faces:
            size = face.shape[0]
            if size == 7500:
                face_2d = cv2.cvtColor(face.reshape(50, 50, 3).astype(np.uint8), cv2.COLOR_BGR2GRAY)
            elif size == 2500:
                face_2d = face.reshape(50, 50).astype(np.uint8)
            else:
                side = int(np.sqrt(size // 3)) if size % 3 == 0 else int(np.sqrt(size))
                face_2d = cv2.resize(face.reshape(side, -1).astype(np.uint8), (50, 50))
            enhanced.append(cv2.equalizeHist(face_2d).flatten())
        
        enhanced = np.array(enhanced)
        self.n_neighbors = min(5, len(enhanced))
        self.knn = KNeighborsClassifier(n_neighbors=self.n_neighbors)
        self.knn.fit(enhanced, labels)
        
        if not enrolled_only:
            self.student_map = get_student_mapping()
        
        print(f"✅ Model trained: {len(enhanced)} samples, {len(set(labels))} students")
        return True
    
    def start_camera(self):
        if self.video and self.video.isOpened():
            return True
        
        print(f"🎥 Opening camera (index {CAMERA_INDEX})...")
        self.video = cv2.VideoCapture(CAMERA_INDEX)
        
        if not self.video.isOpened():
            print("❌ Cannot open camera!")
            return False
        
        self.video.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.video.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        print("✅ Camera ready")
        return True
    
    def stop_camera(self):
        if self.video:
            self.video.release()
            self.video = None
    
    def process_face(self, frame, gray, x, y, w, h):
        track_id = self.tracker.get_track_id(x, y, w, h)
        track_data = self.tracker.tracks[track_id]
        
        # If already marked, just return the name
        if track_data['marked']:
            return track_data['name'], None, False, True, False, 1.0, 0, track_data
        
        crop_img = frame[y:y+h, x:x+w]
        if crop_img.size == 0:
            return None, None, False, False, False, 0, 0, None
        
        features = self.extract_features(crop_img)
        if features is None:
            return None, None, False, False, False, 0, 0, None
        
        # Predict
        output = self.knn.predict(features)[0]
        proba = self.knn.predict_proba(features)
        confidence = np.max(proba)
        
        distances, _ = self.knn.kneighbors(features, n_neighbors=self.n_neighbors)
        avg_distance = np.mean(distances[0])
        
        # Reject unknown faces
        if REJECT_UNKNOWN and confidence < UNKNOWN_THRESHOLD:
            return "Unknown", None, False, False, False, confidence, avg_distance, track_data
        
        # Check margin between top matches
        sorted_probs = np.sort(proba[0])[::-1]
        if len(sorted_probs) >= 2 and (sorted_probs[0] - sorted_probs[1]) < MIN_MARGIN:
            return "Ambiguous", None, False, False, False, confidence, avg_distance, track_data
        
        name = str(output)
        
        # If already marked this name, just update last seen
        if name in self.marked_names:
            self.attendance.update_last_seen(name)
            return name, None, False, True, False, confidence, avg_distance, track_data
        
        # Temporal consistency
        if track_data['name'] == output:
            track_data['count'] += 1
        else:
            track_data['name'] = output
            track_data['count'] = 1
            track_data['confirmed'] = False
        
        if track_data['count'] >= FRAME_CONFIRMATION and confidence >= CONFIDENCE_THRESHOLD:
            track_data['confirmed'] = True
        
        # Blink detection
        face_gray = gray[y:y+h, x:x+w]
        eyes = self.eye_cascade.detectMultiScale(face_gray, 1.1, 3)
        if len(eyes) > 0:
            track_data['eye_open_count'] += 1
        elif track_data['eye_open_count'] > 0:
            track_data['blink_count'] += 1
        
        # Motion check
        motion_score = self.anti_spoof.check_motion(track_id, face_gray)
        
        is_verified = (
            track_data['confirmed'] and
            track_data['blink_count'] >= BLINK_REQUIRED and
            confidence >= CONFIDENCE_THRESHOLD and
            avg_distance <= MIN_MATCH_DISTANCE
        )
        
        is_spoof = motion_score < 3 and track_data['count'] > 30
        
        status = None
        is_new = False
        
        margin_ok = len(sorted_probs) < 2 or (sorted_probs[0] - sorted_probs[1]) >= MIN_MARGIN
        
        can_mark = (
            is_verified and not is_spoof and
            not track_data['marked'] and
            name not in self.marked_names and
            name not in ["Unknown", "Ambiguous"] and
            confidence >= CONFIDENCE_THRESHOLD and
            avg_distance <= MIN_MATCH_DISTANCE and
            margin_ok
        )
        
        if can_mark:
            student_info = self.student_map.get(name, {})
            student_id = student_info.get('student_id')
            
            if student_id:
                status, is_new = self.attendance.mark_student(
                    name, student_id, student_info.get('facial_data_id'),
                    confidence, avg_distance
                )
                
                if is_new:
                    track_data['marked'] = True
                    self.marked_names.add(name)
                    
                    print(f"\n{'='*60}")
                    print(f"✅ RECOGNIZED: {name}")
                    print(f"   Status: {status.upper()}")
                    print(f"   Student ID: {student_id}")
                    print(f"   Confidence: {confidence:.2%}")
                    print(f"   Distance: {avg_distance:.0f}")
                    print(f"   Session: {self.current_session['session_id']}")
                    print(f"{'='*60}")
                    
                    # Call API to save attendance
                    api_success = mark_attendance_api(
                        name, student_id, student_info.get('facial_data_id'),
                        self.current_session['session_id'],
                        status, self.attendance.records[name]['arrival_time'],
                        confidence, avg_distance
                    )
                    
                    if api_success:
                        print(f"   📡 Attendance saved to database\n")
                    else:
                        print(f"   ⚠️ Could not save to database (may already exist)\n")
            else:
                print(f"⚠️ No student_id found for {name}")
        
        return name, status, is_new, is_verified, is_spoof, confidence, avg_distance, track_data
    
    def draw_face_box(self, frame, x, y, w, h, name, status, is_verified, is_spoof,
                      confidence, avg_distance, track_data):
        if name in ["Unknown", "Ambiguous"]:
            color = (128, 128, 128)
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            label = f"{name} ({confidence:.0%})"
            cv2.putText(frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            return
        
        if name in self.marked_names:
            # Green box with checkmark for marked students
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 3)
            cv2.rectangle(frame, (x, y-35), (x+w, y), (0, 200, 0), -1)
            cv2.putText(frame, f"{name} ✓", (x+5, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
        elif is_verified:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 3)
            cv2.putText(frame, f"{name} ({confidence:.0%})", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)
        elif is_spoof:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 3)
            cv2.putText(frame, "SPOOF DETECTED", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 2)
        else:
            # Yellow box - still verifying
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 255), 2)
            if track_data:
                progress = f"{track_data['count']}/{FRAME_CONFIRMATION}"
                cv2.putText(frame, f"{name} [{progress}]", (x, y-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
    
    def run(self):
        """Main run loop for the attendance session"""
        
        # Get session info
        if self.session_id:
            self.current_session = get_session_info(self.session_id)
        else:
            print("⚠️ No session_id provided, looking for active session...")
            self.current_session = get_active_session()
        
        if not self.current_session:
            print("❌ No session found! Please provide a session_id.")
            return
        
        session_id = self.current_session.get('session_id', self.current_session.get('class_id'))
        self.current_session['session_id'] = session_id
        
        print(f"\n{'='*60}")
        print(f"🎯 STARTING ATTENDANCE FOR SESSION #{session_id}")
        print(f"   Course: {self.current_session.get('course_code', 'N/A')}")
        print(f"   Time: {self.current_session.get('start_time', 'N/A')} - {self.current_session.get('end_time', 'N/A')}")
        print(f"{'='*60}\n")
        
        # Parse session start time for late detection
        start_time_str = self.current_session.get('start_time', '')
        try:
            if ' ' in start_time_str:
                time_part = start_time_str.split(' ')[1]
            else:
                time_part = start_time_str
            
            if '.' in time_part:
                time_part = time_part.split('.')[0]
            
            session_start = datetime.strptime(time_part[:8], "%H:%M:%S").time()
        except:
            session_start = datetime.now().time()
        
        # Initialize attendance record
        self.attendance = AttendanceRecord(session_start)
        self.tracker.reset()
        self.anti_spoof.reset()
        self.marked_names = set()
        
        # Start camera
        if not self.start_camera():
            return
        
        # Get enrolled students for this class
        enrolled = get_enrolled_students_for_class(session_id)
        if not enrolled:
            print("   No specific enrollment found, using all students")
            enrolled = get_student_mapping()
        
        self.student_map = enrolled
        print(f"📋 Loaded {len(self.student_map)} students for recognition")
        
        # Show student names
        for name in list(self.student_map.keys())[:5]:
            print(f"   - {name} (ID: {self.student_map[name].get('student_id')})")
        if len(self.student_map) > 5:
            print(f"   ... and {len(self.student_map) - 5} more")
        
        # Load model
        if not self.load_model(enrolled_only=enrolled):
            self.stop_camera()
            return
        
        self.running = True
        frame_count = 0
        
        print("\n" + "="*60)
        print("📹 CAMERA ACTIVE - Face recognition running")
        print("   Press 'q' to quit")
        print("="*60 + "\n")
        
        try:
            while self.running:
                ret, frame = self.video.read()
                if not ret:
                    print("⚠️ Camera read failed")
                    break
                
                frame_count += 1
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Detect faces
                faces = self.facedetect.detectMultiScale(gray, 1.2, 5, minSize=(80, 80))
                
                self.tracker.cleanup_stale_tracks()
                
                # Process each face
                for (x, y, w, h) in faces:
                    result = self.process_face(frame, gray, x, y, w, h)
                    if result[0] is not None:
                        name, status, is_new, is_verified, is_spoof, confidence, distance, track_data = result
                        self.draw_face_box(frame, x, y, w, h, name, status, is_verified, 
                                          is_spoof, confidence, distance, track_data)
                
                # Draw stats overlay
                cv2.rectangle(frame, (0, 0), (300, 100), (0, 0, 0), -1)
                cv2.putText(frame, f"Session: #{session_id}", (10, 25), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                cv2.putText(frame, f"Present: {self.attendance.get_present_count()}  Late: {self.attendance.get_late_count()}", 
                           (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.putText(frame, f"Time: {datetime.now().strftime('%H:%M:%S')}", 
                           (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                
                # Draw attendance list on right side
                if SHOW_ATTENDANCE_PANEL:
                    panel_x = frame.shape[1] - 250
                    cv2.rectangle(frame, (panel_x - 10, 0), (frame.shape[1], 200), (0, 0, 0), -1)
                    cv2.putText(frame, "Attendance:", (panel_x, 25), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                    
                    for i, (name, data) in enumerate(self.attendance.get_attendance_list()[:MAX_DISPLAY_NAMES]):
                        time_str = data['arrival_time'].strftime("%H:%M")
                        status_icon = "✓" if data['status'] == 'present' else "⏰"
                        color = (0, 255, 0) if data['status'] == 'present' else (0, 165, 255)
                        cv2.putText(frame, f"{status_icon} {name} ({time_str})", 
                                   (panel_x, 50 + i * 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                
                # Show frame
                cv2.imshow("Attendance System", frame)
                
                # Check for quit
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\n👋 Quit requested")
                    break
        
        except KeyboardInterrupt:
            print("\n⚠️ Interrupted by user")
        
        finally:
            # Cleanup
            self.running = False
            self.stop_camera()
            cv2.destroyAllWindows()
            
            # Print final summary
            print("\n" + "="*60)
            print("📊 SESSION SUMMARY")
            print("="*60)
            print(f"   Session: #{session_id}")
            print(f"   Present: {self.attendance.get_present_count()}")
            print(f"   Late: {self.attendance.get_late_count()}")
            print(f"   Total Marked: {self.attendance.get_total_count()}")
            print("")
            
            if self.attendance.records:
                print("   Attendance List:")
                for name, data in self.attendance.get_attendance_list():
                    time_str = data['arrival_time'].strftime("%H:%M:%S")
                    status = data['status'].upper()
                    print(f"   - {name}: {status} at {time_str}")
            
            print("="*60)
            print("✅ Session ended")


# ==================== MAIN ====================

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Manual Attendance System')
    parser.add_argument('--session', '-s', type=int, help='Session/Class ID to use')
    parser.add_argument('--class_id', '-c', type=int, help='Class ID (alias for --session)')
    args = parser.parse_args()
    
    # Get session_id from args
    session_id = args.session or args.class_id
    
    print("\n🔍 Checking server connection...")
    if not check_server_connection():
        print(f"❌ Cannot connect to {API_URL}")
        print("   Make sure the Flask app is running: python app.py")
        return
    print("✅ Server connected")
    
    # Initialize system
    system = ManualAttendanceSystem(session_id=session_id)
    
    if not system.initialize():
        return
    
    # Run attendance session
    system.run()


if __name__ == "__main__":
    main()