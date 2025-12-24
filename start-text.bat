@echo off
:: JARVIS Quick Start Script (Windows) - Text Mode
:: Starts JARVIS in text-only mode (no voice)

echo.
echo ========================================
echo   JARVIS - Text Mode
echo ========================================
echo.

:: Activate virtual environment if exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: Start JARVIS in text mode
python run.py --text %*

:: Keep window open on error
if errorlevel 1 pause
