"""
Bulk Facial Data Collector
==========================
Collect facial data from multiple students for bulk import.

Updated to use 7500 pixels (50x50x3 color) to match the browser webcam recognition system.

Usage:
    python bulk_facial_data_collector.py

Features:
    - Webcam capture with live face detection
    - Image file processing
    - Generates 50x50x3 color samples (7500 pixels each)
    - Augmentation for better recognition
    - Saves to portable JSON format
"""

import cv2
import numpy as np
import json
import base64
import zlib
import os
from datetime import datetime


class BulkFacialDataCollector:
    """Collect facial data from webcam or image files."""
    
    # Configuration - UPDATED to 7500 pixels (50x50x3)
    FACE_SIZE = 50  # 50x50 pixels
    SAMPLES_PER_STUDENT = 100  # Number of augmented samples
    PIXELS_PER_SAMPLE = 7500  # 50 * 50 * 3 (color)
    
    def __init__(self, output_file='facial_data_bulk.json'):
        self.output_file = output_file
        self.collected_data = []
        self.face_cascade = self._load_face_detector()
        
    def _load_face_detector(self):
        """Load Haar Cascade face detector."""
        cascade_paths = [
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml',
            'haarcascade_frontalface_default.xml',
            'data/haarcascade_frontalface_default.xml',
        ]
        
        for path in cascade_paths:
            try:
                cascade = cv2.CascadeClassifier(path)
                if not cascade.empty():
                    print(f"✅ Face detector loaded: {path}")
                    return cascade
            except:
                continue
        
        print("⚠️ Face detector not found - will use center crop")
        return None
    
    def _detect_and_crop_face(self, img):
        """Detect face and crop with padding."""
        if self.face_cascade is None:
            # Fallback: center crop
            h, w = img.shape[:2]
            size = min(h, w)
            start_h = (h - size) // 2
            start_w = (w - size) // 2
            return img[start_h:start_h+size, start_w:start_w+size], False
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=5, 
            minSize=(60, 60)
        )
        
        if len(faces) > 0:
            # Get largest face
            largest = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = largest
            
            # Add padding (10%)
            pad_w = int(0.1 * w)
            pad_h = int(0.1 * h)
            x1 = max(0, x - pad_w)
            y1 = max(0, y - pad_h)
            x2 = min(img.shape[1], x + w + pad_w)
            y2 = min(img.shape[0], y + h + pad_h)
            
            return img[y1:y2, x1:x2], True
        
        # No face found - use center crop
        h, w = img.shape[:2]
        margin_h = int(h * 0.2)
        margin_w = int(w * 0.2)
        return img[margin_h:h-margin_h, margin_w:w-margin_w], False
    
    def _generate_augmented_samples(self, face_img, num_samples=None):
        """
        Generate augmented training samples from a face image.
        
        Returns COLOR images (50x50x3 = 7500 values per sample).
        """
        if num_samples is None:
            num_samples = self.SAMPLES_PER_STUDENT
        
        all_samples = []
        
        # Resize to slightly larger for augmentation
        base_face = cv2.resize(face_img, (60, 60))
        
        # Ensure it's color (BGR)
        if len(base_face.shape) == 2:
            base_face = cv2.cvtColor(base_face, cv2.COLOR_GRAY2BGR)
        
        for i in range(num_samples):
            augmented = base_face.copy()
            
            # Random scale (80% - 120%)
            scale = np.random.uniform(0.8, 1.2)
            new_size = int(60 * scale)
            
            if new_size > 20:
                scaled = cv2.resize(augmented, (new_size, new_size))
                if new_size >= 60:
                    start = (new_size - 60) // 2
                    augmented = scaled[start:start+60, start:start+60]
                else:
                    pad = (60 - new_size) // 2
                    augmented = cv2.copyMakeBorder(
                        scaled, pad, pad, pad, pad, 
                        cv2.BORDER_REPLICATE
                    )
                    augmented = cv2.resize(augmented, (60, 60))
            
            # Random brightness (-40 to +40)
            brightness = np.random.randint(-40, 40)
            augmented = np.clip(
                augmented.astype(np.int16) + brightness, 
                0, 255
            ).astype(np.uint8)
            
            # Random contrast (every 4th sample)
            if i % 4 == 0:
                alpha = np.random.uniform(0.7, 1.3)
                augmented = np.clip(alpha * augmented, 0, 255).astype(np.uint8)
            
            # Random rotation (every 3rd sample, ±20 degrees)
            if i % 3 == 0:
                angle = np.random.uniform(-20, 20)
                h, w = augmented.shape[:2]
                M = cv2.getRotationMatrix2D((w/2, h/2), angle, 1.0)
                augmented = cv2.warpAffine(
                    augmented, M, (w, h), 
                    borderMode=cv2.BORDER_REPLICATE
                )
            
            # Random horizontal flip (50% chance)
            if np.random.random() > 0.5:
                augmented = cv2.flip(augmented, 1)
            
            # Random translation (every 5th sample)
            if i % 5 == 0:
                tx = np.random.randint(-5, 6)
                ty = np.random.randint(-5, 6)
                M = np.float32([[1, 0, tx], [0, 1, ty]])
                augmented = cv2.warpAffine(
                    augmented, M, 
                    (augmented.shape[1], augmented.shape[0]),
                    borderMode=cv2.BORDER_REPLICATE
                )
            
            # Random blur (every 6th sample)
            if i % 6 == 0:
                ksize = np.random.choice([3, 5])
                augmented = cv2.GaussianBlur(augmented, (ksize, ksize), 0)
            
            # Final resize to 50x50 and flatten
            final = cv2.resize(augmented, (self.FACE_SIZE, self.FACE_SIZE))
            
            # Flatten to 7500 values (50*50*3)
            flattened = final.flatten()
            all_samples.append(flattened)
        
        return np.array(all_samples, dtype=np.uint8)
    
    def _encode_facial_data(self, samples_array):
        """
        Encode facial data with SHAPE header and compression.
        Returns base64 string for JSON storage.
        """
        # Get shape info
        rows, cols = samples_array.shape
        
        # Create SHAPE header
        shape_header = f"SHAPE:{rows},{cols};".encode('utf-8')
        
        # Compress the raw bytes
        raw_bytes = samples_array.tobytes()
        compressed = zlib.compress(raw_bytes)
        
        # Combine header + compressed data
        full_data = shape_header + compressed
        
        # Base64 encode for JSON
        return base64.b64encode(full_data).decode('utf-8')
    
    def collect_from_webcam(self, user_id, name, num_photos=5):
        """
        Collect facial data from webcam.
        
        Args:
            user_id: Database user ID
            name: Student name
            num_photos: Number of photos to capture
        
        Returns:
            bool: Success status
        """
        print(f"\n📸 Collecting data for: {name} (ID: {user_id})")
        print(f"   Press SPACE to capture photo ({num_photos} needed)")
        print(f"   Press ENTER when done, ESC to cancel")
        
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Could not open webcam")
            return False
        
        captured_faces = []
        
        while len(captured_faces) < num_photos:
            ret, frame = cap.read()
            if not ret:
                continue
            
            # Mirror the frame
            display = cv2.flip(frame, 1)
            
            # Detect face for preview
            if self.face_cascade is not None:
                gray = cv2.cvtColor(display, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))
                
                for (x, y, w, h) in faces:
                    cv2.rectangle(display, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # Show status
            cv2.putText(
                display, 
                f"Photos: {len(captured_faces)}/{num_photos} - SPACE=capture, ENTER=done, ESC=cancel",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2
            )
            cv2.putText(
                display,
                f"Student: {name} (ID: {user_id})",
                (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2
            )
            
            cv2.imshow('Capture - Press SPACE to take photo', display)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == 32:  # SPACE
                face_img, detected = self._detect_and_crop_face(frame)
                if face_img is not None and face_img.size > 0:
                    captured_faces.append(face_img)
                    print(f"   ✅ Photo {len(captured_faces)} captured" + 
                          (" (face detected)" if detected else " (center crop)"))
                else:
                    print("   ⚠️ Could not capture - try again")
            
            elif key == 13:  # ENTER
                if len(captured_faces) >= 3:
                    break
                else:
                    print(f"   ⚠️ Need at least 3 photos (have {len(captured_faces)})")
            
            elif key == 27:  # ESC
                print("   ❌ Cancelled")
                cap.release()
                cv2.destroyAllWindows()
                return False
        
        cap.release()
        cv2.destroyAllWindows()
        
        if len(captured_faces) == 0:
            print("   ❌ No photos captured")
            return False
        
        # Generate augmented samples from all captured faces
        all_samples = []
        samples_per_photo = max(10, self.SAMPLES_PER_STUDENT // len(captured_faces))
        
        for face in captured_faces:
            samples = self._generate_augmented_samples(face, samples_per_photo)
            all_samples.append(samples)
        
        # Combine all samples
        combined_samples = np.vstack(all_samples)
        
        # Encode for storage
        encoded_data = self._encode_facial_data(combined_samples)
        
        # Add to collection
        self.collected_data.append({
            'user_id': user_id,
            'name': name,
            'face_encoding': encoded_data,
            'sample_count': combined_samples.shape[0],
            'pixels_per_sample': combined_samples.shape[1],
            'collected_at': datetime.now().isoformat(),
            'num_photos': len(captured_faces)
        })
        
        print(f"   ✅ Generated {combined_samples.shape[0]} samples ({combined_samples.shape[1]} pixels each)")
        return True
    
    def collect_from_images(self, user_id, name, image_paths):
        """
        Collect facial data from image files.
        
        Args:
            user_id: Database user ID
            name: Student name
            image_paths: List of image file paths
        
        Returns:
            bool: Success status
        """
        print(f"\n📁 Processing images for: {name} (ID: {user_id})")
        
        captured_faces = []
        
        for img_path in image_paths:
            if not os.path.exists(img_path):
                print(f"   ⚠️ File not found: {img_path}")
                continue
            
            img = cv2.imread(img_path)
            if img is None:
                print(f"   ⚠️ Could not read: {img_path}")
                continue
            
            face_img, detected = self._detect_and_crop_face(img)
            if face_img is not None and face_img.size > 0:
                captured_faces.append(face_img)
                print(f"   ✅ Processed: {os.path.basename(img_path)}" +
                      (" (face detected)" if detected else " (center crop)"))
        
        if len(captured_faces) == 0:
            print("   ❌ No valid images processed")
            return False
        
        # Generate augmented samples
        all_samples = []
        samples_per_photo = max(10, self.SAMPLES_PER_STUDENT // len(captured_faces))
        
        for face in captured_faces:
            samples = self._generate_augmented_samples(face, samples_per_photo)
            all_samples.append(samples)
        
        combined_samples = np.vstack(all_samples)
        encoded_data = self._encode_facial_data(combined_samples)
        
        self.collected_data.append({
            'user_id': user_id,
            'name': name,
            'face_encoding': encoded_data,
            'sample_count': combined_samples.shape[0],
            'pixels_per_sample': combined_samples.shape[1],
            'collected_at': datetime.now().isoformat(),
            'num_photos': len(captured_faces)
        })
        
        print(f"   ✅ Generated {combined_samples.shape[0]} samples ({combined_samples.shape[1]} pixels each)")
        return True
    
    def collect_from_base64(self, user_id, name, base64_images):
        """
        Collect facial data from base64-encoded images.
        
        Args:
            user_id: Database user ID
            name: Student name
            base64_images: List of base64 image strings
        
        Returns:
            bool: Success status
        """
        print(f"\n📷 Processing base64 images for: {name} (ID: {user_id})")
        
        captured_faces = []
        
        for i, b64_img in enumerate(base64_images):
            try:
                # Remove data URL prefix if present
                if ',' in b64_img:
                    b64_img = b64_img.split(',')[1]
                
                img_bytes = base64.b64decode(b64_img)
                img_array = np.frombuffer(img_bytes, dtype=np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                
                if img is None:
                    print(f"   ⚠️ Could not decode image {i+1}")
                    continue
                
                face_img, detected = self._detect_and_crop_face(img)
                if face_img is not None and face_img.size > 0:
                    captured_faces.append(face_img)
                    print(f"   ✅ Processed image {i+1}" +
                          (" (face detected)" if detected else " (center crop)"))
            except Exception as e:
                print(f"   ⚠️ Error processing image {i+1}: {e}")
        
        if len(captured_faces) == 0:
            print("   ❌ No valid images processed")
            return False
        
        # Generate augmented samples
        all_samples = []
        samples_per_photo = max(10, self.SAMPLES_PER_STUDENT // len(captured_faces))
        
        for face in captured_faces:
            samples = self._generate_augmented_samples(face, samples_per_photo)
            all_samples.append(samples)
        
        combined_samples = np.vstack(all_samples)
        encoded_data = self._encode_facial_data(combined_samples)
        
        self.collected_data.append({
            'user_id': user_id,
            'name': name,
            'face_encoding': encoded_data,
            'sample_count': combined_samples.shape[0],
            'pixels_per_sample': combined_samples.shape[1],
            'collected_at': datetime.now().isoformat(),
            'num_photos': len(captured_faces)
        })
        
        print(f"   ✅ Generated {combined_samples.shape[0]} samples ({combined_samples.shape[1]} pixels each)")
        return True
    
    def save_to_file(self, filename=None):
        """Save collected data to JSON file."""
        if filename is None:
            filename = self.output_file
        
        output = {
            'version': '2.0',
            'format': 'color_50x50x3',
            'pixels_per_sample': self.PIXELS_PER_SAMPLE,
            'created_at': datetime.now().isoformat(),
            'total_students': len(self.collected_data),
            'students': self.collected_data
        }
        
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n💾 Saved {len(self.collected_data)} students to {filename}")
        return filename
    
    def get_collected_data(self):
        """Return collected data for direct import."""
        return self.collected_data
    
    def clear(self):
        """Clear collected data."""
        self.collected_data = []


def interactive_mode():
    """Run in interactive command-line mode."""
    print("\n" + "="*60)
    print("   BULK FACIAL DATA COLLECTOR")
    print("   Format: 50x50x3 color (7500 pixels per sample)")
    print("="*60)
    
    collector = BulkFacialDataCollector()
    
    while True:
        print("\n📋 Menu:")
        print("   1. Collect from webcam")
        print("   2. Collect from image files")
        print("   3. Save and exit")
        print("   4. Exit without saving")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == '1':
            try:
                user_id = int(input("Enter User ID: ").strip())
                name = input("Enter Name: ").strip()
                num_photos = int(input("Number of photos (default 5): ").strip() or "5")
                collector.collect_from_webcam(user_id, name, num_photos)
            except ValueError as e:
                print(f"❌ Invalid input: {e}")
        
        elif choice == '2':
            try:
                user_id = int(input("Enter User ID: ").strip())
                name = input("Enter Name: ").strip()
                paths_str = input("Enter image paths (comma-separated): ").strip()
                paths = [p.strip() for p in paths_str.split(',')]
                collector.collect_from_images(user_id, name, paths)
            except ValueError as e:
                print(f"❌ Invalid input: {e}")
        
        elif choice == '3':
            if collector.collected_data:
                collector.save_to_file()
            else:
                print("⚠️ No data to save")
            break
        
        elif choice == '4':
            print("👋 Exiting without saving")
            break
        
        else:
            print("❌ Invalid choice")


if __name__ == '__main__':
    interactive_mode()