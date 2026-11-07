@echo off
cd /d "%~dp0"
python tools\run_sim.py %*
exit /b %errorlevel%
