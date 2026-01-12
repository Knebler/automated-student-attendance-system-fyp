"""
Fully Automatic Attendance System Client - Complete Version
============================================================
Features:
✓ Automatically starts before each session
✓ Multiple person detection & tracking
✓ Enhanced anti-spoofing (motion, depth, multi-blink)
✓ Mask-friendly recognition (uses upper face)
✓ Timestamp recording for each student
✓ Late detection (configurable grace period)
✓ Absent marking when session ends
✓ Real-time statistics
✓ Auto-stops after session ends

Author: AI Assistant
Date: 2026-01-12
"""

from sklearn.neighbors import KNeighborsClassifier
import cv2
import numpy as np
import time
from datetime import datetime, timedelta
from collections import defaultdict, deque
import requests
import json

# ==================== CONFIGURATION ====================
API_URL = "http://localhost:5000"
CAMERA_INDEX = 0

# Timing configuration
MINUTES_BEFORE_START = 10      # Start camera X minutes before session
MINUTES_AFTER_END = 5          # Keep running X minutes after session ends
LATE_THRESHOLD_MINUTES = 30    # Students arriving after this are marked LATE
CHECK_INTERVAL = 30            # Check for sessions every X seconds

# Recognition thresholds
CONFIDENCE_THRESHOLD = 0.25
MIN_MATCH_DISTANCE = 7500
FRAME_CONFIRMATION = 5

# Enhanced anti-spoofing settings
BLINK_REQUIRED = 2             # Must blink at least twice
EYE_OPEN_FRAMES = 3            # Eyes must be open for X frames
MOTION_THRESHOLD = 10          # Minimum motion variance required
DEPTH_CHECK_FRAMES = 5         # Frames to check for depth variation

# Mask detection settings - uses upper 60% of face for recognition
USE_UPPER_FACE_ONLY = True     # Enable for mask support

# Display settings
SHOW_ATTENDANCE_PANEL = True   # Show real-time attendance list on screen
MAX_DISPLAY_NAMES = 8          # Max names to show in attendance panel

print("=" * 80)
print("🎓 FULLY AUTOMATIC ATTENDANCE SYSTEM - Complete Version")
print("=" * 80)
print(f"⏰ Auto-start: {MINUTES_BEFORE_START} minutes before session")
print(f"⏰ Late after: {LATE_THRESHOLD_MINUTES} minutes from session start")
print(f"⏰ Auto-stop: {MINUTES_AFTER_END} minutes after session ends")
print("=" * 80)

# ==================== TRACKING CLASSES ====================

class PersonTracker:
    """
    Advanced multi-person tracking with anti-spoofing support.
    Tracks multiple faces simultaneously and maintains state for each.
    """
    def __init__(self):
        self.tracks = {}
        self.next_id = 0
        self.position_history = defaultdict(lambda: deque(maxlen=10))
        self.face_size_history = defaultdict(lambda: deque(maxlen=10))
        
    def reset(self):
        """Reset all tracks for new session"""
        self.tracks = {}
        self.next_id = 0
        self.position_history = defaultdict(lambda: deque(maxlen=10))
        self.face_size_history = defaultdict(lambda: deque(maxlen=10))
        
    def get_track_id(self, x, y, w, h):
        """
        Get or create track ID for a face at given position.
        Uses grid-based position matching to handle movement.
        """
        current_pos = (x // 30, y // 30)
        
        # Find existing track within proximity
        for track_id, data in self.tracks.items():
            last_pos = data['last_pos']
            if abs(current_pos[0] - last_pos[0]) <= 2 and abs(current_pos[1] - last_pos[1]) <= 2:
                data['last_pos'] = current_pos
                data['last_seen'] = time.time()
                return track_id
        
        # Create new track for new face
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
            'depth_score': 0,
            'spoof_alerts': 0,
            'marked': False
        }
        return track_id
    
    def cleanup_stale_tracks(self):
        """Remove tracks not seen for 3+ seconds"""
        now = time.time()
        stale_ids = [tid for tid, data in self.tracks.items() 
                     if now - data['last_seen'] > 3]
        for tid in stale_ids:
            del self.tracks[tid]
            if tid in self.position_history:
                del self.position_history[tid]
            if tid in self.face_size_history:
                del self.face_size_history[tid]
    
    def get_active_count(self):
        """Get number of currently tracked faces"""
        return len(self.tracks)


