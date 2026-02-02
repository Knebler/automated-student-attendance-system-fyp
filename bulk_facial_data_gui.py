"""
Bulk Facial Data GUI
====================
GUI application for collecting and importing facial data.

Updated to use 7500 pixels (50x50x3 color) format.

Usage:
    python bulk_facial_data_gui.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
import threading
import json
import base64
import zlib
import os
from datetime import datetime


class BulkFacialDataGUI:
    """GUI for collecting and importing facial data."""
    
    # Configuration - 7500 pixels (50x50x3 color)
    FACE_SIZE = 50
    SAMPLES_PER_STUDENT = 100
    PIXELS_PER_SAMPLE = 7500  # 50 * 50 * 3
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Bulk Facial Data Collection & Import")
        self.root.geometry("1000x700")
        self.root.minsize(900, 600)
        
        # State
        self.camera = None
        self.camera_running = False
        self.captured_photos = []
        self.collected_students = []
        self.face_cascade = self._load_face_detector()
        self.current_frame = None
        
        # Build UI
        self._create_ui()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _load_face_detector(self):
        """Load Haar Cascade face detector."""
        paths = [
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml',
            'haarcascade_frontalface_default.xml',
            'data/haarcascade_frontalface_default.xml',
        ]
        for path in paths:
            try:
                cascade = cv2.CascadeClassifier(path)
                if not cascade.empty():
                    print(f"✅ Face detector loaded: {path}")
                    return cascade
            except:
                continue
        print("⚠️ Face detector not found - using center crop")
        return None
    
    def _create_ui(self):
        """Create the main UI."""
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Collection
        self.collection_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.collection_tab, text="📸 Collect Data")
        self._create_collection_tab()
        
        # Tab 2: Import
        self.import_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.import_tab, text="📥 Import to Database")
        self._create_import_tab()
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)
    
    def _create_collection_tab(self):
        """Create the data collection tab."""
        # Main container
        main_frame = ttk.Frame(self.collection_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left side: Camera
        left_frame = ttk.LabelFrame(main_frame, text="Camera Preview")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Camera canvas
        self.camera_canvas = tk.Canvas(left_frame, width=480, height=360, bg='black')
        self.camera_canvas.pack(padx=10, pady=10)
        
        # Camera controls
        cam_controls = ttk.Frame(left_frame)
        cam_controls.pack(fill=tk.X, padx=10, pady=5)
        
        self.start_cam_btn = ttk.Button(cam_controls, text="▶ Start Camera", command=self._start_camera)
        self.start_cam_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_cam_btn = ttk.Button(cam_controls, text="⏹ Stop Camera", command=self._stop_camera, state=tk.DISABLED)
        self.stop_cam_btn.pack(side=tk.LEFT, padx=5)
        
        self.capture_btn = ttk.Button(cam_controls, text="📷 Capture Photo", command=self._capture_photo, state=tk.DISABLED)
        self.capture_btn.pack(side=tk.LEFT, padx=5)
        
        # Photo count
        self.photo_count_var = tk.StringVar(value="Photos: 0")
        ttk.Label(cam_controls, textvariable=self.photo_count_var).pack(side=tk.RIGHT, padx=10)
        
        # Right side: Student info
        right_frame = ttk.LabelFrame(main_frame, text="Student Information")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # User ID
        ttk.Label(right_frame, text="User ID:").pack(anchor=tk.W, padx=10, pady=(10, 0))
        self.user_id_var = tk.StringVar()
        self.user_id_entry = ttk.Entry(right_frame, textvariable=self.user_id_var, width=30)
        self.user_id_entry.pack(fill=tk.X, padx=10, pady=5)
        
        # Name
        ttk.Label(right_frame, text="Name:").pack(anchor=tk.W, padx=10, pady=(10, 0))
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(right_frame, textvariable=self.name_var, width=30)
        self.name_entry.pack(fill=tk.X, padx=10, pady=5)
        
        # Sample count
        ttk.Label(right_frame, text="Samples per image:").pack(anchor=tk.W, padx=10, pady=(10, 0))
        self.sample_count_var = tk.StringVar(value="100")
        self.sample_count_entry = ttk.Entry(right_frame, textvariable=self.sample_count_var, width=30)
        self.sample_count_entry.pack(fill=tk.X, padx=10, pady=5)
        
        # Info label
        info_text = "Format: 50×50×3 color (7500 pixels per sample)"
        ttk.Label(right_frame, text=info_text, foreground='gray').pack(anchor=tk.W, padx=10, pady=5)
        
        # Thumbnails frame
        ttk.Label(right_frame, text="Captured Photos:").pack(anchor=tk.W, padx=10, pady=(20, 5))
        self.thumbnails_frame = ttk.Frame(right_frame)
        self.thumbnails_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Process button
        self.process_btn = ttk.Button(right_frame, text="✅ Process & Save Student", 
                                       command=self._process_student, state=tk.DISABLED)
        self.process_btn.pack(fill=tk.X, padx=10, pady=20)
        
        # Collected students list
        ttk.Label(right_frame, text="Collected Students:").pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        list_frame = ttk.Frame(right_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.students_listbox = tk.Listbox(list_frame, height=6)
        self.students_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.students_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.students_listbox.config(yscrollcommand=scrollbar.set)
        
        # Save collection button
        self.save_btn = ttk.Button(right_frame, text="💾 Save Collection to File", 
                                   command=self._save_collection, state=tk.DISABLED)
        self.save_btn.pack(fill=tk.X, padx=10, pady=10)
    
    def _create_import_tab(self):
        """Create the import tab."""
        main_frame = ttk.Frame(self.import_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # File selection
        file_frame = ttk.LabelFrame(main_frame, text="Select Data File")
        file_frame.pack(fill=tk.X, pady=10)
        
        self.file_path_var = tk.StringVar(value="facial_data_bulk.json")
        ttk.Entry(file_frame, textvariable=self.file_path_var, width=60).pack(side=tk.LEFT, padx=10, pady=10)
        ttk.Button(file_frame, text="Browse...", command=self._browse_file).pack(side=tk.LEFT, padx=5, pady=10)
        
        # Options
        options_frame = ttk.LabelFrame(main_frame, text="Import Options")
        options_frame.pack(fill=tk.X, pady=10)
        
        self.skip_existing_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Skip existing records (don't update)", 
                        variable=self.skip_existing_var).pack(anchor=tk.W, padx=10, pady=5)
        
        self.dry_run_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Dry run (test mode - don't save to database)", 
                        variable=self.dry_run_var).pack(anchor=tk.W, padx=10, pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=20)
        
        ttk.Button(btn_frame, text="📥 Import Data", command=self._import_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🔍 Verify Import", command=self._verify_import).pack(side=tk.LEFT, padx=5)
        
        # Log
        ttk.Label(main_frame, text="Import Log:").pack(anchor=tk.W, pady=(10, 5))
        
        log_frame = ttk.Frame(main_frame)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.import_log = tk.Text(log_frame, height=15, width=80, state=tk.DISABLED)
        self.import_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.import_log.yview)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.import_log.config(yscrollcommand=log_scroll.set)
    
    # ==================== Camera Functions ====================
    
    def _start_camera(self):
        """Start the camera."""
        self.camera = cv2.VideoCapture(0)
        if not self.camera.isOpened():
            messagebox.showerror("Error", "Could not open camera")
            return
        
        self.camera_running = True
        self.start_cam_btn.config(state=tk.DISABLED)
        self.stop_cam_btn.config(state=tk.NORMAL)
        self.capture_btn.config(state=tk.NORMAL)
        
        self._update_camera()
    
    def _stop_camera(self):
        """Stop the camera."""
        self.camera_running = False
        if self.camera:
            self.camera.release()
            self.camera = None
        
        self.start_cam_btn.config(state=tk.NORMAL)
        self.stop_cam_btn.config(state=tk.DISABLED)
        self.capture_btn.config(state=tk.DISABLED)
        
        # Clear canvas
        self.camera_canvas.delete("all")
    
    def _update_camera(self):
        """Update camera frame."""
        if not self.camera_running or not self.camera:
            return
        
        ret, frame = self.camera.read()
        if ret:
            self.current_frame = frame.copy()
            
            # Mirror
            display = cv2.flip(frame, 1)
            
            # Detect faces and draw rectangles
            if self.face_cascade is not None:
                gray = cv2.cvtColor(display, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))
                for (x, y, w, h) in faces:
                    cv2.rectangle(display, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # Convert for Tkinter
            display = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
            display = cv2.resize(display, (480, 360))
            img = Image.fromarray(display)
            imgtk = ImageTk.PhotoImage(image=img)
            
            self.camera_canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
            self.camera_canvas.imgtk = imgtk
        
        if self.camera_running:
            self.root.after(30, self._update_camera)
    
    def _capture_photo(self):
        """Capture a photo."""
        if self.current_frame is None:
            return
        
        # Detect and crop face
        face_img, detected = self._detect_and_crop_face(self.current_frame)
        
        if face_img is not None and face_img.size > 0:
            self.captured_photos.append(face_img)
            self._update_thumbnails()
            self.photo_count_var.set(f"Photos: {len(self.captured_photos)}")
            
            status = "Face detected" if detected else "Center crop"
            self.status_var.set(f"Photo {len(self.captured_photos)} captured ({status})")
            
            if len(self.captured_photos) >= 3:
                self.process_btn.config(state=tk.NORMAL)
    
    def _detect_and_crop_face(self, img):
        """Detect and crop face from image."""
        if self.face_cascade is None:
            h, w = img.shape[:2]
            size = min(h, w)
            sh, sw = (h - size) // 2, (w - size) // 2
            return img[sh:sh+size, sw:sw+size], False
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))
        
        if len(faces) > 0:
            largest = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = largest
            pad = int(0.1 * w)
            x1, y1 = max(0, x - pad), max(0, y - pad)
            x2, y2 = min(img.shape[1], x + w + pad), min(img.shape[0], y + h + pad)
            return img[y1:y2, x1:x2], True
        
        # Center crop fallback
        h, w = img.shape[:2]
        margin = min(h, w) // 4
        return img[margin:h-margin, margin:w-margin], False
    
    def _update_thumbnails(self):
        """Update thumbnail display."""
        # Clear existing thumbnails
        for widget in self.thumbnails_frame.winfo_children():
            widget.destroy()
        
        # Show last 5 photos
        for i, photo in enumerate(self.captured_photos[-5:]):
            thumb = cv2.resize(photo, (60, 60))
            thumb = cv2.cvtColor(thumb, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(thumb)
            imgtk = ImageTk.PhotoImage(image=img)
            
            label = ttk.Label(self.thumbnails_frame, image=imgtk)
            label.image = imgtk
            label.pack(side=tk.LEFT, padx=2)
    
    # ==================== Processing Functions ====================
    
    def _process_student(self):
        """Process captured photos for a student."""
        user_id = self.user_id_var.get().strip()
        name = self.name_var.get().strip()
        
        if not user_id:
            messagebox.showerror("Error", "Please enter User ID")
            return
        
        if not name:
            messagebox.showerror("Error", "Please enter Name")
            return
        
        try:
            user_id = int(user_id)
        except ValueError:
            messagebox.showerror("Error", "User ID must be a number")
            return
        
        if len(self.captured_photos) < 3:
            messagebox.showerror("Error", "Please capture at least 3 photos")
            return
        
        try:
            sample_count = int(self.sample_count_var.get())
        except ValueError:
            sample_count = 100
        
        # Disable button during processing
        self.process_btn.config(state=tk.DISABLED)
        self.status_var.set("Processing facial data...")
        
        # Process in background thread
        def process_thread():
            try:
                # Generate samples from all photos
                all_samples = []
                samples_per_photo = max(10, sample_count // len(self.captured_photos))
                
                for photo in self.captured_photos:
                    samples = self._generate_augmented_samples(photo, samples_per_photo)
                    all_samples.append(samples)
                
                combined = np.vstack(all_samples)
                encoded = self._encode_facial_data(combined)
                
                student_data = {
                    'user_id': user_id,
                    'name': name,
                    'face_encoding': encoded,
                    'sample_count': combined.shape[0],
                    'pixels_per_sample': combined.shape[1],
                    'collected_at': datetime.now().isoformat(),
                    'num_photos': len(self.captured_photos)
                }
                
                # Update UI in main thread
                self.root.after(0, lambda: self._on_process_success(student_data))
                
            except Exception as ex:
                error_msg = str(ex)
                self.root.after(0, lambda msg=error_msg: self._on_process_error(msg))
        
        threading.Thread(target=process_thread, daemon=True).start()
    
    def _on_process_success(self, student_data):
        """Handle successful processing."""
        self.collected_students.append(student_data)
        self.students_listbox.insert(tk.END, f"{student_data['name']} (ID: {student_data['user_id']}) - {student_data['sample_count']} samples")
        
        # Reset for next student
        self.captured_photos = []
        self.user_id_var.set("")
        self.name_var.set("")
        self.photo_count_var.set("Photos: 0")
        self._update_thumbnails()
        
        self.process_btn.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.NORMAL)
        
        self.status_var.set(f"Student '{student_data['name']}' processed successfully!")
        messagebox.showinfo("Success", f"Processed {student_data['sample_count']} samples for {student_data['name']}")
    
    def _on_process_error(self, error_msg):
        """Handle processing error."""
        self.process_btn.config(state=tk.NORMAL)
        self.status_var.set("Processing failed")
        messagebox.showerror("Error", f"Processing failed: {error_msg}")
    
    def _generate_augmented_samples(self, face_img, num_samples=100):
        """Generate augmented samples (7500 pixels each)."""
        all_samples = []
        base_face = cv2.resize(face_img, (60, 60))
        
        if len(base_face.shape) == 2:
            base_face = cv2.cvtColor(base_face, cv2.COLOR_GRAY2BGR)
        
        for i in range(num_samples):
            aug = base_face.copy()
            
            # Scale
            scale = np.random.uniform(0.8, 1.2)
            new_size = int(60 * scale)
            if new_size > 20:
                scaled = cv2.resize(aug, (new_size, new_size))
                if new_size >= 60:
                    s = (new_size - 60) // 2
                    aug = scaled[s:s+60, s:s+60]
                else:
                    p = (60 - new_size) // 2
                    aug = cv2.copyMakeBorder(scaled, p, p, p, p, cv2.BORDER_REPLICATE)
                    aug = cv2.resize(aug, (60, 60))
            
            # Brightness
            brightness = np.random.randint(-40, 40)
            aug = np.clip(aug.astype(np.int16) + brightness, 0, 255).astype(np.uint8)
            
            # Contrast
            if i % 4 == 0:
                alpha = np.random.uniform(0.7, 1.3)
                aug = np.clip(alpha * aug, 0, 255).astype(np.uint8)
            
            # Rotation
            if i % 3 == 0:
                angle = np.random.uniform(-20, 20)
                M = cv2.getRotationMatrix2D((30, 30), angle, 1.0)
                aug = cv2.warpAffine(aug, M, (60, 60), borderMode=cv2.BORDER_REPLICATE)
            
            # Flip
            if np.random.random() > 0.5:
                aug = cv2.flip(aug, 1)
            
            # Final resize and flatten
            final = cv2.resize(aug, (self.FACE_SIZE, self.FACE_SIZE))
            all_samples.append(final.flatten())
        
        return np.array(all_samples, dtype=np.uint8)
    
    def _encode_facial_data(self, samples_array):
        """Encode facial data with SHAPE header."""
        rows, cols = samples_array.shape
        shape_header = f"SHAPE:{rows},{cols};".encode('utf-8')
        compressed = zlib.compress(samples_array.tobytes())
        full_data = shape_header + compressed
        return base64.b64encode(full_data).decode('utf-8')
    
    def _save_collection(self):
        """Save collected data to JSON file."""
        if not self.collected_students:
            messagebox.showwarning("Warning", "No students collected yet")
            return
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile="facial_data_bulk.json"
        )
        
        if not filepath:
            return
        
        output = {
            'version': '2.0',
            'format': 'color_50x50x3',
            'pixels_per_sample': self.PIXELS_PER_SAMPLE,
            'created_at': datetime.now().isoformat(),
            'total_students': len(self.collected_students),
            'students': self.collected_students
        }
        
        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)
        
        self.status_var.set(f"Saved {len(self.collected_students)} students to {filepath}")
        messagebox.showinfo("Success", f"Saved {len(self.collected_students)} students to {filepath}")
    
    # ==================== Import Functions ====================
    
    def _browse_file(self):
        """Browse for JSON file."""
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filepath:
            self.file_path_var.set(filepath)
    
    def _log(self, message):
        """Add message to import log."""
        self.import_log.config(state=tk.NORMAL)
        self.import_log.insert(tk.END, message + "\n")
        self.import_log.see(tk.END)
        self.import_log.config(state=tk.DISABLED)
    
    def _import_data(self):
        """Import data to database."""
        filepath = self.file_path_var.get()
        
        if not os.path.exists(filepath):
            messagebox.showerror("Error", f"File not found: {filepath}")
            return
        
        self._log(f"\n{'='*50}")
        self._log(f"Importing from: {filepath}")
        self._log(f"Skip existing: {self.skip_existing_var.get()}")
        self._log(f"Dry run: {self.dry_run_var.get()}")
        self._log(f"{'='*50}\n")
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            students = data.get('students', [])
            self._log(f"Found {len(students)} students in file")
            self._log(f"Format: {data.get('format', 'unknown')}")
            self._log(f"Pixels per sample: {data.get('pixels_per_sample', 'unknown')}\n")
            
            # Try to import
            try:
                from bulk_facial_data_importer import BulkFacialDataImporter
                importer = BulkFacialDataImporter(filepath)
                imported, skipped, errors = importer.import_data(
                    skip_existing=self.skip_existing_var.get(),
                    dry_run=self.dry_run_var.get()
                )
                
                self._log(f"\n{'='*50}")
                self._log(f"RESULTS:")
                self._log(f"  Imported: {imported}")
                self._log(f"  Skipped: {skipped}")
                self._log(f"  Errors: {errors}")
                self._log(f"{'='*50}\n")
                
                if not self.dry_run_var.get():
                    messagebox.showinfo("Import Complete", 
                                       f"Imported: {imported}\nSkipped: {skipped}\nErrors: {errors}")
                else:
                    messagebox.showinfo("Dry Run Complete", 
                                       f"Would import: {imported}\nWould skip: {skipped}\nErrors: {errors}")
                
            except ImportError:
                self._log("⚠️ bulk_facial_data_importer not found")
                self._log("Falling back to direct database import...\n")
                self._direct_import(students)
            
        except Exception as e:
            self._log(f"❌ Error: {e}")
            messagebox.showerror("Error", str(e))
    
    def _direct_import(self, students):
        """Direct import without using the importer module."""
        self._log("Direct import requires database connection.")
        self._log("Please use the importer script or configure database connection.")
    
    def _verify_import(self):
        """Verify imported data."""
        filepath = self.file_path_var.get()
        
        if not os.path.exists(filepath):
            messagebox.showerror("Error", f"File not found: {filepath}")
            return
        
        self._log(f"\n{'='*50}")
        self._log(f"Verifying import from: {filepath}")
        self._log(f"{'='*50}\n")
        
        try:
            from bulk_facial_data_importer import BulkFacialDataImporter
            importer = BulkFacialDataImporter(filepath)
            importer.verify_import()
            self._log("\nVerification complete - check above for results")
            
        except ImportError:
            self._log("⚠️ bulk_facial_data_importer not found")
            messagebox.showwarning("Warning", "Importer module not found")
        except Exception as e:
            self._log(f"❌ Error: {e}")
            messagebox.showerror("Error", str(e))
    
    # ==================== Cleanup ====================
    
    def _on_close(self):
        """Handle window close."""
        self._stop_camera()
        self.root.destroy()
    
    def run(self):
        """Run the application."""
        self.root.mainloop()


def main():
    print("\n" + "="*60)
    print("   BULK FACIAL DATA COLLECTION GUI")
    print("   Format: 50×50×3 color (7500 pixels per sample)")
    print("="*60 + "\n")
    
    app = BulkFacialDataGUI()
    app.run()


if __name__ == '__main__':
    main()