# Bulk Facial Data Collection & Import System

Independent system for collecting and importing facial data in bulk, using the same mechanisms as the main attendance system.

## Overview

This system consists of two standalone scripts:

1. **`bulk_facial_data_collector.py`** - Collect facial data from multiple students
2. **`bulk_facial_data_importer.py`** - Import collected data into the database

## Features

- ✅ Uses same OpenCV processing as main system (40×40 images, 50 samples, zlib compression)
- ✅ Collect from webcam OR image files
- ✅ Store data in portable JSON format
- ✅ Bulk import with user ID matching
- ✅ Update existing records or skip them
- ✅ Dry-run mode for testing
- ✅ Verification of imported data

---

## Quick Start - GUI Application

### Launch the GUI (Recommended)

```bash
python bulk_facial_data_gui.py
```

**Features:**
- 📸 **Collection Tab** - Live webcam capture with face detection preview
- 📥 **Import Tab** - Import saved data into database with verification
- Real-time face detection overlay
- Photo counter and progress tracking
- Automatic processing and validation
- Easy file management

---

## 1. Data Collection

### GUI Mode (Recommended)

```bash
python bulk_facial_data_gui.py
```

**Collection Tab Workflow:**
1. Click "Start Camera"
2. Enter User ID and Name
3. Click "Capture Photo" for each photo (minimum 3)
4. Click "Process & Save Student"
5. Repeat for more students
6. Click "Save Collection to File" when done

### Command-Line Interactive Mode

```bash
python bulk_facial_data_collector.py
```

**Menu Options:**
1. Collect from webcam - Live capture for each student
2. Collect from image files - Process existing photos
3. Save and exit - Saves to `facial_data_bulk.json`
4. Exit without saving

**Webcam Capture:**
- Enter student's **User ID** (must match database)
- Enter student's **Name**
- Press **SPACE** to capture each photo
- Press **ENTER** when done (minimum 3 photos)
- Press **ESC** to cancel

### Programmatic Usage

```python
from bulk_facial_data_collector import BulkFacialDataCollector

collector = BulkFacialDataCollector(output_file='my_data.json')

# Collect from webcam
collector.collect_from_webcam(
    user_id=1001,
    name="John Doe",
    num_photos=5
)

# Collect from image files
collector.collect_from_images(
    user_id=1002,
    name="Jane Smith",
    image_paths=['photo1.jpg', 'photo2.jpg', 'photo3.jpg']
)

# Save to file
collector.save_to_file()
```

### Batch Processing from Folders

```python
import os
from bulk_facial_data_collector import BulkFacialDataCollector

collector = BulkFacialDataCollector()

# Example: Process folders named by user ID
base_dir = 'student_photos'
for folder in os.listdir(base_dir):
    user_id = int(folder)  # Folder name = user ID
    name = f"Student_{user_id}"
    
    folder_path = os.path.join(base_dir, folder)
    image_files = [os.path.join(folder_path, f) 
                   for f in os.listdir(folder_path)
                   if f.endswith(('.jpg', '.png'))]
    
    collector.collect_from_images(user_id, name, image_files)

collector.save_to_file()
```

---

## 2. Data Import

### GUI Mode (Recommended)

```bash
python bulk_facial_data_gui.py
```

