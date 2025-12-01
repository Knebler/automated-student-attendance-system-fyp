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
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    department VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (institution_id) REFERENCES Institutions(institution_id) ON DELETE CASCADE,
    UNIQUE KEY unique_lecturer_email (institution_id, email),
    INDEX idx_lecturer_institution (institution_id)
);

CREATE TABLE Courses (
    course_id INT PRIMARY KEY AUTO_INCREMENT,
    institution_id INT NOT NULL,
    course_code VARCHAR(50) NOT NULL,
    course_name VARCHAR(255) NOT NULL,
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