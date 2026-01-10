-- =============================================
-- Group 1: Platform & Onboarding Entities
-- =============================================

CREATE TABLE Platform_Managers (
    platform_mgr_id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Subscription_Plans (
    plan_id INT PRIMARY KEY AUTO_INCREMENT,
    plan_name VARCHAR(100) NOT NULL,
    description TEXT,
    price_per_cycle DECIMAL(10,2) NOT NULL,
    billing_cycle ENUM('monthly', 'quarterly', 'annual') NOT NULL,
    max_students INT NOT NULL,
    max_courses INT NOT NULL,
    max_lecturers INT NOT NULL,
    features JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Unregistered_Users (
    unreg_user_id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    institution_name VARCHAR(255) NOT NULL,
    institution_address TEXT,
    phone_number VARCHAR(20),
    message TEXT,
    selected_plan_id INT,
    status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    reviewed_by INT NULL,
    reviewed_at DATETIME NULL,
    response_message TEXT,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (selected_plan_id) REFERENCES Subscription_Plans(plan_id),
    FOREIGN KEY (reviewed_by) REFERENCES Platform_Managers(platform_mgr_id)
);

CREATE TABLE Subscriptions (
    subscription_id INT PRIMARY KEY AUTO_INCREMENT,
    unreg_user_id INT NOT NULL,
    plan_id INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status ENUM('active', 'expired', 'cancelled', 'pending_payment') DEFAULT 'active',
    stripe_subscription_id VARCHAR(255) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (unreg_user_id) REFERENCES Unregistered_Users(unreg_user_id),
    FOREIGN KEY (plan_id) REFERENCES Subscription_Plans(plan_id)
);

CREATE TABLE Assignments (
    assignment_id INT PRIMARY KEY AUTO_INCREMENT,
    platform_mgr_id INT NOT NULL,
    unreg_user_id INT NOT NULL,
    subscription_id INT NOT NULL,
    assigned_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (platform_mgr_id) REFERENCES Platform_Managers(platform_mgr_id),
    FOREIGN KEY (unreg_user_id) REFERENCES Unregistered_Users(unreg_user_id),
    FOREIGN KEY (subscription_id) REFERENCES Subscriptions(subscription_id)
);

-- =============================================
-- Group 2: Institution & Access Control
-- =============================================

CREATE TABLE Institutions (
    institution_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    website VARCHAR(255),
    subscription_id INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subscription_id) REFERENCES Subscriptions(subscription_id),
    INDEX idx_institution_subscription (subscription_id)
);

CREATE TABLE Institution_Admins (
    inst_admin_id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    institution_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (institution_id) REFERENCES Institutions(institution_id) ON DELETE CASCADE,
    UNIQUE KEY unique_institution_email (institution_id, email),
    INDEX idx_institution_admin (institution_id)
);

-- =============================================
-- Group 3: Academic Structure
-- =============================================

CREATE TABLE Venues (
    venue_id INT PRIMARY KEY AUTO_INCREMENT,
    institution_id INT NOT NULL,
    venue_name VARCHAR(100) NOT NULL,
    building VARCHAR(100),
    capacity INT,
    facilities JSON,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (institution_id) REFERENCES Institutions(institution_id) ON DELETE CASCADE,
    UNIQUE KEY unique_venue_location (institution_id, venue_name, building),
    INDEX idx_venue_institution (institution_id)
);

CREATE TABLE Timetable_Slots (
    slot_id INT PRIMARY KEY AUTO_INCREMENT,
    institution_id INT NOT NULL,
    day_of_week TINYINT NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    slot_name VARCHAR(50),
    FOREIGN KEY (institution_id) REFERENCES Institutions(institution_id) ON DELETE CASCADE,
    UNIQUE KEY unique_slot_timing (institution_id, day_of_week, start_time, end_time),
    INDEX idx_slot_institution (institution_id)
);

CREATE TABLE Lecturers (
    lecturer_id INT PRIMARY KEY AUTO_INCREMENT,
    institution_id INT NOT NULL,
    age INT,
    gender ENUM('male', 'female', 'other'),
    phone_number VARCHAR(20),
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    department VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    year_joined INT,
    FOREIGN KEY (institution_id) REFERENCES Institutions(institution_id) ON DELETE CASCADE,
    UNIQUE KEY unique_lecturer_email (institution_id, email),
    INDEX idx_lecturer_institution (institution_id)
);

CREATE TABLE Courses (
    course_id INT PRIMARY KEY AUTO_INCREMENT,
    institution_id INT NOT NULL,
    course_code VARCHAR(50) NOT NULL,
    course_name VARCHAR(255) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    description TEXT,
    credits INT,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (institution_id) REFERENCES Institutions(institution_id) ON DELETE CASCADE,
    UNIQUE KEY unique_course_code (institution_id, course_code),
    INDEX idx_course_institution (institution_id)
);

CREATE TABLE Course_Lecturers (
    course_id INT NOT NULL,
    lecturer_id INT NOT NULL,
    PRIMARY KEY (course_id, lecturer_id),
    FOREIGN KEY (course_id) REFERENCES Courses(course_id) ON DELETE CASCADE,
    FOREIGN KEY (lecturer_id) REFERENCES Lecturers(lecturer_id) ON DELETE CASCADE,
    INDEX idx_course_lecturer (lecturer_id)
);

CREATE TABLE Students (
    student_id INT PRIMARY KEY AUTO_INCREMENT,
    institution_id INT NOT NULL,
    student_code VARCHAR(50) NOT NULL,
    age INT,
    gender ENUM('male', 'female', 'other'),
    phone_number VARCHAR(20),
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    enrollment_year INT,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (institution_id) REFERENCES Institutions(institution_id) ON DELETE CASCADE,
    UNIQUE KEY unique_student_code (institution_id, student_code),
    UNIQUE KEY unique_student_email (institution_id, email),
    INDEX idx_student_institution (institution_id)
);

CREATE TABLE Course_Students (
    course_id INT NOT NULL,
    student_id INT NOT NULL,
    PRIMARY KEY (course_id, student_id),
    FOREIGN KEY (course_id) REFERENCES Courses(course_id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES Students(student_id) ON DELETE CASCADE,
    INDEX idx_course_student (student_id)
);

CREATE TABLE Enrollments (
    enrollment_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    course_id INT NOT NULL,
    academic_year VARCHAR(9) NOT NULL,
    semester VARCHAR(20),
    enrollment_date DATE DEFAULT (CURRENT_DATE),
    status ENUM('active', 'dropped', 'completed') DEFAULT 'active',
    FOREIGN KEY (student_id) REFERENCES Students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES Courses(course_id) ON DELETE CASCADE,
    UNIQUE KEY unique_enrollment (student_id, course_id, academic_year, semester),
    INDEX idx_enrollment_student (student_id),
    INDEX idx_enrollment_course (course_id)
);

-- =============================================
-- Group 4: Attendance Core
-- =============================================

CREATE TABLE Sessions (
    session_id INT PRIMARY KEY AUTO_INCREMENT,
    course_id INT NOT NULL,
    venue_id INT NOT NULL,
    slot_id INT NOT NULL,
    lecturer_id INT NOT NULL,
    session_date DATE NOT NULL,
    session_topic VARCHAR(255),
    status ENUM('scheduled', 'completed', 'cancelled', 'rescheduled') DEFAULT 'scheduled',
    cancellation_reason TEXT,
    FOREIGN KEY (course_id) REFERENCES Courses(course_id) ON DELETE CASCADE,
    FOREIGN KEY (venue_id) REFERENCES Venues(venue_id),
    FOREIGN KEY (slot_id) REFERENCES Timetable_Slots(slot_id),
    FOREIGN KEY (lecturer_id) REFERENCES Lecturers(lecturer_id),
    UNIQUE KEY unique_venue_booking (venue_id, slot_id, session_date),
    UNIQUE KEY unique_course_session (course_id, session_date, slot_id),
    INDEX idx_session_course (course_id),
    INDEX idx_session_venue (venue_id),
    INDEX idx_session_lecturer (lecturer_id),
    INDEX idx_session_date (session_date)
);

CREATE TABLE Attendance_Records (
    attendance_id INT PRIMARY KEY AUTO_INCREMENT,
    session_id INT NOT NULL,
    student_id INT NOT NULL,
    status ENUM('present', 'absent', 'late', 'excused') DEFAULT 'absent',
    marked_by ENUM('system', 'lecturer') NOT NULL,
    lecturer_id INT NULL,
    captured_image_path VARCHAR(500) NULL,
    attendance_time TIME NULL,
    notes TEXT,
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES Sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES Students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (lecturer_id) REFERENCES Lecturers(lecturer_id),
    UNIQUE KEY unique_session_attendance (session_id, student_id),
    INDEX idx_attendance_session (session_id),
    INDEX idx_attendance_student (student_id),
    INDEX idx_attendance_lecturer (lecturer_id),
    INDEX idx_attendance_recorded (recorded_at)
);

-- =============================================
-- Group 5: Data Reporting & Analytics
-- =============================================

CREATE TABLE Reports (
    -- Primary identifier
    report_id INT PRIMARY KEY AUTO_INCREMENT,
    
    -- Report metadata
    report_uuid VARCHAR(36) UNIQUE NOT NULL DEFAULT (UUID()),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    report_type VARCHAR(50) NOT NULL,
    
    -- Who generated the report (reporter)
    institution_id INT NOT NULL,
    reporter_email VARCHAR(255) NOT NULL,
    reporter_role ENUM('admin', 'lecturer', 'system') NOT NULL,
    
    -- Report content and parameters
    report_data JSON NOT NULL,  -- Stores the actual report data (charts, tables, stats)
    parameters JSON,            -- Stores filters/parameters used to generate report
    format ENUM('pdf', 'csv', 'html', 'json', 'excel') DEFAULT 'html',
    
    -- Report status and metadata
    status ENUM('generating', 'completed', 'failed', 'scheduled') DEFAULT 'generating',
    generation_time INT,  -- Time taken to generate (in seconds)
    file_size_bytes INT,  -- Size of generated file if applicable
    
    -- Storage locations
    file_path VARCHAR(500),      -- Local file system path
    storage_url VARCHAR(500),    -- Cloud storage URL (Azure Blob, S3, etc.)
    preview_url VARCHAR(500),    -- URL for HTML preview
    
    -- Schedule information (for recurring reports)
    schedule_type ENUM('once', 'daily', 'weekly', 'monthly', 'quarterly', 'yearly') DEFAULT 'once',
    schedule_config JSON,        -- Cron-like configuration
    next_scheduled_run DATETIME,
    
    -- Timestamps
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,         -- When report should be auto-deleted
    viewed_at DATETIME,          -- When report was last viewed
    deleted_at DATETIME,         -- Soft delete timestamp
    
    -- Access control
    is_public BOOLEAN DEFAULT FALSE,
    access_code VARCHAR(100),    -- For sharing with password
    allowed_viewers JSON,        -- Specific users who can view
    
    -- Foreign keys
    FOREIGN KEY (institution_id) REFERENCES Institutions(institution_id) ON DELETE CASCADE,
    
    -- Indexes for performance
    INDEX idx_reports_institution (institution_id),
    INDEX idx_reports_reporter (reporter_email),
    INDEX idx_reports_type (report_type),
    INDEX idx_reports_status (status),
    INDEX idx_reports_generated (generated_at),
    INDEX idx_reports_composite (institution_id, reporter_email, report_type)
);

CREATE TABLE Platform_Issues (
    -- Primary identifier
    issue_id INT PRIMARY KEY AUTO_INCREMENT,
    issue_uuid VARCHAR(36) UNIQUE NOT NULL DEFAULT (UUID()),
    
    -- Reporter information (supports all user types)
    reporter_type ENUM('student', 'lecturer', 'admin', 'platform_manager') NOT NULL,
    reporter_id INT NOT NULL,  -- ID from respective table (student_id, lecturer_id, etc.)
    reporter_email VARCHAR(255) NOT NULL,
    institution_id INT NULL,  -- NULL for platform managers
    
    -- Issue details
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    
    -- Categorization - FIXED: 'other' added to ENUM since it's the default
    issue_type ENUM('bug', 'feature_request', 'ui_issue', 'performance', 'security', 'other') DEFAULT 'bug',
    category ENUM('attendance', 'timetable', 'reports', 'authentication', 'api', 'mobile', 'web', 'database', 'integration', 'other') DEFAULT 'other',
    priority ENUM('critical', 'high', 'medium', 'low') DEFAULT 'medium',
    severity ENUM('blocker', 'major', 'minor', 'trivial') DEFAULT 'minor',
    
    -- Technical details
    module VARCHAR(100),  -- e.g., "Facial Recognition", "Attendance Marking"
    page_url VARCHAR(500),
    browser_info JSON,    -- {browser: "Chrome", version: "120.0", os: "Windows 10"}
    device_type ENUM('desktop', 'mobile', 'tablet'),
    
    -- Supporting files/evidence
    screenshot_path VARCHAR(500),
    log_file_path VARCHAR(500),
    additional_files JSON,  -- Array of file paths
    
    -- Status tracking
    status ENUM(
        'new', 
        'acknowledged', 
        'investigating', 
        'in_progress', 
        'resolved', 
        'closed', 
        'reopened', 
        'duplicate', 
        'wont_fix'
    ) DEFAULT 'new',
    
    -- Assignment and resolution
    assigned_to INT NULL,  -- Platform manager ID
    assigned_at DATETIME,
    
    resolution ENUM(
        'fixed', 
        'workaround', 
        'cannot_reproduce', 
        'obsolete', 
        'as_designed',
        'pending_release',
        'duplicate'
    ),
    resolution_notes TEXT,
    fix_version VARCHAR(50),  -- e.g., "v2.1.5"
    
    -- Time tracking
    estimated_hours DECIMAL(5,2),
    actual_hours DECIMAL(5,2),
    due_date DATE,
    
    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    acknowledged_at DATETIME,
    resolved_at DATETIME,
    closed_at DATETIME,
    
    -- Feedback loop
    reporter_notified BOOLEAN DEFAULT FALSE,
    reporter_feedback TEXT,
    reporter_rating TINYINT CHECK (reporter_rating BETWEEN 1 AND 5),
    
    -- Foreign key constraints
    FOREIGN KEY (institution_id) REFERENCES Institutions(institution_id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_to) REFERENCES Platform_Managers(platform_mgr_id),
    
    -- Indexes for performance
    INDEX idx_issues_reporter (reporter_type, reporter_id),
    INDEX idx_issues_institution (institution_id),
    INDEX idx_issues_status (status),
    INDEX idx_issues_priority (priority),
    INDEX idx_issues_type (issue_type),
    INDEX idx_issues_assigned (assigned_to),
    INDEX idx_issues_created (created_at),
    INDEX idx_issues_composite (reporter_type, reporter_id, institution_id)
);

-- =============================================
-- Group 6: Testimonials & User Feedback
-- =============================================

CREATE TABLE Testimonials (
    testimonial_id INT PRIMARY KEY AUTO_INCREMENT,
    testimonial_uuid VARCHAR(36) UNIQUE NOT NULL DEFAULT (UUID()),
    
    -- Author information (supports institution_admins, lecturers, and students)
    author_type ENUM('institution_admin', 'lecturer', 'student') NOT NULL,
    author_id INT NOT NULL,  -- ID from respective table (inst_admin_id, lecturer_id, student_id)
    author_email VARCHAR(255) NOT NULL,
    author_full_name VARCHAR(100) NOT NULL,
    author_department VARCHAR(100),  -- For lecturers/admins
    author_year INT,  -- For students (enrollment_year)
    author_student_code VARCHAR(50),  -- For students
    
    -- Institution context
    institution_id INT NOT NULL,
    institution_name VARCHAR(255) NOT NULL,
    
    -- Testimonial content
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    
    -- Rating
    rating TINYINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    
    -- Display preferences
    is_featured BOOLEAN DEFAULT FALSE,
    is_approved BOOLEAN DEFAULT FALSE,
    display_order INT DEFAULT 0,
    is_anonymous BOOLEAN DEFAULT FALSE,
    
    -- Media support
    profile_image_path VARCHAR(500),
    additional_media JSON,  -- Array of image/video paths
    
    -- Metadata
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    approved_by INT NULL,  -- Platform manager who approved
    approved_at DATETIME NULL,
    
    -- For soft delete
    deleted_at DATETIME NULL,
    
    -- Foreign key constraints
    FOREIGN KEY (institution_id) REFERENCES Institutions(institution_id) ON DELETE CASCADE,
    FOREIGN KEY (approved_by) REFERENCES Platform_Managers(platform_mgr_id),
    
    -- Indexes for performance
    INDEX idx_testimonials_author (author_type, author_id),
    INDEX idx_testimonials_institution (institution_id),
    INDEX idx_testimonials_rating (rating),
    INDEX idx_testimonials_approved (is_approved),
    INDEX idx_testimonials_featured (is_featured),
    INDEX idx_testimonials_created (created_at),
    INDEX idx_testimonials_author_email (author_email),
    INDEX idx_testimonials_composite (institution_id, is_approved, is_featured)
);

-- Trigger to update timestamps
DELIMITER //
CREATE TRIGGER before_testimonials_update
BEFORE UPDATE ON Testimonials
FOR EACH ROW
BEGIN
    SET NEW.updated_at = CURRENT_TIMESTAMP;
    
    -- Update approved_at when is_approved changes from false to true
    IF NEW.is_approved = TRUE AND OLD.is_approved = FALSE THEN
        SET NEW.approved_at = CURRENT_TIMESTAMP;
    END IF;
END//
DELIMITER ;

-- =============================================
-- Group 7: Facial Recognition & Biometric Data
-- =============================================

CREATE TABLE Student_Facial_Data (
    -- Primary identifier
    facial_data_id INT PRIMARY KEY AUTO_INCREMENT,
    facial_data_uuid VARCHAR(36) UNIQUE NOT NULL DEFAULT (UUID()),
    
    -- Student reference
    student_id INT NOT NULL,
    institution_id INT NOT NULL,
    
    -- Facial data storage
    facial_encodings BLOB NOT NULL,  -- Serialized facial encoding data
    encoding_type ENUM('knn_pickle', 'dlib_128d', 'facenet_512d', 'openface_128d') DEFAULT 'knn_pickle',
    encoding_version VARCHAR(20),     -- e.g., "v1.0", "model_v2"
    
    -- Metadata about the data collection
    samples_count INT NOT NULL DEFAULT 0,     -- Number of face samples (e.g., 100)
    image_dimensions JSON,                    -- {"width": 50, "height": 50, "channels": 3}
    collection_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    collection_method ENUM('manual', 'auto_capture', 'batch_import', 'api') DEFAULT 'manual',
    
    -- Quality metrics
    confidence_score DECIMAL(5,4),            -- Model confidence on these encodings
    quality_score DECIMAL(5,4),               -- Image quality metric
    variance_score DECIMAL(10,4),             -- Variance across samples
    
    -- Status and validation
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,        -- Manually verified by admin
    verification_date DATETIME,
    verified_by INT,                          -- Platform manager or admin
    
    -- Storage location (for file-based fallback)
    pickle_file_path VARCHAR(500),            -- Path to .pkl file if stored separately
    backup_location VARCHAR(500),             -- Cloud/backup location
    
    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    expires_at DATETIME,                      -- When encodings should be refreshed
    
    -- Foreign key constraints
    FOREIGN KEY (student_id) REFERENCES Students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (institution_id) REFERENCES Institutions(institution_id) ON DELETE CASCADE,
    FOREIGN KEY (verified_by) REFERENCES Platform_Managers(platform_mgr_id),
    
    -- Indexes for performance
    UNIQUE KEY unique_active_face (student_id, is_active),
    INDEX idx_facial_student (student_id),
    INDEX idx_facial_institution (institution_id),
    INDEX idx_facial_active (is_active),
    INDEX idx_facial_encoding_type (encoding_type),
    INDEX idx_facial_created (created_at)
);

-- Create a more specific table for face samples (if you need individual samples)
CREATE TABLE Face_Samples (
    sample_id INT PRIMARY KEY AUTO_INCREMENT,
    sample_uuid VARCHAR(36) UNIQUE NOT NULL DEFAULT (UUID()),
    facial_data_id INT NOT NULL,
    student_id INT NOT NULL,
    
    -- Sample image/encoding
    face_image BLOB,                         -- Optional: store actual image
    face_encoding BLOB,                      -- Individual face encoding
    sample_metadata JSON,                    -- {"crop_coords": {"x": 10, "y": 20, "w": 50, "h": 50}}
    
    -- Quality metrics per sample
    brightness DECIMAL(6,2),
    contrast DECIMAL(6,2),
    sharpness DECIMAL(6,2),
    face_confidence DECIMAL(5,4),            -- Face detection confidence
    
    -- Capture info
    capture_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    capture_device VARCHAR(100),             -- "webcam", "mobile", "ip_camera"
    device_info JSON,                        -- {"camera_model": "Logitech C920", "resolution": "640x480"}
    
    -- Foreign keys
    FOREIGN KEY (facial_data_id) REFERENCES Student_Facial_Data(facial_data_id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES Students(student_id) ON DELETE CASCADE,
    
    -- Indexes
    INDEX idx_samples_facial_data (facial_data_id),
    INDEX idx_samples_student (student_id),
    INDEX idx_samples_timestamp (capture_timestamp)
);

-- Create audit table for facial recognition events
CREATE TABLE Facial_Recognition_Events (
    event_id INT PRIMARY KEY AUTO_INCREMENT,
    event_uuid VARCHAR(36) UNIQUE NOT NULL DEFAULT (UUID()),
    
    -- Recognition event
    session_id INT NOT NULL,
    student_id INT NOT NULL,
    facial_data_id INT NOT NULL,
    
    -- Recognition results
    recognition_confidence DECIMAL(5,4) NOT NULL,
    matched_name VARCHAR(100) NOT NULL,
    expected_name VARCHAR(100),              -- For verification
    
    -- Match quality
    distance_metric DECIMAL(10,4),           -- KNN distance
    is_correct_match BOOLEAN,                -- Manual verification result
    
    -- Image data (optional)
    captured_image BLOB,                     -- The frame where recognition happened
    crop_coordinates JSON,                   -- {"x": 100, "y": 150, "w": 200, "h": 200}
    
    -- Technical info
    processing_time_ms INT,                  -- Time taken to process
    model_version VARCHAR(20),
    
    -- Event metadata
    event_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    device_id VARCHAR(100),                  -- Which device/camera
    location VARCHAR(255),                   -- Physical location if known
    
    -- Foreign keys
    FOREIGN KEY (session_id) REFERENCES Sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES Students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (facial_data_id) REFERENCES Student_Facial_Data(facial_data_id),
    
    -- Indexes
    INDEX idx_events_session (session_id),
    INDEX idx_events_student (student_id),
    INDEX idx_events_timestamp (event_timestamp),
    INDEX idx_events_confidence (recognition_confidence),
    INDEX idx_events_composite (session_id, student_id, event_timestamp)
);

-- Create triggers for timestamps
DELIMITER //
CREATE TRIGGER before_platform_issues_update 
BEFORE UPDATE ON Platform_Issues 
FOR EACH ROW 
BEGIN
    SET NEW.updated_at = CURRENT_TIMESTAMP;
    
    -- Update status timestamps
    IF NEW.status = 'acknowledged' AND OLD.status != 'acknowledged' THEN
        SET NEW.acknowledged_at = CURRENT_TIMESTAMP;
    END IF;
    
    IF NEW.status = 'resolved' AND OLD.status != 'resolved' THEN
        SET NEW.resolved_at = CURRENT_TIMESTAMP;
    END IF;
    
    IF NEW.status = 'closed' AND OLD.status != 'closed' THEN
        SET NEW.closed_at = CURRENT_TIMESTAMP;
    END IF;
END//
DELIMITER ;

-- =============================================
-- Sample Data for Testing
-- =============================================

-- Insert a sample subscription plan
INSERT INTO Subscription_Plans (
    plan_name, description, price_per_cycle, billing_cycle, 
    max_students, max_courses, max_lecturers, features
) VALUES (
    'Starter Plan', 
    'Perfect for small institutions getting started with automated attendance', 
    99.99, 
    'monthly', 
    500, 
    50, 
    20, 
    '{"facial_recognition": true, "basic_reporting": true, "email_support": true}'
);

-- Insert a platform manager
INSERT INTO Platform_Managers (email, password_hash, full_name) 
VALUES ('admin@attendanceplatform.com', '$2b$10$examplehash', 'System Administrator');

-- =============================================
-- Useful Views for Reporting
-- =============================================

-- View for active subscriptions with institution info
CREATE VIEW Active_Subscriptions_View AS
SELECT 
    s.subscription_id,
    s.start_date,
    s.end_date,
    sp.plan_name,
    i.institution_id,
    i.name as institution_name,
    u.full_name as admin_name,
    u.email as admin_email
FROM Subscriptions s
JOIN Subscription_Plans sp ON s.plan_id = sp.plan_id
JOIN Institutions i ON s.subscription_id = i.subscription_id
JOIN Unregistered_Users u ON s.unreg_user_id = u.unreg_user_id
WHERE s.status = 'active' AND s.end_date > CURDATE();

-- View for attendance summary
CREATE VIEW Attendance_Summary_View AS
SELECT 
    ses.session_id,
    c.course_code,
    c.course_name,
    ses.session_date,
    v.venue_name,
    l.full_name as lecturer_name,
    COUNT(CASE WHEN ar.status = 'present' THEN 1 END) as present_count,
    COUNT(CASE WHEN ar.status = 'absent' THEN 1 END) as absent_count,
    COUNT(CASE WHEN ar.status = 'late' THEN 1 END) as late_count,
    COUNT(ar.student_id) as total_students
FROM Sessions ses
JOIN Courses c ON ses.course_id = c.course_id
JOIN Venues v ON ses.venue_id = v.venue_id
JOIN Lecturers l ON ses.lecturer_id = l.lecturer_id
LEFT JOIN Attendance_Records ar ON ses.session_id = ar.session_id
GROUP BY ses.session_id, c.course_code, c.course_name, ses.session_date, v.venue_name, l.full_name;

-- Create a view for easier report lookup
CREATE VIEW Report_Overview AS
SELECT 
    r.report_id,
    r.report_uuid,
    r.title,
    r.description,
    r.report_type,
    r.institution_id,
    r.reporter_email,
    r.reporter_role,
    r.status,
    r.generated_at,
    r.expires_at,
    r.file_size_bytes,
    r.format,
    r.is_public,
    i.name AS institution_name,
    CASE 
        WHEN r.reporter_role = 'admin' THEN ia.full_name
        WHEN r.reporter_role = 'lecturer' THEN l.full_name
        ELSE 'System Generated'
    END AS reporter_name
FROM Reports r
JOIN Institutions i ON r.institution_id = i.institution_id
LEFT JOIN Institution_Admins ia ON r.reporter_email = ia.email AND r.institution_id = ia.institution_id AND r.reporter_role = 'admin'
LEFT JOIN Lecturers l ON r.reporter_email = l.email AND r.institution_id = l.institution_id AND r.reporter_role = 'lecturer';

-- Create a comprehensive view for issue management
CREATE VIEW Platform_Issues_Overview AS
SELECT 
    pi.issue_id,
    pi.issue_uuid,
    pi.title,
    pi.description,
    pi.issue_type,
    pi.category,
    pi.priority,
    pi.severity,
    pi.status,
    
    -- Reporter info
    pi.reporter_type,
    pi.reporter_id,
    pi.reporter_email,
    pi.institution_id,
    
    CASE 
        WHEN pi.reporter_type = 'student' THEN s.full_name
        WHEN pi.reporter_type = 'lecturer' THEN l.full_name
        WHEN pi.reporter_type = 'admin' THEN ia.full_name
        WHEN pi.reporter_type = 'platform_manager' THEN pm.full_name
    END AS reporter_name,
    
    CASE 
        WHEN pi.reporter_type = 'student' THEN s.student_code
        WHEN pi.reporter_type = 'lecturer' THEN l.department
        WHEN pi.reporter_type = 'admin' THEN ia.email
        WHEN pi.reporter_type = 'platform_manager' THEN 'Platform Team'
    END AS reporter_detail,
    
    -- Institution info
    i.name AS institution_name,
    
    -- Assignment info
    pi.assigned_to,
    pm_assigned.full_name AS assigned_to_name,
    pi.assigned_at,
    
    -- Resolution info
    pi.resolution,
    pi.resolution_notes,
    pi.fix_version,
    
    -- Timestamps
    pi.created_at,
    pi.updated_at,
    pi.acknowledged_at,
    pi.resolved_at,
    pi.closed_at,
    
    -- Technical info
    pi.module,
    pi.page_url,
    pi.browser_info,
    pi.device_type,
    
    -- Feedback
    pi.reporter_rating,
    pi.reporter_feedback,
    
    -- Age calculations
    DATEDIFF(CURRENT_DATE(), pi.created_at) AS days_open,
    CASE 
        WHEN pi.status IN ('resolved', 'closed') 
        THEN DATEDIFF(pi.resolved_at, pi.created_at)
        ELSE DATEDIFF(CURRENT_DATE(), pi.created_at)
    END AS days_to_resolution
    
FROM Platform_Issues pi
LEFT JOIN Students s ON pi.reporter_type = 'student' 
    AND pi.reporter_id = s.student_id 
    AND pi.institution_id = s.institution_id
LEFT JOIN Lecturers l ON pi.reporter_type = 'lecturer' 
    AND pi.reporter_id = l.lecturer_id 
    AND pi.institution_id = l.institution_id
LEFT JOIN Institution_Admins ia ON pi.reporter_type = 'admin' 
    AND pi.reporter_id = ia.inst_admin_id 
    AND pi.institution_id = ia.institution_id
LEFT JOIN Platform_Managers pm ON pi.reporter_type = 'platform_manager' 
    AND pi.reporter_id = pm.platform_mgr_id
LEFT JOIN Platform_Managers pm_assigned ON pi.assigned_to = pm_assigned.platform_mgr_id
LEFT JOIN Institutions i ON pi.institution_id = i.institution_id;

-- Create view for dashboard statistics
CREATE VIEW Platform_Issues_Stats AS
SELECT 
    -- Overall stats
    COUNT(*) as total_issues,
    SUM(CASE WHEN status = 'new' THEN 1 ELSE 0 END) as new_issues,
    SUM(CASE WHEN status IN ('acknowledged', 'investigating', 'in_progress') THEN 1 ELSE 0 END) as in_progress,
    SUM(CASE WHEN status IN ('resolved', 'closed') THEN 1 ELSE 0 END) as resolved_issues,
    
    -- By type
    SUM(CASE WHEN issue_type = 'bug' THEN 1 ELSE 0 END) as bugs,
    SUM(CASE WHEN issue_type = 'feature_request' THEN 1 ELSE 0 END) as feature_requests,
    SUM(CASE WHEN issue_type = 'ui_issue' THEN 1 ELSE 0 END) as ui_issues,
    
    -- By priority
    SUM(CASE WHEN priority = 'critical' THEN 1 ELSE 0 END) as critical,
    SUM(CASE WHEN priority = 'high' THEN 1 ELSE 0 END) as high,
    SUM(CASE WHEN priority = 'medium' THEN 1 ELSE 0 END) as medium,
    SUM(CASE WHEN priority = 'low' THEN 1 ELSE 0 END) as low,
    
    -- By reporter type
    SUM(CASE WHEN reporter_type = 'student' THEN 1 ELSE 0 END) as student_reports,
    SUM(CASE WHEN reporter_type = 'lecturer' THEN 1 ELSE 0 END) as lecturer_reports,
    SUM(CASE WHEN reporter_type = 'admin' THEN 1 ELSE 0 END) as admin_reports,
    SUM(CASE WHEN reporter_type = 'platform_manager' THEN 1 ELSE 0 END) as internal_reports,
    
    -- Average time to resolution (for resolved issues)
    AVG(CASE WHEN status IN ('resolved', 'closed') 
        THEN DATEDIFF(resolved_at, created_at) END) as avg_days_to_resolve,
    
    -- Unassigned issues
    SUM(CASE WHEN assigned_to IS NULL AND status NOT IN ('resolved', 'closed') THEN 1 ELSE 0 END) as unassigned
    
FROM Platform_Issues;

-- Create a view for platform managers to review testimonials
CREATE VIEW Testimonials_For_Review AS
SELECT 
    t.testimonial_id,
    t.testimonial_uuid,
    t.author_type,
    t.author_full_name,
    t.author_email,
    t.author_department,
    t.author_year,
    t.institution_name,
    t.title,
    SUBSTRING(t.content, 1, 100) AS content_preview,
    t.rating,
    t.created_at,
    t.is_anonymous,
    t.profile_image_path,
    
    -- Additional author verification info
    CASE t.author_type
        WHEN 'student' THEN s.student_code
        WHEN 'lecturer' THEN l.department
        WHEN 'institution_admin' THEN ia.email
    END AS author_identifier,
    
    CASE t.author_type
        WHEN 'student' THEN 'Student'
        WHEN 'lecturer' THEN CONCAT('Lecturer - ', l.department)
        WHEN 'institution_admin' THEN 'Institution Admin'
    END AS author_role_display
    
FROM Testimonials t
LEFT JOIN Students s ON t.author_type = 'student' 
    AND t.author_id = s.student_id 
    AND t.institution_id = s.institution_id
    AND t.author_email = s.email
LEFT JOIN Lecturers l ON t.author_type = 'lecturer' 
    AND t.author_id = l.lecturer_id 
    AND t.institution_id = l.institution_id
    AND t.author_email = l.email
LEFT JOIN Institution_Admins ia ON t.author_type = 'institution_admin' 
    AND t.author_id = ia.inst_admin_id 
    AND t.institution_id = ia.institution_id
    AND t.author_email = ia.email
WHERE t.is_approved = FALSE 
    AND t.deleted_at IS NULL
ORDER BY t.created_at ASC;

-- Create a view for easier testimonial lookup with aggregated author info
CREATE VIEW Testimonials_Display_View AS
SELECT 
    t.testimonial_id,
    t.testimonial_uuid,
    
    -- Author display information
    CASE 
        WHEN t.is_anonymous = TRUE THEN 'Anonymous'
        ELSE t.author_full_name
    END AS display_name,
    
    CASE 
        WHEN t.is_anonymous = TRUE THEN 'User'
        ELSE t.author_type
    END AS display_role,
    
    -- Author details (only shown if not anonymous)
    t.author_type,
    t.author_full_name,
    t.author_email,
    t.author_department,
    t.author_year,
    t.author_student_code,
    t.is_anonymous,
    
    -- Institution info
    t.institution_id,
    t.institution_name,
    
    -- Testimonial content
    t.title,
    t.content,
    t.rating,
    
    -- Display properties
    t.is_featured,
    t.is_approved,
    t.display_order,
    
    -- Media
    t.profile_image_path,
    t.additional_media,
    
    -- Timestamps
    t.created_at,
    t.updated_at,
    t.approved_at,
    
    -- Approver info
    t.approved_by,
    pm.full_name AS approved_by_name,
    
    -- Additional calculated fields
    CASE 
        WHEN t.rating = 5 THEN 'Excellent'
        WHEN t.rating = 4 THEN 'Very Good'
        WHEN t.rating = 3 THEN 'Good'
        WHEN t.rating = 2 THEN 'Fair'
        ELSE 'Poor'
    END AS rating_label,
    
    -- Time since creation
    CONCAT(FLOOR(DATEDIFF(CURRENT_DATE(), t.created_at) / 30), ' months ago') AS time_since_creation
    
FROM Testimonials t
LEFT JOIN Platform_Managers pm ON t.approved_by = pm.platform_mgr_id
WHERE t.is_approved = TRUE AND t.deleted_at IS NULL
ORDER BY 
    t.is_featured DESC,
    t.display_order ASC,
    t.created_at DESC;

-- Create a view for testimonial statistics
CREATE VIEW Testimonials_Stats AS
SELECT 
    -- Overall stats
    COUNT(*) as total_testimonials,
    SUM(CASE WHEN is_approved = TRUE THEN 1 ELSE 0 END) as approved_count,
    SUM(CASE WHEN is_featured = TRUE THEN 1 ELSE 0 END) as featured_count,
    
    -- Rating distribution
    AVG(rating) as average_rating,
    SUM(CASE WHEN rating = 5 THEN 1 ELSE 0 END) as five_star,
    SUM(CASE WHEN rating = 4 THEN 1 ELSE 0 END) as four_star,
    SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END) as three_star,
    SUM(CASE WHEN rating = 2 THEN 1 ELSE 0 END) as two_star,
    SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) as one_star,
    
    -- By author type
    SUM(CASE WHEN author_type = 'student' THEN 1 ELSE 0 END) as student_testimonials,
    SUM(CASE WHEN author_type = 'lecturer' THEN 1 ELSE 0 END) as lecturer_testimonials,
    SUM(CASE WHEN author_type = 'institution_admin' THEN 1 ELSE 0 END) as admin_testimonials,
    
    -- By institution
    COUNT(DISTINCT institution_id) as institutions_with_testimonials,
    
    -- Time-based
    SUM(CASE WHEN created_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) THEN 1 ELSE 0 END) as last_30_days,
    SUM(CASE WHEN created_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY) THEN 1 ELSE 0 END) as last_7_days,
    
    -- Anonymous stats
    SUM(CASE WHEN is_anonymous = TRUE THEN 1 ELSE 0 END) as anonymous_count
    
FROM Testimonials
WHERE deleted_at IS NULL;

-- Create view for facial data with student info
CREATE VIEW Student_Facial_Profiles AS
SELECT 
    sfd.facial_data_id,
    sfd.facial_data_uuid,
    sfd.student_id,
    s.student_code,
    s.full_name,
    s.email,
    s.institution_id,
    i.name AS institution_name,
    
    -- Facial data info
    sfd.encoding_type,
    sfd.samples_count,
    sfd.confidence_score,
    sfd.quality_score,
    sfd.is_active,
    sfd.is_verified,
    
    -- Storage info
    LENGTH(sfd.facial_encodings) AS encoding_size_bytes,
    sfd.pickle_file_path,
    
    -- Timestamps
    sfd.created_at,
    sfd.updated_at,
    sfd.expires_at,
    
    -- Student status
    s.is_active AS student_active
    
FROM Student_Facial_Data sfd
JOIN Students s ON sfd.student_id = s.student_id
JOIN Institutions i ON s.institution_id = i.institution_id;