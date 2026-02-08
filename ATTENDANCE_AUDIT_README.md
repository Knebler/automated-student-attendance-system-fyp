# Attendance Audit Feature Documentation

## Overview

The Attendance Audit feature allows Institution Admins to verify attendance records using facial recognition technology. This ensures that students who were marked as present actually attended the class and prevents proxy attendance.

## Features

### 1. Audit Status Tracking
Each attendance record now has three possible audit statuses:
- **No Audit**: Record has not been audited yet (default)
- **Pass**: Student verified successfully through facial recognition
- **Fail**: Student could not be verified or face didn't match

### 2. Individual Facial Recognition Audit
Audit students one at a time:
- Capture individual student photos
- Compare with registered facial data
- Get immediate pass/fail results with confidence scores

### 3. Bulk Class Audit
Audit the entire class at once with a single class photo:
- Capture one photo of all students present
- System detects all faces in the photo
- Automatically matches detected faces to registered students
- Students recognized in photo: **PASS**
- Students not detected in photo: **FAIL**
- View detailed results for each student

### 4. Manual Audit Override
Admins can manually mark records as Pass or Fail when:
- Facial recognition is unavailable
- Technical issues occur
- Special circumstances require manual review

## Database Changes

### New Fields in `attendance_records` Table

1. **audit_status** (ENUM): Current audit status
   - Values: 'no_audit', 'pass', 'fail'
   - Default: 'no_audit'

2. **audited_at** (DATETIME): Timestamp when audit was performed
   - Nullable

3. **audited_by** (INT): Foreign key to users table
   - References the admin who performed the audit
   - Nullable

## How to Use

### For Institution Admins

#### Option 1: Bulk Audit (Recommended for Full Classes)
1. Navigate to Attendance Management → Select a class → Click "🔍 Audit Attendance"
2. Click "📸 Bulk Audit Entire Class" button
3. Position camera to capture all students in the class
4. Ensure:
   - Good lighting conditions
   - Students' faces are clearly visible
   - No obstructions blocking faces
5. Click "📸 Capture Class Photo & Audit"
6. System will:
   - Detect all faces in the photo
   - Match faces with registered student data
   - Mark detected students as PASS
   - Mark undetected students as FAIL
7. View detailed results showing:
   - Total audited, passed, and failed counts
   - Faces detected in photo
   - Individual results for each student

#### Option 2: Individual Audit
1. On the audit page, click "📷 Audit" for a specific student
2. Camera modal will open
3. Ask the student to look at the camera
4. Click "📷 Capture & Audit"
5. System will:
   - Capture the image
   - Run facial recognition
   - Compare with registered facial data
   - Display Pass/Fail result with confidence score

#### Option 3: Manual Audit
If facial recognition fails or is unavailable:
1. Click "✓ Pass" to manually approve
2. Click "✗ Fail" to manually reject
3. Confirm your decision

### Audit Results
- **Pass (✓)**: Green badge - Student verified successfully
- **Fail (✗)**: Red badge - Verification failed
- **Not Audited (⏳)**: Yellow badge - Pending audit

## API Endpoints

### 1. View Audit Page
```
GET /institution/attendance/class/<class_id>/audit
```
**Access**: Institution Admin only
**Returns**: Audit page with attendance records

### 2. Audit with Facial Recognition
```
POST /institution/attendance/audit/<attendance_id>
Content-Type: application/json

{
  "image": "data:image/jpeg;base64,..."
}
```
**Returns**:
```json
{
  "success": true,
  "audit_result": "pass",
  "message": "Student verified successfully (85.3% confidence)",
  "confidence": 85.3,
  "recognized_name": "John Doe (ID: 123)",
  "attendance_id": 456
}
```

### 3. Manual Audit Update
```
POST /institution/attendance/audit/<attendance_id>/manual
Content-Type: application/json

{
  "audit_status": "pass"
}
```
**Returns**:
```json
{
  "success": true,
  "message": "Audit status updated to pass",
  "attendance_id": 456,
  "audit_status": "pass"
}
```

