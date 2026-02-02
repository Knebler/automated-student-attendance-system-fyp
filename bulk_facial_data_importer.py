"""
Bulk Facial Data Importer
=========================
Import collected facial data into the database.

Updated to work with your Flask app structure.

Usage:
    python bulk_facial_data_importer.py facial_data_bulk.json
    python bulk_facial_data_importer.py --skip-existing
    python bulk_facial_data_importer.py --dry-run
    python bulk_facial_data_importer.py --verify
"""

import json
import base64
import argparse
import sys
import os


class BulkFacialDataImporter:
    """Import bulk facial data into database."""
    
    def __init__(self, json_file, app=None, db=None):
        self.json_file = json_file
        self.app = app
        self.db = db
        self.session = None
        self.data = None
        self._app_context = None
        
    def _init_database(self):
        """Initialize database connection."""
        # If db was passed directly, use it
        if self.db is not None:
            try:
                self.session = self.db.session
                return True
            except:
                pass
        
        # If app was passed, get db from it
        if self.app is not None:
            try:
                self.db = self.app.config.get('db')
                if self.db:
                    self.session = self.db.session
                    return True
            except:
                pass
        
        # Try to create Flask app and get db
        try:
            # Method 1: Use create_flask_app from app.py
            from app import create_flask_app
            app = create_flask_app('dev')
            self.app = app
            
            # Push app context
            self._app_context = app.app_context()
            self._app_context.push()
            
            self.db = app.config.get('db')
            if self.db:
                self.session = self.db.session
                print("✅ Database connected via create_flask_app")
                return True
        except Exception as e:
            print(f"Method 1 failed: {e}")
        
        # Method 2: Try direct SQLAlchemy connection
        try:
            from sqlalchemy import create_engine, text
            from sqlalchemy.orm import sessionmaker
            
            # Try to load config
            db_url = os.environ.get('DATABASE_URL')
            
            if not db_url:
                # Try to read from config
                try:
                    from config import config_by_name
                    config = config_by_name.get('dev') or config_by_name.get('default')
                    if config:
                        from urllib.parse import quote_plus
                        encoded_password = quote_plus(config.MYSQL_PASSWORD)
                        db_url = (
                            f"mysql+pymysql://{config.MYSQL_USER}:{encoded_password}"
                            f"@{config.MYSQL_HOST}:{config.MYSQL_PORT}/{config.MYSQL_DB}"
                        )
                except Exception as config_err:
                    print(f"Could not load config: {config_err}")
            
            if db_url:
                engine = create_engine(db_url)
                Session = sessionmaker(bind=engine)
                self.session = Session()
                print("✅ Database connected via SQLAlchemy direct")
                return True
                
        except Exception as e:
            print(f"Method 2 failed: {e}")
        
        print("❌ Could not connect to database")
        print("   Make sure you're running this from the project directory")
        return False
    
    def load_data(self):
        """Load data from JSON file."""
        try:
            with open(self.json_file, 'r') as f:
                self.data = json.load(f)
            
            version = self.data.get('version', '1.0')
            total = self.data.get('total_students', len(self.data.get('students', [])))
            format_info = self.data.get('format', 'unknown')
            pixels = self.data.get('pixels_per_sample', 'unknown')
            
            print(f"📂 Loaded: {self.json_file}")
            print(f"   Version: {version}")
            print(f"   Format: {format_info}")
            print(f"   Pixels per sample: {pixels}")
            print(f"   Students: {total}")
            
            return True
        except Exception as e:
            print(f"❌ Failed to load file: {e}")
            return False
    
    def _decode_facial_data(self, encoded_data):
        """Decode base64 facial data back to binary."""
        try:
            return base64.b64decode(encoded_data)
        except Exception as e:
            print(f"   ⚠️ Decode error: {e}")
            return None
    
    def import_data(self, skip_existing=False, dry_run=False):
        """
        Import facial data into database.
        
        Args:
            skip_existing: If True, skip users who already have facial data
            dry_run: If True, don't commit changes
        
        Returns:
            tuple: (imported_count, skipped_count, error_count)
        """
        if not self.data:
            if not self.load_data():
                return 0, 0, 0
        
        if not self._init_database():
            return 0, 0, 0
        
        # Import text for raw SQL
        try:
            from sqlalchemy import text
        except ImportError:
            print("❌ SQLAlchemy not installed")
            return 0, 0, 0
        
        students = self.data.get('students', [])
        imported = 0
        skipped = 0
        errors = 0
        
        print(f"\n{'🧪 DRY RUN - ' if dry_run else ''}Importing {len(students)} students...")
        
        for student in students:
            user_id = student.get('user_id')
            name = student.get('name')
            encoded_data = student.get('face_encoding')
            sample_count = student.get('sample_count', 100)
            
            if not user_id or not encoded_data:
                print(f"   ❌ Invalid data for {name}")
                errors += 1
                continue
            
            try:
                # Check if user exists
                result = self.session.execute(
                    text("SELECT user_id, name FROM users WHERE user_id = :uid"),
                    {'uid': user_id}
                ).fetchone()
                
                if not result:
                    print(f"   ❌ User not found: {name} (ID: {user_id})")
                    errors += 1
                    continue
                
                db_name = result[1]
                
                # Decode facial data
                facial_data_binary = self._decode_facial_data(encoded_data)
                if facial_data_binary is None:
                    print(f"   ❌ Failed to decode data for {name}")
                    errors += 1
                    continue
                
                # Check existing record
                existing = self.session.execute(
                    text("SELECT facial_data_id FROM facial_data WHERE user_id = :uid"),
                    {'uid': user_id}
                ).fetchone()
                
                if existing:
                    if skip_existing:
                        print(f"   ⏭️ Skipped (exists): {db_name}")
                        skipped += 1
                        continue
                    
                    # Update existing
                    if not dry_run:
                        self.session.execute(
                            text("""
                                UPDATE facial_data 
                                SET face_encoding = :data, 
                                    sample_count = :count,
                                    is_active = TRUE
                                WHERE user_id = :uid
                            """),
                            {'data': facial_data_binary, 'count': sample_count, 'uid': user_id}
                        )
                    print(f"   🔄 Updated: {db_name} ({sample_count} samples, {len(facial_data_binary)} bytes)")
                else:
                    # Insert new
                    if not dry_run:
                        self.session.execute(
                            text("""
                                INSERT INTO facial_data (user_id, face_encoding, sample_count, is_active)
                                VALUES (:uid, :data, :count, TRUE)
                            """),
                            {'uid': user_id, 'data': facial_data_binary, 'count': sample_count}
                        )
                    print(f"   ✅ Imported: {db_name} ({sample_count} samples, {len(facial_data_binary)} bytes)")
                
                imported += 1
                
            except Exception as e:
                print(f"   ❌ Error for {name}: {e}")
                errors += 1
        
        # Commit if not dry run
        if not dry_run and imported > 0:
            try:
                self.session.commit()
                print(f"\n✅ Committed {imported} records to database")
            except Exception as e:
                self.session.rollback()
                print(f"\n❌ Commit failed: {e}")
                return 0, skipped, len(students)
        
        print(f"\n📊 Summary:")
        print(f"   Imported: {imported}")
        print(f"   Skipped: {skipped}")
        print(f"   Errors: {errors}")
        
        return imported, skipped, errors
    
    def verify_import(self):
        """Verify imported data in database."""
        if not self._init_database():
            return False
        
        if not self.data:
            if not self.load_data():
                return False
        
        from sqlalchemy import text
        
        students = self.data.get('students', [])
        
        print(f"\n🔍 Verifying {len(students)} students...")
        
        verified = 0
        issues = 0
        
        for student in students:
            user_id = student.get('user_id')
            name = student.get('name')
            expected_samples = student.get('sample_count', 100)
            
            result = self.session.execute(
                text("""
                    SELECT fd.sample_count, LENGTH(fd.face_encoding) as size, u.name
                    FROM facial_data fd
                    JOIN users u ON fd.user_id = u.user_id
                    WHERE fd.user_id = :uid
                """),
                {'uid': user_id}
            ).fetchone()
            
            if not result:
                print(f"   ❌ Not found: {name} (ID: {user_id})")
                issues += 1
                continue
            
            db_samples, db_size, db_name = result
            
            # Check size is reasonable
            if db_size < 10000:
                print(f"   ⚠️ {db_name}: Size too small ({db_size} bytes) - may be corrupted")
                issues += 1
            elif db_samples != expected_samples:
                print(f"   ⚠️ {db_name}: Sample count mismatch (expected {expected_samples}, got {db_samples})")
                issues += 1
            else:
                print(f"   ✅ {db_name}: {db_samples} samples, {db_size} bytes")
                verified += 1
        
        print(f"\n📊 Verification Summary:")
        print(f"   Verified: {verified}")
        print(f"   Issues: {issues}")
        
        return issues == 0
    
    def __del__(self):
        """Cleanup app context."""
        if self._app_context:
            try:
                self._app_context.pop()
            except:
                pass


def main():
    parser = argparse.ArgumentParser(description='Import bulk facial data')
    parser.add_argument('file', nargs='?', default='facial_data_bulk.json',
                        help='JSON file to import (default: facial_data_bulk.json)')
    parser.add_argument('--skip-existing', action='store_true',
                        help='Skip users who already have facial data')
    parser.add_argument('--dry-run', action='store_true',
                        help='Test import without committing')
    parser.add_argument('--verify', action='store_true',
                        help='Verify imported data')
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("   BULK FACIAL DATA IMPORTER")
    print("="*60)
    
    importer = BulkFacialDataImporter(args.file)
    
    if args.verify:
        importer.verify_import()
    else:
        importer.import_data(
            skip_existing=args.skip_existing,
            dry_run=args.dry_run
        )


if __name__ == '__main__':
    main()