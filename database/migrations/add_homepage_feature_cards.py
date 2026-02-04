"""
Migration Script: Add Homepage Feature Cards Table
Date: 2026-02-04
Description: Adds the homepage_feature_cards table to store dynamic feature cards for the homepage
"""

from sqlalchemy import text
from datetime import datetime
import sys
import os

# Add parent directory to path to import base and models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from base import engine, get_session
from models import HomepageFeatureCard, Base

def migrate_up():
    """Create the homepage_feature_cards table"""
    print("Starting migration: add_homepage_feature_cards")
    
    try:
        # Create the table
        with engine.begin() as conn:
            HomepageFeatureCard.__table__.create(bind=conn, checkfirst=True)
        
        print("✓ Created homepage_feature_cards table")
        
        # Seed initial data
        seed_initial_data()
        
        print("✓ Migration completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Migration failed: {str(e)}")
        return False

def seed_initial_data():
    """Seed the table with default feature cards"""
    with get_session() as session:
        # Check if data already exists
        existing_count = session.query(HomepageFeatureCard).count()
        if existing_count > 0:
            print(f"  Homepage feature cards already exist ({existing_count} records), skipping seed")
            return
        
        feature_cards_data = [
            {
                'title': 'Our Team',
                'description': 'Learn more about AttendAI and the dedicated team behind our innovative solutions',
                'icon': '👥',
                'bg_image': 'https://images.unsplash.com/photo-1522071820081-009f0129c71c?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=800&q=80',
                'link_url': '/about',
                'link_text': 'Learn More',
                'display_order': 1,
                'is_active': True
            },
            {
                'title': 'Testimonials',
                'description': 'Read glowing reviews from educational institutions and businesses using AttendAI',
                'icon': '⭐',
                'bg_image': 'https://images.unsplash.com/photo-1552664730-d307ca884978?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w-800&q=80',
                'link_url': '/testimonials',
                'link_text': 'Read Stories',
                'display_order': 2,
                'is_active': True
            },
            {
                'title': 'Affordable Plans',
                'description': 'Choose from our range of subscription plans designed to suit institutions of all sizes',
                'icon': '💳',
                'bg_image': 'https://images.unsplash.com/photo-1554224155-6726b3ff858f?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=800&q=80',
                'link_url': '/subscriptions',
                'link_text': 'View Plans',
                'display_order': 3,
                'is_active': True
            },
            {
                'title': 'AI Powered',
                'description': 'Leverage artificial intelligence for facial recognition and predictive analytics',
                'icon': '🤖',
                'bg_image': 'https://images.unsplash.com/photo-1677442136019-21780ecad995?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=800&q=80',
                'link_url': '/features',
                'link_text': 'Explore Features',
                'display_order': 4,
                'is_active': True
            },
            {
                'title': 'Real-time Reports',
                'description': 'Generate comprehensive attendance reports and analytics instantly',
                'icon': '📊',
                'bg_image': 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=800&q=80',
                'link_url': '/features',
                'link_text': 'See Analytics',
                'display_order': 5,
                'is_active': True
            },
            {
                'title': 'Easy Tracking',
                'description': 'Mark attendance with a single click using QR codes or facial recognition',
                'icon': '📱',
                'bg_image': 'https://images.unsplash.com/photo-1611224923853-80b023f02d71?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=800&q=80',
                'link_url': '/features',
                'link_text': 'Learn How',
                'display_order': 6,
                'is_active': True
            }
        ]
        
        for card_data in feature_cards_data:
            feature_card = HomepageFeatureCard(**card_data)
            session.add(feature_card)
        
        session.commit()
        print(f"  ✓ Seeded {len(feature_cards_data)} homepage feature cards")

def migrate_down():
    """Drop the homepage_feature_cards table (rollback)"""
    print("Rolling back migration: add_homepage_feature_cards")
    
    try:
        with engine.begin() as conn:
            HomepageFeatureCard.__table__.drop(bind=conn, checkfirst=True)
        
        print("✓ Dropped homepage_feature_cards table")
        print("✓ Rollback completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Rollback failed: {str(e)}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate homepage feature cards table')
    parser.add_argument('action', choices=['up', 'down'], help='Migration action: up (apply) or down (rollback)')
    
    args = parser.parse_args()
    
    if args.action == 'up':
        success = migrate_up()
    else:
        success = migrate_down()
    
    sys.exit(0 if success else 1)