### 4. Bulk Audit Class
```
POST /institution/attendance/class/<class_id>/bulk-audit
Content-Type: application/json

{
  "image": "data:image/jpeg;base64,..."
}
```
**Description**: Audits all students in a class using a single class photo
**Returns**:
```json
{
  "success": true,
  "message": "Bulk audit completed: 25 passed, 3 failed",
  "audited_count": 28,
  "pass_count": 25,
  "fail_count": 3,
  "faces_detected": 26,
  "results": [
    {
      "attendance_id": 123,
      "student_id": 45,
      "student_name": "John Doe",
      "audit_result": "pass",
      "confidence": 87.5,
      "message": "Verified (87.5% confidence)"
    },
    {
      "attendance_id": 124,
      "student_id": 46,
      "student_name": "Jane Smith",
      "audit_result": "fail",
      "confidence": 0,
      "message": "Not detected in class photo"
    }
  ]
}
```

## Migration Instructions

### Apply Migration
To add audit fields to your database:

```bash
# Windows
cd database\migrations
python add_audit_fields_to_attendance_records.py

# Linux/Mac
cd database/migrations
python3 add_audit_fields_to_attendance_records.py
```

### Rollback Migration
If you need to remove the audit fields:

```bash
# Windows
python add_audit_fields_to_attendance_records.py --down

# Linux/Mac
python3 add_audit_fields_to_attendance_records.py --down
```

## Security Considerations

1. **Authorization**: Only Institution Admins can access audit functionality
2. **Institution Isolation**: Admins can only audit classes within their institution
3. **Audit Trail**: All audits record who performed them and when
4. **Camera Permissions**: Users must grant camera access for facial recognition

## Troubleshooting

### Camera Not Working
- Ensure browser has permission to access camera
- Check if another application is using the camera
- Try refreshing the page
- For bulk audit, ensure using a device with good camera quality

### Facial Recognition Fails
- Ensure proper lighting
- Student should face the camera directly
- Verify facial data is registered in the system
- Check if facial recognition service is initialized

### Bulk Audit Issues

**Not All Students Detected:**
- Ensure all students are in frame
- Check for proper lighting across the entire class
- Make sure faces aren't obstructed (masks, hats, hands)
- Try getting closer or using a higher resolution camera
- Students should face the camera

**Too Many False Positives/Negatives:**
- Improve lighting conditions
- Ensure students are clearly visible
- Verify quality of registered facial data
- Consider using individual audit for problem cases

**Low Faces Detected Count:**
- Students may be too far from camera
- Increase image resolution
- Ensure faces are at least 50x50 pixels in the photo
- Check for adequate lighting

### Low Confidence Scores
- Improve lighting conditions
- Ensure student is close enough to camera
- Verify quality of registered facial data
- Consider re-registering student's face

## Future Enhancements

Potential improvements for future versions:
1. ✅ **Bulk facial recognition audit using class photos** (IMPLEMENTED)
2. Automated periodic audits (scheduled audits)
3. Enhanced audit reports and analytics dashboard
4. Integration with attendance appeals system
5. Machine learning to improve recognition accuracy over time
6. Support for multiple face angles and poses
7. Liveness detection to prevent photo spoofing
8. Video-based audit (recording class sessions)
9. Export audit reports to PDF/Excel
10. Audit history and trend analysis

## Technical Details

### Confidence Threshold
- Minimum confidence: 70%
- Below threshold: Audit marked as FAIL
- Above threshold: Compared with expected student ID

### Facial Recognition Model
- Uses KNN (K-Nearest Neighbors) classifier
- Trained on registered student facial data
- Haar Cascade for face detection
- 50x50 pixel face image preprocessing

### Performance
- Average audit time: 2-3 seconds
- Concurrent audits: Supported
- Image format: JPEG (Base64 encoded)
- Max image size: Recommended < 5MB

## Support

For issues or questions:
1. Check system logs in `logs/` directory
2. Review facial recognition initialization logs
3. Contact system administrator
4. Submit issue to development team
