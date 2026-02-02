from flask import Blueprint, render_template, session, redirect, url_for, flash, current_app, request, jsonify
from application.controls.auth_control import AuthControl, requires_roles
from application.controls.student_control import StudentControl
from application.entities2.notification import NotificationModel
from database.base import get_session
from datetime import datetime, date, timedelta
import calendar
import zlib
import pickle
import cv2
import numpy as np
import base64

student_bp = Blueprint('student', __name__)

@student_bp.route('/')
@requires_roles('student')
def dashboard():
    """Main dashboard route"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to access the dashboard', 'warning')
            return redirect(url_for('auth.login'))
        
        # Get all dashboard data including announcements
        dashboard_data = StudentControl.get_dashboard_data(user_id)
        
        if not dashboard_data.get('success'):
            flash(dashboard_data.get('error', 'Error loading dashboard'), 'danger')
            return render_template('institution/student/student_dashboard.html')
        
        # Prepare context similar to lecturer dashboard
        context = {
            'student_name': dashboard_data.get('student', {}).get('name', 'Student'),
            'student_info': dashboard_data.get('student', {}),
            'today_classes': dashboard_data.get('today_classes', []),
            'announcements': dashboard_data.get('announcements', []),
            'current_time': dashboard_data.get('current_time', ''),
            'current_date': dashboard_data.get('current_date', ''),
            'statistics': dashboard_data.get('statistics', {})
        }
        
        return render_template('institution/student/student_dashboard.html', **context)
        
    except Exception as e:
        current_app.logger.error(f"Error loading student dashboard: {e}")
        flash('An error occurred while loading your dashboard', 'danger')
        return render_template('institution/student/student_dashboard.html')
    
@student_bp.route('/profile')
@requires_roles('student')
def profile():
    """User profile route"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to access your profile', 'warning')
            return redirect(url_for('auth.login'))
        
        profile_data = StudentControl.get_student_profile(user_id)
        return render_template('institution/student/student_profile_management.html', **profile_data)
        
    except Exception as e:
        current_app.logger.error(f"Error loading student profile: {e}")
        flash('An error occurred while loading your profile', 'danger')
        return render_template('institution/student/student_profile_management.html')

