from sklearn.neighbors import KNeighborsClassifier
import cv2
import pickle
import numpy as np
import os
import csv
import time
from datetime import datetime
from collections import defaultdict

# ------------------ LOAD VIDEO + CASCADES ------------------
video = cv2.VideoCapture(0)

facedetect = cv2.CascadeClassifier('data/haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

# ------------------ LOAD TRAINED DATA ------------------
with open('data/names.pkl', 'rb') as w:
    LABELS = pickle.load(w)

with open('data/faces_data.pkl', 'rb') as f:
    FACES = pickle.load(f)

# ------------------ TRAIN KNN ------------------
n_samples = FACES.shape[0]
n_neighbors = min(5, n_samples)

knn = KNeighborsClassifier(n_neighbors=n_neighbors)
knn.fit(FACES, LABELS)

# ------------------ THRESHOLDS ------------------
CONFIDENCE_THRESHOLD = 0.3
MIN_MATCH_DISTANCE = 5000

# ------------------ TEMPORAL SMOOTHING ------------------
FRAME_CONFIRMATION = 5

face_memory = defaultdict(lambda: {
    "name": None,
    "count": 0,
    "confirmed": False,
    "blinked": False
})

# ------------------ BLINK DETECTION ------------------
BLINK_FRAMES = 2
EYE_OPEN_FRAMES = 3

blink_counter = defaultdict(int)
eye_open_counter = defaultdict(int)

# ------------------ ATTENDANCE ------------------
taken_today = set()
last_seen = {}   # 👈 NEW
ABSENCE_TIMEOUT = 1800  # 30 minutes

current_date = datetime.now().strftime("%d-%m-%Y")
csv_path = f"Attendance/Attendance_{current_date}.csv"
os.makedirs("Attendance", exist_ok=True)

COL_NAMES = ['NAME', 'TIME']

# ------------------ BACKGROUND ------------------
imgBackground = cv2.imread("background.png")
if imgBackground is None:
    raise FileNotFoundError("background.png not found")

# ------------------ MAIN LOOP ------------------
while True:
    ret, frame = video.read()
    if not ret:
        break

    now = time.time()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = facedetect.detectMultiScale(gray, 1.3, 5)

    detected_names = set()

    for (x, y, w, h) in faces:
        face_id = (x // 20, y // 20)

        crop_img = frame[y:y+h, x:x+w]
        if crop_img.size == 0:
            continue

        resized = cv2.resize(crop_img, (50, 50)).flatten().reshape(1, -1)

        output = knn.predict(resized)[0]
        proba = knn.predict_proba(resized)
        confidence = np.max(proba)

        distances, _ = knn.kneighbors(resized, n_neighbors=n_neighbors)
        avg_distance = np.mean(distances[0])

        memory = face_memory[face_id]

        # -------- TEMPORAL SMOOTHING --------
        if memory["name"] == output:
            memory["count"] += 1
        else:
            memory["name"] = output
            memory["count"] = 1
            memory["confirmed"] = False
            memory["blinked"] = False

        if memory["count"] >= FRAME_CONFIRMATION:
            memory["confirmed"] = True

        # -------- BLINK DETECTION --------
        face_gray = gray[y:y+h, x:x+w]
        eyes = eye_cascade.detectMultiScale(face_gray, 1.1, 3)

        if len(eyes) > 0:
            eye_open_counter[face_id] += 1
        else:
            blink_counter[face_id] += 1

        if blink_counter[face_id] >= BLINK_FRAMES and eye_open_counter[face_id] >= EYE_OPEN_FRAMES:
            memory["blinked"] = True

        # -------- FINAL DECISION --------
        if (
            memory["confirmed"]
            and memory["blinked"]
            and confidence >= CONFIDENCE_THRESHOLD
            and avg_distance <= MIN_MATCH_DISTANCE
        ):
            name = str(output)
            detected_names.add(name)
            last_seen[name] = now

            cv2.rectangle(frame, (x, y), (x+w, y+h), (50, 50, 255), 2)
            cv2.rectangle(frame, (x, y-40), (x+w, y), (50, 50, 255), -1)
            cv2.putText(frame, name, (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

            if name not in taken_today:
                taken_today.add(name)
                with open(csv_path, "a", newline="") as f:
                    writer = csv.writer(f)
                    if f.tell() == 0:
                        writer.writerow(COL_NAMES)
                    writer.writerow([name, datetime.now().strftime("%H:%M:%S")])
                print(f"✅ {name} marked present")

        else:
            # SPOOF
            dash = 10
            for i in range(0, w, dash * 2):
                cv2.line(frame, (x+i, y), (x+min(i+dash, w), y), (0,255,255), 2)
                cv2.line(frame, (x+i, y+h), (x+min(i+dash, w), y+h), (0,255,255), 2)

            cv2.putText(frame, "UNKNOWN / SPOOF", (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 2)

    # -------- AUTO UNMARK (ABSENCE CHECK) --------
    for name in list(taken_today):
        if now - last_seen.get(name, now) > ABSENCE_TIMEOUT:
            taken_today.remove(name)
            print(f"❌ {name} removed (absent > 2 minutes)")

    # -------- DISPLAY --------
    imgBackground[162:162+480, 55:55+640] = frame

    cv2.putText(imgBackground, f"Present: {len(taken_today)}",
                (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)

    cv2.imshow("Attendance System", imgBackground)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

video.release()
cv2.destroyAllWindows()
