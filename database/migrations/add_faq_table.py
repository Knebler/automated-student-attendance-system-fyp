"""
Migration Script: Add FAQ Table
Date: 2026-02-05
Description: Adds the faqs table to store frequently asked questions for the public FAQ page
"""

from sqlalchemy import text
from datetime import datetime
import sys
import os

# Add parent directory to path to import base and models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from base import engine, get_session
from models import FAQ, Base

def migrate_up():
    """Create the faqs table"""
    print("Starting migration: add_faq_table")
    
    try:
        # Create the table
        with engine.begin() as conn:
            FAQ.__table__.create(bind=conn, checkfirst=True)
        
        print("✓ Created faqs table")
        
        # Seed initial data
        seed_initial_data()
        
        print("✓ Migration completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Migration failed: {str(e)}")
        return False

def seed_initial_data():
    """Seed the table with default FAQ data"""
    with get_session() as session:
        # Check if data already exists
        existing_count = session.query(FAQ).count()
        if existing_count > 0:
            print(f"  FAQs already exist ({existing_count} records), skipping seed")
            return
        
        faqs_data = [
            # General FAQs
            {
                'category': 'general',
                'question': 'What is AttendAI and how does it work?',
                'answer': """AttendAI is an AI-powered attendance management system that revolutionizes how educational institutions and businesses track attendance. Our system uses multiple verification methods including facial recognition, QR code scanning, and mobile check-ins to accurately record attendance in real-time.

The platform processes attendance data through our secure cloud infrastructure, providing administrators with real-time dashboards, predictive analytics, and comprehensive reporting tools. Everything is designed to be user-friendly while maintaining enterprise-grade security and reliability.""",
                'display_order': 1,
                'is_active': True
            },
            {
                'category': 'general',
                'question': 'Is there a free trial available?',
                'answer': """Yes! We offer a 14-day free trial for all our plans. During the trial period, you'll have access to all features of the Professional plan, including AI face recognition, real-time analytics, and up to 500 student capacity. No credit card is required to start your trial.

Our support team will help you set up the system and provide training materials to ensure you get the most out of your trial period.""",
                'display_order': 2,
                'is_active': True
            },
            {
                'category': 'general',
                'question': 'How accurate is the facial recognition technology?',
                'answer': """Our AI-powered facial recognition system achieves 99.8% accuracy in optimal conditions. The system uses advanced machine learning algorithms that continuously improve with use. Key features include:

• Works in various lighting conditions
• Adapts to different angles and distances
• Handles accessories like glasses and masks
• Protects against spoofing attempts
• Processes recognition in under 2 seconds

We also provide multiple fallback methods (QR codes, PINs) to ensure reliability in all situations.""",
                'display_order': 3,
                'is_active': True
            },
            
            # Features FAQs
            {
                'category': 'features',
                'question': 'Does AttendAI integrate with existing school management systems?',
                'answer': """Yes, AttendAI offers seamless integration with popular school management systems including:

• Google Classroom and Microsoft Teams
• Popular LMS platforms (Canvas, Moodle, Blackboard)
• Student Information Systems (SIS)
• Human Resource Management Systems (HRMS)

We provide comprehensive API documentation for custom integrations, and our technical team can assist with implementation to ensure smooth data synchronization.""",
                'display_order': 1,
                'is_active': True
            },
            {
                'category': 'features',
                'question': 'Can parents or guardians receive attendance notifications?',
                'answer': """Absolutely. AttendAI includes a comprehensive notification system that can alert parents and guardians via:

• Email notifications for daily, weekly, or monthly attendance reports
• SMS alerts for immediate attendance concerns
• Mobile app notifications through our dedicated parent portal
• Customizable alert thresholds (e.g., notify when attendance drops below 90%)

Parents can also access a secure portal to view their child's attendance history, patterns, and receive automated alerts about upcoming parent-teacher meetings.""",
                'display_order': 2,
                'is_active': True
            },
            
            # Pricing FAQs
            {
                'category': 'pricing',
                'question': 'What payment methods do you accept?',
                'answer': """We accept all major payment methods for your convenience:

• Credit and debit cards (Visa, MasterCard, American Express)
• PayPal for quick online payments
• Bank transfers for enterprise customers
• Annual billing with 15% discount
• Purchase orders for educational institutions

All payments are processed through secure, PCI-compliant payment gateways to ensure your financial information is protected.""",
                'display_order': 1,
                'is_active': True
            },
            {
                'category': 'pricing',
                'question': 'Can I upgrade or downgrade my plan later?',
                'answer': """Yes, you can change your plan at any time. When upgrading, the new features become available immediately, and you'll be charged the prorated difference for the remainder of your billing cycle. When downgrading, the changes take effect at the start of your next billing cycle.

Our system automatically handles data migration between plans, so you don't need to worry about losing any attendance records or settings when changing plans.""",
                'display_order': 2,
                'is_active': True
            },
            
            # Technical FAQs
            {
                'category': 'technical',
                'question': 'What are the system requirements for AttendAI?',
                'answer': """AttendAI is a cloud-based solution with minimal system requirements:

• Web Browser: Chrome, Firefox, Safari, or Edge (latest versions)
• Internet Connection: Minimum 5 Mbps for smooth operation
• For facial recognition: Any device with a camera (720p or higher recommended)
• Mobile App: iOS 12+ or Android 8+

No special hardware or installation is required. The system works on desktops, laptops, tablets, and smartphones.""",
                'display_order': 1,
                'is_active': True
            },
            
            # Implementation FAQs
            {
                'category': 'implementation',
                'question': 'How long does it take to set up AttendAI?',
                'answer': """The setup process is quick and straightforward:

• Initial Setup: 1-2 hours to configure your institution details
• User Import: Bulk import students and staff via CSV (5-10 minutes)
• Training: 2-hour training session for administrators
• Facial Data Collection: Students can register in 30 seconds each
• Go Live: Most institutions are fully operational within 1-3 days

Our dedicated onboarding team guides you through every step and provides ongoing support.""",
                'display_order': 1,
                'is_active': True
            },
        ]
        
        faqs = [FAQ(**faq_data) for faq_data in faqs_data]
        session.add_all(faqs)
        session.commit()
        
        print(f"  ✓ Seeded {len(faqs)} FAQs")

def migrate_down():
    """Drop the faqs table (rollback)"""
    print("Rolling back migration: add_faq_table")
    
    try:
        with engine.begin() as conn:
            FAQ.__table__.drop(bind=conn, checkfirst=True)
        
        print("✓ Dropped faqs table")
        print("✓ Rollback completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Rollback failed: {str(e)}")
        return False

if __name__ == "__main__":
    import sys
    
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python add_faq_table.py [up|down]")
        print("  up   - Run migration (create table and seed data)")
        print("  down - Rollback migration (drop table)")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "up":
        success = migrate_up()
    elif command == "down":
        success = migrate_down()
    else:
        print(f"Unknown command: {command}")
        print("Use 'up' to migrate or 'down' to rollback")
        sys.exit(1)
    
    sys.exit(0 if success else 1)