@student_bp.route('/facial-recognition-retrain')
@requires_roles('student')
def facial_recognition_retrain():
    """Facial recognition retrain page for students"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('auth.login'))
        
        # Get student info and facial data status
        with get_session() as db_session:
            from database.models import User, FacialData
            
            student = db_session.query(User).filter(User.user_id == user_id).first()
            
            # Check for existing facial data
            facial_data = db_session.query(FacialData).filter(
                FacialData.user_id == user_id,
                FacialData.is_active == True
            ).order_by(FacialData.updated_at.desc()).first()
            
            context = {
                'name': student.name if student else 'Student',
                'email': student.email if student else '',
                'user_id': user_id,
                'facial_data_exists': facial_data is not None,
                'last_updated': facial_data.updated_at.strftime('%Y-%m-%d %H:%M') if facial_data and facial_data.updated_at else None,
                'sample_count': facial_data.sample_count if facial_data else 0
            }
        
        return render_template('institution/student/student_facial_recognition_retrain.html', **context)
        
    except Exception as e:
        current_app.logger.error(f"Error loading facial recognition retrain page: {e}")
        flash('An error occurred while loading the page', 'danger')
        return redirect(url_for('student.profile'))


@student_bp.route('/api/facial-data/save', methods=['POST'])
def save_facial_data():
    """API endpoint to save facial encoding data"""
    try:
        # Check authentication manually for API endpoint
        user_id = session.get('user_id')
        user_role = session.get('user_role') or session.get('role')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated'}), 401
        
        if user_role != 'student':
            return jsonify({'success': False, 'error': 'Unauthorized access'}), 403
        
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data received'}), 400
        
        # Check if we have photo data (base64 images) instead of encodings
        if 'photos' in data and data['photos']:
            # New format: Process actual photos for OpenCV-based system
            import cv2
            import numpy as np
            import base64
            import zlib
            
            photos = data['photos']
            
            if len(photos) == 0:
                return jsonify({'success': False, 'error': 'No photos captured'}), 400
            
            # Load face detector
            face_cascade = None
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
                        face_cascade = cascade
                        break
                except:
                    continue
            
            all_faces = []
            
            # Process each photo (limit to 100 samples total)
            samples_per_photo = max(1, 100 // len(photos))  # Distribute 100 samples across all photos
            
            for photo_base64 in photos:
                try:
                    # Remove data URL prefix if present
                    if ',' in photo_base64:
                        photo_base64 = photo_base64.split(',')[1]
                    
                    # Decode base64
                    img_data = base64.b64decode(photo_base64)
                    img_array = np.frombuffer(img_data, dtype=np.uint8)
                    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                    
                    if img is None:
                        continue
                    
                    # Detect and crop face
                    if face_cascade is not None:
                        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                        faces = face_cascade.detectMultiScale(gray, 1.05, 3, minSize=(30, 30))
                        
                        if len(faces) > 0:
                            # Get largest face
                            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                            face_img = img[y:y+h, x:x+w]
                        else:
                            # No face detected, use center crop
                            h, w = img.shape[:2]
                            size = min(h, w)
                            sh = (h - size) // 2
                            sw = (w - size) // 2
                            face_img = img[sh:sh+size, sw:sw+size]
                    else:
                        # No cascade, use center crop
                        h, w = img.shape[:2]
                        size = min(h, w)
                        sh = (h - size) // 2
                        sw = (w - size) // 2
                        face_img = img[sh:sh+size, sw:sw+size]
                    
                    # Generate augmented samples (limited per photo)
                    # Use smaller 40x40 images instead of 50x50 to reduce data size
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
                        
                        # Final resize to 40x40 to reduce data size (40*40 = 1600 vs 50*50 = 2500)
                        aug = cv2.resize(aug, (40, 40))
                        all_faces.append(aug.flatten())
                
                except Exception as e:
                    current_app.logger.error(f"Error processing photo: {e}")
                    continue
            
            # Limit to exactly 100 samples
            if len(all_faces) > 100:
                # Evenly sample to get exactly 100
                indices = np.linspace(0, len(all_faces) - 1, 100, dtype=int)
                all_faces = [all_faces[i] for i in indices]
            
            if len(all_faces) == 0:
                return jsonify({'success': False, 'error': 'No faces detected in photos'}), 400
            
            # Convert to numpy array
            faces_array = np.array(all_faces, dtype=np.uint8)
            sample_count = faces_array.shape[0]
            
            # Compress with SHAPE header
            faces_bytes = faces_array.tobytes()
            compressed = zlib.compress(faces_bytes)
            header = f"SHAPE:{faces_array.shape[0]},{faces_array.shape[1]};".encode("utf-8")
            encodings_binary = header + compressed
            
        elif 'encodings' in data:
            # Old format: face-api.js encodings (INCOMPATIBLE with OpenCV system)
            return jsonify({
                'success': False,
                'error': 'Face encodings format is not supported. Please capture photos instead.'
            }), 400
        else:
            return jsonify({'success': False, 'error': 'No photos or encodings received'}), 400
        
        with get_session() as db_session:
            from database.models import FacialData
            
            # Check if user already has facial data
            existing = db_session.query(FacialData).filter(
                FacialData.user_id == user_id,
                FacialData.is_active == True
            ).first()
            
            current_time = datetime.now()
            
            if existing:
                # Update existing record
                existing.face_encoding = encodings_binary
                existing.sample_count = sample_count
                existing.updated_at = current_time
            else:
                # Insert new record
                new_facial_data = FacialData(
                    user_id=user_id,
                    face_encoding=encodings_binary,
                    sample_count=sample_count,
                    created_at=current_time,
                    updated_at=current_time,
                    is_active=True
                )
                db_session.add(new_facial_data)
            
            db_session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Facial data saved successfully',
                'sample_count': sample_count
            })
            
    except Exception as e:
        current_app.logger.error(f"Error saving facial data: {e}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while saving facial data'
        }), 500


@student_bp.route('/api/facial-data/delete', methods=['POST'])
@requires_roles('student')
def delete_facial_data():
    """API endpoint to delete (deactivate) facial data"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated'}), 401
        
        with get_session() as db_session:
            from database.models import FacialData
            
            # Soft delete - set is_active to False
            db_session.query(FacialData).filter(
                FacialData.user_id == user_id,
                FacialData.is_active == True
            ).update({
                'is_active': False,
                'updated_at': datetime.now()
            })
            
            db_session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Facial data deleted successfully'
            })
            
    except Exception as e:
        current_app.logger.error(f"Error deleting facial data: {e}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while deleting facial data'
        }), 500


