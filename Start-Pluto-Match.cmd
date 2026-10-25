@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-Pluto-Match.ps1" %*
if errorlevel 1 pause
