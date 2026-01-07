from sklearn.neighbors import KNeighborsClassifier
import cv2
import pickle
import numpy as np
import os
import csv
import time
from datetime import datetime
import pandas as pd

# ------------------ LOAD VIDEO + FACE CASCADE ------------------
video = cv2.VideoCapture(0)
facedetect = cv2.CascadeClassifier('data/haarcascade_frontalface_default.xml')

# Load eye cascade for masked face detection
eyedetect = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

# ------------------ LOAD TRAINED DATA ------------------
with open('data/names.pkl', 'rb') as w:
    LABELS = pickle.load(w)

with open('data/faces_data.pkl', 'rb') as f:
    FACES = pickle.load(f)

print("Faces shape:", FACES.shape)

# ------------------ TRAIN KNN MODEL ------------------
# Adjust n_neighbors based on available samples
n_samples = FACES.shape[0]
n_neighbors = min(5, n_samples)  # Use 5 or less if not enough samples

print(f"Training KNN with {n_samples} samples and {n_neighbors} neighbors")

knn = KNeighborsClassifier(n_neighbors=n_neighbors)
knn.fit(FACES, LABELS)

# ------------------ SPOOF/UNKNOWN DETECTION THRESHOLD ------------------
CONFIDENCE_THRESHOLD = 0.3  # Lowered for limited training data
MIN_MATCH_DISTANCE = 5000  # Increased for limited training data (more lenient)

# ------------------ LOAD BACKGROUND ------------------
imgBackground = cv2.imread("background.png")
if imgBackground is None:
    raise FileNotFoundError("background.png not found. Place it beside test.py")

COL_NAMES = ['NAME', 'TIME']

# Track who has already taken attendance today
taken_today = set()

# Track who has been logged (to avoid repeated console messages)
logged_users = set()
logged_spoofs = set()

# Get today's date once
current_date = datetime.now().strftime("%d-%m-%Y")
csv_path = f"Attendance/Attendance_{current_date}.csv"

# Create Attendance directory if it doesn't exist
os.makedirs("Attendance", exist_ok=True)

# ------------------ HELPER FUNCTION FOR MASKED FACE DETECTION ------------------
def detect_masked_face(frame, gray):
    """
    Detect faces with masks by looking for eye pairs
    Returns list of face regions (x, y, w, h)
    """
    # Try multiple detection parameters for better results
    eyes = eyedetect.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3, minSize=(15, 15), maxSize=(100, 100))
    
    if len(eyes) < 2:
        # Try again with even more lenient parameters
        eyes = eyedetect.detectMultiScale(gray, scaleFactor=1.03, minNeighbors=2, minSize=(10, 10), maxSize=(120, 120))
    
    if len(eyes) < 2:
        return []
    
    masked_faces = []
    used_eyes = set()
    
    # Group eyes into pairs (left and right eye)
    for i, (ex1, ey1, ew1, eh1) in enumerate(eyes):
        if i in used_eyes:
            continue
            
        for j, (ex2, ey2, ew2, eh2) in enumerate(eyes):
            if i >= j or j in used_eyes:
                continue
            
            # Check if two eyes are at similar height (same face)
            vertical_distance = abs(ey1 - ey2)
            horizontal_distance = abs(ex1 - ex2)
            
            # Eyes should be horizontally aligned and spaced appropriately (very relaxed)
            if vertical_distance < 60 and 25 < horizontal_distance < 300:
                # Found a pair of eyes, estimate face region
                left_eye_x = min(ex1, ex2)
                right_eye_x = max(ex1 + ew1, ex2 + ew2)
                eye_y = min(ey1, ey2)
                
                # Calculate face boundaries
                eye_center_y = (ey1 + ey2) // 2
                face_width = int((right_eye_x - left_eye_x) * 2.2)
                face_height = int(face_width * 1.5)
                
                face_x = max(0, left_eye_x - int(face_width * 0.25))
                face_y = max(0, eye_center_y - int(face_height * 0.3))
                
                masked_faces.append((face_x, face_y, face_width, face_height))
                used_eyes.add(i)
                used_eyes.add(j)
                break
    
    return masked_faces