@student_bp.route('/api/facial-data/status', methods=['GET'])
@requires_roles('student')
def get_facial_data_status():
    """API endpoint to get facial data status"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated'}), 401
        
        with get_session() as db_session:
            from database.models import FacialData
            
            facial_data = db_session.query(FacialData).filter(
                FacialData.user_id == user_id,
                FacialData.is_active == True
            ).first()
            
            if facial_data:
                return jsonify({
                    'success': True,
                    'exists': True,
                    'sample_count': facial_data.sample_count,
                    'created_at': facial_data.created_at.strftime('%Y-%m-%d %H:%M') if facial_data.created_at else None,
                    'updated_at': facial_data.updated_at.strftime('%Y-%m-%d %H:%M') if facial_data.updated_at else None
                })
            else:
                return jsonify({
                    'success': True,
                    'exists': False,
                    'sample_count': 0
                })
                
    except Exception as e:
        current_app.logger.error(f"Error getting facial data status: {e}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while getting facial data status'
        }), 500


@student_bp.route('/attendance')
@requires_roles('student')
def attendance():
    """Student attendance overview"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to view attendance', 'warning')
            return redirect(url_for('auth.login'))
        
        attendance_data = StudentControl.get_student_attendance(user_id)
        return render_template('institution/student/student_attendance_management.html', **attendance_data)
        
    except Exception as e:
        current_app.logger.error(f"Error loading student attendance: {e}")
        flash('An error occurred while loading attendance data', 'danger')
        return render_template('institution/student/student_attendance_management.html')
    
@student_bp.route('/attendance/statistics')
def attendance_statistics():
    """Get attendance statistics as JSON for JavaScript"""
    if 'user_id' not in session or session.get('user_role') != 'student':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    user_id = session['user_id']
    stats = StudentControl.get_attendance_statistics(user_id)
    
    return jsonify(stats)

@student_bp.route('/attendance/history')
@requires_roles('student')
def attendance_history():
    """Attendance history route"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to view attendance history', 'warning')
            return redirect(url_for('auth.login'))
        
        # Get filter parameters from request
        search_query = request.args.get('search', '')
        status_filter = request.args.get('status', '')
        month_filter = request.args.get('month', '')
        venue_filter = request.args.get('venue', '')
        page = request.args.get('page', 1, type=int)
        
        history_data = StudentControl.get_attendance_history(
            user_id,
            search_query=search_query,
            status_filter=status_filter,
            month_filter=month_filter,
            venue_filter=venue_filter,
            page=page,
            per_page=8
        )
        
        return render_template('institution/student/student_attendance_management_history.html', **history_data)
        
    except Exception as e:
        current_app.logger.error(f"Error loading attendance history: {e}")
        flash('An error occurred while loading attendance history', 'danger')
        return render_template('institution/student/student_attendance_management_history.html')

@student_bp.route('/appeal')
@requires_roles('student')
def appeal_management():
    """Student appeal management"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to manage appeals', 'warning')
            return redirect(url_for('auth.login'))
        
        # Get filter parameters from request
        module_filter = request.args.get('module', '')
        status_filter = request.args.get('status', '')
        date_filter = request.args.get('date', '')
        
        appeal_data = StudentControl.get_student_appeals(
            current_app,
            user_id, 
            module_filter=module_filter, 
            status_filter=status_filter, 
            date_filter=date_filter
        )
        
        return render_template('institution/student/student_appeal_management.html', **appeal_data)
        
    except Exception as e:
        current_app.logger.error(f"Error loading appeal management: {e}")
        flash('An error occurred while loading appeal data', 'danger')
        return render_template('institution/student/student_appeal_management.html')

