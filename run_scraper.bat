@echo off
cd /d "%~dp0"
echo ===================================================
echo     BAM NPA Property Scraper Launcher
echo ===================================================
echo.
set /p pages="Enter number of pages to scrape (e.g. 5, 20, all) [default: 5]: "
if "%pages%"=="" set pages=5

echo.
echo Starting BAM scraper ^(pages: %pages%^)...
echo.

if not exist ".venv\Scripts\python.exe" goto no_venv

".venv\Scripts\python.exe" bam_scraper.py --pages %pages%
goto end

:no_venv
echo [-] Error: Virtual environment .venv not found!
echo Please make sure you are in the correct project folder.
goto end

:end
echo.
echo ===================================================
echo Scraper finished or stopped.
echo ===================================================
pause
