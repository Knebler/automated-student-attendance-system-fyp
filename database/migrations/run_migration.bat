@echo off
REM Migration script for adding homepage feature cards table
REM Run this from the database directory

echo ================================================
echo  Homepage Feature Cards Migration
echo ================================================
echo.

cd /d "%~dp0.."

echo Current directory: %CD%
echo.

:menu
echo Choose an action:
echo   1. Apply migration (create table)
echo   2. Rollback migration (drop table)
echo   3. Exit
echo.

set /p choice="Enter your choice (1-3): "

if "%choice%"=="1" goto apply
if "%choice%"=="2" goto rollback
if "%choice%"=="3" goto end
echo Invalid choice. Please try again.
echo.
goto menu

:apply
echo.
echo Applying migration...
python migrations\add_homepage_feature_cards.py up
echo.
if %errorlevel% equ 0 (
    echo Migration applied successfully!
) else (
    echo Migration failed!
)
pause
goto end

:rollback
echo.
echo WARNING: This will delete the homepage_feature_cards table and all data!
set /p confirm="Are you sure? (yes/no): "
if /i not "%confirm%"=="yes" (
    echo Rollback cancelled.
    pause
    goto menu
)
echo.
echo Rolling back migration...
python migrations\add_homepage_feature_cards.py down
echo.
if %errorlevel% equ 0 (
    echo Rollback completed successfully!
) else (
    echo Rollback failed!
)
pause
goto end

:end
echo.
echo Done.
