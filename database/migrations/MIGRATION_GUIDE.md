# Homepage Feature Cards - Database Migration Guide

## Overview

This migration adds a new `homepage_feature_cards` table to the database, allowing platform managers to dynamically manage the feature cards displayed on the homepage through the admin interface.

## What's Changed

### Database Changes
- **New Table**: `homepage_feature_cards`
- **Seeded Data**: 6 default feature cards (matching the previous hardcoded cards)

### Code Changes
1. **models.py**: Added `HomepageFeatureCard` model
2. **manage_db.py**: Added `seed_feature_cards()` function
3. **main_boundary.py**: Updated to fetch and pass feature cards to homepage
4. **index.html**: Updated to use dynamic feature cards
5. **platform_boundary.py**: Added CRUD API endpoints for feature cards
6. **platform_manager_landing_page.html**: Added management UI for feature cards

## Migration Files

### 1. Migration Script
**Location**: `database/migrations/add_homepage_feature_cards.py`

This Python script handles:
- Creating the `homepage_feature_cards` table
- Seeding initial data (6 cards)
- Rolling back the migration (dropping the table)

### 2. Helper Scripts
- **Windows**: `database/migrations/run_migration.bat`
- **Linux/Mac**: `database/migrations/run_migration.sh`

Interactive scripts that guide you through applying or rolling back the migration.

### 3. Documentation
- **README**: `database/migrations/README.md`

## How to Apply the Migration

### Option 1: Using Python Directly

```bash
# Navigate to database directory
cd c:\Users\User\Documents\automated-student-attendance-system-fyp\database

# Apply migration
python migrations\add_homepage_feature_cards.py up

# If you need to rollback
python migrations\add_homepage_feature_cards.py down
```

### Option 2: Using the Helper Script (Windows)

```bash
# Navigate to migrations directory
cd c:\Users\User\Documents\automated-student-attendance-system-fyp\database\migrations

# Run the helper script
run_migration.bat

# Follow the on-screen menu
```

### Option 3: Using the Helper Script (Linux/Mac)

```bash
# Navigate to migrations directory
cd ~/Documents/automated-student-attendance-system-fyp/database/migrations

# Make script executable (first time only)
chmod +x run_migration.sh

# Run the helper script
./run_migration.sh

# Follow the on-screen menu
```

## Expected Output

### Successful Migration

```
Starting migration: add_homepage_feature_cards
✓ Created homepage_feature_cards table
  ✓ Seeded 6 homepage feature cards
✓ Migration completed successfully
```

## Seeded Data

The migration automatically seeds 6 feature cards:

1. **Our Team** - Links to `/about`
2. **Testimonials** - Links to `/testimonials`
3. **Affordable Plans** - Links to `/subscriptions`
4. **AI Powered** - Links to `/features`
5. **Real-time Reports** - Links to `/features`
6. **Easy Tracking** - Links to `/features`

All cards are:
- Active by default (`is_active = True`)
- Ordered by `display_order` (1-6)
- Include emoji icons
- Have background images from Unsplash
- Have clickable links with button text

## Verifying the Migration

After running the migration, verify it worked:

### 1. Check Database

```sql
-- Check table exists
SHOW TABLES LIKE 'homepage_feature_cards';

-- View all cards
SELECT * FROM homepage_feature_cards;

-- Count cards
SELECT COUNT(*) FROM homepage_feature_cards;
-- Expected: 6
```

### 2. Check Homepage

1. Start your Flask application
2. Visit the homepage (`/`)
3. Scroll down to see the feature cards section
4. All 6 cards should be displayed

### 3. Check Admin Panel

1. Login as platform manager
2. Navigate to `/platform/landing-page`
3. Click the "🎴 Feature Cards" tab
4. You should see all 6 cards listed

## Managing Feature Cards After Migration

Once migrated, platform managers can:

1. **View Cards**: Go to `/platform/landing-page` → "Feature Cards" tab
2. **Add Cards**: Click "+ Add Feature Card" button
3. **Edit Cards**: Click the ✏️ edit icon on any card
4. **Toggle Status**: Click the 👁️ icon to activate/deactivate
5. **Delete Cards**: Click the 🗑️ delete icon
6. **Reorder**: Change the "Display Order" field when editing

## Troubleshooting

### Migration Already Applied

If you see:
```
Homepage feature cards already exist (6 records), skipping seed
```

This is normal - the migration has already been applied and data exists.

### Table Already Exists Error

The migration uses `checkfirst=True`, so it won't fail if the table exists. However, if you encounter issues:

1. Check if table exists: `SHOW TABLES LIKE 'homepage_feature_cards';`
2. If it exists but is empty, the seed will run automatically
3. If you want to start fresh, run rollback first: `python migrations\add_homepage_feature_cards.py down`

### Import Errors

Make sure you're running the migration from the database directory:
```bash
cd c:\Users\User\Documents\automated-student-attendance-system-fyp\database
python migrations\add_homepage_feature_cards.py up
```

## Rollback

If you need to remove the feature cards table:

```bash
# This will delete the table and all data
python migrations\add_homepage_feature_cards.py down
```

**Warning**: This is destructive and will delete all feature card data!

## Integration with Existing System

### For New Installations

If you're running `manage_db.py` for the first time, the feature cards table and data will be created automatically as part of the `seed_database()` function.

### For Existing Installations

Use the migration script to add the table to your existing database without affecting other data.

## Next Steps

After migration:

1. Verify the homepage displays cards correctly
2. Test the platform manager interface
3. Customize the default cards as needed
4. Add additional cards for your specific use case

## Files Modified

- ✅ `database/models.py` - Added model
- ✅ `database/manage_db.py` - Added seed function
- ✅ `application/boundaries/main_boundary.py` - Added data fetching
- ✅ `application/boundaries/platform_boundary.py` - Added API endpoints
- ✅ `templates/index.html` - Made cards dynamic
- ✅ `templates/platmanager/platform_manager_landing_page.html` - Added management UI

## Support

If you encounter any issues with the migration, check:
1. Database connection is working
2. Python environment has required packages
3. You're in the correct directory
4. Database user has CREATE/DROP table permissions
