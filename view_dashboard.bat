@echo off
cd /d "%~dp0"
echo ===================================================
echo     BAM NPA Web Dashboard Launcher (Python)
echo ===================================================
echo.
echo Starting BAM NPA Streamlit Dashboard...
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [-] Error: Python virtual environment not found!
    echo Please make sure you are in the correct folder.
    pause
    exit /b 1
)

:: Run Streamlit via virtualenv python
".venv\Scripts\python.exe" -m streamlit run dashboard.py

echo.
echo ===================================================
echo Dashboard server has stopped.
echo ===================================================
pause

