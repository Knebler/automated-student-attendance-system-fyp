# AttendAI (Automated Student Attendance System)

A full-stack web application built as a school project which aims to demonstrate the integration of generative AI within a modern, secure web environment. The project uses Python and Flask on the backend, MySQL for data storage, Bootstrap for a responsive user interface, and a local DB-backed authentication system.

## Overview

This application showcases generative artificial intelligence capabilities with a focus on Facial Recognition. Users should use this system for their educational institute entirely for attendance taking purposes. Our application allows for a seamless integration experience with any educational institute's operations as the application's primary interface is Web-based. All data is managed through a MySQL database, and user sessions are handled via Flask server-side sessions backed by the local users table.

## Project Structure
```
automated-student-attendance-system-fyp/
├── README.md                           # Project documentation
├── requirements.txt                    # Python dependencies
├── config.py                           # Application configuration
├── app.py                             # Main Flask application entry point
├── .env.example                        # Environment variables template
├── .env                                # Environment variables (create from .env.example)
├── .db_initialized                     # Database initialization marker (auto-created)
├── .gitignore                          # Git ignore file
├── LICENSE                             # Project license
│
├── .github/                            # GitHub-specific files
│   └── copilot-instructions.md         # AI agent guidance for the repo
│
├── database/                           # Database-related files
│   └── schema.sql                      # Complete database schema
│
├── helper/                             # Helper scripts and utilities
│   └── db/                             # Database helpers
│       ├── __init__.py
│       ├── delete_database.py          # Database deletion utility
│       ├── create_database.py          # Database creation utility
│       ├── migrate_sqlalchemy.py       # SQLAlchemy migration helper
│       └── populate_dummy_data.py      # Dummy data population
│
├── application/                        # BCE Architecture Structure
│   ├── __init__.py                     # Application package initializer with blueprint registration
│   ├── extensions.py                   # Flask extensions (if needed)
│   │
│   ├── entities/                       # Data Models (Entities)
│   │   ├── __init__.py                 # Import all entities
│   │   ├── base_entity.py              # Base entity class with common DB operations
│   │   ├── attendance_record.py        # Attendance record entity
│   │   ├── course.py                   # Course entity
│   │   ├── enrollment.py               # Enrollment entity
│   │   ├── institution.py              # Institution entity
│   │   ├── lecturer.py                 # Lecturer entity
│   │   ├── platform_manager.py         # Platform Manager entity
│   │   ├── session.py                  # Session entity
│   │   ├── student.py                  # Student entity
│   │   ├── subscription.py             # Subscription entity
│   │   ├── subscription_plan.py        # Subscription Plan entity
│   │   ├── timetable_slot.py           # Timetable Slot entity
│   │   ├── user.py                     # User entity
│   │   └── venue.py                    # Venue entity
│   │
│   ├── boundaries/                     # Interfaces/APIs (Boundaries)
│   │   ├── __init__.py                 # Import all boundaries
│   │   ├── admin_boundary.py           # Platform admin routes
│   │   ├── attendance_boundary.py      # Attendance-related routes
│   │   ├── auth_boundary.py            # Authentication routes (login, register, logout)
│   │   ├── dashboard_boundary.py       # Dashboard routes for all user types
│   │   ├── dev_actions.py              # Developer action registration
│   │   ├── dev_boundary.py             # Developer routes
│   │   ├── institution_admin_boundary.py # Institution admin routes
│   │   ├── institution_boundary.py     # Institution management (compatibility wrapper)
│   │   ├── lecturer_boundary.py        # Lecturer-specific routes
│   │   ├── main_boundary.py            # Main site routes (home, about, health)
│   │   ├── platform_boundary.py        # Platform manager routes
│   │   └── student_boundary.py         # Student-specific routes
│   │
│   └── controls/                       # Business Logic (Controls)
│       ├── __init__.py                 # Import all controls
│       ├── attendance_control.py       # Attendance business logic
│       ├── auth_control.py             # Authentication business logic
│       ├── database_control.py         # Database initialization and maintenance
│       └── institution_control.py      # Institution management logic
│
├── src/                                # AI/ML Model code
│   └── ai_model.py                     # AI model integration (currently placeholder)
│
├── static/                             # Static assets
│   ├── css/                            # CSS files
│   │   ├── bootstrap.css               # Bootstrap CSS
│   │   ├── bootstrap.min.css           # Bootstrap CSS (minified)
│   │   ├── bootstrap-grid.css          # Bootstrap grid CSS
│   │   ├── bootstrap-grid.min.css      # Bootstrap grid CSS (minified)
│   │   ├── bootstrap-reboot.css        # Bootstrap reboot CSS
│   │   └── bootstrap-reboot.min.css    # Bootstrap reboot CSS (minified)
│   │
│   ├── js/                             # JavaScript files
│   │   ├── bootstrap.js                # Bootstrap JS
│   │   ├── bootstrap.min.js            # Bootstrap JS (minified)
│   │   ├── bootstrap.bundle.js         # Bootstrap bundle JS
│   │   └── bootstrap.bundle.min.js     # Bootstrap bundle JS (minified)
│   │
│   └── img/                            # Image assets
│
├── templates/                          # HTML Templates (Jinja2)
│   ├── layouts/                        # Base layouts
│   │   └── base.html                   # Base template with role-aware navigation
│   │
│   ├── auth/                           # Authentication templates
│   │   ├── login.html                  # Login page
│   │   └── register.html               # Registration page
│   │
│   ├── institution/                    # Institution management templates
│   │   ├── admin/                      # Institution admin templates
│   │   │   ├── institution_admin_dashboard.html
│   │   │   ├── institution_admin_user_management.html
│   │   │   ├── institution_admin_attendance_management.html
│   │   │   ├── institution_admin_attendance_management_student_details.html
│   │   │   ├── institution_admin_attendance_management_class_details.html
│   │   │   ├── institution_admin_attendance_management_report.html
│   │   │   ├── institution_admin_class_management.html
│   │   │   ├── institution_admin_institute_profile.html
│   │   │   └── import_institution_data.html
│   │   ├── lecturer/                   # Lecturer templates
│   │   │   └── lecturer_dashboard.html
│   │   └── student/                    # Student templates
│   │
│   ├── unregistered/                   # Unregistered user pages
│   │   ├── aboutus.html
│   │   ├── faq.html
│   │   ├── features.html
│   │   ├── subscriptionsummary.html
│   │   └── testimonials.html
│   │
│   ├── platmanager/                    # Platform manager templates
│   │   └── platform_dashboard.html
│   │
│   ├── errors/                         # Error pages
│   │   ├── 404.html                    # 404 Not Found
│   │   └── 500.html                    # 500 Internal Server Error
│   │
│   ├── components/                     # Reusable components
│   │
│   ├── dev/                            # Developer-only pages
│   │   └── test_endpoint.html          # Endpoint testing page
│   │
│   └── index.html                      # Home page with feature tabs
│
├── instance/                           # Instance folder (for sensitive config)
│
├── dummy_data/                         # Dummy data helpers
│   ├── dummy_data_reference.csv        # Shorthand dummy data for reference
│   └── load_dummy_data.py              # Standalone data loader script
│
├── AttendanceAI/                       # Facial Recognition AI module (separate)
│   ├── app.py
│   ├── add_faces.py
│   ├── test.py
│   ├── data/
│   │   └── haarcascade_frontalface_default.xml
│   └── Attendance/
│
├── .venv/                              # Python virtual environment (created locally)
│
└── .pytest_cache/                      # pytest cache directory
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

Follow these instructions to get the project running.

### Prerequisites

*   Python 3.10+ installed
*   MySQL Server installed and running
*   Git installed

### Installation Steps

1.  **Clone the Repository**
    ```bash
    git clone github.com
    cd automated-student-attendance-system-fyp
    ```

2.  **Set up a Virtual Environment**
    ```
    python3 -m venv venv
    # Activate the environment (Mac/Linux)
    source venv/bin/activate
    # Activate the environment (Windows)
    .\venv\Scripts\activate
    ```

3.  **Install Python Dependencies**
    ```
    pip install -r requirements.txt
    ```

4.  **Set up Environment Variables**
    cp .env.example .env
    * Edit .env with your MySQL credentials

5.  **Run schema.sql to create the Database**
    mysql -u root -p < schema.sql

6.  **Running the Application**
        Run app.py and go to http://localhost:5000 / http://127.0.0.1:5000 / http://192.168.18.64:5000

### Dev helper endpoint
For local development there is a small developer-only testing page that accepts a plain-text message (POST) and returns it as text/plain so you can quickly verify basic endpoint behavior or echo request bodies. Visit:

    - GET/POST /dev/test-endpoint

This endpoint is intended for development only and should not be exposed in production.

### Contribution Areas
 *  "application" folder is for anything backend related
 *  "src" folder is for anything AI/model related
 *  "templates" folder is for anything frontend related
 *  "static" folder is for anything frontend related in styles

This file will be updated when message standards are consolidated.