# ------------------ MAIN LOOP ------------------
while True:
    ret, frame = video.read()
    if not ret:
        print("Failed to grab frame")
        break
        
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Detect normal faces (without mask)
    faces = facedetect.detectMultiScale(gray, 1.3, 5)
    
    all_faces = []
    face_types = []
    
    # Add normal faces
    for face in faces:
        all_faces.append(face)
        face_types.append("normal")
    
    # Only use masked face detection if NO normal faces were detected
    if len(faces) == 0:
        # Detect masked faces (using eye detection)
        masked_faces = detect_masked_face(frame, gray)
        
        for masked_face in masked_faces:
            all_faces.append(masked_face)
            face_types.append("masked")
    
    # If still no faces detected, skip this frame
    if len(all_faces) == 0:
        imgBackground[162:162 + 480, 55:55 + 640] = frame
        cv2.putText(imgBackground, f"Attendance Today: {len(taken_today)}", 
                    (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(imgBackground, "Red: No Mask | Orange: Mask | Yellow Dash: Unknown/Spoof", 
                    (50, 700), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.imshow("Attendance System", imgBackground)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        continue

    # Process all detected faces
    for i, (x, y, w, h) in enumerate(all_faces):
        face_type = face_types[i]
        
        # Adjust crop region for masked faces (focus on eye region)
        if face_type == "masked":
            # For masked faces, use full face region (not just upper portion)
            # This works better with limited training data
            crop_img = frame[y:y+h, x:x+w, :]
        else:
            # Normal face detection
            crop_img = frame[y:y+h, x:x+w, :]
        
        # Ensure valid crop
        if crop_img.size == 0:
            continue
            
        resized_img = cv2.resize(crop_img, (50, 50)).flatten().reshape(1, -1)
        
        # Get prediction with probability
        output = knn.predict(resized_img)
        proba = knn.predict_proba(resized_img)
        confidence = np.max(proba)
        
        # Calculate distance to nearest neighbor for additional verification
        distances, indices = knn.kneighbors(resized_img, n_neighbors=n_neighbors)
        avg_distance = np.mean(distances[0])
        
        # Check if this is a known person or unknown/spoof
        # Must pass BOTH confidence and distance checks
        if confidence >= CONFIDENCE_THRESHOLD and avg_distance <= MIN_MATCH_DISTANCE:
            # Known person
            name = str(output[0])
            is_spoof = False
            # Only log once per person per session
            if name not in logged_users:
                print(f"✅ Accepted - {name} | Confidence: {confidence:.2f}, Distance: {avg_distance:.2f}")
                logged_users.add(name)
        else:
            # Unknown person or spoof
            name = "UNKNOWN"
            is_spoof = True
            # Only log spoof detection once every 5 seconds to avoid spam
            current_time = time.time()
            if current_time not in logged_spoofs or current_time - max(logged_spoofs, default=0) > 5:
                print(f"🚫 Rejected - Confidence: {confidence:.2f}, Distance: {avg_distance:.2f}")
                logged_spoofs.add(current_time)
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Draw box around face with different colors based on detection type
        if is_spoof:
            # SPOOF/UNKNOWN - Yellow dashed outline
            box_color = (0, 255, 255)  # Yellow
            # Draw dashed rectangle for spoof
            dash_length = 10
            for i in range(0, w, dash_length * 2):
                cv2.line(frame, (x + i, y), (x + min(i + dash_length, w), y), box_color, 3)
                cv2.line(frame, (x + i, y + h), (x + min(i + dash_length, w), y + h), box_color, 3)
            for i in range(0, h, dash_length * 2):
                cv2.line(frame, (x, y + i), (x, y + min(i + dash_length, h)), box_color, 3)
                cv2.line(frame, (x + w, y + i), (x + w, y + min(i + dash_length, h)), box_color, 3)
            
            # Warning background
            cv2.rectangle(frame, (x, y - 40), (x + w, y), box_color, -1)
            cv2.putText(frame, "UNKNOWN/SPOOF", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
            cv2.putText(frame, "ACCESS DENIED", (x, y + h + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            
        else:
            # Known person - solid outline
            box_color = (50, 50, 255) if face_type == "normal" else (255, 100, 0)  # Red for normal, Orange for masked
            cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, 2)
            cv2.rectangle(frame, (x, y - 40), (x + w, y), box_color, -1)
            
            # Display name and mask status
            display_text = f"{name} {'(Mask)' if face_type == 'masked' else ''}"
            cv2.putText(frame, display_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            # Show attendance status
            if name in taken_today:
                cv2.putText(frame, "Already Marked", (x, y + h + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            else:
                cv2.putText(frame, "New Detection", (x, y + h + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

        # ------------- AUTO ATTENDANCE & NO DOUBLE ENTRY -------------
        # Only record attendance for known persons, not spoofs
        if not is_spoof and name not in taken_today:
            taken_today.add(name)

            mask_status = "with mask" if face_type == "masked" else "without mask"
            print(f"Attendance recorded for {name} ({mask_status}) at {timestamp}")

            # Write CSV
            file_exists = os.path.isfile(csv_path)
            with open(csv_path, "a", newline="") as csvfile:
                writer = csv.writer(csvfile)

                # If file didn't exist → write header first
                if not file_exists:
                    writer.writerow(COL_NAMES)

                writer.writerow([name, timestamp])
        elif is_spoof:
            # Only log warning once every 5 seconds to avoid spam
            current_time = time.time()
            if current_time not in logged_spoofs or current_time - max(logged_spoofs, default=0) > 5:
                print(f"⚠️ Unknown/Spoof face detected at {timestamp} - Access denied")

    # Insert camera into your background.png
    imgBackground[162:162 + 480, 55:55 + 640] = frame

    # Display attendance count and legend
    cv2.putText(imgBackground, f"Attendance Today: {len(taken_today)}", 
                (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # Legend
    cv2.putText(imgBackground, "Red: No Mask | Orange: Mask | Yellow Dash: Unknown/Spoof", 
                (50, 700), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

    cv2.imshow("Attendance System", imgBackground)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

video.release()
cv2.destroyAllWindows()

# Print final summary
print(f"\n{'='*50}")
print(f"Attendance Summary for {current_date}")
print(f"{'='*50}")
print(f"Total people marked present: {len(taken_today)}")
print(f"Names: {', '.join(sorted(taken_today))}")
print(f"{'='*50}")