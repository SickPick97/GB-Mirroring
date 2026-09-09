@echo off
cd /d "%~dp0"
"%~dp0runtime\python\python.exe" "%~dp0tools\check_portable.py"
pause
