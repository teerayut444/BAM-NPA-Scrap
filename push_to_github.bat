@echo off
cd /d "%~dp0"
echo ===================================================
echo     BAM NPA GitHub Uploader Launcher (Baania Style)
echo ===================================================
echo.
echo Starting GitHub Push...
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [-] Error: Python virtual environment not found!
    echo Please make sure you are in the correct folder.
    pause
    exit /b 1
)

:: Run github_push.py via virtualenv python
".venv\Scripts\python.exe" github_push.py

echo.
echo ===================================================
echo Git push finished.
echo ===================================================
pause