@student_bp.route('/appeal/form/<int:attendance_record_id>', endpoint='appeal_form')
@requires_roles('student')
def appeal_form(attendance_record_id):
    """Show appeal form"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to submit an appeal', 'warning')
            return redirect(url_for('auth.login'))
        
        # Check if user can appeal this record
        can_appeal = StudentControl.can_appeal_record(user_id, attendance_record_id)
        if not can_appeal.get('can_appeal'):
            flash(can_appeal.get('message', 'Cannot appeal this record'), 'error')
            return redirect(url_for('student.appeal_management'))
        
        form_data = StudentControl.get_appeal_form_data(user_id, attendance_record_id)
        return render_template('institution/student/student_appeal_management_appeal_form.html', **form_data)
        
    except Exception as e:
        current_app.logger.error(f"Error loading appeal form: {e}")
        flash('An error occurred while loading the appeal form', 'danger')
        return redirect(url_for('student.appeal_management'))

@student_bp.route('/appeal/form/<int:attendance_record_id>/submit', methods=['POST'], endpoint='appeal_form_submit')
@requires_roles('student')
def appeal_form_submit(attendance_record_id):
    """Handle appeal form submission"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to submit an appeal', 'warning')
            return redirect(url_for('auth.login'))
        
        reason = request.form.get('appeal_reason', '').strip()
        
        if not reason:
            flash("Appeal reason cannot be empty.", "error")
            return redirect(url_for('student.appeal_form', attendance_record_id=attendance_record_id))
        
        result = StudentControl.submit_appeal(user_id, attendance_record_id, reason)
        
        if result.get('success'):
            flash(result.get('message', 'Your appeal has been submitted successfully.'), 'success')
            return redirect(url_for('student.appeal_management'))
        else:
            flash(result.get('error', 'Failed to submit appeal'), 'error')
            return redirect(url_for('student.appeal_form', attendance_record_id=attendance_record_id))
            
    except Exception as e:
        current_app.logger.error(f"Error submitting appeal: {e}")
        flash('An error occurred while submitting your appeal', 'danger')
        return redirect(url_for('student.appeal_management'))

@student_bp.route('/appeal/retract/<int:appeal_id>', endpoint='appeal_retract')
@requires_roles('student')
def appeal_retract(appeal_id):
    """Handle appeal retraction"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to retract appeals', 'warning')
            return redirect(url_for('auth.login'))
        
        result = StudentControl.retract_appeal(user_id, appeal_id)
        
        if result.get('success'):
            flash(result.get('message', 'Your appeal has been retracted successfully.'), 'success')
        else:
            flash(result.get('error', 'Failed to retract appeal'), 'error')
            
        return redirect(url_for('student.appeal_management'))
        
    except Exception as e:
        current_app.logger.error(f"Error retracting appeal: {e}")
        flash('An error occurred while retracting your appeal', 'danger')
        return redirect(url_for('student.appeal_management'))

@student_bp.route('/absent-records', endpoint='absent_records')
@requires_roles('student')
def absent_records():
    """View all absent records"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to view absent records', 'warning')
            return redirect(url_for('auth.login'))
        
        absent_data = StudentControl.get_absent_records(user_id)
        return render_template('institution/student/student_attendance_management_history.html', **absent_data)
        
    except Exception as e:
        current_app.logger.error(f"Error loading absent records: {e}")
        flash('An error occurred while loading absent records', 'danger')
        return render_template('institution/student/student_attendance_management_history.html')
    
