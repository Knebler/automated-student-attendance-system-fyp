from sklearn.neighbors import KNeighborsClassifier
import cv2
import pickle
import numpy as np
import os
import csv
import time
from datetime import datetime
import pandas as pd
from win32com.client import Dispatch

# ------------------ SPEAK FUNCTION ------------------
def speak(text):
    speaker = Dispatch("SAPI.SpVoice")
    speaker.Speak(text)

# ------------------ LOAD VIDEO + FACE CASCADE ------------------
video = cv2.VideoCapture(0)
facedetect = cv2.CascadeClassifier('data/haarcascade_frontalface_default.xml')

# ------------------ LOAD TRAINED DATA ------------------
with open('data/names.pkl', 'rb') as w:
    LABELS = pickle.load(w)

with open('data/faces_data.pkl', 'rb') as f:
    FACES = pickle.load(f)

print("Faces shape:", FACES.shape)

# ------------------ TRAIN KNN MODEL ------------------
knn = KNeighborsClassifier(n_neighbors=5)
knn.fit(FACES, LABELS)

# ------------------ LOAD BACKGROUND ------------------
imgBackground = cv2.imread("background.png")
if imgBackground is None:
    raise FileNotFoundError("background.png not found. Place it beside test.py")

COL_NAMES = ['NAME', 'TIME']

# Track who has already taken attendance today
taken_today = set()

# ------------------ MAIN LOOP ------------------
while True:
    ret, frame = video.read()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = facedetect.detectMultiScale(gray, 1.3, 5)

    for (x, y, w, h) in faces:
        crop_img = frame[y:y+h, x:x+w, :]
        resized_img = cv2.resize(crop_img, (50, 50)).flatten().reshape(1, -1)
        output = knn.predict(resized_img)

        name = str(output[0])
        ts = time.time()
        date = datetime.fromtimestamp(ts).strftime("%d-%m-%Y")
        timestamp = datetime.fromtimestamp(ts).strftime("%H:%M:%S")

        # CSV file location
        csv_path = f"Attendance/Attendance_{date}.csv"
        file_exists = os.path.isfile(csv_path)

        # Draw box
        cv2.rectangle(frame, (x, y), (x + w, y + h), (50, 50, 255), 2)
        cv2.rectangle(frame, (x, y - 40), (x + w, y), (50, 50, 255), -1)
        cv2.putText(frame, name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        # ------------- AUTO ATTENDANCE & NO DOUBLE ENTRY -------------
        if name not in taken_today:
            taken_today.add(name)

            speak(f"Attendance recorded for {name}")

            # Write CSV
            with open(csv_path, "a", newline="") as csvfile:
                writer = csv.writer(csvfile)

                # If file didn't exist → write header first
                if not file_exists:
                    writer.writerow(COL_NAMES)

                writer.writerow([name, timestamp])

    # Insert camera into your background.png
    imgBackground[162:162 + 480, 55:55 + 640] = frame

    cv2.imshow("Attendance System", imgBackground)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

video.release()
cv2.destroyAllWindows()
