import zlib
import cv2
import numpy as np
import mysql.connector
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Use Azure database from .env
DB = {
    "host": os.getenv('DB_HOST'),
    "user": os.getenv('DB_USER'),
    "password": os.getenv('DB_PASSWORD'),
    "database": os.getenv('DB_NAME'),
    "port": int(os.getenv('DB_PORT', 3306))
}

# Add SSL configuration for Azure
if os.getenv('DB_SSL_ENABLED', 'false').lower() == 'true':
    ssl_ca = os.getenv('DB_SSL_CA', './combined-ca-certificates.pem')
    if os.path.exists(ssl_ca):
        DB['ssl_ca'] = ssl_ca
        DB['ssl_verify_cert'] = True

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

    # Get all active facial data records
    cur.execute("""
        SELECT fd.facial_data_id, fd.user_id, u.name, fd.face_encoding 
        FROM facial_data fd
        JOIN users u ON fd.user_id = u.user_id
        WHERE fd.is_active = 1
        ORDER BY u.name
    """)
    
    all_records = cur.fetchall()
    
    if not all_records:
        print("❌ No facial data records found")
        return
    
    print(f"\n📊 Found {len(all_records)} facial data records\n")
    
    face_cascade = load_face_detector()
    fixed_count = 0
    skipped_count = 0
    error_count = 0
    corrupted_records = []
    
    for facial_data_id, user_id, name, blob in all_records:
        print(f"\n{'='*60}")
        print(f"Processing: {name} (User ID: {user_id})")
        print(f"{'='*60}")
        
        if not blob:
            print(f"⚠️  No blob data - SKIPPING")
            skipped_count += 1
            continue
        
        # Show blob info
        print(f"📦 Blob size: {len(blob)} bytes")
        print(f"📦 First 20 bytes: {blob[:20]}")
        
        # Check if already in correct format
        if blob[:6] == b'SHAPE:':
            print(f"✅ Already in correct format - SKIPPING")
            skipped_count += 1
            continue

        try:
            # Try to decompress if it's already compressed but missing header
            try:
                decompressed = zlib.decompress(blob)
                print(f"⚠️  Data is compressed but missing SHAPE header!")
                print(f"   Decompressed size: {len(decompressed)} bytes")
                
                # Check if it could be facial data
                if len(decompressed) == 750000:  # 100 samples x 7500 features
                    print(f"   Size matches 100 samples x 7500 features")
                    print(f"   Adding SHAPE header...")
                    
                    header = b"SHAPE:100,7500;"
                    full_data = header + blob  # blob is already compressed
                    
                    cur.execute("""
                        UPDATE facial_data
                        SET face_encoding=%s, sample_count=%s, updated_at=NOW()
                        WHERE facial_data_id=%s
                    """, (full_data, 100, facial_data_id))
                    
                    conn.commit()
                    print(f"✅ FIXED by adding SHAPE header!")
                    fixed_count += 1
                    continue
                else:
                    print(f"   Size doesn't match expected format")
            except zlib.error:
                pass  # Not compressed, continue to try decoding as image
            
            # Decode JPEG bytes
            img_np = np.frombuffer(blob, dtype=np.uint8)
            img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
            
            if img is None:
                print(f"❌ Cannot decode as image and not valid compressed data")
                print(f"   This record is CORRUPTED")
                corrupted_records.append((facial_data_id, user_id, name))
                error_count += 1
                continue

            print(f"📸 Image decoded: {img.shape}")
            
            # Detect and crop face
            face = detect_and_crop_face(img, face_cascade)
            print(f"✂️  Face cropped: {face.shape}")
            
            # Generate samples
            faces_array = generate_augmented_samples(face, SAMPLE_COUNT)
            print(f"🔄 Generated {faces_array.shape[0]} samples")
            
            # Compress
            faces_bytes = faces_array.tobytes()
            compressed = zlib.compress(faces_bytes)
            header = f"SHAPE:{faces_array.shape[0]},{faces_array.shape[1]};".encode("utf-8")
            full_data = header + compressed
            
            print(f"📦 Compressed: {len(blob)} → {len(full_data)} bytes")
            
            # Update database
            cur.execute("""
                UPDATE facial_data
                SET face_encoding=%s, sample_count=%s, updated_at=NOW()
                WHERE facial_data_id=%s
            """, (full_data, SAMPLE_COUNT, facial_data_id))
            
            conn.commit()
            print(f"✅ FIXED!")
            fixed_count += 1
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            error_count += 1
            continue
    
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Fixed:   {fixed_count}")
    print(f"⚠️  Skipped: {skipped_count}")
    print(f"❌ Errors:  {error_count}")
    print(f"{'='*60}\n")
    
    # Handle corrupted records
    if corrupted_records:
        print(f"⚠️  CORRUPTED RECORDS FOUND:")
        for facial_data_id, user_id, name in corrupted_records:
            print(f"   - {name} (User ID: {user_id})")
        
        print(f"\n⚠️  These records will cause the camera to CRASH!")
        response = input(f"\n❓ Delete {len(corrupted_records)} corrupted record(s)? (yes/no): ").strip().lower()
        
        if response == 'yes':
            for facial_data_id, user_id, name in corrupted_records:
                cur.execute("DELETE FROM facial_data WHERE facial_data_id=%s", (facial_data_id,))
                print(f"   🗑️  Deleted: {name}")
            
            conn.commit()
            print(f"\n✅ Corrupted records deleted!")
            print(f"   Students will need to re-upload their photos.")
            print(f"   The camera should now work properly.")
        else:
            print(f"\n⚠️  Cancelled - Camera will continue to crash until these are fixed")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
