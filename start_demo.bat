@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 run_all.py
) else (
  python run_all.py
)
echo.
echo Finished. Press any key to close.
pause >nul