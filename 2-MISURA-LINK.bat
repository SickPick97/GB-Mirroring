@echo off
cd /d "%~dp0"
rem Solo se GBMIRRORING LINK TEST gira gia sul GBA acceso.
"%~dp0runtime\python\python.exe" "%~dp0tools\run_link_test.py" --skip-boot
pause
