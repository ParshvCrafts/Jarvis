@echo off
echo.
echo ========================================
echo    JARVIS Essay Import Tool
echo ========================================
echo.
echo This will import all essays from: data\my_essays
echo.
echo Make sure your essays are in the correct format!
echo (See data\my_essays\README.txt for instructions)
echo.
pause

python run.py --import-essays data/my_essays

echo.
echo ========================================
echo Checking status...
echo ========================================
echo.

python run.py --scholarship-status

echo.
echo ========================================
echo Done! Press any key to close.
echo ========================================
pause
