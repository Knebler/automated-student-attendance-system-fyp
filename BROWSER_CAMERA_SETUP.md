# Browser-Based Face Recognition Setup

## Overview
The facial recognition system now uses **browser-based camera access via WebRTC** instead of server-side camera access. This allows the system to work on cloud platforms like Render where physical cameras are not available.

## How It Works

### Architecture
1. **Browser Camera**: Uses `navigator.mediaDevices.getUserMedia()` to access the user's webcam
2. **Frame Capture**: Captures video frames at 2 FPS using HTML5 Canvas
3. **Server Processing**: Sends frames as base64-encoded images to the server
4. **Face Recognition**: Server processes frames using OpenCV and KNN classifier
5. **Real-time Updates**: Attendance is marked automatically and UI updates in real-time

### Components

#### Frontend (JavaScript/WebRTC)
- **File**: `templates/institution/lecturer/lecturer_attendance_management.html`
- **Camera Access**: Uses WebRTC to request user's camera permission
- **Frame Capture**: Draws video frames to canvas and converts to base64
- **Frame Rate**: 2 FPS (one frame every 500ms) to optimize bandwidth

#### Backend (Python/Flask)
- **File**: `browser_face_recognition.py` - Face recognition logic
- **File**: `attendance_ai_blueprint.py` - API endpoints

### API Endpoints

#### Initialize Session
```
POST /api/recognition/browser/init
Body: { "session_id": "123", "class_id": "123" }
```
Initializes face recognition session with training data for the class.

#### Process Frame
```
POST /api/recognition/browser/process
Body: { "frame": "data:image/jpeg;base64,..." }
```
Processes a single video frame and returns recognition results.

#### Get Statistics
```
GET /api/recognition/browser/stats
```
Returns current session statistics (students marked, etc.)

#### Stop Session
```
POST /api/recognition/browser/stop
```
Stops recognition and returns final statistics.

## Usage

### For Lecturers
1. Click **"Face Recognition"** button on attendance management page
2. Click **"Start Camera"** 
3. Browser will request camera permission - **Allow it**
4. Camera preview will appear showing live feed
5. System automatically recognizes and marks students
6. Click **"Stop Camera"** when done

### Browser Compatibility
- ✅ Chrome/Edge (recommended)
- ✅ Firefox
- ✅ Safari (iOS/macOS)
- ⚠️ Requires HTTPS in production (camera access security requirement)

## Deployment on Render

### Requirements
1. **HTTPS**: Browsers require HTTPS for camera access (Render provides this automatically)
2. **Python Packages**: Ensure `requirements.txt` includes:
   ```
   opencv-python-headless
   scikit-learn
   numpy
   ```
   Note: Use `opencv-python-headless` for cloud deployments (no GUI dependencies)

### Environment Setup
No special environment variables needed. The system automatically detects it's running in browser mode.

### Performance Considerations
- Frame processing at 2 FPS is optimal for bandwidth and accuracy
- Each frame is ~50-100 KB when base64 encoded
- Server processes frames using efficient KNN algorithm
- Automatic cleanup of old tracking data prevents memory leaks

## Security

### Camera Permissions
- Browser asks user for camera permission each time
- Camera access is only granted to the specific page
- User can revoke permission anytime via browser settings

### Data Privacy
- Video frames are processed in real-time
- No video recording or storage
- Only attendance records are saved to database
- Recognition confidence and distance metrics are logged for audit

## Troubleshooting

### Camera Not Starting
1. **Check browser permissions**: Ensure camera is allowed for the site
2. **HTTPS required**: Camera API only works on HTTPS (or localhost)
3. **Check browser console**: Look for error messages

### No Faces Detected
1. **Lighting**: Ensure adequate lighting on the face
2. **Distance**: Position face 1-2 feet from camera
3. **Face angle**: Look directly at camera
4. **Training data**: Ensure students have uploaded facial data

### Poor Recognition Accuracy
1. **Add more training samples**: Students should upload multiple photos
2. **Improve photo quality**: Good lighting, clear face shots
3. **Adjust thresholds**: Modify confidence threshold in `browser_face_recognition.py`

### Performance Issues
1. **Reduce frame rate**: Increase interval in `startFrameProcessing()` (default: 500ms)
2. **Lower image quality**: Reduce JPEG quality in `canvas.toDataURL('image/jpeg', 0.8)`
3. **Check server resources**: Ensure sufficient CPU/memory on Render

## Configuration

### Recognition Settings
Edit `browser_face_recognition.py`:

```python
# Recognition thresholds
self.CONFIDENCE_THRESHOLD = 0.70  # Lower = more lenient, Higher = stricter
self.MIN_MATCH_DISTANCE = 4000     # Higher = more lenient, Lower = stricter
self.FRAME_CONFIRMATION = 5        # Frames needed before marking (default: 5)

# Late detection
self.LATE_THRESHOLD_MINUTES = 30   # Minutes after class start = late
```

### Frame Processing Rate
Edit `lecturer_attendance_management.html`:

```javascript
// Process frames every 500ms (2 FPS)
state.frameProcessingInterval = setInterval(processCurrentFrame, 500);
```

## Advantages Over Desktop Camera

✅ **Cloud Compatible**: Works on Render and other cloud platforms  
✅ **No Installation**: No need for server-side camera hardware  
✅ **Cross-Platform**: Works on any device with a camera and browser  
✅ **Mobile Friendly**: Can use phone/tablet cameras  
✅ **Secure**: Browser-enforced camera permissions  
✅ **Scalable**: Each user uses their own camera  

## Migration Notes

### Old System (Desktop Camera)
- Required physical camera on server
- Used `cv2.VideoCapture(0)`
- Spawned subprocess for `attendance_client.py`
- Only worked locally

### New System (Browser Camera)
- Uses user's camera via WebRTC
- Processes frames server-side via API
- No subprocess needed
- Works anywhere (cloud/local)

The old desktop camera system is still available via the original endpoints if needed for local deployment.