@student_bp.route('/announcements')
@requires_roles('student')
def announcements():
    """View all announcements"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to view announcements', 'warning')
            return redirect(url_for('auth.login'))
        
        # Get all dashboard data which includes all announcements
        dashboard_data = StudentControl.get_dashboard_data(user_id)
        
        if not dashboard_data.get('success'):
            flash(dashboard_data.get('error', 'Error loading announcements'), 'danger')
            return render_template('institution/student/student_announcements.html')
        
        # Prepare context for announcements page
        context = {
            'student_name': dashboard_data.get('student', {}).get('name', 'Student'),
            'student_info': dashboard_data.get('student', {}),
            'all_announcements': dashboard_data.get('all_announcements', []),
            'current_time': dashboard_data.get('current_time', ''),
            'current_date': dashboard_data.get('current_date', '')
        }
        
        return render_template('institution/student/student_announcements.html', **context)
        
    except Exception as e:
        current_app.logger.error(f"Error loading student announcements: {e}")
        flash('An error occurred while loading announcements', 'danger')
        return render_template('institution/student/student_announcements.html')

@student_bp.route('/classes/<int:class_id>')
@requires_roles('student')
def class_details(class_id):
    """View class details for a student"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to view class details', 'warning')
            return redirect(url_for('auth.login'))
        
        # Get class details
        class_data = StudentControl.get_class_details(user_id, class_id)
        
        if not class_data.get('success'):
            flash(class_data.get('error', 'Error loading class details'), 'danger')
            return redirect(url_for('student.timetable'))
        
        return render_template('institution/student/student_class_details.html', **class_data)
        
    except Exception as e:
        current_app.logger.error(f"Error loading class details: {e}")
        flash('An error occurred while loading class details', 'danger')
        return redirect(url_for('student.timetable'))

@student_bp.route('/timetable')
@requires_roles('student')
def timetable():
    """Render the student timetable page with multiple views"""
    view_type = request.args.get('view', 'monthly')  # monthly, weekly, list
    selected_date = request.args.get('date')
    course_filter = request.args.get('course')
    class_type_filter = request.args.get('type')
    time_filter = request.args.get('time')
    
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to view timetable', 'warning')
            return redirect(url_for('auth.login'))
        
        # Parse date or use today
        if selected_date:
            current_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        else:
            current_date = date.today()
        
        # Get student's courses for filter dropdown
        courses = StudentControl.get_student_courses(user_id)
        
        # Get timetable data
        timetable_data = StudentControl.get_timetable_data(
            current_app, 
            user_id, 
            view_type, 
            current_date
        )
        
        if not timetable_data.get('success'):
            flash(timetable_data.get('error', 'Error loading timetable'), 'danger')
            return render_template('institution/student/student_timetable.html')
        
        # Prepare context based on view type
        context = {
            'view_type': view_type,
            'courses': courses,
            'today': date.today()
        }
        
        if view_type == 'monthly':
            # Generate monthly calendar
            calendar_data = generate_student_monthly_calendar(
                current_date, user_id, course_filter, class_type_filter
            )
            
            context.update({
                'current_month': current_date.strftime('%B'),
                'current_year': current_date.year,
                'calendar_weeks': calendar_data
            })
            
        elif view_type == 'weekly':
            # Get weekly data
            week_data = generate_student_weekly_data(
                current_date, user_id, course_filter, class_type_filter
            )
            
            context.update({
                'week_start': week_data['week_start'].strftime('%b %d'),
                'week_end': week_data['week_end'].strftime('%b %d'),
                'week_days': week_data['days']
            })
            
        else:  # list view
            # Get upcoming classes
            upcoming_classes = StudentControl.get_upcoming_classes(
                user_id, current_date, course_filter, class_type_filter
            )
            
            context.update({
                'upcoming_classes': upcoming_classes
            })
        
        return render_template('institution/student/student_timetable.html', **context)
        
    except Exception as e:
        current_app.logger.error(f"Error loading student timetable: {e}")
        flash('Error loading timetable', 'danger')
        return render_template('institution/student/student_timetable.html')
    
