@echo off
REM Bulk Facial Data Manager - GUI Launcher
echo Starting Bulk Facial Data Manager...
echo.

REM Activate virtual environment and run GUI
call venv\Scripts\activate.bat
python bulk_facial_data_gui.py

pause
