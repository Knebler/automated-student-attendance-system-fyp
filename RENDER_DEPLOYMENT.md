# Render Deployment Guide for Browser-Based Face Recognition

## Pre-Deployment Checklist

### 1. Update requirements.txt for Cloud
Replace `opencv-python` with `opencv-python-headless`:

```bash
# In requirements.txt, change:
opencv-python==4.8.1.78

# To:
opencv-python-headless==4.8.1.78
```

**Why?** `opencv-python-headless` doesn't include GUI dependencies (Qt, GTK) that aren't needed on servers and cause build failures.

### 2. Verify Dependencies
Ensure these are in `requirements.txt`:
```
Flask==3.0.0
opencv-python-headless==4.8.1.78
scikit-learn==1.3.2
numpy==1.26.4
Pillow==12.1.0
```

### 3. Check Environment Variables
In Render dashboard, set:
```
FLASK_ENV=production
MYSQL_HOST=<your-mysql-host>
MYSQL_USER=<your-mysql-user>
MYSQL_PASSWORD=<your-mysql-password>
MYSQL_DB=<your-database-name>
SECRET_KEY=<your-secret-key>
```

## Deployment Steps

### Step 1: Connect Repository
1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Select your branch (usually `main` or `master`)

### Step 2: Configure Service
```yaml
Name: attendance-system
Environment: Python 3
Region: Choose closest to your users
Branch: main
Build Command: pip install -r requirements.txt
Start Command: python app.py
```

### Step 3: Environment Variables
Add all required environment variables from `.env` file:
- Database credentials (MYSQL_*)
- API keys (STRIPE_*, etc.)
- SECRET_KEY
- Any other custom variables

### Step 4: Deploy
1. Click **"Create Web Service"**
2. Wait for build to complete (5-10 minutes)
3. Render will provide a URL: `https://your-app.onrender.com`

## Post-Deployment Testing

### Test 1: Health Check
```bash
curl https://your-app.onrender.com/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "success": true,
  "database": "Connected",
  "timestamp": "2026-01-30T..."
}
```

### Test 2: Browser Camera Access
1. Visit your app URL (must be HTTPS)
2. Login as a lecturer
3. Go to Attendance Management
4. Click "Face Recognition" → "Start Camera"
5. Browser should request camera permission
6. Grant permission and verify camera preview appears

### Test 3: Face Recognition
1. Position face in front of camera
2. System should detect and recognize enrolled students
3. Check attendance records are created in database
4. Verify real-time UI updates

## Common Deployment Issues

### Issue 1: OpenCV Build Failure
**Error**: `Building opencv-python-headless failed`

**Solution**:
1. Make sure you're using `opencv-python-headless` not `opencv-python`
2. Add to `requirements.txt` before opencv:
   ```
   numpy==1.26.4
   ```

### Issue 2: Camera Not Working
**Error**: Camera permission denied or not available

**Solutions**:
- ✅ Ensure site is using HTTPS (Render provides this automatically)
- ✅ Clear browser cache and cookies
- ✅ Try different browser (Chrome recommended)
- ✅ Check browser console for errors (F12)

### Issue 3: Database Connection Failed
**Error**: `No database session` or connection timeout

**Solutions**:
1. Verify environment variables are set correctly
2. Check database allows connections from Render IPs
3. Test database connection:
   ```bash
   curl https://your-app.onrender.com/api/ping
   ```

### Issue 4: Memory/CPU Limits
**Error**: Service crashes under load

**Solutions**:
1. Upgrade Render plan (free tier has limits)
2. Reduce frame processing rate:
   - Edit `lecturer_attendance_management.html`
   - Change `setInterval(processCurrentFrame, 500)` to `1000` (1 FPS)
3. Optimize image quality:
   - Change `canvas.toDataURL('image/jpeg', 0.8)` to `0.6`

## Performance Optimization

### For Free Tier
```javascript
// In lecturer_attendance_management.html
// Reduce to 1 FPS (one frame per second)
state.frameProcessingInterval = setInterval(processCurrentFrame, 1000);

// Lower JPEG quality to 60%
const frameData = canvas.toDataURL('image/jpeg', 0.6);
```

### For Paid Tier
```javascript
// Can increase to 3-4 FPS
state.frameProcessingInterval = setInterval(processCurrentFrame, 250);

// Higher quality at 90%
const frameData = canvas.toDataURL('image/jpeg', 0.9);
```

## Monitoring

### Check Logs
In Render dashboard:
1. Go to your service
2. Click **"Logs"** tab
3. Look for:
   - `✅ Browser recognition initialized`
   - `✅ Marked: [Student Name]`
   - Any error messages

### Monitor Performance
1. **Response Time**: Should be < 2s per frame
2. **Memory Usage**: Should stay under plan limits
3. **CPU Usage**: Spikes during frame processing are normal

## Security Considerations

### HTTPS Required
- Browsers require HTTPS for camera access
- Render provides free SSL certificates
- No additional configuration needed

### Camera Permissions
- Users must grant permission each time
- Cannot access camera without explicit permission
- Camera only active when recognition panel is open

### Data Privacy
- No video is stored on server
- Only attendance records saved to database
- Frames processed in memory and discarded

## Scaling Considerations

### Horizontal Scaling
- Each lecturer uses their own browser camera
- No server-side camera resource contention
- Can handle multiple concurrent sessions

### Database Optimization
- Index frequently queried fields:
  ```sql
  CREATE INDEX idx_attendance_class ON attendance_records(class_id);
  CREATE INDEX idx_attendance_student ON attendance_records(student_id);
  ```

### CDN for Static Assets
- Consider using CDN for CSS/JS files
- Reduces server load
- Improves page load times

## Backup Strategy

### Regular Backups
1. Database: Use Render's automatic backups
2. Code: Keep GitHub repository up to date
3. Environment Variables: Document in secure location

### Disaster Recovery
1. Keep local copy of database schema
2. Export attendance records periodically
3. Test restore process

## Support

### Documentation
- [BROWSER_CAMERA_SETUP.md](BROWSER_CAMERA_SETUP.md) - Technical details
- [README.md](README.md) - General project info

### Troubleshooting
1. Check Render logs first
2. Verify environment variables
3. Test database connection
4. Check browser console for frontend errors

### Getting Help
- Render Docs: https://render.com/docs
- OpenCV Docs: https://docs.opencv.org/
- WebRTC Docs: https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API

## Maintenance

### Regular Updates
- Update Python packages monthly
- Check for security vulnerabilities
- Test after each dependency update

### Monitoring
- Set up Render health checks
- Monitor database size
- Track error rates in logs

### Performance Tuning
- Review frame processing rate based on usage
- Adjust recognition thresholds if needed
- Optimize database queries

---

**Last Updated**: January 30, 2026  
**Tested On**: Render Free Tier, Chrome 120+, Firefox 121+
