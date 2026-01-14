#!/usr/bin/env python3
"""
Test database connection with SSL
"""
import os
from dotenv import load_dotenv
import pymysql
import ssl

load_dotenv()

def test_direct_connection():
    """Test direct PyMySQL connection to verify SSL works"""
    try:
        # Get credentials from environment
        host = os.getenv('DB_HOST', 'attendai-fyp-project.mysql.database.azure.com')
        user = os.getenv('DB_USER', 'attendai_superuser')
        password = os.getenv('DB_PASSWORD', 'passwordComplicated557')
        database = os.getenv('DB_NAME', 'attendance_system')
        port = int(os.getenv('DB_PORT', '3306'))
        ssl_ca = os.getenv('DB_SSL_CA', './combined-ca-certificates.pem')
        
        print(f"Testing connection to: {host}:{port}")
        print(f"Database: {database}")
        print(f"User: {user}")
        print(f"SSL Certificate: {ssl_ca}")
        
        # Check if SSL certificate exists
        if os.path.exists(ssl_ca):
            print("✅ SSL certificate found")
            # Create SSL context with certificate
            ssl_context = ssl.create_default_context(cafile=ssl_ca)
            ssl_context.verify_mode = ssl.CERT_REQUIRED
            ssl_args = {'ssl': ssl_context}
        else:
            print("⚠️ SSL certificate not found, trying without...")
            # Try without certificate
            ssl_args = {'ssl': {'check_hostname': False}}
        
        # Try to connect
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            **ssl_args
        )
        
        print("✅ Direct PyMySQL connection successful!")
        
        # Test SSL status
        with connection.cursor() as cursor:
            cursor.execute("SHOW STATUS LIKE 'Ssl_cipher'")
            result = cursor.fetchone()
            print(f"SSL Status: {result}")
            
            cursor.execute("SELECT DATABASE(), VERSION()")
            db_info = cursor.fetchone()
            print(f"Connected to: {db_info['DATABASE()']}")
            print(f"MySQL Version: {db_info['VERSION()']}")
        
        connection.close()
        return True
        
    except pymysql.err.OperationalError as e:
        print(f"❌ Operational Error: {e}")
        print(f"Error code: {e.args[0]}")
        
        # Specific handling for SSL errors
        if e.args[0] == 3159:  # require_secure_transport error
            print("\n🔒 Azure MySQL requires SSL connection.")
            print("Solution: Enable SSL in your connection or disable require_secure_transport in Azure Portal.")
            
        elif e.args[0] == 1045:  # Access denied
            print("\n🔐 Access denied. Check username and password.")
            
        elif e.args[0] == 2003:  # Can't connect to MySQL server
            print("\n🌐 Can't connect to server. Check:")
            print("1. Hostname is correct")
            print("2. Port is correct (usually 3306)")
            print("3. Firewall allows your IP in Azure Portal")
            print("4. Server is running")
            
        return False
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_direct_connection()
    if success:
        print("\n✅ Direct connection test PASSED")
        print("\nIf this works but Flask-SQLAlchemy doesn't, check:")
        print("1. Flask-SQLAlchemy configuration in app.py")
        print("2. Make sure SQLAlchemy is using PyMySQL (not mysqlclient)")
        print("3. Check SQLAlchemy engine options")
    else:
        print("\n❌ Direct connection test FAILED")
        print("\nTroubleshooting:")
        print("1. Download SSL certificate if missing:")
        print("   Run: python -c \"import ssl; print(ssl.get_default_verify_paths())\"")
        print("2. Check Azure Portal → MySQL server → Connection security")
        print("3. Add your IP to firewall rules in Azure")
        print("4. Temporarily disable 'Enforce SSL connection' in Azure to test")