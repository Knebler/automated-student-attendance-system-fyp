import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

class Config:
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # MySQL Configuration for SQLAlchemy
    MYSQL_HOST = os.getenv('DB_HOST', 'attendai-fyp-project.mysql.database.azure.com')
    MYSQL_USER = os.getenv('DB_USER', 'attendai_superuser')
    MYSQL_PASSWORD = os.getenv('DB_PASSWORD', 'passwordComplicated557')
    MYSQL_DB = os.getenv('DB_NAME', 'attendance_system')
    MYSQL_PORT = int(os.getenv('DB_PORT', '3306'))

    # SSL Configuration for Azure (REQUIRED)
    MYSQL_SSL_CA = os.getenv('DB_SSL_CA', './combined-ca-certificates.pem')
    MYSQL_SSL_ENABLED = os.getenv('DB_SSL_ENABLED', 'True').lower() == 'true'

    # Connection Pool Settings
    SQLALCHEMY_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '10'))
    SQLALCHEMY_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '20'))
    SQLALCHEMY_POOL_RECYCLE = int(os.getenv('DB_POOL_RECYCLE', '300'))
    SQLALCHEMY_POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', '30'))
    
    # Application Settings
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

class DevelopmentConfig(Config):
    DEBUG = True
    # Uncomment below if using local MySQL for development
    # MYSQL_HOST = 'localhost'
    # MYSQL_USER = 'root'
    # MYSQL_PASSWORD = ''
    # MYSQL_SSL_ENABLED = False

class ProductionConfig(Config):
    DEBUG = False
    # Production MUST use SSL
    MYSQL_SSL_ENABLED = True

config_by_name = {
    'dev': DevelopmentConfig,
    'prod': ProductionConfig,
    'default': DevelopmentConfig
}