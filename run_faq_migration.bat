@echo off
echo ========================================
echo FAQ Table Migration Script
echo ========================================
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Run migration
cd database
python migrations\add_faq_table.py up

echo.
echo ========================================
echo Migration Complete!
echo ========================================
pause
