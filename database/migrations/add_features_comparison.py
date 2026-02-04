"""
Migration: Add Features Comparison Table
Created: 2024
Description: Creates the Features_Comparison table for managing comparison items between traditional methods and AttendAI
"""

from sqlalchemy import text
import sys
import os

# Add parent directory to path to import base and models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from base import engine, get_session
from models import FeaturesComparison

def migrate_up():
    """Create Features_Comparison table and seed initial data"""
    print("Creating Features_Comparison table...")
    
    with engine.begin() as conn:
        # Create the table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS Features_Comparison (
                comparison_id INT AUTO_INCREMENT PRIMARY KEY,
                feature_text VARCHAR(255) NOT NULL,
                traditional_has BOOLEAN NOT NULL DEFAULT FALSE,
                attendai_has BOOLEAN NOT NULL DEFAULT TRUE,
                display_order INT NOT NULL DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_active_order (is_active, display_order)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """))
        
        print("✓ Features_Comparison table created")
    
    # Seed initial data
    print("Seeding comparison items...")
    with get_session() as session:
        comparison_data = [
            {
                'feature_text': 'Manual roll calls',
                'traditional_has': True,
                'attendai_has': False,
                'display_order': 1,
                'is_active': True
            },
            {
                'feature_text': 'Automated attendance marking',
                'traditional_has': False,
                'attendai_has': True,
                'display_order': 2,
                'is_active': True
            },
            {
                'feature_text': 'Paper-based tracking',
                'traditional_has': True,
                'attendai_has': False,
                'display_order': 3,
                'is_active': True
            },
            {
                'feature_text': 'Digital tracking system',
                'traditional_has': False,
                'attendai_has': True,
                'display_order': 4,
                'is_active': True
            },
            {
                'feature_text': 'Time-consuming data entry',
                'traditional_has': True,
                'attendai_has': False,
                'display_order': 5,
                'is_active': True
            },
            {
                'feature_text': 'Instant data processing',
                'traditional_has': False,
                'attendai_has': True,
                'display_order': 6,
                'is_active': True
            },
            {
                'feature_text': 'Human errors common',
                'traditional_has': True,
                'attendai_has': False,
                'display_order': 7,
                'is_active': True
            },
            {
                'feature_text': '99.8% accuracy rate',
                'traditional_has': False,
                'attendai_has': True,
                'display_order': 8,
                'is_active': True
            },
            {
                'feature_text': 'No real-time insights',
                'traditional_has': True,
                'attendai_has': False,
                'display_order': 9,
                'is_active': True
            },
            {
                'feature_text': 'Real-time dashboards',
                'traditional_has': False,
                'attendai_has': True,
                'display_order': 10,
                'is_active': True
            },
            {
                'feature_text': 'Difficult to analyze trends',
                'traditional_has': True,
                'attendai_has': False,
                'display_order': 11,
                'is_active': True
            },
            {
                'feature_text': 'Advanced analytics',
                'traditional_has': False,
                'attendai_has': True,
                'display_order': 12,
                'is_active': True
            },
            {
                'feature_text': 'No automated reporting',
                'traditional_has': True,
                'attendai_has': False,
                'display_order': 13,
                'is_active': True
            },
            {
                'feature_text': 'Automated report generation',
                'traditional_has': False,
                'attendai_has': True,
                'display_order': 14,
                'is_active': True
            },
            {
                'feature_text': 'Limited accessibility',
                'traditional_has': True,
                'attendai_has': False,
                'display_order': 15,
                'is_active': True
            },
            {
                'feature_text': 'Access anywhere, anytime',
                'traditional_has': False,
                'attendai_has': True,
                'display_order': 16,
                'is_active': True
            }
        ]
        
        for comparison in comparison_data:
            comparison_item = FeaturesComparison(**comparison)
            session.add(comparison_item)
        
        session.commit()
        print(f"✓ Seeded {len(comparison_data)} comparison items")
    
    print("Migration completed successfully!")

def migrate_down():
    """Drop Features_Comparison table"""
    print("Dropping Features_Comparison table...")
    
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS Features_Comparison;"))
        print("✓ Features_Comparison table dropped")
    
    print("Rollback completed successfully!")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "down":
        migrate_down()
    else:
        migrate_up()
