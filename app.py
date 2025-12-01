from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import pyrebase
from application import create_app
import os

def create_flask_app(config_name='default'):
    """Factory function to create Flask application"""
    app = Flask(__name__)
    
    # Load configuration
    from config import config_by_name
    app.config.from_object(config_by_name[config_name])
    
    # Configure SQLAlchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{app.config['MYSQL_USER']}:{app.config['MYSQL_PASSWORD']}@{app.config['MYSQL_HOST']}/{app.config['MYSQL_DB']}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize SQLAlchemy
    db = SQLAlchemy(app)
    
    # Configure Firebase
    firebase_config = {
        "apiKey": app.config['FIREBASE_API_KEY'],
        "authDomain": app.config['FIREBASE_AUTH_DOMAIN'],
        "projectId": app.config['FIREBASE_PROJECT_ID'],
        "storageBucket": app.config['FIREBASE_STORAGE_BUCKET'],
        "messagingSenderId": app.config['FIREBASE_MESSAGING_SENDER_ID'],
        "appId": app.config['FIREBASE_APP_ID'],
        "databaseURL": app.config.get('FIREBASE_DATABASE_URL', '')
    }
    
    firebase = pyrebase.initialize_app(firebase_config)
    auth = firebase.auth()
    
    # Store extensions in app config
    app.config['db'] = db  # SQLAlchemy instance
    app.config['firebase_auth'] = auth
    app.config['firebase_app'] = firebase
    
    # Create database and tables on first run
    if not os.path.exists('.db_initialized'):
        print("Initializing database for first run...")
        from helper.db.delete_database import delete_db
        from helper.db.create_database import create_db
        
        # Delete existing database if needed
        delete_db()
        
        # Create database and tables
        if create_db():
            # Create marker file to indicate DB was initialized
            with open('.db_initialized', 'w') as f:
                f.write('1')
            print("Database initialized successfully!")
        else:
            print("Failed to initialize database!")
    
    # Initialize application with BCE structure
    create_app(app)
    
    return app

if __name__ == '__main__':
    app = create_flask_app('dev')
    app.run(debug=True, host='0.0.0.0', port=5000)