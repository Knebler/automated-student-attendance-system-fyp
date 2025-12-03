# Automated Student Attendance System

A full-stack web application built for a school project demonstrates the integration of generative AI within a modern, secure web environment. The project uses Python and Flask on the backend, MySQL for data storage, Bootstrap for a responsive user interface, and Firebase for authentication.

## Overview

This application showcases generative artificial intelligence capabilities with a focus on Facial Recognition. Users should use this system for their educational institute entirely for attendance taking purposes. Our application allows for a seamless integration experience with any educational institute's operations as the application's primary interface is Web-based. All data is managed through a MySQL database, and user sessions are handled by Firebase Auth.

## Project Structure
```
automated-student-attendance-system/
├── README.md                           # Project documentation
├── requirements.txt                    # Python dependencies
├── config.py                           # Application configuration
├── app.py                             # Main Flask application entry point
├── dummy_data_reference.csv           # CSV with all dummy data
├── DUMMY_DATA_REFERENCE.md            # Markdown reference guide
├── .env.example                        # Environment variables template
├── .env                                # Environment variables (create from .env.example)
├── .db_initialized                     # Database initialization marker (auto-created)
├── .gitignore                          # Git ignore file
│
├── database/                           # Database-related files
│   ├── __init__.py
│   └── schema.sql                      # Complete database schema
│
├── helper/                             # Helper scripts and utilities
│   ├── __init__.py
│   └── db/                             # Database helpers
│       ├── __init__.py
│       ├── delete_database.py          # Database deletion utility
│       ├── create_database.py          # Database creation utility
│       └── populate_dummy_data.py      # Dummy data population
│
├── application/                        # BCE Architecture Structure
│   ├── __init__.py                     # Application package initializer
│   │
│   ├── entities/                       # Data Models (Entities)
│   │   ├── __init__.py                 # Import all entities
│   │   ├── base_entity.py              # Base entity class with common DB operations
│   │   ├── user.py                     # Generic user entity (if needed)
│   │   ├── attendance.py               # Attendance entity
│   │   ├── institution.py              # Institution entity
│   │   ├── course.py                   # Course entity
│   │   ├── lecturer.py                 # Lecturer entity
│   │   ├── student.py                  # Student entity
│   │   ├── enrollment.py               # Enrollment entity
│   │   ├── session.py                  # Session entity
│   │   ├── platform_manager.py         # Platform Manager entity
│   │   ├── subscription_plan.py        # Subscription Plan entity
│   │   ├── subscription.py             # Subscription entity
│   │   ├── venue.py                    # Venue entity
│   │   └── timetable_slot.py           # Timetable Slot entity
│   │
│   ├── boundaries/                     # Interfaces/APIs (Boundaries)
│   │   ├── __init__.py                 # Import all boundaries
│   │   ├── main_boundary.py            # Main site routes (home, about, health)
│   │   ├── auth_boundary.py            # Authentication routes (login, register, logout)
│   │   ├── attendance_boundary.py      # Attendance-related routes
│   │   ├── dashboard_boundary.py       # Dashboard routes for all user types
│   │   ├── institution_boundary.py     # Institution management routes
│   │   ├── admin_boundary.py           # Platform admin routes
│   │   └── dev_boundary.py             # Developer route
│   │
│   └── controls/                       # Business Logic (Controls)
│       ├── __init__.py                 # Import all controls
│       ├── auth_control.py             # Authentication business logic
│       ├── attendance_control.py       # Attendance business logic
│       ├── institution_control.py      # Institution management logic
│       ├── user_control.py             # User management logic
│       └── database_control.py         # Database initialization and maintenance
│
├── static/                             # Static assets
│   ├── css/                            # CSS files
│   │   ├── bootstrap.min.css           # Bootstrap CSS
│   │   └── custom.css                  # Custom CSS
│   │
│   ├── js/                             # JavaScript files
│   │   ├── bootstrap.min.js            # Bootstrap JS
│   │   ├── jquery.min.js               # jQuery (if needed)
│   │   ├── firebase-config.js          # Firebase client-side config
│   │   └── custom.js                   # Custom JavaScript
│   │
│   ├── img/                            # Images
│   │
│   └── uploads/                        # User uploads (attendance images, etc.)
│       ├── attendance/
│       └── profile/
│
├── templates/                          # HTML Templates (Jinja2)
│   ├── layouts/                        # Base layouts
│   │   └── base.html                   # Base template with navigation
│   │
│   ├── auth/                           # Authentication templates
│   │   ├── ...                  
│   │
│   ├── dashboards/                     # Dashboard templates
│   │   ├── ...
│   │
│   ├── attendance/                     # Attendance-related templates
│   │   ├── ...
│   │
│   ├── institution/                    # Institution management
│   │   ├── ...
│   │
│   ├── admin/                          # Platform admin templates
│   │   ├── ...
│   │
│   ├── errors/                         # Error pages
│   │   ├── 404.html                    # 404 Not Found
│   │   └── 500.html                    # 500 Internal Server Error
│   │
│   ├── components/                     # Reusable components
│   │   ├── navbar.html                 # Navigation bar
│   │   ├── footer.html                 # Footer
│   │   ├── sidebar.html                # Sidebar for dashboards
│   │   └── alerts.html                 # Alert messages
│   │
│   ├── dev/                            # Developer-only pages
│   │   └── test_endpoint.html          # Endpoint testing page
│   │
│   └── index.html                      # Home page
│
├── instance/                           # Instance folder (for sensitive config)
│   ├── config.py                       # Instance-specific config
│   └── firebase_service_account.json   # Firebase service account (if using Admin SDK)
│
├── venv/                               # Virtual environment (created locally)
│
|── logs/                               # Application logs
|   ├── app.log                         # General application log
|   ├── error.log                       # Error log
|   └── access.log                      # Access log
|
|── dummy_data/
|   ├── dummy_data_reference.csv        # Shorthand dummy data for reference
|   ├── load_dummy_data.py              # Standalone data loader script
```

## Features

*   **Secure Authentication:** User management via Firebase Authentication (email/password).
*   **Generative AI Integration:** Backend integration with AI models to provide dynamic facial recognition capabilities.
*   **Data Persistence:** Storage of user data and AI generation history in a MySQL relational database.
*   **Scalable Backend:** A flexible Flask microframework architecture.

## Tech Stack

*   **Frontend:** HTML5, CSS3 (Bootstrap framework), JavaScript (for Firebase SDK)
*   **Backend:** Python 3.10+, Flask
*   **Database:** MySQL
*   **Authentication:** Firebase Authentication
*   **AI/ML Libraries:** `openai`, `firebase-admin`, `Flask-SQLAlchemy`, etc.

## Getting Started

Follow these instructions to get the project running.

### Prerequisites

*   Python 3.10+ installed
*   MySQL Server installed and running
*   Git installed
*   A Firebase Project and service account credentials

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
    * Edit .env with your Firebase and MySQL credentials

5.  **Run schema.sql to create the Database**
    mysql -u root -p < schema.sql

6.  **Running the Application**
        Run app.py and go to http://localhost:5000

### Dev helper endpoint
For local development there is a small developer-only testing page that accepts a plain-text message (POST) and returns it as text/plain so you can quickly verify basic endpoint behavior or echo request bodies. Visit:

    - GET/POST /dev/test-endpoint

This endpoint is intended for development only and should not be exposed in production.

### Contribution Areas
 *  "application" folder is for anything backend related
 *  "src" folder is for anything AI/model related
 *  "templates" folder is for anything frontend related
 *  "static" folder is for anything frontend related in styles

This file will be updated when message standards are consolidated for testing.