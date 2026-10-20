@echo off
cd /d "%~dp0"
python inventar.py %*
if errorlevel 1 pause
