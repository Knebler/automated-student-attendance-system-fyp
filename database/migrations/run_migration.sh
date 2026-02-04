#!/bin/bash

# Migration script for adding homepage feature cards table
# Run this from the database directory

echo "================================================"
echo "  Homepage Feature Cards Migration"
echo "================================================"
echo ""

# Change to the database directory (parent of migrations)
cd "$(dirname "$0")/.."

echo "Current directory: $(pwd)"
echo ""

show_menu() {
    echo "Choose an action:"
    echo "  1. Apply migration (create table)"
    echo "  2. Rollback migration (drop table)"
    echo "  3. Exit"
    echo ""
}

apply_migration() {
    echo ""
    echo "Applying migration..."
    python migrations/add_homepage_feature_cards.py up
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "Migration applied successfully!"
    else
        echo ""
        echo "Migration failed!"
    fi
    echo ""
    read -p "Press Enter to continue..."
}

rollback_migration() {
    echo ""
    echo "WARNING: This will delete the homepage_feature_cards table and all data!"
    read -p "Are you sure? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        echo "Rollback cancelled."
        echo ""
        read -p "Press Enter to continue..."
        return
    fi
    
    echo ""
    echo "Rolling back migration..."
    python migrations/add_homepage_feature_cards.py down
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "Rollback completed successfully!"
    else
        echo ""
        echo "Rollback failed!"
    fi
    echo ""
    read -p "Press Enter to continue..."
}

while true; do
    show_menu
    read -p "Enter your choice (1-3): " choice
    
    case $choice in
        1)
            apply_migration
            ;;
        2)
            rollback_migration
            ;;
        3)
            echo ""
            echo "Done."
            exit 0
            ;;
        *)
            echo "Invalid choice. Please try again."
            echo ""
            ;;
    esac
done
