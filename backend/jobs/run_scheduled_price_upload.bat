@echo off
REM Scheduled Price Upload Job Runner
REM This batch file runs the scheduled price upload job
REM Schedule this to run daily using Windows Task Scheduler

echo ========================================
echo Scheduled Price Upload Job
echo ========================================
echo.

REM Get the directory where this batch file is located
set SCRIPT_DIR=%~dp0

REM Change to the backend directory (parent of jobs)
cd /d "%SCRIPT_DIR%.."
echo Working directory: %CD%

REM Activate virtual environment if exists
if exist "..\venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call ..\venv\Scripts\activate.bat
) else (
    echo ⚠️ Virtual environment not found at ..\venv\Scripts\activate.bat
)

REM Run the job from backend directory
echo Running scheduled price upload job...
python jobs\scheduled_price_upload_standalone.py

REM Check exit code
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Job completed successfully!
    echo ========================================
) else (
    echo.
    echo ========================================
    echo Job failed with error code: %ERRORLEVEL%
    echo ========================================
)

REM Keep window open if run manually
if "%1"=="" pause
