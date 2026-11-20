@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title LiveClip Zero Studio - Setup Check
echo.
echo ===== LiveClip Zero Studio Diagnostic =====
echo Checking Python...
where py >nul 2>nul
if not errorlevel 1 py -3 --version
where python >nul 2>nul
if not errorlevel 1 python --version
echo.
echo Checking FFmpeg and ffprobe...
where ffmpeg
where ffprobe
echo.
echo Checking local environment...
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" --version
  ".venv\Scripts\python.exe" -m liveclip doctor
  ".venv\Scripts\python.exe" -c "import numpy,cv2;print('Local VOD analysis: installed')"
) else (
  echo Not initialized yet. Double-click START_WINDOWS.bat first.
)
echo.
echo End of setup report. Share only non-sensitive errors if you need help.
pause
