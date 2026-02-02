"""
Bulk Facial Data Collection & Import - GUI Application
Simple user interface for collecting and importing facial data
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import cv2
from PIL import Image, ImageTk
import threading
import queue
import os
from datetime import datetime
from bulk_facial_data_collector import BulkFacialDataCollector
from bulk_facial_data_importer import BulkFacialDataImporter


class BulkFacialDataGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Bulk Facial Data Manager")
        self.root.geometry("900x700")
        
        # Initialize variables
        self.collector = BulkFacialDataCollector()
        self.cap = None
        self.is_capturing = False
        self.captured_frames = []
        self.current_user_id = None
        self.current_name = None
        self.log_queue = queue.Queue()
        
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create tabs
        self.collection_tab = ttk.Frame(self.notebook)
        self.import_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.collection_tab, text="📸 Collect Data")
        self.notebook.add(self.import_tab, text="📥 Import Data")
        
        # Build interfaces
        self.build_collection_interface()
        self.build_import_interface()
        
        # Start log processor
        self.process_logs()
    
    def build_collection_interface(self):
        """Build the data collection interface"""
        main_frame = ttk.Frame(self.collection_tab)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Left panel - Camera
        left_panel = ttk.LabelFrame(main_frame, text="Camera Preview", padding=10)
        left_panel.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        # Camera controls (moved to top)
        camera_controls = ttk.Frame(left_panel)
        camera_controls.pack(fill='x', pady=(0, 5))
        
        self.start_camera_btn = ttk.Button(camera_controls, text="▶ Start Camera", 
                                           command=self.start_camera)
        self.start_camera_btn.pack(side='left', padx=2, expand=True, fill='x')
        
        self.stop_camera_btn = ttk.Button(camera_controls, text="⏸ Stop Camera", 
                                          command=self.stop_camera, state='disabled')
        self.stop_camera_btn.pack(side='left', padx=2, expand=True, fill='x')
        
        self.capture_btn = ttk.Button(camera_controls, text="📸 Capture Photo", 
                                      command=self.capture_photo, state='disabled')
        self.capture_btn.pack(side='left', padx=2, expand=True, fill='x')
        
        # Camera display
        self.camera_label = tk.Label(left_panel, bg='black', text="Camera Off\n\nClick 'Start Camera' to begin", 
                                     fg='white', font=('Arial', 14))
        self.camera_label.pack(pady=5, fill='both', expand=True)
        
        # Photo counter
        self.photo_count_label = tk.Label(left_panel, text="Photos captured: 0", 
                                         font=('Arial', 12, 'bold'))
        self.photo_count_label.pack(pady=5)
        
        # Right panel - Student info and controls
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side='right', fill='both', padx=(5, 0))
        
        # Student info
        info_frame = ttk.LabelFrame(right_panel, text="Student Information", padding=10)
        info_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(info_frame, text="User ID:").grid(row=0, column=0, sticky='w', pady=5)
        self.user_id_entry = ttk.Entry(info_frame, width=25)
        self.user_id_entry.grid(row=0, column=1, pady=5, padx=5)
        
        ttk.Label(info_frame, text="Name:").grid(row=1, column=0, sticky='w', pady=5)
        self.name_entry = ttk.Entry(info_frame, width=25)
        self.name_entry.grid(row=1, column=1, pady=5, padx=5)
        
        # Action buttons
        action_frame = ttk.LabelFrame(right_panel, text="Actions", padding=10)
        action_frame.pack(fill='x', pady=(0, 10))
        
        self.process_btn = ttk.Button(action_frame, text="✓ Process & Save Student", 
                                      command=self.process_student, state='disabled')
        self.process_btn.pack(fill='x', pady=2)
        
        self.clear_btn = ttk.Button(action_frame, text="🗑 Clear Photos", 
                                    command=self.clear_photos, state='disabled')
        self.clear_btn.pack(fill='x', pady=2)
        
        ttk.Separator(action_frame, orient='horizontal').pack(fill='x', pady=10)
        
        self.save_file_btn = ttk.Button(action_frame, text="💾 Save Collection to File", 
                                        command=self.save_collection_file)
        self.save_file_btn.pack(fill='x', pady=2)
        
        # Statistics
        stats_frame = ttk.LabelFrame(right_panel, text="Statistics", padding=10)
        stats_frame.pack(fill='x', pady=(0, 10))
        
        self.stats_label = tk.Label(stats_frame, text="Students collected: 0", 
                                    justify='left', anchor='w')
        self.stats_label.pack(fill='x')
        
        # Collection log
        log_frame = ttk.LabelFrame(right_panel, text="Log", padding=5)
        log_frame.pack(fill='both', expand=True)
        
        self.collection_log = scrolledtext.ScrolledText(log_frame, height=10, width=40)
        self.collection_log.pack(fill='both', expand=True)
    
    def build_import_interface(self):
        """Build the import interface"""
        main_frame = ttk.Frame(self.import_tab)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # File selection
        file_frame = ttk.LabelFrame(main_frame, text="Select File", padding=10)
        file_frame.pack(fill='x', pady=(0, 10))
        
        self.import_file_path = tk.StringVar(value="facial_data_bulk.json")
        
        ttk.Label(file_frame, text="JSON File:").pack(side='left', padx=5)
        ttk.Entry(file_frame, textvariable=self.import_file_path, width=50).pack(side='left', padx=5, fill='x', expand=True)
        ttk.Button(file_frame, text="Browse...", command=self.browse_import_file).pack(side='left', padx=5)
        
        # Import options
        options_frame = ttk.LabelFrame(main_frame, text="Import Options", padding=10)
        options_frame.pack(fill='x', pady=(0, 10))
        
        self.skip_existing_var = tk.BooleanVar(value=False)
        self.dry_run_var = tk.BooleanVar(value=False)
        
        ttk.Checkbutton(options_frame, text="Skip existing records", 
                       variable=self.skip_existing_var).pack(anchor='w', pady=2)
        ttk.Checkbutton(options_frame, text="Dry run (test mode - don't save)", 
                       variable=self.dry_run_var).pack(anchor='w', pady=2)
        
        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Button(button_frame, text="📥 Import Data", 
                  command=self.import_data).pack(side='left', padx=5)
        ttk.Button(button_frame, text="✓ Verify Import", 
                  command=self.verify_import).pack(side='left', padx=5)
        
        # Import log
        log_frame = ttk.LabelFrame(main_frame, text="Import Log", padding=5)
        log_frame.pack(fill='both', expand=True)
        
        self.import_log = scrolledtext.ScrolledText(log_frame, height=20)
        self.import_log.pack(fill='both', expand=True)
    
    def start_camera(self):
        """Start camera capture"""
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            messagebox.showerror("Error", "Cannot open camera")
            return
        
        self.is_capturing = True
        self.start_camera_btn.config(state='disabled')
        self.stop_camera_btn.config(state='normal')
        self.capture_btn.config(state='normal')
        
        self.update_camera()
        self.log("Camera started")
    
    def stop_camera(self):
        """Stop camera capture"""
        self.is_capturing = False
        if self.cap:
            self.cap.release()
        
        self.camera_label.config(image='', text="Camera Off\n\nClick 'Start Camera' to begin")
        self.start_camera_btn.config(state='normal')
        self.stop_camera_btn.config(state='disabled')
        self.capture_btn.config(state='disabled')
        
        self.log("Camera stopped")
    
    def update_camera(self):
        """Update camera feed"""
        if self.is_capturing and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                # Detect faces for preview
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                if self.collector.face_cascade is not None:
                    faces = self.collector.face_cascade.detectMultiScale(gray, 1.05, 3, minSize=(30, 30))
                    for (x, y, w, h) in faces:
                        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                # Convert to PhotoImage
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                
                # Resize to fit window while maintaining aspect ratio
                img.thumbnail((640, 480), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image=img)
                
                self.camera_label.config(image=photo, text='')
                self.camera_label.image = photo
            
            self.root.after(10, self.update_camera)
    
    def capture_photo(self):
        """Capture current frame"""
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                self.captured_frames.append(frame)
                count = len(self.captured_frames)
                self.photo_count_label.config(text=f"Photos captured: {count}")
                self.log(f"Photo {count} captured")
                
                if count >= 3:
                    self.process_btn.config(state='normal')
                    self.clear_btn.config(state='normal')
    
    def clear_photos(self):
        """Clear captured photos"""
        self.captured_frames = []
        self.photo_count_label.config(text="Photos captured: 0")
        self.process_btn.config(state='disabled')
        self.clear_btn.config(state='disabled')
        self.log("Photos cleared")
    
    def process_student(self):
        """Process student facial data"""
        user_id = self.user_id_entry.get().strip()
        name = self.name_entry.get().strip()
        
        if not user_id or not name:
            messagebox.showerror("Error", "Please enter User ID and Name")
            return
        
        try:
            user_id = int(user_id)
        except ValueError:
            messagebox.showerror("Error", "User ID must be a number")
            return
        
        if len(self.captured_frames) < 3:
            messagebox.showerror("Error", "Need at least 3 photos")
            return
        
        # Process in thread to avoid blocking UI
        self.log(f"Processing {name} (ID: {user_id})...")
        self.process_btn.config(state='disabled')
        
        def process_thread():
            try:
                result = self.collector._process_photos(user_id, name, self.captured_frames, 
                                                       samples_per_photo=50//len(self.captured_frames))
                
                if result:
                    self.collector.data_collection.append(result)
                    self.root.after(0, lambda: self.on_process_complete(name, result['sample_count']))
                else:
                    self.root.after(0, lambda: self.on_process_error("Failed to process photos"))
            except Exception as e:
                self.root.after(0, lambda: self.on_process_error(str(e)))
        
        threading.Thread(target=process_thread, daemon=True).start()
    
    def on_process_complete(self, name, sample_count):
        """Callback when processing completes"""
        self.log(f"✓ {name} processed successfully ({sample_count} samples)")
        self.stats_label.config(text=f"Students collected: {len(self.collector.data_collection)}")
        
        # Clear for next student
        self.clear_photos()
        self.user_id_entry.delete(0, tk.END)
        self.name_entry.delete(0, tk.END)
        
        messagebox.showinfo("Success", f"{name} added successfully!\n{sample_count} samples generated")
    
    def on_process_error(self, error_msg):
        """Callback when processing fails"""
        self.log(f"✗ Error: {error_msg}")
        self.process_btn.config(state='normal')
        messagebox.showerror("Error", f"Failed to process student:\n{error_msg}")
    
    def save_collection_file(self):
        """Save collection to file"""
        if len(self.collector.data_collection) == 0:
            messagebox.showwarning("Warning", "No data to save")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"facial_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        if filename:
            self.collector.output_file = filename
            if self.collector.save_to_file():
                self.log(f"✓ Saved to {os.path.basename(filename)}")
                messagebox.showinfo("Success", 
                                   f"Saved {len(self.collector.data_collection)} student(s) to:\n{filename}")
            else:
                messagebox.showerror("Error", "Failed to save file")
    
    def browse_import_file(self):
        """Browse for import file"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.import_file_path.set(filename)
    
    def import_data(self):
        """Import data from file"""
        file_path = self.import_file_path.get()
        
        if not os.path.exists(file_path):
            messagebox.showerror("Error", f"File not found: {file_path}")
            return
        
        self.import_log.delete(1.0, tk.END)
        
        # Import in thread
        def import_thread():
            importer = BulkFacialDataImporter(file_path)
            
            # Redirect output to log
            import sys
            from io import StringIO
            
            old_stdout = sys.stdout
            sys.stdout = StringIO()
            
            try:
                success = importer.import_data(
                    skip_existing=self.skip_existing_var.get(),
                    dry_run=self.dry_run_var.get()
                )
                
                output = sys.stdout.getvalue()
                sys.stdout = old_stdout
                
                self.root.after(0, lambda: self.on_import_complete(output, success))
            except Exception as e:
                sys.stdout = old_stdout
                self.root.after(0, lambda: self.on_import_error(str(e)))
        
        threading.Thread(target=import_thread, daemon=True).start()
    
    def on_import_complete(self, output, success):
        """Callback when import completes"""
        self.import_log.insert(tk.END, output)
        self.import_log.see(tk.END)
        
        if success:
            messagebox.showinfo("Success", "Import completed successfully!")
        else:
            messagebox.showwarning("Warning", "Import completed with errors. Check log for details.")
    
    def on_import_error(self, error_msg):
        """Callback when import fails"""
        self.import_log.insert(tk.END, f"ERROR: {error_msg}\n")
        messagebox.showerror("Error", f"Import failed:\n{error_msg}")
    
    def verify_import(self):
        """Verify imported data"""
        file_path = self.import_file_path.get()
        
        if not os.path.exists(file_path):
            messagebox.showerror("Error", f"File not found: {file_path}")
            return
        
        self.import_log.delete(1.0, tk.END)
        
        # Verify in thread
        def verify_thread():
            importer = BulkFacialDataImporter(file_path)
            
            import sys
            from io import StringIO
            
            old_stdout = sys.stdout
            sys.stdout = StringIO()
            
            try:
                importer.verify_import()
                output = sys.stdout.getvalue()
                sys.stdout = old_stdout
                
                self.root.after(0, lambda: self.import_log.insert(tk.END, output))
                self.root.after(0, lambda: self.import_log.see(tk.END))
            except Exception as e:
                sys.stdout = old_stdout
                self.root.after(0, lambda: messagebox.showerror("Error", f"Verification failed:\n{str(e)}"))
        
        threading.Thread(target=verify_thread, daemon=True).start()
    
    def log(self, message):
        """Add message to collection log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.collection_log.insert(tk.END, f"[{timestamp}] {message}\n")
        self.collection_log.see(tk.END)
    
    def process_logs(self):
        """Process queued log messages"""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log(message)
        except queue.Empty:
            pass
        
        self.root.after(100, self.process_logs)
    
    def on_closing(self):
        """Handle window close"""
        self.stop_camera()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = BulkFacialDataGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == '__main__':
    main()