def generate_student_monthly_calendar(target_date, student_id, course_filter=None, class_type_filter=None):
    """Generate monthly calendar data with classes for student"""
    # Use StudentControl to get classes
    classes = StudentControl.get_student_classes_in_date_range(
        student_id, 
        date(target_date.year, target_date.month, 1),
        date(target_date.year, target_date.month, 
            calendar.monthrange(target_date.year, target_date.month)[1]),
        course_filter,
        class_type_filter
    )
    
    # Group classes by date
    classes_by_date = {}
    for class_data in classes:
        if class_data.get('start_time'):
            class_date = class_data['start_time'].date() if isinstance(class_data['start_time'], datetime) else class_data['start_time']
            if class_date not in classes_by_date:
                classes_by_date[class_date] = []
            
            classes_by_date[class_date].append({
                'id': class_data['id'],
                'course_code': class_data.get('course_code', 'N/A'),
                'course_name': class_data.get('course_name', 'N/A'),
                'type': class_data.get('type', 'Lecture'),
                'time': class_data.get('time', 'N/A'),
                'room': class_data.get('room', 'N/A'),
                'time_slot': class_data.get('time_slot', 'morning'),
                'lecturer': class_data.get('lecturer', 'N/A')
            })
    
    # Generate calendar grid
    calendar_data = []
    
    # Find the first Sunday on or before the first day of month
    first_day = date(target_date.year, target_date.month, 1)
    current_day = first_day
    while current_day.weekday() != 6:  # 6 = Sunday
        current_day -= timedelta(days=1)
    
    # Generate 6 weeks (42 days) to cover the month
    for week in range(6):
        week_days = []
        for day in range(7):
            day_classes = classes_by_date.get(current_day, [])
            
            week_days.append({
                'date': current_day,
                'day': current_day.day,
                'in_month': current_day.month == target_date.month,
                'classes': day_classes
            })
            current_day += timedelta(days=1)
        
        calendar_data.append(week_days)
    
    return calendar_data

def generate_student_weekly_data(target_date, student_id, course_filter=None, class_type_filter=None):
    """Generate weekly calendar data for student"""
    # Get start of week (Sunday)
    week_start = target_date - timedelta(days=target_date.weekday() + 1)
    if week_start.weekday() != 6:  # Not Sunday
        week_start -= timedelta(days=week_start.weekday() + 1)
    
    week_end = week_start + timedelta(days=6)
    
    # Get classes for this week
    classes = StudentControl.get_student_classes_in_date_range(
        student_id, week_start, week_end, course_filter, class_type_filter
    )
    
    # Group classes by date and format them
    classes_by_date = {}
    for class_data in classes:
        if class_data.get('start_time'):
            class_date = class_data['start_time'].date() if isinstance(class_data['start_time'], datetime) else class_data['start_time']
            if class_date not in classes_by_date:
                classes_by_date[class_date] = []
            
            classes_by_date[class_date].append({
                'id': class_data['id'],
                'course_code': class_data.get('course_code', 'N/A'),
                'title': class_data.get('course_name', 'N/A'),
                'type': class_data.get('type', 'Lecture'),
                'time': class_data.get('time', 'N/A'),
                'room': class_data.get('room', 'N/A'),
                'time_slot': class_data.get('time_slot', 'morning'),
                'lecturer': class_data.get('lecturer', 'N/A')
            })
    
    # Generate week days data
    week_days = []
    for i in range(7):
        current_date = week_start + timedelta(days=i)
        day_classes = classes_by_date.get(current_date, [])
        
        week_days.append({
            'name': current_date.strftime('%a'),
            'date': current_date.day,
            'classes': day_classes
        })
    
    return {
        'week_start': week_start,
        'week_end': week_end,
        'days': week_days
    }

