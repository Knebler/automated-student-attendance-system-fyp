import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

class Config:
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # JWT Configuration (for authentication)
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)  # Can be different from Flask secret
    JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
    
    # Handle JWT expiration with proper integer conversion
    jwt_expires = os.getenv('JWT_ACCESS_TOKEN_EXPIRES', '86400')
    # Strip any comments or whitespace
    jwt_expires = jwt_expires.split('#')[0].strip() if '#' in jwt_expires else jwt_expires.strip()
    JWT_ACCESS_TOKEN_EXPIRES = int(jwt_expires)  # 24 hours in seconds
    
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
    
    # Bcrypt Configuration (for password hashing)
    bcrypt_rounds = os.getenv('BCRYPT_LOG_ROUNDS', '12')
    bcrypt_rounds = bcrypt_rounds.split('#')[0].strip() if '#' in bcrypt_rounds else bcrypt_rounds.strip()
    BCRYPT_LOG_ROUNDS = int(bcrypt_rounds)
    
    # Session Configuration
    SESSION_TYPE = os.getenv('SESSION_TYPE', 'filesystem')
    SESSION_PERMANENT = os.getenv('SESSION_PERMANENT', 'False').lower() == 'true'
    
    session_lifetime = os.getenv('PERMANENT_SESSION_LIFETIME', '3600')
    session_lifetime = session_lifetime.split('#')[0].strip() if '#' in session_lifetime else session_lifetime.strip()
    PERMANENT_SESSION_LIFETIME = int(session_lifetime)  # 1 hour

class DevelopmentConfig(Config):
    DEBUG = True
    # Uncomment below if using local MySQL for development
    # MYSQL_HOST = 'localhost'
    # MYSQL_USER = 'root'
    # MYSQL_PASSWORD = ''
    # MYSQL_SSL_ENABLED = False
    # JWT_ACCESS_TOKEN_EXPIRES = 86400  # 24 hours for dev

class ProductionConfig(Config):
    DEBUG = False
    # Production MUST use SSL
    MYSQL_SSL_ENABLED = True
    # Shorter token expiration for production security
    JWT_ACCESS_TOKEN_EXPIRES = 28800  # 8 hours

config_by_name = {
    'dev': DevelopmentConfig,
    'prod': ProductionConfig,
    'default': DevelopmentConfig
}