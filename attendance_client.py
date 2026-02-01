"""
Attendance Desktop Client - For Local Execution
================================================
This client runs on the USER'S COMPUTER (not the server).
It accesses the local webcam and sends recognition results to the hosted API.

USAGE:
1. Download this file to your computer
2. Install requirements: pip install opencv-python numpy requests scikit-learn
3. Run: python attendance_desktop_client.py --server https://your-render-app.onrender.com --session 1

Author: AI Assistant
Date: 2026-01-30
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
import threading

# ==================== CONFIGURATION ====================
# These will be set from command line or config file
API_URL = None  # Will be set from --server argument
CAMERA_INDEX = 0

# Timing configuration
LATE_THRESHOLD_MINUTES = 30

# Recognition thresholds
CONFIDENCE_THRESHOLD = 0.85
MIN_MATCH_DISTANCE = 3500
FRAME_CONFIRMATION = 30
REJECT_UNKNOWN = True
UNKNOWN_THRESHOLD = 0.60
MIN_MARGIN = 0.20

# Anti-spoofing
BLINK_REQUIRED = 1

# Display settings
SHOW_ATTENDANCE_PANEL = True
MAX_DISPLAY_NAMES = 8


def print_banner():
    print("=" * 70)
    print("🎓 ATTENDANCE DESKTOP CLIENT")
    print("=" * 70)
    print("This client runs on YOUR computer and connects to the hosted server.")
    print(f"⏰ Late threshold: {LATE_THRESHOLD_MINUTES} minutes from session start")
    print("=" * 70)


# ==================== API FUNCTIONS ====================

def check_server_connection(api_url):
    """Check if API server is reachable"""
    try:
        # Try multiple endpoints
        endpoints = ['/api/ping', '/api/health', '/ping', '/health']
        for endpoint in endpoints:
            try:
                response = requests.get(f"{api_url}{endpoint}", timeout=5)
                if response.status_code == 200:
                    print(f"✅ Connected to server: {api_url}")
                    return True
            except:
                continue
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


def get_session_info(api_url, session_id):
    """Get specific session info by ID"""
    try:
        response = requests.get(f"{api_url}/api/sessions?all=true", timeout=10)
        data = response.json()
        
        if data.get('success'):
            sessions = data.get('sessions', data.get('classes', []))
            for session in sessions:
                sid = session.get('session_id', session.get('class_id'))
                if str(sid) == str(session_id):
                    return session
        
        # If not found, create a placeholder
        print(f"   Session #{session_id} not found in list, using as class_id directly")
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


def get_active_session(api_url):
    """Get any currently active session"""
    try:
        response = requests.get(f"{api_url}/api/sessions", timeout=10)
        data = response.json()
        
        if data.get('success'):
            sessions = data.get('sessions', data.get('classes', []))
            if sessions:
                session = sessions[0]
                session['session_id'] = session.get('session_id', session.get('class_id'))
                return session
        return None
    except Exception as e:
        print(f"⚠️ Could not get active session: {e}")
        return None


def load_training_data(api_url):
    """Load training data from server"""
    try:
        print("📥 Downloading training data from server...")
        response = requests.get(f"{api_url}/api/students/training-data", timeout=30)
        data = response.json()
        
        if not data.get('success') or data.get('student_count', 0) == 0:
            print("❌ No training data available on server")
            return None, None
        
        faces = np.array(data['faces'], dtype=np.uint8)
        labels = np.array(data['labels'])
        print(f"✅ Downloaded {len(faces)} samples for {data['student_count']} students")
        return faces, labels
    except Exception as e:
        print(f"❌ Error loading training data: {e}")
        return None, None


def get_student_mapping(api_url):
    """Get student ID to name mapping"""
    try:
        response = requests.get(f"{api_url}/api/students", timeout=10)
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


def get_enrolled_students(api_url, class_id):
    """Get students enrolled in a specific class"""
    try:
        response = requests.get(f"{api_url}/api/class/{class_id}/students", timeout=10)
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


def mark_attendance_api(api_url, student_name, student_id, facial_data_id, session_id,
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
                'arrival_time': arrival_time.strftime("%H:%M:%S") if arrival_time else None,
                'source': 'desktop_client'
            }
        }
        
        response = requests.post(
            f"{api_url}/api/attendance/mark",
            json=payload,
            timeout=10
        )
        data = response.json()
        
        success = data.get('success', False)
        already_present = data.get('already_present', False)
        
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
            'confidence': confidence
        }
        
        return status, True
    
    def get_present_count(self):
        return sum(1 for r in self.records.values() if r['status'] == 'present')
    
    def get_late_count(self):
        return sum(1 for r in self.records.values() if r['status'] == 'late')
    
    def get_attendance_list(self):
        return sorted(self.records.items(), key=lambda x: x[1]['arrival_datetime'])


# ==================== MAIN CLIENT ====================

class AttendanceDesktopClient:
    def __init__(self, api_url, session_id=None, camera_index=0):
        self.api_url = api_url
        self.session_id = session_id
        self.camera_index = camera_index
        
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
        print("\n🔧 Initializing local components...")
        
        # Load face detector from OpenCV
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.facedetect = cv2.CascadeClassifier(cascade_path)
        
        if self.facedetect.empty():
            print("❌ Error: Could not load face detector!")
            return False
        
        print("✅ Face detector loaded")
        
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )
        
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
        faces, labels = load_training_data(self.api_url)
        
        if faces is None:
            return False
        
        # Filter to enrolled students if provided
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
            self.student_map = get_student_mapping(self.api_url)
        
        print(f"✅ Model ready: {len(enhanced)} samples, {len(set(labels))} students")
        return True
    
    def start_camera(self):
        if self.video and self.video.isOpened():
            return True
        
        print(f"🎥 Opening camera (index {self.camera_index})...")
        self.video = cv2.VideoCapture(self.camera_index)
        
        if not self.video.isOpened():
            print("❌ Cannot open camera!")
            print("   Make sure:")
            print("   - A webcam is connected")
            print("   - No other app is using the camera")
            print("   - You have camera permissions")
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
        
        # Reject unknown
        if REJECT_UNKNOWN and confidence < UNKNOWN_THRESHOLD:
            return "Unknown", None, False, False, False, confidence, avg_distance, track_data
        
        # Check margin
        sorted_probs = np.sort(proba[0])[::-1]
        if len(sorted_probs) >= 2 and (sorted_probs[0] - sorted_probs[1]) < MIN_MARGIN:
            return "Ambiguous", None, False, False, False, confidence, avg_distance, track_data
        
        name = str(output)
        
        if name in self.marked_names:
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
                    print(f"   Confidence: {confidence:.2%}")
                    print(f"{'='*60}")
                    
                    # Send to server
                    api_success = mark_attendance_api(
                        self.api_url,
                        name, student_id, student_info.get('facial_data_id'),
                        self.current_session['session_id'],
                        status, self.attendance.records[name]['arrival_time'],
                        confidence, avg_distance
                    )
                    
                    if api_success:
                        print(f"   📡 Saved to server\n")
                    else:
                        print(f"   ⚠️ Server sync pending\n")
        
        return name, status, is_new, is_verified, is_spoof, confidence, avg_distance, track_data
    
    def draw_face_box(self, frame, x, y, w, h, name, is_verified, confidence, track_data):
        if name in ["Unknown", "Ambiguous"]:
            color = (128, 128, 128)
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            cv2.putText(frame, f"{name}", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            return
        
        if name in self.marked_names:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 3)
            cv2.rectangle(frame, (x, y-35), (x+w, y), (0, 200, 0), -1)
            cv2.putText(frame, f"{name} [OK]", (x+5, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
        elif is_verified:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 3)
            cv2.putText(frame, f"{name} ({confidence:.0%})", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)
        else:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 255), 2)
            if track_data:
                progress = f"{track_data['count']}/{FRAME_CONFIRMATION}"
                cv2.putText(frame, f"{name} [{progress}]", (x, y-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
    
    def run(self):
        """Main run loop"""
        
        # Get session info
        if self.session_id:
            self.current_session = get_session_info(self.api_url, self.session_id)
        else:
            print("⚠️ No session_id provided, looking for active session...")
            self.current_session = get_active_session(self.api_url)
        
        if not self.current_session:
            print("❌ No session found!")
            print("   Use: python attendance_desktop_client.py --server URL --session ID")
            return
        
        session_id = self.current_session.get('session_id', self.current_session.get('class_id'))
        self.current_session['session_id'] = session_id
        
        print(f"\n{'='*60}")
        print(f"🎯 SESSION #{session_id}")
        print(f"   Course: {self.current_session.get('course_code', 'N/A')}")
        print(f"   Server: {self.api_url}")
        print(f"{'='*60}\n")
        
        # Parse start time
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
        
        self.attendance = AttendanceRecord(session_start)
        self.tracker.reset()
        self.anti_spoof.reset()
        self.marked_names = set()
        
        if not self.start_camera():
            return
        
        # Get enrolled students
        enrolled = get_enrolled_students(self.api_url, session_id)
        if not enrolled:
            enrolled = get_student_mapping(self.api_url)
        
        self.student_map = enrolled
        print(f"📋 {len(self.student_map)} students loaded")
        
        if not self.load_model(enrolled_only=enrolled):
            self.stop_camera()
            return
        
        self.running = True
        
        print("\n" + "="*60)
        print("📹 CAMERA ACTIVE - Press 'q' to quit")
        print("="*60 + "\n")
        
        try:
            while self.running:
                ret, frame = self.video.read()
                if not ret:
                    break
                
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.facedetect.detectMultiScale(gray, 1.2, 5, minSize=(80, 80))
                
                self.tracker.cleanup_stale_tracks()
                
                for (x, y, w, h) in faces:
                    result = self.process_face(frame, gray, x, y, w, h)
                    if result[0] is not None:
                        name, status, is_new, is_verified, is_spoof, confidence, distance, track_data = result
                        self.draw_face_box(frame, x, y, w, h, name, is_verified, confidence, track_data)
                
                # Stats overlay
                cv2.rectangle(frame, (0, 0), (320, 80), (0, 0, 0), -1)
                cv2.putText(frame, f"Session #{session_id} | Server: Connected", (10, 25), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cv2.putText(frame, f"Present: {self.attendance.get_present_count()}  Late: {self.attendance.get_late_count()}", 
                           (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.putText(frame, f"Time: {datetime.now().strftime('%H:%M:%S')}", 
                           (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                
                # Attendance panel
                if SHOW_ATTENDANCE_PANEL:
                    panel_x = frame.shape[1] - 250
                    cv2.rectangle(frame, (panel_x - 10, 0), (frame.shape[1], 200), (0, 0, 0), -1)
                    cv2.putText(frame, "Attendance:", (panel_x, 25), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                    
                    for i, (name, data) in enumerate(self.attendance.get_attendance_list()[:MAX_DISPLAY_NAMES]):
                        time_str = data['arrival_time'].strftime("%H:%M")
                        color = (0, 255, 0) if data['status'] == 'present' else (0, 165, 255)
                        cv2.putText(frame, f"+ {name} ({time_str})", 
                                   (panel_x, 50 + i * 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                
                cv2.imshow("Attendance - Desktop Client", frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("\n👋 Quit requested")
                    break
        
        except KeyboardInterrupt:
            print("\n⚠️ Interrupted")
        
        finally:
            self.running = False
            self.stop_camera()
            cv2.destroyAllWindows()
            
            # Summary
            print("\n" + "="*60)
            print("📊 SESSION SUMMARY")
            print("="*60)
            print(f"   Present: {self.attendance.get_present_count()}")
            print(f"   Late: {self.attendance.get_late_count()}")
            print("="*60)


def main():
    print_banner()
    
    parser = argparse.ArgumentParser(description='Attendance Desktop Client')
    parser.add_argument('--server', '-s', required=True, help='Server URL (e.g., https://your-app.onrender.com)')
    parser.add_argument('--session', '-n', type=int, help='Session/Class ID')
    parser.add_argument('--camera', '-c', type=int, default=0, help='Camera index (default: 0)')
    args = parser.parse_args()
    
    # Clean up server URL
    api_url = args.server.rstrip('/')
    if not api_url.startswith('http'):
        api_url = 'https://' + api_url
    
    print(f"\n🔍 Connecting to: {api_url}")
    
    if not check_server_connection(api_url):
        print(f"❌ Cannot connect to server: {api_url}")
        print("   Check the URL and make sure the server is running")
        return
    
    client = AttendanceDesktopClient(
        api_url=api_url,
        session_id=args.session,
        camera_index=args.camera
    )
    
    if not client.initialize():
        return
    
    client.run()


if __name__ == "__main__":
    main()