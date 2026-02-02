"""
Bulk Facial Data Collector
Independent system to collect facial data for multiple students
Stores data in JSON file for bulk import later
"""

import cv2
import numpy as np
import json
import zlib
import base64
import os
from datetime import datetime
from pathlib import Path

class BulkFacialDataCollector:
    def __init__(self, output_file='facial_data_bulk.json'):
        self.output_file = output_file
        self.data_collection = []
        self.face_cascade = self._load_face_cascade()
        
    def _load_face_cascade(self):
        """Load Haar Cascade face detector"""
        cascade_paths = [
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml',
            'data/haarcascade_frontalface_default.xml',
            'haarcascade_frontalface_default.xml',
            './AttendanceAI/data/haarcascade_frontalface_default.xml'
        ]
        
        for path in cascade_paths:
            try:
                cascade = cv2.CascadeClassifier(path)
                if not cascade.empty():
                    print(f"✓ Face detector loaded from: {path}")
                    return cascade
            except:
                continue
        
        print("⚠ Warning: Face detector not found. Using center crop fallback.")
        return None
    
    def collect_from_webcam(self, user_id, name, num_photos=5, samples_per_photo=10):
        """
        Collect facial data from webcam for a single student
        
        Args:
            user_id: Student's user ID (must match database)
            name: Student's name (for display)
            num_photos: Number of photos to capture
            samples_per_photo: Augmented samples per photo
        """
        print(f"\n{'='*60}")
        print(f"Collecting facial data for: {name} (ID: {user_id})")
        print(f"{'='*60}")
        
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("❌ Error: Cannot open webcam")
            return False
        
        photos = []
        photo_count = 0
        
        print(f"\nPress SPACE to capture photo ({num_photos} needed)")
        print("Press ESC to cancel")
        print("Press ENTER when done capturing\n")
        
        while photo_count < num_photos:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Display preview with face detection
            display_frame = frame.copy()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            if self.face_cascade is not None:
                faces = self.face_cascade.detectMultiScale(gray, 1.05, 3, minSize=(30, 30))
                for (x, y, w, h) in faces:
                    cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # Show progress
            cv2.putText(display_frame, f"Photos: {photo_count}/{num_photos}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(display_frame, "SPACE=Capture ESC=Cancel ENTER=Done", 
                       (10, display_frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.6, (255, 255, 255), 1)
            
            cv2.imshow(f'Collecting: {name}', display_frame)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == 27:  # ESC
                print("❌ Cancelled")
                cap.release()
                cv2.destroyAllWindows()
                return False
            elif key == 13:  # ENTER
                if photo_count >= 3:  # Minimum 3 photos
                    break
                else:
                    print(f"⚠ Need at least 3 photos (current: {photo_count})")
            elif key == 32:  # SPACE
                photos.append(frame.copy())
                photo_count += 1
                print(f"✓ Photo {photo_count} captured")
        
        cap.release()
        cv2.destroyAllWindows()
        
        if len(photos) < 3:
            print("❌ Insufficient photos captured")
            return False
        
        # Process photos
        print(f"\n📊 Processing {len(photos)} photos...")
        result = self._process_photos(user_id, name, photos, samples_per_photo)
        
        if result:
            print(f"✓ Successfully processed {result['sample_count']} samples")
            self.data_collection.append(result)
            return True
        else:
            print("❌ Failed to process photos")
            return False
    
    def collect_from_images(self, user_id, name, image_paths, samples_per_photo=10):
        """
        Collect facial data from image files
        
        Args:
            user_id: Student's user ID
            name: Student's name
            image_paths: List of paths to image files
            samples_per_photo: Augmented samples per photo
        """
        print(f"\n{'='*60}")
        print(f"Processing images for: {name} (ID: {user_id})")
        print(f"{'='*60}")
        
        photos = []
        
        for img_path in image_paths:
            if not os.path.exists(img_path):
                print(f"⚠ Skipping missing file: {img_path}")
                continue
            
            img = cv2.imread(img_path)
            if img is not None:
                photos.append(img)
                print(f"✓ Loaded: {os.path.basename(img_path)}")
            else:
                print(f"⚠ Failed to load: {img_path}")
        
        if len(photos) < 3:
            print(f"❌ Insufficient valid images (need at least 3, got {len(photos)})")
            return False
        
        # Process photos
        print(f"\n📊 Processing {len(photos)} images...")
        result = self._process_photos(user_id, name, photos, samples_per_photo)
        
        if result:
            print(f"✓ Successfully processed {result['sample_count']} samples")
            self.data_collection.append(result)
            return True
        else:
            print("❌ Failed to process images")
            return False
    
    def _process_photos(self, user_id, name, photos, samples_per_photo):
        """Process photos using same mechanism as student_boundary.py"""
        all_faces = []
        target_samples = 100  # Increased for better recognition accuracy
        samples_per_photo = max(1, target_samples // len(photos))
        
        for idx, photo in enumerate(photos):
            try:
                # Detect and crop face (same as original)
                if self.face_cascade is not None:
                    gray = cv2.cvtColor(photo, cv2.COLOR_BGR2GRAY)
                    faces = self.face_cascade.detectMultiScale(gray, 1.05, 3, minSize=(30, 30))
                    
                    if len(faces) > 0:
                        # Get largest face
                        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                        face_img = photo[y:y+h, x:x+w]
                    else:
                        # No face detected, use center crop
                        h, w = photo.shape[:2]
                        size = min(h, w)
                        sh = (h - size) // 2
                        sw = (w - size) // 2
                        face_img = photo[sh:sh+size, sw:sw+size]
                else:
                    # No cascade, use center crop
                    h, w = photo.shape[:2]
                    size = min(h, w)
                    sh = (h - size) // 2
                    sw = (w - size) // 2
                    face_img = photo[sh:sh+size, sw:sw+size]
                
                # Generate augmented samples (same as original)
                base = cv2.resize(face_img, (50, 50))
                for i in range(samples_per_photo):
                    aug = base.copy()
                    
                    # Random flip
                    if np.random.rand() > 0.5:
                        aug = cv2.flip(aug, 1)
                    
                    # Random rotation every 3rd sample
                    if i % 3 == 0:
                        angle = np.random.uniform(-15, 15)
                        h, w = aug.shape[:2]
                        M = cv2.getRotationMatrix2D((w/2, h/2), angle, 1.0)
                        aug = cv2.warpAffine(aug, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
                    
                    # Final resize to 40x40 (same as original)
                    aug = cv2.resize(aug, (40, 40))
                    all_faces.append(aug.flatten())
                
                print(f"  Photo {idx+1}: Generated {samples_per_photo} samples")
                
            except Exception as e:
                print(f"  ⚠ Error processing photo {idx+1}: {e}")
                continue
        
        # Limit to exactly 100 samples for optimal recognition
        if len(all_faces) > 100:
            indices = np.linspace(0, len(all_faces) - 1, 100, dtype=int)
            all_faces = [all_faces[i] for i in indices]
        
        if len(all_faces) == 0:
            return None
        
        # Convert to numpy array and compress (same as original)
        faces_array = np.array(all_faces, dtype=np.uint8)
        sample_count = faces_array.shape[0]
        
        faces_bytes = faces_array.tobytes()
        compressed = zlib.compress(faces_bytes)
        header = f"SHAPE:{faces_array.shape[0]},{faces_array.shape[1]};".encode("utf-8")
        encodings_binary = header + compressed
        
        # Encode to base64 for JSON storage
        encodings_base64 = base64.b64encode(encodings_binary).decode('utf-8')
        
        return {
            'user_id': user_id,
            'name': name,
            'face_encoding': encodings_base64,
            'sample_count': sample_count,
            'collected_at': datetime.now().isoformat(),
            'num_photos': len(photos)
        }
    
    def save_to_file(self):
        """Save collected data to JSON file"""
        if not self.data_collection:
            print("⚠ No data to save")
            return False
        
        data = {
            'version': '1.0',
            'created_at': datetime.now().isoformat(),
            'total_students': len(self.data_collection),
            'students': self.data_collection
        }
        
        with open(self.output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\n{'='*60}")
        print(f"✓ Saved {len(self.data_collection)} student(s) to: {self.output_file}")
        print(f"{'='*60}")
        return True
    
    def load_from_file(self, input_file):
        """Load existing collection file"""
        if not os.path.exists(input_file):
            print(f"❌ File not found: {input_file}")
            return False
        
        with open(input_file, 'r') as f:
            data = json.load(f)
        
        self.data_collection = data.get('students', [])
        print(f"✓ Loaded {len(self.data_collection)} student(s) from: {input_file}")
        return True


def interactive_mode():
    """Interactive collection mode"""
    collector = BulkFacialDataCollector()
    
    print("\n" + "="*60)
    print("BULK FACIAL DATA COLLECTOR")
    print("="*60)
    
    while True:
        print("\nOptions:")
        print("1. Collect from webcam")
        print("2. Collect from image files")
        print("3. Save and exit")
        print("4. Exit without saving")
        
        choice = input("\nChoice: ").strip()
        
        if choice == '1':
            user_id = input("Enter User ID: ").strip()
            name = input("Enter Name: ").strip()
            
            if not user_id or not name:
                print("❌ User ID and Name are required")
                continue
            
            try:
                user_id = int(user_id)
            except ValueError:
                print("❌ User ID must be a number")
                continue
            
            num_photos = input("Number of photos (default 5): ").strip()
            num_photos = int(num_photos) if num_photos else 5
            
            collector.collect_from_webcam(user_id, name, num_photos=num_photos)
            
        elif choice == '2':
            user_id = input("Enter User ID: ").strip()
            name = input("Enter Name: ").strip()
            
            if not user_id or not name:
                print("❌ User ID and Name are required")
                continue
            
            try:
                user_id = int(user_id)
            except ValueError:
                print("❌ User ID must be a number")
                continue
            
            folder = input("Enter folder path with images: ").strip()
            
            if not os.path.exists(folder):
                print("❌ Folder not found")
                continue
            
            # Get all image files
            image_extensions = ('.jpg', '.jpeg', '.png', '.bmp')
            image_files = [os.path.join(folder, f) for f in os.listdir(folder) 
                          if f.lower().endswith(image_extensions)]
            
            if not image_files:
                print("❌ No image files found in folder")
                continue
            
            collector.collect_from_images(user_id, name, image_files)
            
        elif choice == '3':
            collector.save_to_file()
            break
            
        elif choice == '4':
            print("Exiting without saving...")
            break
        
        else:
            print("❌ Invalid choice")


if __name__ == '__main__':
    interactive_mode()
