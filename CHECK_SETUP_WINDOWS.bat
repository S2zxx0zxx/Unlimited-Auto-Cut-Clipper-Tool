@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title LiveClip Zero Studio - Setup Diagnostics
echo.
echo LIVECLIP / diagnostics  @S2zxx0zxx
echo.
echo Python:
py -3 --version 2>nul
if errorlevel 1 python --version
echo.
echo Video tools:
ffmpeg -version >nul 2>nul
if errorlevel 1 (
    echo ffmpeg: NOT AVAILABLE
) else (
    echo ffmpeg: available
)
ffprobe -version >nul 2>nul
if errorlevel 1 (
    echo ffprobe: NOT AVAILABLE
) else (
    echo ffprobe: available
)
echo.
echo Local environment:
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" --version
    ".venv\Scripts\python.exe" -m liveclip doctor
    ".venv\Scripts\python.exe" -c "import numpy,cv2;print('Local VOD analysis: installed')"
    ".venv\Scripts\python.exe" -c "import rich;print('Terminal styling: installed')"
) else (
    echo Not initialized. Run START_WINDOWS.bat first.
)
echo.
echo Do not share secrets, private stream URLs or personal file paths in reports.
pause
