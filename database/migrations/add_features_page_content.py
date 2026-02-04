"""
Migration Script: Add Features Page Content Table
Date: 2026-02-04
Description: Adds the features_page_content table to store editable header and hero content for the features page
"""

from sqlalchemy import text
from datetime import datetime
import sys
import os

# Add parent directory to path to import base and models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from base import engine, get_session
from models import FeaturesPageContent, Base

def migrate_up():
    """Create the features_page_content table"""
    print("Starting migration: add_features_page_content")
    
    try:
        # Create the table
        with engine.begin() as conn:
            FeaturesPageContent.__table__.create(bind=conn, checkfirst=True)
        
        print("✓ Created features_page_content table")
        
        # Seed initial data
        seed_initial_data()
        
        print("✓ Migration completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Migration failed: {str(e)}")
        return False

def seed_initial_data():
    """Seed the table with default content"""
    with get_session() as session:
        # Check if data already exists
        existing_count = session.query(FeaturesPageContent).count()
        if existing_count > 0:
            print(f"  Features page content already exists ({existing_count} records), skipping seed")
            return
        
        content_data = [
            {
                'section': 'header',
                'title': 'Powerful Features for Modern Attendance Management',
                'content': 'Discover how AttendAI revolutionizes attendance tracking with AI-powered features designed for efficiency, accuracy, and ease of use.',
                'is_active': True
            },
            {
                'section': 'hero',
                'title': 'Why Choose AttendAI?',
                'content': 'Traditional attendance methods are time-consuming, error-prone, and lack insights. AttendAI transforms this process with intelligent automation, real-time analytics, and seamless integration - saving you hours of administrative work while providing valuable data-driven insights.',
                'is_active': True
            }
        ]
        
        for content in content_data:
            page_content = FeaturesPageContent(**content)
            session.add(page_content)
        
        session.commit()
        print(f"  ✓ Seeded {len(content_data)} features page content items")

def migrate_down():
    """Drop the features_page_content table (rollback)"""
    print("Rolling back migration: add_features_page_content")
    
    try:
        with engine.begin() as conn:
            FeaturesPageContent.__table__.drop(bind=conn, checkfirst=True)
        
        print("✓ Dropped features_page_content table")
        print("✓ Rollback completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Rollback failed: {str(e)}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate features page content table')
    parser.add_argument('action', choices=['up', 'down'], help='Migration action: up (apply) or down (rollback)')
    
    args = parser.parse_args()
    
    if args.action == 'up':
        success = migrate_up()
    else:
        success = migrate_down()
    
    sys.exit(0 if success else 1)