**Import Tab Workflow:**
1. Click "Browse..." to select JSON file (or use default)
2. Choose options:
   - ☑ Skip existing records (don't update)
   - ☑ Dry run (test mode - don't save)
3. Click "Import Data"
4. Review log output
5. Click "Verify Import" to check results

### Command-Line Basic Import

```bash
# Import data (updates existing records)
python bulk_facial_data_importer.py facial_data_bulk.json
```

### Import Options

```bash
# Skip users who already have facial data
python bulk_facial_data_importer.py --skip-existing

# Dry run (test without saving)
python bulk_facial_data_importer.py --dry-run

# Verify imported data
python bulk_facial_data_importer.py --verify
```

### Programmatic Usage

```python
from bulk_facial_data_importer import BulkFacialDataImporter

importer = BulkFacialDataImporter('facial_data_bulk.json')

# Import with options
importer.import_data(
    skip_existing=False,  # Update existing records
    dry_run=False         # Commit to database
)

# Verify import
importer.verify_import()
```

---

## Output File Format

The collection script creates a JSON file with this structure:

```json
{
  "version": "1.0",
  "created_at": "2026-02-01T10:30:00",
  "total_students": 2,
  "students": [
    {
      "user_id": 1001,
      "name": "John Doe",
      "face_encoding": "U0hBUEU6NTAsMTYwMDtxBWkAYgJ...",
      "sample_count": 50,
      "collected_at": "2026-02-01T10:25:00",
      "num_photos": 5
    },
    {
      "user_id": 1002,
      "name": "Jane Smith",
      "face_encoding": "U0hBUEU6NTAsMTYwMDteXcRz...",
      "sample_count": 50,
      "collected_at": "2026-02-01T10:28:00",
      "num_photos": 4
    }
  ]
}
```

**Key Fields:**
- `user_id` - Must match User table in database
- `face_encoding` - Base64-encoded compressed facial data (SHAPE header + zlib)
- `sample_count` - Number of augmented samples (typically 50)
- `num_photos` - Original photos captured

---

## Workflow Examples

### Example 1: On-site Registration Event

```bash
# Day 1: Collect data from students
python bulk_facial_data_collector.py
# - Capture 5 photos per student using webcam
# - Save to facial_data_bulk.json

# Day 2: Import to database
python bulk_facial_data_importer.py facial_data_bulk.json
```

### Example 2: Import from ID Card Photos

```python
# Organize photos: student_photos/1001/photo.jpg, student_photos/1002/photo.jpg, etc.
from bulk_facial_data_collector import BulkFacialDataCollector
import os

collector = BulkFacialDataCollector('id_cards_import.json')

for user_folder in os.listdir('student_photos'):
    user_id = int(user_folder)
    photos = [f'student_photos/{user_folder}/{f}' 
              for f in os.listdir(f'student_photos/{user_folder}')]
    
    # Get name from database or CSV
    name = get_student_name(user_id)  # Your function
    
    collector.collect_from_images(user_id, name, photos)

collector.save_to_file()
```

```bash
# Import to database
python bulk_facial_data_importer.py id_cards_import.json
```

### Example 3: Safe Testing

```bash
# Test import without committing
python bulk_facial_data_importer.py --dry-run

# If successful, do real import
python bulk_facial_data_importer.py

# Verify everything imported correctly
python bulk_facial_data_importer.py --verify
```

---

## Technical Details

### Data Processing Pipeline

Same as main system (`student_boundary.py`):

1. **Face Detection** - Haar Cascade or center crop fallback
2. **Augmentation** - Random flips, rotations (±15°)
3. **Resize** - 40×40 pixels per sample
4. **Sampling** - Exactly 50 samples per student
5. **Compression** - zlib with SHAPE header
6. **Encoding** - Base64 for JSON storage

### Database Schema

Imports into `FacialData` table:
- `user_id` (FK to User table)
- `face_encoding` (BLOB - compressed binary)
- `sample_count` (INT)
- `is_active` (BOOLEAN)
- `created_at`, `updated_at` (TIMESTAMP)

### Compatibility

✅ **Compatible** - OpenCV-based attendance system  
❌ **Incompatible** - face-api.js encodings (different format)

---

## Error Handling

The importer provides detailed feedback:

- **User not found** - User ID doesn't exist in database
- **Decode failed** - Corrupted or invalid facial data
- **Commit failed** - Database transaction error

All errors are logged with student names for easy debugging.

---

## Best Practices

1. **Always test first** - Use `--dry-run` before real import
2. **Verify after import** - Use `--verify` to check data
3. **Backup database** - Before bulk imports
4. **User ID accuracy** - Double-check user IDs match database
5. **Photo quality** - Well-lit, front-facing photos work best
6. **Minimum photos** - At least 3-5 photos per student

---

## Troubleshooting

### "Face detector not found"
- System will use center crop fallback
- Works fine but less accurate face detection
- Copy `haarcascade_frontalface_default.xml` to project root

### "User ID not found in database"
- User must exist in database before importing facial data
- Create user accounts first, then import facial data

### "No faces detected"
- Check photo quality and lighting
- Ensure faces are clearly visible
- System will fall back to center crop

### Import shows 0 imported
- Check if `--skip-existing` is enabled
- Use `--dry-run` to see what would happen
- Verify user IDs exist in database

---

## License

Same as main project (see LICENSE file)
