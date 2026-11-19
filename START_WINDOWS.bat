@echo off
setlocal
cd /d "%~dp0"
title LiveClip Zero Smart
where ffmpeg >nul 2>nul || goto missing_ffmpeg
where ffprobe >nul 2>nul || goto missing_ffmpeg
if not exist ".venv\Scripts\python.exe" (
  where py >nul 2>nul
  if not errorlevel 1 (py -3 -m venv .venv) else (python -m venv .venv)
  if errorlevel 1 goto missing_python
)
".venv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 goto install_failed
".venv\Scripts\python.exe" -m liveclip.gui
if errorlevel 1 pause
exit /b 0
:missing_ffmpeg
echo ERROR: Install FFmpeg and ffprobe and add them to PATH. Visit https://ffmpeg.org/download.html
pause
exit /b 1
:missing_python
echo ERROR: Python 3.10 or later is required. Visit https://python.org/downloads/
pause
exit /b 1
:install_failed
echo ERROR: Dependency installation failed. Check Python and internet connection.
pause
exit /b 1