# Notification API endpoints
@student_bp.route('/api/notifications', methods=['GET'])
@requires_roles('student')
def get_notifications():
    """API endpoint to get notifications for the student"""
    try:
        student_id = session.get('user_id')
        if not student_id:
            return jsonify({'success': False, 'error': 'User not authenticated'}), 401
        
        with get_session() as db_session:
            notification_model = NotificationModel(db_session)
            
            # Get all notifications (or just unread ones based on query param)
            unread_only = request.args.get('unread_only', 'false').lower() == 'true'
            notifications = notification_model.get_user_notifications(student_id, unread_only=unread_only)
            
            # Format notifications for JSON response
            formatted_notifications = []
            for notif in notifications:
                formatted_notifications.append({
                    'notification_id': notif.notification_id,
                    'content': notif.content,
                    'created_at': notif.created_at.strftime('%b %d, %Y at %I:%M %p') if notif.created_at else 'N/A',
                    'created_at_relative': get_relative_time(notif.created_at) if notif.created_at else 'N/A',
                    'acknowledged': notif.acknowledged
                })
            
            return jsonify({
                'success': True,
                'notifications': formatted_notifications,
                'count': len(formatted_notifications)
            })
            
    except Exception as e:
        current_app.logger.error(f"Error fetching notifications: {e}")
        return jsonify({'success': False, 'error': 'Failed to fetch notifications'}), 500

@student_bp.route('/api/notifications/<int:notification_id>/mark-read', methods=['POST'])
@requires_roles('student')
def mark_notification_read(notification_id):
    """API endpoint to mark a notification as read"""
    try:
        student_id = session.get('user_id')
        if not student_id:
            return jsonify({'success': False, 'error': 'User not authenticated'}), 401
        
        with get_session() as db_session:
            notification_model = NotificationModel(db_session)
            
            # Verify the notification belongs to this user
            from database.models import Notification
            notification = db_session.query(Notification).filter_by(
                notification_id=notification_id,
                user_id=student_id
            ).first()
            
            if not notification:
                return jsonify({'success': False, 'error': 'Notification not found'}), 404
            
            # Mark as read
            notification_model.mark_as_read(notification_id)
            
            return jsonify({'success': True, 'message': 'Notification marked as read'})
            
    except Exception as e:
        current_app.logger.error(f"Error marking notification as read: {e}")
        return jsonify({'success': False, 'error': 'Failed to mark notification as read'}), 500

@student_bp.route('/api/notifications/mark-all-read', methods=['POST'])
@requires_roles('student')
def mark_all_notifications_read():
    """API endpoint to mark all notifications as read"""
    try:
        student_id = session.get('user_id')
        if not student_id:
            return jsonify({'success': False, 'error': 'User not authenticated'}), 401
        
        with get_session() as db_session:
            notification_model = NotificationModel(db_session)
            count = notification_model.mark_all_as_read(student_id)
            
            return jsonify({
                'success': True,
                'message': f'{count} notification(s) marked as read',
                'count': count
            })
            
    except Exception as e:
        current_app.logger.error(f"Error marking all notifications as read: {e}")
        return jsonify({'success': False, 'error': 'Failed to mark all notifications as read'}), 500

#clear all notifications
@student_bp.route('/api/notifications/clear-all', methods=['POST'])
@requires_roles('student')
def clear_all_notifications():
    """API endpoint to clear all notifications"""
    try:
        student_id = session.get('user_id')
        if not student_id:
            return jsonify({'success': False, 'error': 'User not authenticated'}), 401
        
        with get_session() as db_session:
            notification_model = NotificationModel(db_session)
            count = notification_model.clear_all_notifications(student_id)
            
            return jsonify({
                'success': True,
                'message': f'All notifications cleared ({count} deleted)',
                'count': count
            })
            
    except Exception as e:
        current_app.logger.error(f"Error clearing all notifications: {e}")
        return jsonify({'success': False, 'error': 'Failed to clear notifications'}), 500

def get_relative_time(dt):
    """Get relative time string (e.g., '2 hours ago', 'Just now')"""
    if not dt:
        return 'N/A'
    
    now = datetime.now()
    diff = now - dt
    
    if diff.total_seconds() < 60:
        return 'Just now'
    elif diff.total_seconds() < 3600:
        minutes = int(diff.total_seconds() / 60)
        return f'{minutes} minute{"s" if minutes != 1 else ""} ago'
    elif diff.total_seconds() < 86400:
        hours = int(diff.total_seconds() / 3600)
        return f'{hours} hour{"s" if hours != 1 else ""} ago'
    elif diff.days < 7:
        return f'{diff.days} day{"s" if diff.days != 1 else ""} ago'
    else:
        return dt.strftime('%b %d, %Y')