class AntiSpoofDetector:
    """
    Enhanced anti-spoofing detection.
    Detects photo/video attacks by checking for:
    - Natural face motion (not static)
    - Depth variation (face size changes)
    - Blinking (eyes open/close)
    """
    def __init__(self):
        self.motion_history = defaultdict(lambda: deque(maxlen=30))
        self.last_frames = {}
    
    def reset(self):
        """Reset for new session"""
        self.motion_history = defaultdict(lambda: deque(maxlen=30))
        self.last_frames = {}
        
    def check_motion(self, track_id, face_roi):
        """
        Detect natural face motion by comparing consecutive frames.
        Returns variance of motion - higher = more natural movement.
        """
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
        
        # Natural motion has varying scores
        if len(self.motion_history[track_id]) >= 10:
            variance = np.var(list(self.motion_history[track_id]))
            return variance
        return 0
    
    def check_depth(self, track_id, face_size, tracker):
        """
        Check for natural depth variations.
        Real faces have slight size changes as person moves.
        """
        history = tracker.face_size_history[track_id]
        history.append(face_size)
        
        if len(history) >= 5:
            size_variance = np.var(list(history))
            return size_variance > 5  # Threshold for natural movement
        return False


# ==================== ATTENDANCE RECORD CLASS ====================

class AttendanceRecord:
    """
    Stores attendance information for a session.
    Tracks status (present/late/absent) and timestamps.
    """
    def __init__(self, session_start_time):
        self.session_start_time = session_start_time
        self.records = {}  # name -> {status, timestamp, student_id, etc.}
        self.late_threshold = timedelta(minutes=LATE_THRESHOLD_MINUTES)
    
    def mark_student(self, name, student_id, facial_data_id, confidence, distance):
        """
        Mark a student's attendance with appropriate status.
        Returns: status ('present' or 'late'), is_new_entry
        """
        if name in self.records:
            return self.records[name]['status'], False
        
        now = datetime.now()
        arrival_time = now.time()
        
        # Determine if late
        session_start_dt = datetime.combine(now.date(), self.session_start_time)
        late_cutoff = session_start_dt + self.late_threshold
        
        if now > late_cutoff:
            status = 'late'
        else:
            status = 'present'
        
        self.records[name] = {
            'status': status,
            'arrival_time': arrival_time,
            'arrival_datetime': now,
            'student_id': student_id,
            'facial_data_id': facial_data_id,
            'confidence': confidence,
            'distance': distance
        }
        
        return status, True
    
    def get_present_count(self):
        """Get count of students marked present (on time)"""
        return sum(1 for r in self.records.values() if r['status'] == 'present')
    
    def get_late_count(self):
        """Get count of students marked late"""
        return sum(1 for r in self.records.values() if r['status'] == 'late')
    
    def get_total_count(self):
        """Get total students who attended"""
        return len(self.records)
    
    def get_attendance_list(self):
        """Get sorted list of attendance records"""
        sorted_records = sorted(
            self.records.items(),
            key=lambda x: x[1]['arrival_datetime']
        )
        return sorted_records
    
    def get_display_list(self, max_items=10):
        """Get formatted list for display"""
        records = self.get_attendance_list()
        display = []
        for name, data in records[:max_items]:
            time_str = data['arrival_time'].strftime("%H:%M:%S")
            status_icon = "✓" if data['status'] == 'present' else "⏰"
            display.append(f"{status_icon} {name} ({time_str})")
        return display


# ==================== API FUNCTIONS ====================

def check_server_connection():
    """Check if API server is reachable"""
    try:
        response = requests.get(f"{API_URL}/api/health", timeout=3)
        return response.status_code == 200
    except:
        return False


def get_todays_sessions():
    """Get all sessions for today"""
    try:
        response = requests.get(f"{API_URL}/api/sessions", timeout=5)
        data = response.json()
        
        if data.get('success') and data.get('sessions'):
            return data['sessions']
        return []
    except Exception as e:
        print(f"⚠️ Could not load sessions: {e}")
        return []


def parse_time(time_str):
    """Parse time string to time object"""
    try:
        # Handle various formats
        time_str = str(time_str).strip()
        if len(time_str) > 8:
            time_str = time_str[:8]
        return datetime.strptime(time_str, "%H:%M:%S").time()
    except:
        try:
            return datetime.strptime(time_str, "%H:%M").time()
        except:
            return None


