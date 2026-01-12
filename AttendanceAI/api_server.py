"""
Attendance Management API Server with MySQL Integration
Complete version with all endpoints for attendance_system database
Author: AI Assistant
Date: 2026-01-12
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import pickle
import numpy as np
import cv2
import base64
from datetime import datetime
import json
import os

app = Flask(__name__)
CORS(app)

# Allow large file uploads (50MB max)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# ==================== DATABASE CONFIGURATION ====================
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '030528',
    'database': 'attendance_system',
    'port': 3306
}

def get_db_connection():
    """Create and return a database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"❌ Error connecting to MySQL: {e}")
        return None

def execute_query(query, params=None, fetch=False, fetch_one=False):
    """Execute a database query"""
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params or ())
        
        if fetch_one:
            result = cursor.fetchone()
        elif fetch:
            result = cursor.fetchall()
        else:
            connection.commit()
            result = cursor.lastrowid or cursor.rowcount
        
        cursor.close()
        connection.close()
        return result
    except Error as e:
        print(f"❌ Database error: {e}")
        if connection:
            connection.close()
        return None


# ==================== LECTURER MANAGEMENT ====================

@app.route('/api/lecturers', methods=['GET'])
def get_lecturers():
    """Get list of all lecturers"""
    try:
        query = """
            SELECT 
                lecturer_id,
                full_name,
                email,
                department,
                is_active
            FROM Lecturers
            WHERE is_active = TRUE
            ORDER BY full_name
        """
        
        results = execute_query(query, fetch=True)
        
        if results is None:
            return jsonify({'success': True, 'lecturers': [], 'count': 0, 'message': 'No lecturers found'})
        
        return jsonify({
            'success': True,
            'lecturers': results,
            'count': len(results)
        })
    
    except Exception as e:
        print(f"❌ Error in get_lecturers: {e}")
        return jsonify({'success': True, 'lecturers': [], 'count': 0, 'error': str(e)})


