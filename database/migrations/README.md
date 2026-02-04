# Database Migrations

This directory contains database migration scripts for the AttendAI application.

## Available Migrations

### add_homepage_feature_cards.py
**Date:** 2026-02-04  
**Description:** Adds the `homepage_feature_cards` table to store dynamic feature cards displayed on the homepage.

**Table Structure:**
- `feature_card_id` (INT) - Primary key
- `title` (VARCHAR 200) - Card title
- `description` (TEXT) - Card description
- `icon` (VARCHAR 50) - Emoji or icon
- `bg_image` (VARCHAR 500) - Background image URL
- `link_url` (VARCHAR 500) - Optional link URL
- `link_text` (VARCHAR 100) - Optional link button text
- `is_active` (BOOLEAN) - Whether the card is visible
- `display_order` (INT) - Display order on homepage
- `created_at` (DATETIME) - Creation timestamp

### add_features_page_content.py
**Date:** 2026-02-04  
**Description:** Adds the `features_page_content` table to store editable header and hero content for the features page.

**Table Structure:**
- `content_id` (INT) - Primary key
- `section` (VARCHAR 50) - Section type: 'header' or 'hero'
- `title` (VARCHAR 200) - Content title
- `content` (TEXT) - Main content text
- `is_active` (BOOLEAN) - Whether the content is visible
- `created_at` (DATETIME) - Creation timestamp
- `updated_at` (DATETIME) - Last update timestamp

## How to Run Migrations

### Windows (PowerShell)

```powershell
# Navigate to the database directory
cd c:\Users\User\Documents\automated-student-attendance-system-fyp\database

# Apply homepage feature cards migration
python migrations\add_homepage_feature_cards.py up

# Apply features page content migration
python migrations\add_features_page_content.py up

# Rollback migrations if needed
python migrations\add_homepage_feature_cards.py down
python migrations\add_features_page_content.py down
```

### Linux/Mac

```bash
# Navigate to the database directory
cd ~/Documents/automated-student-attendance-system-fyp/database

# Apply homepage feature cards migration
python migrations/add_homepage_feature_cards.py up

# Apply features page content migration
python migrations/add_features_page_content.py up

# Rollback migrations if needed
python migrations/add_homepage_feature_cards.py down
python migrations/add_features_page_content.py down
```

## Migration Output

**Successful migration:**
```
Starting migration: add_homepage_feature_cards
✓ Created homepage_feature_cards table
  ✓ Seeded 6 homepage feature cards
✓ Migration completed successfully
```

**If table already exists:**
```
Starting migration: add_homepage_feature_cards
✓ Created homepage_feature_cards table
  Homepage feature cards already exist (6 records), skipping seed
✓ Migration completed successfully
```

## Verify Migration

After running the migration, you can verify the table was created:

```sql
-- Check table exists
SHOW TABLES LIKE 'homepage_feature_cards';

-- View seeded data
SELECT feature_card_id, title, is_active, display_order FROM homepage_feature_cards;

-- Count records
SELECT COUNT(*) FROM homepage_feature_cards;
```

## Notes

- The migration script is idempotent - it's safe to run multiple times
- The script uses `checkfirst=True` to avoid errors if the table already exists
- Initial seed data includes 6 feature cards matching the original hardcoded cards
- All seeded cards are active by default
