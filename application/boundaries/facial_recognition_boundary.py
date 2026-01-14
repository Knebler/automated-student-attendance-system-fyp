# application/boundaries/facial_recognition_boundary.py
from flask import Blueprint, request, jsonify, session, current_app
from application.controls.auth_control import AuthControl
from application.controls.facial_recognition_control import FacialRecognitionControl
from application.controls.attendance_control import AttendanceControl
import base64
import io

facial_recognition_bp = Blueprint('facial_recognition', __name__)
fr_control = FacialRecognitionControl()

@facial_recognition_bp.route('/initialize', methods=['POST'])
def initialize_facial_recognition():
    """Initialize the facial recognition system"""
    auth_result = AuthControl.verify_session(current_app, session)
    
    if not auth_result['success']:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
    
    # Only admins or lecturers can initialize
    user_info = auth_result['user']
    if user_info.get('user_type') not in ['admin', 'lecturer', 'institution_admin']:
        return jsonify({
            'success': False,
            'error': 'Permission denied'
        }), 403
    
    if fr_control.initialize(current_app):
        return jsonify({
            'success': True,
            'message': 'Facial recognition initialized',
            'samples_loaded': len(fr_control.labels)
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to initialize facial recognition'
        }), 500

@facial_recognition_bp.route('/recognize', methods=['POST'])
def recognize_face():
    """Recognize face from uploaded image and mark attendance"""
    auth_result = AuthControl.verify_session(current_app, session)
    
    if not auth_result['success']:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
    
    data = request.get_json() or {}
    
    # Get image data (base64 encoded)
    image_base64 = data.get('image')
    session_id = data.get('session_id')
    
    if not image_base64:
        return jsonify({
            'success': False,
            'error': 'Image data is required'
        }), 400
    
    if not session_id:
        return jsonify({
            'success': False,
            'error': 'Session ID is required'
        }), 400
    
    try:
        # Decode base64 image
        image_data = base64.b64decode(image_base64.split(',')[1] if ',' in image_base64 else image_base64)
        
        # Recognize face
        recognition_result = fr_control.recognize_face_from_image(image_data)
        
        if not recognition_result['success']:
            return jsonify(recognition_result), 400
        
        # Get the highest confidence recognition
        recognitions = recognition_result.get('recognitions', [])
        if not recognitions:
            return jsonify({
                'success': False,
                'error': 'No faces recognized'
            }), 400
        
        best_recognition = max(recognitions, key=lambda r: r['confidence'])
        
        # If confidence is too low, require manual verification
        if best_recognition['confidence'] < 70:  # Threshold
            return jsonify({
                'success': False,
                'error': 'Low confidence recognition',
                'suggested_name': best_recognition['name'],
                'confidence': best_recognition['confidence'],
                'requires_verification': True
            }), 400
        
        # Mark attendance
        student_id = best_recognition.get('student_id')
        if not student_id:
            # Try to extract from name or use the name itself
            student_id = best_recognition['name']
        
        attendance_result = AttendanceControl.mark_attendance(
            current_app,
            class_id=session_id,
            student_id=student_id,
            status='present',
            marked_by='system',
            captured_image_path=f"data:image/jpeg;base64,{image_base64[:100]}..."  # Store partial
        )
        
        if attendance_result['success']:
            return jsonify({
                'success': True,
                'message': f'Attendance marked for {best_recognition["name"]}',
                'recognition': best_recognition,
                'attendance': attendance_result
            })
        else:
            return jsonify({
                'success': False,
                'error': attendance_result.get('error', 'Failed to mark attendance'),
                'recognition': best_recognition
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@facial_recognition_bp.route('/register', methods=['POST'])
def register_face():
    """Register a new face for a student"""
    auth_result = AuthControl.verify_session(current_app, session)
    
    if not auth_result['success']:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
    
    data = request.get_json() or {}
    
    student_id = data.get('student_id')
    image_base64 = data.get('image')
    student_name = data.get('student_name')
    
    if not student_id:
        return jsonify({
            'success': False,
            'error': 'Student ID is required'
        }), 400
    
    if not image_base64:
        return jsonify({
            'success': False,
            'error': 'Image data is required'
        }), 400
    
    try:
        # Decode base64 image
        image_data = base64.b64decode(image_base64.split(',')[1] if ',' in image_base64 else image_base64)
        
        # Register face
        result = fr_control.register_new_face(student_id, image_data, student_name)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@facial_recognition_bp.route('/status', methods=['GET'])
def get_facial_recognition_status():
    """Get status of facial recognition system"""
    auth_result = AuthControl.verify_session(current_app, session)
    
    if not auth_result['success']:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
    
    return jsonify({
        'success': True,
        'initialized': fr_control.is_initialized,
        'samples_loaded': len(fr_control.labels) if fr_control.is_initialized else 0,
        'model_ready': fr_control.knn_model is not None
    })