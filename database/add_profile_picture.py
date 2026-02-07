"""
Add profile_picture column to users table
"""
from sqlalchemy import text
from base import engine

def add_profile_picture_column():
    """Add profile_picture column to users table if it doesn't exist"""
    
    with engine.connect() as conn:
        print("Starting migration to add profile_picture column...")
        
        try:
            # Check if column exists
            print("1. Checking if profile_picture column already exists...")
            result = conn.execute(text("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'users'
                AND COLUMN_NAME = 'profile_picture'
            """))
            
            exists = result.fetchone()[0] > 0
            
            if exists:
                print("✓ Column 'profile_picture' already exists in 'users' table")
                print("\n✅ Migration completed - no changes needed!")
                return
            
            # Add the column
            print("2. Adding 'profile_picture' column to 'users' table...")
            conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN profile_picture MEDIUMBLOB NULL
                AFTER password_hash
            """))
            conn.commit()
            print("✓ Successfully added 'profile_picture' column (MEDIUMBLOB, max 16MB)")
            
            print("\n✅ Migration completed successfully!")
            print("Profile picture column has been added to users table")
            
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            print("\nNote: If there are issues, check:")
            print("1. Database connection is working")
            print("2. Users table exists")
            print("3. You have ALTER TABLE permissions")
            raise

if __name__ == '__main__':
    add_profile_picture_column()