def get_current_or_upcoming_session():
    """Find session that should be active now or starting soon"""
    sessions = get_todays_sessions()
    
    if not sessions:
        return None
    
    now = datetime.now()
    current_time = now.time()
    
    for session in sessions:
        start_time = parse_time(session['start_time'])
        end_time = parse_time(session['end_time'])
        
        if not start_time or not end_time:
            continue
        
        # Calculate session window
        start_datetime = datetime.combine(now.date(), start_time)
        window_start = (start_datetime - timedelta(minutes=MINUTES_BEFORE_START)).time()
        
        end_datetime = datetime.combine(now.date(), end_time)
        window_end = (end_datetime + timedelta(minutes=MINUTES_AFTER_END)).time()
        
        # Check if current time is within the session window
        if window_start <= current_time <= window_end:
            session['parsed_start'] = start_time
            session['parsed_end'] = end_time
            session['window_start'] = window_start
            session['window_end'] = window_end
            return session
    
    return None


def get_next_session_info():
    """Get info about the next upcoming session"""
    sessions = get_todays_sessions()
    
    if not sessions:
        return None, None
    
    now = datetime.now()
    current_time = now.time()
    
    for session in sessions:
        start_time = parse_time(session['start_time'])
        if not start_time:
            continue
        
        start_datetime = datetime.combine(now.date(), start_time)
        window_start = (start_datetime - timedelta(minutes=MINUTES_BEFORE_START)).time()
        
        if current_time < window_start:
            window_start_dt = datetime.combine(now.date(), window_start)
            time_until = window_start_dt - now
            return session, time_until
    
    return None, None


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
                mapping[student['name']] = {
                    'student_id': student['student_id'],
                    'facial_data_id': student['facial_data_id']
                }
            return mapping
        return {}
    except:
        return {}


def get_enrolled_students(session_id):
    """Get list of students enrolled in the course for this session"""
    # This would need a new API endpoint to get enrolled students
    # For now, return all students
    return get_student_mapping()


def mark_attendance_api(student_name, student_id, facial_data_id, session_id,
                        status, arrival_time, confidence, distance):
    """Mark student attendance via API with status and timestamp"""
    try:
        response = requests.post(
            f"{API_URL}/api/attendance/mark",
            json={
                'student_id': student_id,
                'session_id': session_id,
                'status': status,  # 'present', 'late', or 'absent'
                'recognition_data': {
                    'facial_data_id': facial_data_id,
                    'confidence': float(confidence),
                    'distance': float(distance),
                    'name': student_name,
                    'arrival_time': arrival_time.strftime("%H:%M:%S") if arrival_time else None,
                    'model_version': 'v3.0-auto-complete'
                }
            },
            timeout=3
        )
        
        data = response.json()
        return data.get('success', False) and not data.get('already_present', False)
    except Exception as e:
        print(f"⚠️ API error: {e}")
        return False


def mark_absent_students(session_id, present_students, all_students):
    """Mark all students who didn't attend as absent"""
    absent_count = 0
    for name, info in all_students.items():
        if name not in present_students:
            try:
                requests.post(
                    f"{API_URL}/api/attendance/mark",
                    json={
                        'student_id': info['student_id'],
                        'session_id': session_id,
                        'status': 'absent',
                        'recognition_data': {
                            'name': name,
                            'model_version': 'v3.0-auto-complete'
                        }
                    },
                    timeout=2
                )
                absent_count += 1
            except:
                pass
    return absent_count


# ==================== MAIN ATTENDANCE SYSTEM ====================

