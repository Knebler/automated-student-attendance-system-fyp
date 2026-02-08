# application/controls/facial_recognition_control.py
import cv2
import pickle
import numpy as np
import os
from datetime import datetime
import time

class FacialRecognitionControl:
    """Control class for facial recognition operations"""
    
    def __init__(self, app=None):
        self.app = app
        self.knn_model = None
        self.labels = []
        self.faces_data = []
        self.haar_cascade = None
        self.is_initialized = False
        
    def initialize(self, app):
        """Initialize the facial recognition system"""
        try:
            self.app = app
            data_dir = app.config.get('FACIAL_DATA_DIR', './AttendanceAI/data/')
            
            # Load Haar Cascade
            cascade_path = os.path.join(data_dir, 'haarcascade_frontalface_default.xml')
            self.haar_cascade = cv2.CascadeClassifier(cascade_path)
            
            if self.haar_cascade.empty():
                raise FileNotFoundError("Haar Cascade XML file not found")
            
            # Load trained data
            names_path = os.path.join(data_dir, 'names.pkl')
            faces_path = os.path.join(data_dir, 'faces_data.pkl')
            
            with open(names_path, 'rb') as w:
                self.labels = pickle.load(w)
            
            with open(faces_path, 'rb') as f:
                self.faces_data = pickle.load(f)
            
            # Fix mismatch
            min_samples = min(len(self.faces_data), len(self.labels))
            self.faces_data = self.faces_data[:min_samples]
            self.labels = self.labels[:min_samples]
            
            # Train KNN model
            from sklearn.neighbors import KNeighborsClassifier
            self.knn_model = KNeighborsClassifier(n_neighbors=5)
            self.knn_model.fit(self.faces_data, self.labels)
            
            self.is_initialized = True
            self.app.logger.info("Facial recognition system initialized successfully")
            
            return True
            
        except Exception as e:
            self.app.logger.error(f"Failed to initialize facial recognition: {e}")
            return False
    
    def recognize_face_from_image(self, image_data, student_id=None):
        """Recognize face from image data"""
        if not self.is_initialized:
            return {'success': False, 'error': 'Facial recognition not initialized'}
        
        try:
            # Convert image data to numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                return {'success': False, 'error': 'Invalid image data'}
            
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.haar_cascade.detectMultiScale(gray, 1.3, 5)
            
            if len(faces) == 0:
                return {'success': False, 'error': 'No face detected'}
            
            # Process each detected face
            recognitions = []
            for (x, y, w, h) in faces:
                crop_img = frame[y:y+h, x:x+w, :]
                resized_img = cv2.resize(crop_img, (50, 50)).flatten().reshape(1, -1)
                
                # Predict using probability (same as attendance marking)
                output = self.knn_model.predict(resized_img)
                name = str(output[0])
                
                # Calculate confidence using predict_proba (SAME as attendance marking)
                # Keep confidence on 0-1 scale to match attendance marking logic
                proba = self.knn_model.predict_proba(resized_img)
                confidence = float(np.max(proba))  # Keep as 0-1 scale (SAME as attendance)
                
                recognitions.append({
                    'name': name,
                    'confidence': round(confidence, 4),
                    'bbox': {'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)},
                    'student_id': self._get_student_id_by_name(name)
                })
            
            return {
                'success': True,
                'recognitions': recognitions,
                'face_count': len(faces)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def register_new_face(self, student_id, image_data, student_name=None):
        """Register a new face for a student"""
        try:
            # Convert and process image
            nparr = np.frombuffer(image_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                return {'success': False, 'error': 'Invalid image data'}
            
            # Detect and extract face
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.haar_cascade.detectMultiScale(gray, 1.3, 5)
            
            if len(faces) == 0:
                return {'success': False, 'error': 'No face detected'}
            
            # Take the largest face
            largest_face = max(faces, key=lambda rect: rect[2] * rect[3])
            x, y, w, h = largest_face
            
            crop_img = frame[y:y+h, x:x+w, :]
            resized_img = cv2.resize(crop_img, (50, 50))
            flattened = resized_img.flatten()
            
            # Save to training data
            data_dir = self.app.config.get('FACIAL_DATA_DIR', './AttendanceAI/data/')
            os.makedirs(data_dir, exist_ok=True)
            
            # Update faces data
            self.faces_data = np.append(self.faces_data, [flattened], axis=0)
            
            # Update labels
            name_to_use = student_name or f"Student_{student_id}"
            self.labels.append(name_to_use)
            
            # Save updated data
            with open(os.path.join(data_dir, 'faces_data.pkl'), 'wb') as f:
                pickle.dump(self.faces_data, f)
            
            with open(os.path.join(data_dir, 'names.pkl'), 'wb') as w:
                pickle.dump(self.labels, w)
            
            # Retrain model
            self.knn_model.fit(self.faces_data, self.labels)
            
            return {
                'success': True,
                'message': f'Face registered for {name_to_use}',
                'samples_collected': len(self.faces_data)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _get_student_id_by_name(self, name):
        """Helper to extract student ID from recognized name"""
        # This depends on how you name students in your training data
        # Example: "John Doe (ID: 123)" -> extract 123
        import re
        match = re.search(r'\(ID:\s*(\d+)\)', name)
        return match.group(1) if match else None