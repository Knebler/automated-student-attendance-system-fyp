from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
import os
import sys
from contextlib import contextmanager

db_details = [
    os.environ['DB_USER'],
    os.environ['DB_PASSWORD'],
    os.environ['DB_HOST'],
    os.environ['DB_PORT'],
    os.environ['DB_NAME'],
]
DATABASE_URL = "mysql+pymysql://{}:{}@{}:{}/{}?charset=utf8mb4".format(*db_details)
ROOT_URL = "mysql+pymysql://{}:{}@{}:{}".format(*db_details[:-1])

connect_args = {}
if os.environ['DB_SSL_ENABLED'] == 'true':
    ssl_ca_path = os.getenv('DB_SSL_CA', None)
    
    # If path is relative, resolve it relative to the project root (where .env is located)
    if not os.path.isabs(ssl_ca_path):
        # Get the project root directory (2 levels up from database/base.py)
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        ssl_ca_path = os.path.join(project_root, ssl_ca_path)
    
    if not os.path.exists(ssl_ca_path):
        print(f"SSL enabled but certificate not found at {ssl_ca_path}")
        print("Download it using: curl -o DigiCertGlobalRootCA.crt https://cacerts.digicert.com/DigiCertGlobalRootCA.crt")
        print("Download DigiCertGlobalRootG2.crt.pem from: https://www.digicert.com/CACerts/DigiCertGlobalRootG2.crt.pem")
        print("Download Microsoft RSA Root Certificate Authority 2017.crt from: https://aka.ms/MicrosoftRSA2017")
        print("Convert Microsoft RSA Root Certificate Authority 2017.crt to PEM format.")
        print("Then create combined-ca-certificates.pem by concatenating the downloaded certs.")
        sys.exit(1)
    connect_args = {
        'ssl': {
            'ca': ssl_ca_path,
        }
    }

root_engine = create_engine(ROOT_URL, connect_args=connect_args)

with root_engine.connect() as conn:
    conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {os.environ['DB_NAME']}"))

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=30,
    # echo=True,
    connect_args=connect_args
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()