class AutomaticAttendanceSystem:
    """
    Main attendance system class.
    Handles camera, face detection, recognition, and attendance tracking.
    """
    
    def __init__(self):
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
        self.spoof_attempts = 0
        self.total_detections = 0
        self.imgBackground = None
        self.n_neighbors = 5
        
    def initialize(self):
        """Initialize the system components"""
        print("\n🔧 Initializing system components...")
        
        # Load face detection cascades
        self.facedetect = cv2.CascadeClassifier('data/haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        
        if self.facedetect.empty():
            print("❌ Error: haarcascade_frontalface_default.xml not found!")
            print("   Please ensure 'data/haarcascade_frontalface_default.xml' exists")
            return False
        
        # Load background image (optional)
        self.imgBackground = cv2.imread("background.png")
        if self.imgBackground is None:
            print("ℹ️ background.png not found - using plain background")
        else:
            print("✅ Background image loaded")
        
        print("✅ System components initialized")
        return True
    
    def load_model(self):
        """Load and train the KNN model"""
        print("📥 Loading training data from database...")
        faces, labels = load_training_data()
        
        if faces is None or labels is None:
            print("❌ No training data available!")
            return False
        
        # Train KNN classifier
        n_samples = faces.shape[0]
        self.n_neighbors = min(5, n_samples)
        
        self.knn = KNeighborsClassifier(n_neighbors=self.n_neighbors)
        self.knn.fit(faces, labels)
        
        # Load student mapping
        self.student_map = get_student_mapping()
        
        print(f"✅ Model trained: {n_samples} samples, {len(self.student_map)} students")
        return True
    
    def start_camera(self):
        """Start the camera"""
        if self.video is not None and self.video.isOpened():
            return True
        
        print(f"🎥 Opening camera {CAMERA_INDEX}...")
        self.video = cv2.VideoCapture(CAMERA_INDEX)
        
        if not self.video.isOpened():
            print("❌ Cannot open camera!")
            return False
        
        # Set camera properties for better quality
        self.video.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.video.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        print("✅ Camera ready")
        return True
    
    def stop_camera(self):
        """Stop the camera"""
        if self.video is not None:
            self.video.release()
            self.video = None
            print("📷 Camera stopped")
    
    def reset_session_data(self, session_start_time):
        """Reset all data for a new session"""
        self.attendance = AttendanceRecord(session_start_time)
        self.tracker.reset()
        self.anti_spoof.reset()
        self.spoof_attempts = 0
        self.total_detections = 0
    
    def process_face(self, frame, gray, x, y, w, h, frame_count):
        """
        Process a detected face.
        Returns: (name, status, is_new, is_verified, is_spoof)
        """
        track_id = self.tracker.get_track_id(x, y, w, h)
        track_data = self.tracker.tracks[track_id]
        
        # Extract face region
        crop_img = frame[y:y+h, x:x+w]
        if crop_img.size == 0:
            return None, None, False, False, False
        
        # For mask support - use upper face region (eyes, forehead)
        if USE_UPPER_FACE_ONLY:
            upper_h = int(h * 0.6)  # Top 60% of face
            crop_for_recognition = crop_img[0:upper_h, :]
        else:
            crop_for_recognition = crop_img
        
        # Resize and flatten for KNN
        try:
            resized = cv2.resize(crop_for_recognition, (50, 50)).flatten().reshape(1, -1)
        except:
            return None, None, False, False, False
        
        # Predict identity
        output = self.knn.predict(resized)[0]
        proba = self.knn.predict_proba(resized)
        confidence = np.max(proba)
        
        # Get distance metric
        distances, _ = self.knn.kneighbors(resized, n_neighbors=self.n_neighbors)
        avg_distance = np.mean(distances[0])
        
        # === ANTI-SPOOFING CHECKS ===
        face_gray_roi = gray[y:y+h, x:x+w]
        
        # 1. Motion check - face should have natural micro-movements
        motion_score = self.anti_spoof.check_motion(track_id, face_gray_roi)
        
        # 2. Depth check - face size should vary slightly as person moves
        has_depth = self.anti_spoof.check_depth(track_id, w * h, self.tracker)
        
        # 3. Blink detection - real faces blink
        eyes = self.eye_cascade.detectMultiScale(face_gray_roi, 1.1, 3)
        
        if len(eyes) > 0:
            track_data['eye_open_count'] += 1
        elif track_data['eye_open_count'] > 0:
            # Eyes were open, now closed = blink detected
            track_data['blink_count'] += 1
        
        # === TEMPORAL SMOOTHING ===
        # Require consistent identification across multiple frames
        if track_data['name'] == output:
            track_data['count'] += 1
        else:
            track_data['name'] = output
            track_data['count'] = 1
            track_data['confirmed'] = False
        
        if track_data['count'] >= FRAME_CONFIRMATION:
            track_data['confirmed'] = True
        
        # === VERIFICATION DECISION ===
        is_verified = (
            track_data['confirmed'] and
            track_data['blink_count'] >= BLINK_REQUIRED and
            track_data['eye_open_count'] >= EYE_OPEN_FRAMES and
            confidence >= CONFIDENCE_THRESHOLD and
            avg_distance <= MIN_MATCH_DISTANCE and
            motion_score > MOTION_THRESHOLD
        )
        
        # === SPOOF DETECTION ===
        is_spoof = (
            motion_score < 5 or  # Too static - likely a photo
            (not has_depth and frame_count > 30) or  # No depth variation
            (track_data['blink_count'] == 0 and track_data['count'] > 20)  # No blinks after 20 frames
        )
        
        if is_spoof and track_data['count'] > 10:
            track_data['spoof_alerts'] += 1
            self.spoof_attempts += 1
        
        # === MARK ATTENDANCE ===
        name = str(output)
        status = None
        is_new = False
        
        if is_verified and not is_spoof and not track_data['marked']:
            student_info = self.student_map.get(name, {})
            student_id = student_info.get('student_id')
            facial_data_id = student_info.get('facial_data_id')
            
            if student_id:
                status, is_new = self.attendance.mark_student(
                    name, student_id, facial_data_id, confidence, avg_distance
                )
                
                if is_new:
                    track_data['marked'] = True
                    arrival_time = self.attendance.records[name]['arrival_time']
                    
                    # Send to API
                    mark_attendance_api(
                        name, student_id, facial_data_id,
                        self.current_session['session_id'],
                        status, arrival_time, confidence, avg_distance
                    )
        
        return name, status, is_new, is_verified, is_spoof, confidence, avg_distance, track_data
    
    def draw_face_box(self, frame, x, y, w, h, name, status, is_verified, is_spoof, 
                      confidence, avg_distance, track_data):
        """Draw bounding box and info for a face"""
        
        if is_verified and not is_spoof:
            # GREEN - Verified and marked
            color = (0, 255, 0)
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 3)
            
            # Name banner
            banner_color = (0, 200, 0) if status == 'present' else (0, 165, 255)  # Orange for late
            cv2.rectangle(frame, (x, y-45), (x+w, y), banner_color, -1)
            
            # Name and status
            status_text = "LATE" if status == 'late' else ""
            cv2.putText(frame, name, (x+5, y-25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
            if status_text:
                cv2.putText(frame, status_text, (x+5, y-8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255,255,255), 1)
        
        elif is_spoof:
            # RED - Spoof detected
            color = (0, 0, 255)
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 3)
            cv2.rectangle(frame, (x, y-30), (x+w, y), color, -1)
            cv2.putText(frame, "SPOOF DETECTED", (x+5, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 2)
        
        else:
            # YELLOW - Verifying
            color = (0, 255, 255)
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            
            # Show progress
            status_parts = []
            if not track_data['confirmed']:
                status_parts.append(f"Hold:{track_data['count']}/{FRAME_CONFIRMATION}")
            if track_data['blink_count'] < BLINK_REQUIRED:
                status_parts.append(f"Blink:{track_data['blink_count']}/{BLINK_REQUIRED}")
            
            if status_parts:
                cv2.putText(frame, " ".join(status_parts), (x, y-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)
        
        # Confidence info below face
        cv2.putText(frame, f"Conf:{confidence:.2f} Dist:{avg_distance:.0f}", 
                   (x, y+h+15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255,255,255), 1)
    
    def draw_ui_panel(self, frame, session):
        """Draw the information panel on the frame (for camera feed only, not background)"""
        # This panel is drawn on the camera feed
        # When using background, we'll draw on the background instead
        panel_h = 280
        panel_w = 350
        
        if frame.shape[0] < panel_h or frame.shape[1] < panel_w:
            return
        
        # Semi-transparent background
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (panel_w, panel_h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        cv2.rectangle(frame, (10, 10), (panel_w, panel_h), (100, 100, 100), 2)
        
        y_pos = 35
        line_height = 22
        
        # Title
        cv2.putText(frame, "AUTO ATTENDANCE SYSTEM", (20, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        y_pos += line_height + 5
        
        # Session info
        cv2.putText(frame, f"Session: #{session['session_id']}", (20, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1)
        y_pos += line_height
        
        cv2.putText(frame, f"Course: {session.get('course_code', 'N/A')}", (20, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        y_pos += line_height
        
        cv2.putText(frame, f"Time: {session['start_time']} - {session['end_time']}", (20, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        y_pos += line_height + 5
        
        # Attendance stats
        present = self.attendance.get_present_count()
        late = self.attendance.get_late_count()
        total = self.attendance.get_total_count()
        
        cv2.putText(frame, f"Present: {present}", (20, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        cv2.putText(frame, f"Late: {late}", (150, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)
        y_pos += line_height
        
        cv2.putText(frame, f"Total: {total}", (20, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"Spoofs: {self.spoof_attempts}", (150, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        y_pos += line_height + 5
        
        # Recent attendance
        cv2.putText(frame, "Recent:", (20, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        y_pos += line_height - 5
        
        display_list = self.attendance.get_display_list(MAX_DISPLAY_NAMES)
        for item in display_list[-5:]:  # Show last 5
            cv2.putText(frame, item[:35], (25, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)
            y_pos += 15
        
        # Current time
        current_time_str = datetime.now().strftime("%H:%M:%S")
        cv2.putText(frame, f"Time: {current_time_str}", (20, panel_h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
        
        # Late threshold indicator
        late_cutoff = datetime.combine(
            datetime.now().date(), 
            session['parsed_start']
        ) + timedelta(minutes=LATE_THRESHOLD_MINUTES)
        
        if datetime.now() < late_cutoff:
            remaining = late_cutoff - datetime.now()
            mins = int(remaining.total_seconds() // 60)
            secs = int(remaining.total_seconds() % 60)
            cv2.putText(frame, f"On-time: {mins}m {secs}s left", (150, panel_h - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        else:
            cv2.putText(frame, "Late period active", (150, panel_h - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 165, 255), 1)
    
    def run_attendance_session(self, session):
        """Run attendance for a specific session"""
        self.current_session = session
        session_id = session['session_id']
        
        print("\n" + "=" * 70)
        print(f"🎯 STARTING ATTENDANCE SESSION")
        print("=" * 70)
        print(f"   Session ID:  #{session_id}")
        print(f"   Course:      {session.get('course_code', 'N/A')} - {session.get('course_name', 'N/A')}")
        print(f"   Lecturer:    {session.get('lecturer_name', 'N/A')}")
        print(f"   Venue:       {session.get('venue_name', 'N/A')}")
        print(f"   Time:        {session['start_time']} - {session['end_time']}")
        print(f"   Late after:  {LATE_THRESHOLD_MINUTES} minutes")
        print("=" * 70)
        print("\n⌨️ Controls: 'q'=Quit, 'l'=List, 's'=Summary")
        print("")
        
        # Initialize for this session
        self.reset_session_data(session['parsed_start'])
        
        if not self.start_camera():
            return
        
        if not self.load_model():
            self.stop_camera()
            return
        
        self.running = True
        frame_count = 0
        
        try:
            while self.running:
                # Check if session window has ended
                now = datetime.now().time()
                if now > session['window_end']:
                    print(f"\n⏰ Session window ended")
                    break
                
                ret, frame = self.video.read()
                if not ret:
                    print("❌ Failed to read frame")
                    break
                
                frame_count += 1
                display_frame = frame.copy()
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Detect all faces in frame (multi-person)
                faces = self.facedetect.detectMultiScale(gray, 1.2, 5, minSize=(80, 80))
                self.total_detections += len(faces)
                
                # Cleanup old tracks
                self.tracker.cleanup_stale_tracks()
                
                # Process each detected face
                for (x, y, w, h) in faces:
                    result = self.process_face(frame, gray, x, y, w, h, frame_count)
                    
                    if result[0] is None:
                        continue
                    
                    name, status, is_new, is_verified, is_spoof, confidence, avg_distance, track_data = result
                    
                    # Print new attendance
                    if is_new:
                        arrival_time = self.attendance.records[name]['arrival_time'].strftime("%H:%M:%S")
                        if status == 'late':
                            print(f"⏰ {name} marked LATE (arrived {arrival_time})")
                        else:
                            print(f"✅ {name} marked PRESENT (arrived {arrival_time})")
                    
                    # Draw face box
                    self.draw_face_box(
                        display_frame, x, y, w, h, name, status,
                        is_verified, is_spoof, confidence, avg_distance, track_data
                    )
                
                # Draw UI panel only if NO background (otherwise it's on the right side)
                if self.imgBackground is None:
                    self.draw_ui_panel(display_frame, session)
                
                # Apply background if available
                if self.imgBackground is not None:
                    try:
                        bg_copy = self.imgBackground.copy()
                        
                        # Camera feed position (left side)
                        x_offset, y_offset = 55, 162
                        feed_w, feed_h = 640, 480
                        resized_feed = cv2.resize(display_frame, (feed_w, feed_h))
                        
                        if (y_offset + feed_h <= bg_copy.shape[0] and 
                            x_offset + feed_w <= bg_copy.shape[1]):
                            bg_copy[y_offset:y_offset+feed_h, x_offset:x_offset+feed_w] = resized_feed
                        
                        # Draw info INSIDE the red smiley face box (no black background)
                        # Adjust these coordinates to fit inside your red box
                        panel_x = 870   # X position inside the red box
                        panel_y = 220   # Y position inside the red box
                        
                        y_pos = panel_y
                        line_height = 32
                        
                        # Session info
                        cv2.putText(bg_copy, f"Session: #{session['session_id']}", (panel_x, y_pos),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
                        y_pos += line_height
                        
                        cv2.putText(bg_copy, f"Course: {session.get('course_code', 'N/A')}", (panel_x, y_pos),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
                        y_pos += line_height
                        
                        cv2.putText(bg_copy, f"Time: {session['start_time'][:5]} - {session['end_time'][:5]}", (panel_x, y_pos),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
                        y_pos += line_height + 20
                        
                        # Attendance stats
                        present = self.attendance.get_present_count()
                        late = self.attendance.get_late_count()
                        total = self.attendance.get_total_count()
                        
                        cv2.putText(bg_copy, f"Present: {present}", (panel_x, y_pos),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 150, 0), 2)
                        y_pos += line_height
                        
                        cv2.putText(bg_copy, f"Late: {late}", (panel_x, y_pos),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 100, 255), 2)
                        y_pos += line_height
                        
                        cv2.putText(bg_copy, f"Total: {total}", (panel_x, y_pos),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
                        y_pos += line_height
                        
                        cv2.putText(bg_copy, f"Spoofs: {self.spoof_attempts}", (panel_x, y_pos),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 200), 2)
                        y_pos += line_height + 20
                        
                        # Recent attendance
                        cv2.putText(bg_copy, "Recent:", (panel_x, y_pos),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 80, 80), 2)
                        y_pos += line_height - 5
                        
                        display_list = self.attendance.get_display_list(10)
                        for item in display_list[-5:]:  # Show last 5
                            cv2.putText(bg_copy, item[:30], (panel_x, y_pos),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (50, 50, 50), 1)
                            y_pos += 24
                        
                        # Current time at bottom
                        current_time_str = datetime.now().strftime("%H:%M:%S")
                        cv2.putText(bg_copy, f"Time: {current_time_str}", (panel_x, y_pos + 20),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 2)
                        
                        # Late threshold indicator
                        late_cutoff = datetime.combine(
                            datetime.now().date(), 
                            session['parsed_start']
                        ) + timedelta(minutes=LATE_THRESHOLD_MINUTES)
                        
                        if datetime.now() < late_cutoff:
                            remaining = late_cutoff - datetime.now()
                            mins = int(remaining.total_seconds() // 60)
                            secs = int(remaining.total_seconds() % 60)
                            cv2.putText(bg_copy, f"On-time: {mins}m {secs}s left", (panel_x, y_pos + 50),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 150, 0), 2)
                        else:
                            cv2.putText(bg_copy, "Late period active", (panel_x, y_pos + 50),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 100, 255), 2)
                        
                        final_frame = bg_copy
                    except Exception as e:
                        print(f"Background error: {e}")
                        final_frame = display_frame
                else:
                    final_frame = display_frame
                
                cv2.imshow("Automatic Attendance System", final_frame)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\n👋 Manual quit requested")
                    self.running = False
                    break
                elif key == ord('l'):
                    self.print_attendance_list()
                elif key == ord('s'):
                    self.print_session_summary(final=False)
        
        except KeyboardInterrupt:
            print("\n⚠️ Interrupted by user")
        
        finally:
            # Mark absent students
            print("\n📝 Marking absent students...")
            absent_count = mark_absent_students(
                session_id,
                set(self.attendance.records.keys()),
                self.student_map
            )
            print(f"   Marked {absent_count} students as absent")
            
            # Final summary
            self.print_session_summary(final=True)
            self.stop_camera()
            cv2.destroyAllWindows()
    
    def print_attendance_list(self):
        """Print detailed attendance list"""
        print("\n" + "=" * 60)
        print(f"📋 ATTENDANCE LIST")
        print("=" * 60)
        
        records = self.attendance.get_attendance_list()
        
        if not records:
            print("   No students marked yet")
        else:
            print(f"{'Name':<25} {'Status':<10} {'Time':<12}")
            print("-" * 50)
            
            for name, data in records:
                time_str = data['arrival_time'].strftime("%H:%M:%S")
                status = data['status'].upper()
                status_icon = "✓" if data['status'] == 'present' else "⏰"
                print(f"{status_icon} {name:<23} {status:<10} {time_str:<12}")
        
        print("=" * 60 + "\n")
    
    def print_session_summary(self, final=True):
        """Print session summary"""
        title = "FINAL SESSION SUMMARY" if final else "CURRENT SESSION STATUS"
        
        print("\n" + "=" * 60)
        print(f"📊 {title}")
        print("=" * 60)
        
        if self.current_session:
            print(f"   Session:     #{self.current_session['session_id']}")
            print(f"   Course:      {self.current_session.get('course_code', 'N/A')}")
        
        print(f"\n   📈 Attendance Statistics:")
        print(f"      Present (on-time): {self.attendance.get_present_count()}")
        print(f"      Late:              {self.attendance.get_late_count()}")
        print(f"      Total Attended:    {self.attendance.get_total_count()}")
        print(f"      Absent:            {len(self.student_map) - self.attendance.get_total_count()}")
        
        print(f"\n   🔒 Security Statistics:")
        print(f"      Spoof Attempts:    {self.spoof_attempts}")
        print(f"      Total Detections:  {self.total_detections}")
        
        if final and self.attendance.get_total_count() > 0:
            print(f"\n   📋 Final Attendance List:")
            for name, data in self.attendance.get_attendance_list():
                time_str = data['arrival_time'].strftime("%H:%M:%S")
                status = "LATE" if data['status'] == 'late' else "ON-TIME"
                icon = "⏰" if data['status'] == 'late' else "✓"
                print(f"      {icon} {name} - {status} ({time_str})")
        
        print("=" * 60)


# ==================== MAIN SCHEDULER ====================

def main():
    """Main function - runs the automatic scheduler"""
    
    print("\n🔍 Checking server connection...")
    if not check_server_connection():
        print("❌ Cannot connect to API server!")
        print(f"   Make sure the server is running at {API_URL}")
        print(f"   Run: python api_server.py")
        return
    print("✅ Server connected")
    
    # Initialize the attendance system
    system = AutomaticAttendanceSystem()
    if not system.initialize():
        return
    
    print("\n" + "=" * 70)
    print("🤖 AUTOMATIC MODE ACTIVE")
    print("=" * 70)
    print("The system will automatically:")
    print(f"  • Start {MINUTES_BEFORE_START} minutes before each session")
    print(f"  • Mark students as LATE after {LATE_THRESHOLD_MINUTES} minutes")
    print(f"  • Mark remaining students as ABSENT when session ends")
    print(f"  • Stop {MINUTES_AFTER_END} minutes after session ends")
    print(f"  • Check for sessions every {CHECK_INTERVAL} seconds")
    print("\nPress Ctrl+C to stop the system")
    print("=" * 70)
    
    last_session_id = None
    
    try:
        while True:
            # Check for current or upcoming session
            session = get_current_or_upcoming_session()
            
            if session:
                session_id = session['session_id']
                
                # Don't re-run the same session
                if session_id != last_session_id:
                    print(f"\n🎯 Session #{session_id} is ready!")
                    system.run_attendance_session(session)
                    last_session_id = session_id
                    print("\n⏳ Session complete. Waiting for next session...")
            else:
                # Show countdown to next session
                next_session, time_until = get_next_session_info()
                
                if next_session:
                    minutes = int(time_until.total_seconds() // 60)
                    seconds = int(time_until.total_seconds() % 60)
                    print(f"\r⏳ Next: Session #{next_session['session_id']} "
                          f"({next_session.get('course_code', 'N/A')}) "
                          f"in {minutes}m {seconds}s    ", end="", flush=True)
                else:
                    current_time = datetime.now().strftime("%H:%M:%S")
                    print(f"\r⏳ [{current_time}] No more sessions today. Waiting...    ", end="", flush=True)
            
            time.sleep(CHECK_INTERVAL)
    
    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("👋 System stopped by user")
        print("=" * 70)
        print("Goodbye!")


if __name__ == "__main__":
    main()