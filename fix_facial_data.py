import zlib
import cv2
import numpy as np
import mysql.connector

DB = {
  "host": "localhost",
  "user": "root",
  "password": "030528",
  "database": "attendance_system"
}

USER_ID = 17
SAMPLE_COUNT = 100

def load_face_detector():
    paths = [
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml",
        "data/haarcascade_frontalface_default.xml",
        "haarcascade_frontalface_default.xml",
    ]
    for p in paths:
        c = cv2.CascadeClassifier(p)
        if not c.empty():
            return c
    return None

def detect_and_crop_face(img, face_cascade):
    if face_cascade is None:
        h, w = img.shape[:2]
        size = min(h, w)
        sh = (h - size) // 2
        sw = (w - size) // 2
        return img[sh:sh+size, sw:sw+size]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.05, 3, minSize=(30,30))
    if len(faces) > 0:
        x,y,w,h = max(faces, key=lambda f: f[2]*f[3])
        return img[y:y+h, x:x+w]
    return img

def generate_augmented_samples(face_img, sample_count=100):
    all_faces = []
    base = cv2.resize(face_img, (60, 60))
    for i in range(sample_count):
        aug = base.copy()
        # simple augments (keep close to your server logic)
        if np.random.rand() > 0.5:
            aug = cv2.flip(aug, 1)
        if i % 3 == 0:
            angle = np.random.uniform(-15, 15)
            h, w = aug.shape[:2]
            M = cv2.getRotationMatrix2D((w/2, h/2), angle, 1.0)
            aug = cv2.warpAffine(aug, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        aug = cv2.resize(aug, (50, 50))
        all_faces.append(aug.flatten())
    return np.array(all_faces, dtype=np.uint8)  # shape: (N, 7500)

def main():
    conn = mysql.connector.connect(**DB)
    cur = conn.cursor()

    cur.execute("SELECT face_encoding FROM facial_data WHERE user_id=%s AND is_active=1", (USER_ID,))
    row = cur.fetchone()
    if not row or not row[0]:
        print("No blob found for user_id", USER_ID)
        return

    blob = row[0]

    # Decode JPEG bytes
    img_np = np.frombuffer(blob, dtype=np.uint8)
    img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
    if img is None:
        print("Blob is not a decodable image (maybe already compressed training data).")
        return

    face_cascade = load_face_detector()
    face = detect_and_crop_face(img, face_cascade)

    faces_array = generate_augmented_samples(face, SAMPLE_COUNT)
    faces_bytes = faces_array.tobytes()
    compressed = zlib.compress(faces_bytes)
    header = f"SHAPE:{faces_array.shape[0]},{faces_array.shape[1]};".encode("utf-8")
    full_data = header + compressed

    cur.execute("""
        UPDATE facial_data
        SET face_encoding=%s, sample_count=%s, updated_at=NOW(), created_at=COALESCE(created_at, NOW()), is_active=1
        WHERE user_id=%s
    """, (full_data, SAMPLE_COUNT, USER_ID))

    conn.commit()
    print("✅ Updated face_encoding into SHAPE+compressed samples for user_id", USER_ID)

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