@app.route('/api/lecturers/import', methods=['POST'])
def import_lecturers():
    """Import multiple lecturers"""
    try:
        data = request.json
        lecturers_data = data.get('lecturers', [])
        institution_id = data.get('institution_id', 1)
        
        if not lecturers_data:
            return jsonify({'success': False, 'error': 'No lecturers provided'}), 400
        
        imported_count = 0
        lecturer_names = []
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cursor = connection.cursor(dictionary=True)
        
        try:
            for lecturer_info in lecturers_data:
                name = lecturer_info.get('name')
                email = lecturer_info.get('email')
                department = lecturer_info.get('department', '')
                
                if not name or not email:
                    continue
                
                # Check if lecturer exists
                cursor.execute(
                    """SELECT lecturer_id FROM Lecturers 
                       WHERE email = %s AND institution_id = %s""",
                    (email, institution_id)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing lecturer
                    cursor.execute(
                        """UPDATE Lecturers 
                           SET full_name = %s, department = %s, is_active = TRUE
                           WHERE lecturer_id = %s""",
                        (name, department, existing['lecturer_id'])
                    )
                else:
                    # Create new lecturer
                    cursor.execute(
                        """INSERT INTO Lecturers 
                           (institution_id, full_name, email, password_hash, department, is_active) 
                           VALUES (%s, %s, %s, %s, %s, TRUE)""",
                        (institution_id, name, email, "temp_hash", department)
                    )
                
                imported_count += 1
                lecturer_names.append(name)
            
            connection.commit()
            
            return jsonify({
                'success': True,
                'message': f'Successfully imported {imported_count} lecturers',
                'lecturers': lecturer_names
            })
        
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            cursor.close()
            connection.close()
    
    except Exception as e:
        print(f"❌ Error in import_lecturers: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== COURSE MANAGEMENT ====================

@app.route('/api/courses', methods=['GET'])
def get_courses():
    """Get list of all courses"""
    try:
        query = """
            SELECT 
                course_id,
                course_code,
                course_name,
                start_date,
                end_date,
                description,
                is_active
            FROM Courses
            WHERE is_active = TRUE
            ORDER BY course_code
        """
        
        results = execute_query(query, fetch=True)
        
        if results is None:
            return jsonify({'success': True, 'courses': [], 'count': 0, 'message': 'No courses found'})
        
        # Convert dates to strings
        for course in results:
            if course['start_date']:
                course['start_date'] = course['start_date'].strftime('%Y-%m-%d')
            if course['end_date']:
                course['end_date'] = course['end_date'].strftime('%Y-%m-%d')
        
        return jsonify({
            'success': True,
            'courses': results,
            'count': len(results)
        })
    
    except Exception as e:
        print(f"❌ Error in get_courses: {e}")
        return jsonify({'success': True, 'courses': [], 'count': 0, 'error': str(e)})


@app.route('/api/courses/import', methods=['POST'])
def import_courses():
    """Import multiple courses"""
    try:
        data = request.json
        courses_data = data.get('courses', [])
        institution_id = data.get('institution_id', 1)
        
        if not courses_data:
            return jsonify({'success': False, 'error': 'No courses provided'}), 400
        
        imported_count = 0
        course_codes = []
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cursor = connection.cursor(dictionary=True)
        
        try:
            for course_info in courses_data:
                code = course_info.get('code')
                name = course_info.get('name')
                start_date = course_info.get('start_date')
                end_date = course_info.get('end_date')
                description = course_info.get('description', '')
                
                if not code or not name or not start_date or not end_date:
                    continue
                
                # Check if course exists
                cursor.execute(
                    """SELECT course_id FROM Courses 
                       WHERE course_code = %s AND institution_id = %s""",
                    (code, institution_id)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing course
                    cursor.execute(
                        """UPDATE Courses 
                           SET course_name = %s, start_date = %s, end_date = %s, 
                               description = %s, is_active = TRUE
                           WHERE course_id = %s""",
                        (name, start_date, end_date, description, existing['course_id'])
                    )
                else:
                    # Create new course
                    cursor.execute(
                        """INSERT INTO Courses 
                           (institution_id, course_code, course_name, start_date, end_date, description, is_active) 
                           VALUES (%s, %s, %s, %s, %s, %s, TRUE)""",
                        (institution_id, code, name, start_date, end_date, description)
                    )
                
                imported_count += 1
                course_codes.append(code)
            
            connection.commit()
            
            return jsonify({
                'success': True,
                'message': f'Successfully imported {imported_count} courses',
                'courses': course_codes
            })
        
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            cursor.close()
            connection.close()
    
    except Exception as e:
        print(f"❌ Error in import_courses: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== VENUE MANAGEMENT ====================

@app.route('/api/venues', methods=['GET'])
def get_venues():
    """Get list of all venues"""
    try:
        query = """
            SELECT 
                venue_id,
                venue_name,
                building,
                capacity,
                is_active
            FROM Venues
            WHERE is_active = TRUE
            ORDER BY venue_name
        """
        
        results = execute_query(query, fetch=True)
        
        if results is None:
            return jsonify({'success': True, 'venues': [], 'count': 0, 'message': 'No venues found'})
        
        return jsonify({
            'success': True,
            'venues': results,
            'count': len(results)
        })
    
    except Exception as e:
        print(f"❌ Error in get_venues: {e}")
        return jsonify({'success': True, 'venues': [], 'count': 0, 'error': str(e)})


@app.route('/api/venues/import', methods=['POST'])
def import_venues():
    """Import multiple venues"""
    try:
        data = request.json
        venues_data = data.get('venues', [])
        institution_id = data.get('institution_id', 1)
        
        if not venues_data:
            return jsonify({'success': False, 'error': 'No venues provided'}), 400
        
        imported_count = 0
        venue_names = []
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cursor = connection.cursor(dictionary=True)
        
        try:
            for venue_info in venues_data:
                name = venue_info.get('name')
                building = venue_info.get('building', '')
                capacity = venue_info.get('capacity', 50)
                
                if not name:
                    continue
                
                # Check if venue exists
                cursor.execute(
                    """SELECT venue_id FROM Venues 
                       WHERE venue_name = %s AND institution_id = %s""",
                    (name, institution_id)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing venue
                    cursor.execute(
                        """UPDATE Venues 
                           SET building = %s, capacity = %s, is_active = TRUE
                           WHERE venue_id = %s""",
                        (building, capacity, existing['venue_id'])
                    )
                else:
                    # Create new venue
                    cursor.execute(
                        """INSERT INTO Venues 
                           (institution_id, venue_name, building, capacity, is_active) 
                           VALUES (%s, %s, %s, %s, TRUE)""",
                        (institution_id, name, building, capacity)
                    )
                
                imported_count += 1
                venue_names.append(name)
            
            connection.commit()
            
            return jsonify({
                'success': True,
                'message': f'Successfully imported {imported_count} venues',
                'venues': venue_names
            })
        
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            cursor.close()
            connection.close()
    
    except Exception as e:
        print(f"❌ Error in import_venues: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== TIMETABLE SLOTS MANAGEMENT ====================

@app.route('/api/slots', methods=['GET'])
def get_slots():
    """Get list of all timetable slots"""
    try:
        query = """
            SELECT 
                slot_id,
                day_of_week,
                start_time,
                end_time,
                slot_name
            FROM Timetable_Slots
            ORDER BY day_of_week, start_time
        """
        
        results = execute_query(query, fetch=True)
        
        if results is None:
            return jsonify({'success': True, 'slots': [], 'count': 0, 'message': 'No slots found'})
        
        # Convert times to strings
        for slot in results:
            if slot['start_time']:
                slot['start_time'] = str(slot['start_time'])
            if slot['end_time']:
                slot['end_time'] = str(slot['end_time'])
        
        return jsonify({
            'success': True,
            'slots': results,
            'count': len(results)
        })
    
    except Exception as e:
        print(f"❌ Error in get_slots: {e}")
        return jsonify({'success': True, 'slots': [], 'count': 0, 'error': str(e)})


@app.route('/api/slots/import', methods=['POST'])
def import_slots():
    """Import multiple timetable slots"""
    try:
        data = request.json
        slots_data = data.get('slots', [])
        institution_id = data.get('institution_id', 1)
        
        if not slots_data:
            return jsonify({'success': False, 'error': 'No slots provided'}), 400
        
        imported_count = 0
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cursor = connection.cursor(dictionary=True)
        
        try:
            for slot_info in slots_data:
                day_of_week = slot_info.get('day_of_week')
                start_time = slot_info.get('start_time')
                end_time = slot_info.get('end_time')
                slot_name = slot_info.get('slot_name', '')
                
                if not day_of_week or not start_time or not end_time:
                    continue
                
                # Check if slot exists
                cursor.execute(
                    """SELECT slot_id FROM Timetable_Slots 
                       WHERE institution_id = %s AND day_of_week = %s 
                       AND start_time = %s AND end_time = %s""",
                    (institution_id, day_of_week, start_time, end_time)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing slot
                    cursor.execute(
                        """UPDATE Timetable_Slots 
                           SET slot_name = %s
                           WHERE slot_id = %s""",
                        (slot_name, existing['slot_id'])
                    )
                else:
                    # Create new slot
                    cursor.execute(
                        """INSERT INTO Timetable_Slots 
                           (institution_id, day_of_week, start_time, end_time, slot_name) 
                           VALUES (%s, %s, %s, %s, %s)""",
                        (institution_id, day_of_week, start_time, end_time, slot_name)
                    )
                
                imported_count += 1
            
            connection.commit()
            
            return jsonify({
                'success': True,
                'message': f'Successfully imported {imported_count} time slots'
            })
        
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            cursor.close()
            connection.close()
    
    except Exception as e:
        print(f"❌ Error in import_slots: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== SESSION MANAGEMENT ====================

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """Get available sessions (today's classes)"""
    try:
        query = """
            SELECT 
                s.session_id,
                s.course_id,
                s.session_date,
                t.start_time,
                t.end_time,
                s.session_topic,
                s.status,
                c.course_code,
                c.course_name,
                l.full_name as lecturer_name,
                v.venue_name
            FROM Sessions s
            JOIN Timetable_Slots t ON s.slot_id = t.slot_id
            JOIN Courses c ON s.course_id = c.course_id
            JOIN Lecturers l ON s.lecturer_id = l.lecturer_id
            JOIN Venues v ON s.venue_id = v.venue_id
            WHERE s.session_date = CURDATE()
              AND s.status = 'scheduled'
            ORDER BY t.start_time
        """
        
        results = execute_query(query, fetch=True)
        
        if results is None:
            return jsonify({
                'success': True,
                'sessions': [],
                'count': 0,
                'message': 'No sessions found or database error'
            })
        
        sessions = []
        for row in results:
            sessions.append({
                'session_id': row['session_id'],
                'course_id': row['course_id'],
                'course_code': row['course_code'],
                'course_name': row['course_name'],
                'lecturer_name': row['lecturer_name'],
                'venue_name': row['venue_name'],
                'date': row['session_date'].strftime('%Y-%m-%d'),
                'start_time': str(row['start_time']),
                'end_time': str(row['end_time']),
                'topic': row['session_topic'],
                'type': 'lecture',
                'status': row['status']
            })
        
        return jsonify({
            'success': True,
            'sessions': sessions,
            'count': len(sessions)
        })
    
    except Exception as e:
        print(f"❌ Error in get_sessions: {e}")
        return jsonify({
            'success': True,
            'sessions': [],
            'count': 0,
            'error': str(e)
        })


@app.route('/api/sessions/import', methods=['POST'])
def import_sessions():
    """Create multiple sessions"""
    try:
        data = request.json
        sessions_data = data.get('sessions', [])
        
        if not sessions_data:
            return jsonify({'success': False, 'error': 'No sessions provided'}), 400
        
        imported_count = 0
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cursor = connection.cursor(dictionary=True)
        
        try:
            for session_info in sessions_data:
                session_date = session_info.get('session_date')
                course_id = session_info.get('course_id')
                lecturer_id = session_info.get('lecturer_id')
                venue_id = session_info.get('venue_id')
                slot_id = session_info.get('slot_id')
                session_topic = session_info.get('session_topic', '')
                
                if not session_date or not course_id or not lecturer_id or not venue_id or not slot_id:
                    continue
                
                # Check if session exists (same venue, slot, date)
                cursor.execute(
                    """SELECT session_id FROM Sessions 
                       WHERE venue_id = %s AND slot_id = %s AND session_date = %s""",
                    (venue_id, slot_id, session_date)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing session
                    cursor.execute(
                        """UPDATE Sessions 
                           SET course_id = %s, lecturer_id = %s, session_topic = %s, status = 'scheduled'
                           WHERE session_id = %s""",
                        (course_id, lecturer_id, session_topic, existing['session_id'])
                    )
                else:
                    # Create new session
                    cursor.execute(
                        """INSERT INTO Sessions 
                           (course_id, venue_id, slot_id, lecturer_id, session_date, session_topic, status) 
                           VALUES (%s, %s, %s, %s, %s, %s, 'scheduled')""",
                        (course_id, venue_id, slot_id, lecturer_id, session_date, session_topic)
                    )
                
                imported_count += 1
            
            connection.commit()
            
            return jsonify({
                'success': True,
                'message': f'Successfully created {imported_count} sessions'
            })
        
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            cursor.close()
            connection.close()
    
    except Exception as e:
        print(f"❌ Error in import_sessions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== STUDENT MANAGEMENT ====================

@app.route('/api/students', methods=['GET'])
def get_students():
    """Get list of all registered students with facial data"""
    try:
        query = """
            SELECT 
                s.student_id,
                CONCAT(s.full_name, '') as first_name,
                '' as last_name,
                sfd.facial_data_id,
                sfd.samples_count,
                sfd.encoding_type,
                sfd.confidence_score,
                sfd.is_active,
                sfd.created_at,
                sfd.updated_at
            FROM Students s
            INNER JOIN Student_Facial_Data sfd 
                ON s.student_id = sfd.student_id
            WHERE sfd.is_active = TRUE
            ORDER BY s.full_name
        """
        
        results = execute_query(query, fetch=True)
        
        if results is None:
            return jsonify({'success': False, 'error': 'Database error'}), 500
        
        students = []
        for row in results:
            students.append({
                'student_id': row['student_id'],
                'name': row['first_name'],
                'facial_data_id': row['facial_data_id'],
                'sample_count': row['samples_count'],
                'encoding_type': row['encoding_type'],
                'confidence_score': float(row['confidence_score']) if row['confidence_score'] else None,
                'is_active': row['is_active'],
                'enrolled_date': row['created_at'].strftime('%Y-%m-%d') if row['created_at'] else None
            })
        
        return jsonify({
            'success': True,
            'students': students,
            'count': len(students)
        })
    
    except Exception as e:
        print(f"❌ Error in get_students: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/students/import', methods=['POST'])
def import_students():
    """Import multiple students with their facial training data"""
    try:
        data = request.json
        students_data = data.get('students', [])
        institution_id = data.get('institution_id', 1)
        
        if not students_data:
            return jsonify({'success': False, 'error': 'No students provided'}), 400
        
        imported_count = 0
        total_samples = 0
        student_names = []
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cursor = connection.cursor(dictionary=True)
        
        try:
            for student_info in students_data:
                name = student_info.get('name')
                email = student_info.get('email', '')
                photo_base64 = student_info.get('photo')
                sample_count = student_info.get('sample_count', 50)
                
                if not name or not photo_base64:
                    continue
                
                # Generate email if not provided
                if not email:
                    email = f"{name.lower().replace(' ', '.')}@student.temp.com"
                
                # Check if student exists
                cursor.execute(
                    """SELECT student_id FROM Students 
                       WHERE full_name = %s AND institution_id = %s""",
                    (name, institution_id)
                )
                existing = cursor.fetchone()
                
                if existing:
                    student_id = existing['student_id']
                else:
                    # Create new student with required fields
                    student_code = f"STU{datetime.now().strftime('%Y%m%d%H%M%S')}{imported_count}"
                    cursor.execute(
                        """INSERT INTO Students 
                           (institution_id, student_code, full_name, email, password_hash, is_active) 
                           VALUES (%s, %s, %s, %s, %s, TRUE)""",
                        (institution_id, student_code, name, email, "temp_hash")
                    )
                    student_id = cursor.lastrowid
                
                # Process facial data
                all_faces = []
                
                if ',' in photo_base64:
                    photo_base64 = photo_base64.split(',')[1]
                
                img_data = base64.b64decode(photo_base64)
                img_array = np.frombuffer(img_data, dtype=np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                
                if img is None:
                    continue
                
                # Generate training samples with augmentation
                for i in range(sample_count):
                    h, w = img.shape[:2]
                    scale = 0.9 + np.random.random() * 0.2
                    new_h, new_w = int(h * scale), int(w * scale)
                    
                    if new_h > 0 and new_w > 0:
                        resized = cv2.resize(img, (new_w, new_h))
                        start_h = max(0, (new_h - h) // 2)
                        start_w = max(0, (new_w - w) // 2)
                        
                        if new_h >= h and new_w >= w:
                            cropped = resized[start_h:start_h+h, start_w:start_w+w]
                        else:
                            cropped = cv2.resize(resized, (w, h))
                    else:
                        cropped = img
                    
                    final = cv2.resize(cropped, (50, 50))
                    flattened = final.flatten()
                    all_faces.append(flattened)
                
                faces_array = np.array(all_faces, dtype=np.uint8)
                pickled_data = pickle.dumps(faces_array)
                
                image_dims = {"width": 50, "height": 50, "channels": 3}
                
                # Deactivate old facial data
                cursor.execute(
                    """UPDATE Student_Facial_Data 
                       SET is_active = FALSE 
                       WHERE student_id = %s AND is_active = TRUE""",
                    (student_id,)
                )
                
                # Insert new facial data
                cursor.execute(
                    """INSERT INTO Student_Facial_Data 
                       (student_id, institution_id, facial_encodings, encoding_type, 
                        samples_count, image_dimensions, collection_method)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (student_id, institution_id, pickled_data, 'knn_pickle', 
                     sample_count, json.dumps(image_dims), 'api')
                )
                
                imported_count += 1
                total_samples += sample_count
                student_names.append(name)
            
            connection.commit()
            
            return jsonify({
                'success': True,
                'message': f'Successfully imported {imported_count} students',
                'total_samples': total_samples,
                'students': student_names
            })
        
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            cursor.close()
            connection.close()
    
    except Exception as e:
        print(f"❌ Error in import_students: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/students/<int:student_id>', methods=['DELETE'])
def delete_student(student_id):
    """Delete a student (soft delete)"""
    try:
        student = execute_query(
            """SELECT full_name FROM Students WHERE student_id = %s""",
            (student_id,),
            fetch_one=True
        )
        
        if not student:
            return jsonify({'success': False, 'error': 'Student not found'}), 404
        
        execute_query(
            """UPDATE Student_Facial_Data 
               SET is_active = FALSE 
               WHERE student_id = %s""",
            (student_id,)
        )
        
        execute_query(
            """UPDATE Students 
               SET is_active = FALSE 
               WHERE student_id = %s""",
            (student_id,)
        )
        
        return jsonify({
            'success': True,
            'message': f"Student {student['full_name']} deactivated",
            'student_id': student_id
        })
    
    except Exception as e:
        print(f"❌ Error in delete_student: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/students/training-data', methods=['GET'])
def get_training_data():
    """Get all active facial training data for KNN model"""
    try:
        query = """
            SELECT 
                s.student_id,
                s.full_name,
                sfd.facial_encodings,
                sfd.samples_count
            FROM Students s
            INNER JOIN Student_Facial_Data sfd 
                ON s.student_id = sfd.student_id
            WHERE sfd.is_active = TRUE 
              AND s.is_active = TRUE
            ORDER BY s.student_id
        """
        
        results = execute_query(query, fetch=True)
        
        if not results:
            return jsonify({
                'success': True,
                'faces': [],
                'labels': [],
                'student_count': 0,
                'total_samples': 0
            })
        
        all_faces = []
        all_labels = []
        
        for row in results:
            faces = pickle.loads(row['facial_encodings'])
            student_name = row['full_name']
            
            for face in faces:
                all_faces.append(face.tolist())
                all_labels.append(student_name)
        
        return jsonify({
            'success': True,
            'faces': all_faces,
            'labels': all_labels,
            'student_count': len(results),
            'total_samples': len(all_labels)
        })
    
    except Exception as e:
        print(f"❌ Error in get_training_data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== ATTENDANCE MANAGEMENT ====================

@app.route('/api/attendance/mark', methods=['POST'])
def mark_attendance():
    """Mark student attendance in a session with status (present/late/absent)"""
    try:
        data = request.json
        student_id = data.get('student_id')
        session_id = data.get('session_id')
        status = data.get('status', 'present')  # present, late, or absent
        recognition_data = data.get('recognition_data', {})
        
        # Validate status
        if status not in ['present', 'late', 'absent', 'excused']:
            status = 'present'
        
        if not student_id or not session_id:
            return jsonify({'success': False, 'error': 'student_id and session_id required'}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor(dictionary=True)
        
        try:
            # Check if already marked
            cursor.execute(
                """SELECT attendance_id, status FROM Attendance_Records 
                   WHERE student_id = %s AND session_id = %s""",
                (student_id, session_id)
            )
            existing = cursor.fetchone()
            
            if existing:
                # If already marked as present/late, don't change to absent
                if existing['status'] in ['present', 'late'] and status == 'absent':
                    cursor.close()
                    connection.close()
                    return jsonify({
                        'success': True,
                        'message': f'Already marked as {existing["status"]}',
                        'already_present': True,
                        'attendance_id': existing['attendance_id']
                    })
                
                # Update existing record if status is different
                if existing['status'] != status:
                    cursor.execute(
                        """UPDATE Attendance_Records 
                           SET status = %s 
                           WHERE attendance_id = %s""",
                        (status, existing['attendance_id'])
                    )
                    connection.commit()
                
                cursor.close()
                connection.close()
                return jsonify({
                    'success': True,
                    'message': f'Already marked as {existing["status"]}',
                    'already_present': True,
                    'attendance_id': existing['attendance_id']
                })
            
            # Get arrival time from recognition data or use current time
            arrival_time_str = recognition_data.get('arrival_time')
            if arrival_time_str:
                try:
                    arrival_time = datetime.strptime(arrival_time_str, "%H:%M:%S").time()
                except:
                    arrival_time = datetime.now().time()
            else:
                arrival_time = datetime.now().time()
            
            # Mark attendance
            cursor.execute(
                """INSERT INTO Attendance_Records 
                   (session_id, student_id, status, marked_by, attendance_time)
                   VALUES (%s, %s, %s, 'system', %s)""",
                (session_id, student_id, status, arrival_time)
            )
            attendance_id = cursor.lastrowid
            
            # Log facial recognition event
            if recognition_data:
                facial_data_id = recognition_data.get('facial_data_id')
                confidence = recognition_data.get('confidence')
                distance = recognition_data.get('distance')
                
                if facial_data_id:
                    cursor.execute(
                        """INSERT INTO Facial_Recognition_Events 
                           (session_id, student_id, facial_data_id, 
                            recognition_confidence, distance_metric, matched_name,
                            processing_time_ms, model_version, event_timestamp)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (session_id, student_id, facial_data_id, 
                         confidence, distance, recognition_data.get('name', ''),
                         recognition_data.get('processing_time', 0),
                         recognition_data.get('model_version', 'v1.0'),
                         datetime.now())
                    )
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return jsonify({
                'success': True,
                'message': 'Attendance marked',
                'already_present': False,
                'attendance_id': attendance_id,
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })
        
        except Exception as e:
            connection.rollback()
            cursor.close()
            connection.close()
            raise e
    
    except Exception as e:
        print(f"❌ Error in mark_attendance: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/attendance/unmark', methods=['POST'])
def unmark_attendance():
    """Remove student from attendance (mark as absent)"""
    try:
        data = request.json
        student_id = data.get('student_id')
        session_id = data.get('session_id')
        
        if not student_id or not session_id:
            return jsonify({'success': False, 'error': 'student_id and session_id required'}), 400
        
        result = execute_query(
            """UPDATE Attendance_Records 
               SET status = 'absent' 
               WHERE student_id = %s AND session_id = %s""",
            (student_id, session_id)
        )
        
        if result:
            return jsonify({
                'success': True,
                'message': 'Student marked absent'
            })
        else:
            return jsonify({'success': False, 'error': 'Attendance record not found'}), 404
    
    except Exception as e:
        print(f"❌ Error in unmark_attendance: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/attendance/session/<int:session_id>', methods=['GET'])
def get_session_attendance(session_id):
    """Get attendance records for a specific session"""
    try:
        query = """
            SELECT 
                a.attendance_id,
                a.student_id,
                s.full_name,
                a.status,
                a.attendance_time,
                a.marked_by
            FROM Attendance_Records a
            INNER JOIN Students s ON a.student_id = s.student_id
            WHERE a.session_id = %s
            ORDER BY a.attendance_time DESC
        """
        
        results = execute_query(query, (session_id,), fetch=True)
        
        if results is None:
            return jsonify({'success': False, 'error': 'Database error'}), 500
        
        records = []
        for row in results:
            records.append({
                'attendance_id': row['attendance_id'],
                'student_id': row['student_id'],
                'name': row['full_name'],
                'status': row['status'],
                'check_in_time': str(row['attendance_time']) if row['attendance_time'] else None,
                'check_out_time': None,
                'method': row['marked_by']
            })
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'records': records,
            'count': len(records)
        })
    
    except Exception as e:
        print(f"❌ Error in get_session_attendance: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== SYSTEM STATUS ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        connection = get_db_connection()
        if connection:
            connection.close()
            db_status = 'MySQL'
        else:
            db_status = 'Disconnected'
        
        return jsonify({
            'status': 'healthy',
            'database': db_status,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'Error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get system status and statistics"""
    try:
        student_count = execute_query(
            "SELECT COUNT(*) as count FROM Students WHERE is_active = TRUE",
            fetch_one=True
        )
        
        facial_count = execute_query(
            "SELECT COUNT(*) as count FROM Student_Facial_Data WHERE is_active = TRUE",
            fetch_one=True
        )
        
        samples = execute_query(
            "SELECT SUM(samples_count) as total FROM Student_Facial_Data WHERE is_active = TRUE",
            fetch_one=True
        )
        
        lecturer_count = execute_query(
            "SELECT COUNT(*) as count FROM Lecturers WHERE is_active = TRUE",
            fetch_one=True
        )
        
        course_count = execute_query(
            "SELECT COUNT(*) as count FROM Courses WHERE is_active = TRUE",
            fetch_one=True
        )
        
        venue_count = execute_query(
            "SELECT COUNT(*) as count FROM Venues WHERE is_active = TRUE",
            fetch_one=True
        )
        
        slot_count = execute_query(
            "SELECT COUNT(*) as count FROM Timetable_Slots",
            fetch_one=True
        )
        
        session_count = execute_query(
            "SELECT COUNT(*) as count FROM Sessions WHERE session_date = CURDATE()",
            fetch_one=True
        )
        
        return jsonify({
            'success': True,
            'database': 'MySQL',
            'student_count': student_count['count'] if student_count else 0,
            'facial_data_count': facial_count['count'] if facial_count else 0,
            'total_samples': int(samples['total']) if samples and samples['total'] else 0,
            'lecturer_count': lecturer_count['count'] if lecturer_count else 0,
            'course_count': course_count['count'] if course_count else 0,
            'venue_count': venue_count['count'] if venue_count else 0,
            'slot_count': slot_count['count'] if slot_count else 0,
            'today_sessions': session_count['count'] if session_count else 0
        })
    
    except Exception as e:
        print(f"❌ Error in get_status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== MAIN ====================

if __name__ == '__main__':
    print("=" * 70)
    print("🚀 Attendance API Server with MySQL Integration")
    print("=" * 70)
    print("\n📡 Available Endpoints:")
    print("\nStudent Management:")
    print("  GET    /api/students                    - Get all students")
    print("  POST   /api/students/import             - Import students")
    print("  DELETE /api/students/<id>               - Delete student")
    print("  GET    /api/students/training-data      - Get training data")
    print("\nLecturer Management:")
    print("  GET    /api/lecturers                   - Get all lecturers")
    print("  POST   /api/lecturers/import            - Import lecturers")
    print("\nCourse Management:")
    print("  GET    /api/courses                     - Get all courses")
    print("  POST   /api/courses/import              - Import courses")
    print("\nVenue Management:")
    print("  GET    /api/venues                      - Get all venues")
    print("  POST   /api/venues/import               - Import venues")
    print("\nTimetable Slot Management:")
    print("  GET    /api/slots                       - Get all time slots")
    print("  POST   /api/slots/import                - Import time slots")
    print("\nSession Management:")
    print("  GET    /api/sessions                    - Get today's sessions")
    print("  POST   /api/sessions/import             - Create sessions")
    print("\nAttendance Management:")
    print("  POST   /api/attendance/mark             - Mark attendance")
    print("  POST   /api/attendance/unmark           - Unmark attendance")
    print("  GET    /api/attendance/session/<id>     - Get session attendance")
    print("\nSystem:")
    print("  GET    /api/health                      - Health check")
    print("  GET    /api/status                      - System status")
    print("\n" + "=" * 70)
    
    print("\n🔍 Testing database connection...")
    print(f"   Host: {DB_CONFIG['host']}")
    print(f"   Database: {DB_CONFIG['database']}")
    print(f"   User: {DB_CONFIG['user']}")
    
    conn = get_db_connection()
    if conn:
        print("   ✅ Database connected successfully")
        conn.close()
    else:
        print("   ❌ Database connection failed!")
        print("   Please check DB_CONFIG settings")
    
    print("\n🌐 Server starting on http://localhost:5000")
    print("=" * 70 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)