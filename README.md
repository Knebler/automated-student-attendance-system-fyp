# AttendAI (Automated Student Attendance System)

A full-stack web application built as a school project which aims to demonstrate the integration of generative AI within a modern, secure web environment. The project uses Python and Flask on the backend, MySQL for data storage, Bootstrap for a responsive user interface, and a local DB-backed authentication system.

## Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Attendance / Facial-recognition module](#attendance--facial-recognition-module)
- [Running tests](#running-tests)

## Overview

This application showcases generative artificial intelligence capabilities with a focus on Facial Recognition. Users should use this system for their educational institute entirely for attendance taking purposes. Our application allows for a seamless integration experience with any educational institute's operations as the application's primary interface is Web-based. All data is managed through a MySQL database, and user sessions are handled via Flask server-side sessions backed by the local users table.

## Project Structure
```
automated-student-attendance-system-fyp/
├── README.md
├── requirements.txt
├── config.py
├── app.py
├── attendance_ai_blueprint.py
├── attendance_client.py
├── bulk_facial_data_collector.py
├── bulk_facial_data_gui.py
├── bulk_facial_data_importer.py
├── delete_bad_facial_data.py
├── fix_facial_data.py
├── increase_facial_data_column.py
├── launch_bulk_facial_gui.bat
├── run_faq_migration.bat
├── ATTENDANCE_AUDIT_README.md
├── BULK_FACIAL_DATA_README.md
├── SENTIMENT_ANALYSIS_README.md
├── combined-ca-certificates.pem
├── LICENSE
├── .env.example
├── .env
├── .gitignore
├── .venv/                                   # local virtual environment (not committed)
├── .vscode/                                 # VS Code workspace settings
├── .pytest_cache/
├── backups/
├── database/                                # DB schema & migration helpers
│   ├── schema.sql
│   ├── manage_db.py
│   ├── migrations/
│   └── models.py
├── application/                             # Backend (BCE structure)
│   ├── __init__.py
│   ├── extensions.py
│   ├── boundaries/                           # HTTP/API boundaries (Flask blueprints)
│   │   ├── attendance_boundary.py
│   │   ├── auth_boundary.py
│   │   ├── dev_actions.py
│   │   ├── dev_boundary.py
│   │   ├── facial_recognition_boundary.py
│   │   ├── institution_admin_boundary.py
│   │   ├── lecturer_boundary.py
│   │   ├── main_boundary.py
│   │   └── platform_boundary.py
│   ├── controls/                             # Business logic / controllers
│   │   ├── announcement_control.py
│   │   ├── attendance_control.py
│   │   ├── auth_control.py
│   │   ├── class_control.py
│   │   ├── course_control.py
│   │   ├── database_control.py
│   │   ├── facial_recognition_control.py
│   │   ├── import_data_control.py
│   │   ├── institution_control.py
│   │   ├── lecturer_control.py
│   │   ├── platformissue_control.py
│   │   ├── platform_control.py
│   │   ├── student_control.py
│   │   └── testimonial_control.py
│   ├── entities/                             # Legacy / domain entities
│   │   ├── base_entity.py
│   │   ├── attendance_record.py
│   │   ├── course.py
│   │   ├── enrollment.py
│   │   ├── institution.py
│   │   ├── institution_admin.py
│   │   ├── lecturer.py
│   │   ├── platform_manager.py
│   │   ├── report.py
│   │   ├── session.py
│   │   ├── student.py
│   │   ├── subscription.py
│   │   ├── subscription_plan.py
│   │   ├── timetable_slot.py
│   │   ├── unregistered_user.py
│   │   └── venue.py
│   └── entities2/                            # Current data models (entities2)
│       ├── __init__.py
│       ├── announcement.py
│       ├── attendance_appeal.py
│       ├── attendance_record.py
│       ├── base_entity.py
│       ├── classes.py
│       ├── course.py
│       ├── course_user.py
│       ├── institution.py
│       ├── notification.py
│       ├── platformissue.py
│       ├── semester.py
│       ├── subscription.py
│       ├── subscription_plans.py
│       ├── testimonial.py
│       ├── user.py
│       └── venue.py
├── AttendanceAI/                            # Facial-recognition module / helpers
│   ├── app.py                               # optional Streamlit viewer
│   ├── add_faces.py                         # webcam capture helper
│   ├── test.py
│   └── data/
│       ├── haarcascade_frontalface_default.xml
│       ├── faces_data.pkl
│       └── names.pkl
├── instance/
├── src/                                     # ML / AI experiments
│   └── ai_model.py
├── static/                                  # frontend static assets (css/js/img)
├── templates/                                # Jinja2 templates for UI
│   ├── layouts/
│   │   ├── base.html
│   │   └── navbar.html
│   ├── auth/
│   │   ├── login.html
│   │   ├── payment.html
│   │   └── register.html
│   ├── institution/
│   │   ├── admin/
│   │   │   ├── import_institution_data.html
│   │   │   ├── import_institution_data_results.html
│   │   │   ├── institution_admin_add_class.html
│   │   │   ├── institution_admin_add_course.html
│   │   │   ├── institution_admin_add_user.html
│   │   │   ├── institution_admin_appeal_management.html
│   │   │   ├── institution_admin_attendance_management.html
│   │   │   ├── institution_admin_attendance_management_class_details.html
│   │   │   ├── institution_admin_attendance_management_report.html
│   │   │   ├── institution_admin_attendance_management_student_details.html
│   │   │   ├── institution_admin_audit_attendance.html
│   │   │   ├── institution_admin_class_management.html
│   │   │   ├── institution_admin_class_management_module_classes_details.html
│   │   │   ├── institution_admin_class_management_module_details.html
│   │   │   ├── institution_admin_create_announcement.html
│   │   │   ├── institution_admin_dashboard.html
│   │   │   ├── institution_admin_edit_class.html
│   │   │   ├── institution_admin_institution_profile.html
│   │   │   ├── institution_admin_manage_announcements.html
│   │   │   ├── institution_admin_profile_update.html
│   │   │   ├── institution_admin_student_class_attendance_page.html
│   │   │   ├── institution_admin_user_management.html
│   │   │   ├── institution_admin_user_management_user_details.html
│   │   │   ├── institution_admin_user_management_user_edit.html
│   │   │   ├── institution_admin_view_announcement.html
│   │   │   └── institution_admin_view_appeal.html
│   │   ├── lecturer/
│   │   │   ├── lecturer_attendance_management.html
│   │   │   ├── lecturer_attendance_management_statistics.html
│   │   │   ├── lecturer_class_management.html
│   │   │   ├── lecturer_dashboard.html
│   │   │   └── lecturer_timetable.html
│   │   └── student/
│   │       ├── student_announcements.html
│   │       ├── student_appeal_management.html
│   │       ├── student_appeal_management_appeal_form.html
│   │       ├── student_appeal_management_module_details.html
│   │       ├── student_attendance_management.html
│   │       ├── student_attendance_management_history.html
│   │       ├── student_class_checkin.html
│   │       ├── student_class_checkin_face.html
│   │       ├── student_class_details.html
│   │       ├── student_dashboard.html
│   │       ├── student_facial_recognition_retrain.html
│   │       ├── student_inbox_management.html
│   │       ├── student_profile_management.html
│   │       ├── student_timetable.html
│   │       └── student_update_facial_data.html
│   ├── unregistered/
│   │   ├── aboutus.html
│   │   ├── faq.html
│   │   ├── features.html
│   │   ├── subscriptionsummary.html
│   │   ├── testimonialdetails.html
│   │   ├── testimonials.html
│   │   └── testimonial_submission.html
│   ├── platmanager/
│   │   ├── platform_manager_dashboard.html
│   │   ├── platform_manager_feature_management.html
│   │   ├── platform_manager_landing_page.html
│   │   ├── platform_manager_performance_management.html
│   │   ├── platform_manager_report_management.html
│   │   ├── platform_manager_report_management_report_details.html
│   │   ├── platform_manager_settings_management.html
│   │   ├── platform_manager_subscription_management.html
│   │   ├── platform_manager_subscription_management_pending_registrations.html
│   │   ├── platform_manager_subscription_management_profile_creator.html
│   │   ├── platform_manager_testimonial_approve.html
│   │   └── platform_manager_user_management.html
│   ├── errors/
│   │   ├── 404.html
│   │   └── 500.html
│   ├── components/
│   │   ├── my_reports.html
│   │   ├── report_issue_button.html
│   │   └── report_issue_details.html
│   ├── dev/
│   │   └── test_endpoint.html
│   └── index.html
├── test_sentiment_analysis.py
└── __pycache__/
```

## Features

*   **Secure Authentication:** User management via local DB (bcrypt password hashing).
*   **Generative AI Integration:** Backend integration with AI models to provide dynamic facial recognition capabilities.
*   **Data Persistence:** Storage of user data and AI generation history in a MySQL relational database.
*   **Scalable Backend:** A flexible Flask microframework architecture.

## Tech Stack

*   **Frontend:** HTML5, CSS3 (Bootstrap framework), JavaScript
*   **Backend:** Python 3.10+, Flask
*   **Database:** MySQL
*   **Authentication:** Local DB-based (bcrypt)
*   **AI/ML Libraries:** `openai`, `Flask-SQLAlchemy`, etc.

## Getting Started

Follow these instructions to get the project running locally. The examples include a Windows PowerShell quickstart (project is cross-platform).

### Prerequisites

*   Python 3.10+ installed
*   MySQL Server installed and running
*   Git installed

---

### Quickstart — Windows (PowerShell)

```powershell
# clone
git clone <repo-url>
cd automated-student-attendance-system-fyp

# create + activate venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# install deps
pip install -r requirements.txt

# copy env file and edit DB_* values
Copy-Item .env.example .env
# edit .env with your DB credentials (DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT)

# create schema (using MySQL client)
mysql -u root -p < database\schema.sql

# run the server
python app.py
# open http://localhost:5000
```

### Quickstart — macOS / Linux

```bash
git clone <repo-url>
cd automated-student-attendance-system-fyp
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # edit .env
mysql -u root -p < database/schema.sql
python app.py
```

---

### Environment variables

Edit `.env` (copied from `.env.example`) and set your MySQL connection values (`DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_PORT`) and SSL options if needed.

### Database & migrations

* Primary schema: `database/schema.sql`
* Helper scripts: `helper/db/create_database.py`, `helper/db/populate_dummy_data.py`, and `database/manage_db.py` for maintenance/migrations.

### Running the web application

* Start the server: `python app.py` (recommended for local dev).
* The server exposes an Attendance AI API at `/api` and the web UI at `/`.
* To start facial recognition from the client: `python attendance_client.py` or POST `/api/recognition/start`.

### Attendance / Facial-recognition module

Location: `AttendanceAI/` and `application` (server-side API)

* Collect training images: `python AttendanceAI/add_faces.py` (local webcam) — images and names are stored under `AttendanceAI/data/`.
* Desktop client: `attendance_client.py` — run locally and point to `http://localhost:5000` (client uploads recognition results to the server).
* Streamlit attendance viewer (optional): `streamlit run AttendanceAI/app.py` (install `streamlit` separately if you want to run this UI).

> Note: `AttendanceAI/add_faces.py` and `attendance_client.py` expect OpenCV (`opencv-python`) and scikit-learn which are listed in `requirements.txt`.

### Running tests

Run the unit tests with:

```bash
pytest -q
```