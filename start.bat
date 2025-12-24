@echo off
:: JARVIS Quick Start Script (Windows)
:: Starts JARVIS in full voice mode

echo.
echo ========================================
echo   JARVIS - Personal AI Assistant
echo ========================================
echo.

:: Activate virtual environment if exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: Start JARVIS
python run.py %*

:: Keep window open on error
if errorlevel 1 pause
