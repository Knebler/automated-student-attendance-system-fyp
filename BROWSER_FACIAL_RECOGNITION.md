# Browser-Based Facial Recognition for Attendance

## Overview

The attendance system now uses **browser-based facial recognition** - no separate Python client needed! Everything runs through the web interface.

## How It Works

```
┌─────────────────┐         ┌──────────────────┐
│  Web Browser    │────────▶│   Flask Server   │
│  (Lecturer)     │         │   (Render)       │
│                 │         │                  │
│  1. Open Camera │  HTTP   │  1. Receive      │
│  2. Capture     │  POST   │     Frame        │
│  3. Send Frame  │─ image─▶│  2. Detect Face  │
│                 │         │  3. Recognize    │
│                 │◀─JSON───│  4. Mark Present │
│  4. Update UI   │         │  5. Return       │
└─────────────────┘         └──────────────────┘
```

## Features

✅ **No Installation** - Works entirely in browser  
✅ **Real-time Recognition** - Captures every 2 seconds  
✅ **HTTPS Compatible** - Runs on Render  
✅ **Mobile Friendly** - Works on tablets/phones  
✅ **Automatic Marking** - Attendance saved instantly  
✅ **Live Updates** - UI refreshes automatically  

## Usage

### For Lecturers

1. **Login** to the web interface
2. Go to **Attendance Management** for your class
3. Click **"Face Recognition"** button
4. Click **"Start Camera"**
5. Position students in front of camera
6. System automatically:
   - Detects faces
   - Recognizes students
   - Marks attendance
   - Shows status in real-time

### Technical Flow

1. **Camera Access**
   ```javascript
   navigator.mediaDevices.getUserMedia({ video: true })
   ```

2. **Frame Capture** (every 2 seconds)
   ```javascript
   canvas.drawImage(video, 0, 0)
   canvas.toBlob(blob => sendToServer(blob))
   ```

3. **Server Processing**
   ```python
   - Receive image
   - Detect faces (Haar Cascade)
   - Extract features (50x50 normalized)
   - Match against KNN model
   - Mark attendance if confidence > 85%
   ```

4. **Response**
   ```json
   {
     "success": true,
     "recognized": true,
     "students": [{
       "name": "John Doe",
       "student_id": 123,
       "status": "present",
       "confidence": 0.92
     }]
   }
   ```

## API Endpoint

**POST** `/api/attendance/recognize-face`

**Headers:**
- `Content-Type: multipart/form-data`
- `X-CSRFToken: <token>`

**Body:**
- `image`: JPEG blob from canvas
- `class_id`: Session/class identifier

**Response:**
```json
{
  "success": true,
  "recognized": true,
  "students": [
    {
      "name": "Student Name",
      "student_id": 123,
      "status": "present",
      "confidence": 0.92,
      "distance": 1234.5
    }
  ],
  "count": 1
}
```

## Configuration

### Recognition Thresholds (server-side)

```python
CONFIDENCE_THRESHOLD = 0.85  # 85% minimum confidence
MAX_DISTANCE = 3500         # Maximum KNN distance
MIN_NEIGHBORS = 5           # KNN neighbors
```

### Capture Settings (client-side)

```javascript
CAPTURE_INTERVAL = 2000     // Capture every 2 seconds
VIDEO_WIDTH = 640          // Camera resolution
VIDEO_HEIGHT = 480
JPEG_QUALITY = 0.8         // Image compression
```

## Advantages Over Python Client

| Feature | Python Client | Browser Solution |
|---------|--------------|------------------|
| Installation | Required | None |
| Platform | Windows/Mac/Linux | Any with browser |
| Updates | Manual | Automatic |
| Deployment | Local machine | Cloud (Render) |
| Access | Local only | Remote capable |
| Mobile | No | Yes |

## Security

✅ **Authentication Required** - Lecturer/admin only  
✅ **Session-based** - CSRF protection  
✅ **HTTPS Only** - Camera requires secure context  
✅ **Server-side Processing** - No client-side model exposure  

## Browser Compatibility

- ✅ Chrome 53+
- ✅ Firefox 36+
- ✅ Safari 11+
- ✅ Edge 12+
- ⚠️ **Requires HTTPS** (works on localhost for testing)

## Troubleshooting

### Camera Won't Start

**Issue:** "Camera access not supported"  
**Fix:** Ensure you're using HTTPS (Render provides this automatically)

### Permission Denied

**Issue:** Browser blocks camera  
**Fix:** Click camera icon in address bar, allow access

### No Faces Detected

**Issue:** Recognition not working  
**Fix:**
1. Ensure good lighting
2. Position face clearly in frame
3. Check server logs for errors

### Low Confidence

**Issue:** Students not recognized  
**Fix:**
1. Ensure students have training data
2. Check image quality
3. Verify facial data in database

## Development Testing

### Local Testing (HTTP)

```bash
# Start Flask app
python app.py

# Access at http://localhost:5000
# Camera will work on localhost even without HTTPS
```

### Production (HTTPS)

```bash
# Deploy to Render
git push

# Access at https://your-app.onrender.com
# Camera will work automatically
```

## Performance

- **Frame Capture:** ~2 FPS
- **Recognition Time:** < 1 second per frame
- **Network:** ~50KB per request
- **Bandwidth:** ~25 KB/s average

## Future Enhancements

Potential improvements:

1. **Client-side Detection** - Use TensorFlow.js for face detection in browser
2. **WebRTC Optimization** - Reduce bandwidth with compression
3. **Batch Recognition** - Handle multiple faces per frame
4. **Anti-spoofing** - Add liveness detection
5. **WebSocket** - Real-time bidirectional communication

## Migration Note

This replaces the previous `attendance_client.py` system. The camera polling functionality has been removed in favor of this browser-based approach.

**No longer needed:**
- ❌ `attendance_client.py --poll`
- ❌ `camera_commands` table
- ❌ Remote camera trigger button
- ❌ Local client installation

**Now available:**
- ✅ Click button in web interface
- ✅ Instant camera access
- ✅ Works from anywhere
- ✅ No setup required
