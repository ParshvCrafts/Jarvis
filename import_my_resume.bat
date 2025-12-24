@echo off
echo ================================================================================
echo                    JARVIS Resume and Project Importer
echo ================================================================================
echo.

cd /d "%~dp0"

echo Checking Python...
python --version
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python first.
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo                         IMPORTING YOUR RESUME DATA
echo ================================================================================
echo.

python run.py --import-resume data/my_resume

echo.
echo ================================================================================
echo                              IMPORT COMPLETE
echo ================================================================================
echo.

echo Checking status...
echo.
python run.py --internship-status

echo.
echo ================================================================================
echo.
echo NEXT STEPS:
echo   1. Run JARVIS: python run.py
echo   2. Say: "Find internships for me"
echo   3. Say: "Customize resume for Google"
echo.
echo ================================================================================
pause
