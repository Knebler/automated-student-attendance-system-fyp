"""
Bulk Facial Data Importer
Imports facial data from JSON file into database
Matches by user_id
"""

import json
import base64
from datetime import datetime
from database.base import get_session
from database.models import FacialData, User

class BulkFacialDataImporter:
    def __init__(self, input_file='facial_data_bulk.json'):
        self.input_file = input_file
        self.stats = {
            'total': 0,
            'imported': 0,
            'updated': 0,
            'failed': 0,
            'user_not_found': 0
        }
    
    def import_data(self, skip_existing=False, dry_run=False):
        """
        Import facial data from JSON file into database
        
        Args:
            skip_existing: If True, skip users who already have facial data
            dry_run: If True, don't commit to database (test mode)
        """
        print(f"\n{'='*60}")
        print(f"BULK FACIAL DATA IMPORTER")
        print(f"{'='*60}")
        
        # Load JSON file
        try:
            with open(self.input_file, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"❌ File not found: {self.input_file}")
            return False
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON file: {e}")
            return False
        
        students = data.get('students', [])
        self.stats['total'] = len(students)
        
        print(f"\n📊 Found {len(students)} student(s) in file")
        print(f"   Created at: {data.get('created_at', 'Unknown')}")
        
        if dry_run:
            print(f"\n⚠ DRY RUN MODE - No changes will be saved\n")
        
        # Import each student
        with get_session() as db_session:
            for idx, student_data in enumerate(students, 1):
                user_id = student_data.get('user_id')
                name = student_data.get('name')
                face_encoding_b64 = student_data.get('face_encoding')
                sample_count = student_data.get('sample_count', 0)
                
                print(f"\n[{idx}/{len(students)}] Processing: {name} (ID: {user_id})")
                
                # Validate data
                if not user_id or not face_encoding_b64:
                    print(f"  ❌ Missing required data")
                    self.stats['failed'] += 1
                    continue
                
                # Check if user exists in database
                user = db_session.query(User).filter(User.user_id == user_id).first()
                
                if not user:
                    print(f"  ⚠ User ID {user_id} not found in database")
                    self.stats['user_not_found'] += 1
                    continue
                
                # Decode base64 to binary
                try:
                    face_encoding_binary = base64.b64decode(face_encoding_b64)
                except Exception as e:
                    print(f"  ❌ Failed to decode facial data: {e}")
                    self.stats['failed'] += 1
                    continue
                
                # Check if facial data already exists
                existing = db_session.query(FacialData).filter(
                    FacialData.user_id == user_id,
                    FacialData.is_active == True
                ).first()
                
                if existing:
                    if skip_existing:
                        print(f"  ⏭ Skipping (already has facial data)")
                        continue
                    else:
                        # Update existing record
                        if not dry_run:
                            existing.face_encoding = face_encoding_binary
                            existing.sample_count = sample_count
                            existing.updated_at = datetime.now()
                        print(f"  ✓ Updated existing facial data ({sample_count} samples)")
                        self.stats['updated'] += 1
                else:
                    # Insert new record
                    if not dry_run:
                        new_facial_data = FacialData(
                            user_id=user_id,
                            face_encoding=face_encoding_binary,
                            sample_count=sample_count,
                            created_at=datetime.now(),
                            updated_at=datetime.now(),
                            is_active=True
                        )
                        db_session.add(new_facial_data)
                    print(f"  ✓ Imported new facial data ({sample_count} samples)")
                    self.stats['imported'] += 1
            
            # Commit changes
            if not dry_run:
                try:
                    db_session.commit()
                    print(f"\n✓ Changes committed to database")
                except Exception as e:
                    db_session.rollback()
                    print(f"\n❌ Failed to commit: {e}")
                    return False
            else:
                print(f"\n⚠ Dry run completed - no changes saved")
        
        # Print summary
        self._print_summary()
        return True
    
    def verify_import(self):
        """Verify imported data by checking database"""
        print(f"\n{'='*60}")
        print(f"VERIFYING IMPORT")
        print(f"{'='*60}\n")
        
        try:
            with open(self.input_file, 'r') as f:
                data = json.load(f)
        except Exception as e:
            print(f"❌ Failed to load file: {e}")
            return False
        
        students = data.get('students', [])
        
        with get_session() as db_session:
            verified = 0
            missing = 0
            
            for student_data in students:
                user_id = student_data.get('user_id')
                name = student_data.get('name')
                expected_samples = student_data.get('sample_count', 0)
                
                # Check database
                facial_data = db_session.query(FacialData).filter(
                    FacialData.user_id == user_id,
                    FacialData.is_active == True
                ).first()
                
                if facial_data:
                    if facial_data.sample_count == expected_samples:
                        print(f"✓ {name} (ID: {user_id}) - {facial_data.sample_count} samples")
                        verified += 1
                    else:
                        print(f"⚠ {name} (ID: {user_id}) - Sample count mismatch "
                              f"(expected: {expected_samples}, found: {facial_data.sample_count})")
                        verified += 1
                else:
                    print(f"❌ {name} (ID: {user_id}) - NOT FOUND in database")
                    missing += 1
            
            print(f"\n{'='*60}")
            print(f"Verification Results:")
            print(f"  ✓ Verified: {verified}")
            print(f"  ❌ Missing: {missing}")
            print(f"{'='*60}")
    
    def _print_summary(self):
        """Print import summary"""
        print(f"\n{'='*60}")
        print(f"IMPORT SUMMARY")
        print(f"{'='*60}")
        print(f"  Total students in file: {self.stats['total']}")
        print(f"  ✓ Newly imported:       {self.stats['imported']}")
        print(f"  ✓ Updated existing:     {self.stats['updated']}")
        print(f"  ⚠ User not found:       {self.stats['user_not_found']}")
        print(f"  ❌ Failed:               {self.stats['failed']}")
        print(f"{'='*60}\n")


def main():
    """Main function with CLI"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Bulk import facial data into database')
    parser.add_argument('file', nargs='?', default='facial_data_bulk.json',
                       help='JSON file containing facial data (default: facial_data_bulk.json)')
    parser.add_argument('--skip-existing', action='store_true',
                       help='Skip users who already have facial data')
    parser.add_argument('--dry-run', action='store_true',
                       help='Test mode - do not commit changes to database')
    parser.add_argument('--verify', action='store_true',
                       help='Verify imported data against file')
    
    args = parser.parse_args()
    
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
