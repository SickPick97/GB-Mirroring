@echo off
cd /d "%~dp0"
"%~dp0runtime\python\python.exe" "%~dp0tools\run_link_test.py" --extended
pause
