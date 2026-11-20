@echo off
setlocal EnableExtensions
cd /d "%~dp0"
rem Alternative diagnostic launch with visible errors. Normal users should
rem double-click START_WEB_STUDIO.vbs for a console-free experience.
set "PATH=C:\Windows\System32;C:\Windows;C:\ffmpeg-9.1-essentials_build\bin;%PATH%"
if not exist ".venv\Scripts\python.exe" (
 echo Install the app first using START_WINDOWS.bat
 pause
 exit /b 1
)
".venv\Scripts\python.exe" -m liveclip.web_studio
if errorlevel 1 pause
