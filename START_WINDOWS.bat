@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title LiveClip Zero Studio - Launcher
echo.
echo ========================================
echo          LIVECLIP ZERO STUDIO
echo ========================================
echo.
echo [1/4] Checking required video tools...
where ffmpeg >nul 2>nul
if errorlevel 1 goto missing_video_tools
where ffprobe >nul 2>nul
if errorlevel 1 goto missing_video_tools

echo [2/4] Preparing private Python environment...
if not exist ".venv\Scripts\python.exe" (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 -m venv ".venv"
    ) else (
        python -m venv ".venv"
    )
    if errorlevel 1 goto missing_python
)
".venv\Scripts\python.exe" -c "import sys; assert sys.version_info >= (3,10), 'Python 3.10+ required'"
if errorlevel 1 goto missing_python

echo [3/4] Checking free local media-analysis packages...
".venv\Scripts\python.exe" -c "import liveclip,numpy,cv2,streamlink; assert liveclip.__version__=='2.4.0'" >nul 2>nul
if errorlevel 1 (
    echo Installing missing packages; first run may need internet.
    ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -e ".[neon]"
    if errorlevel 1 goto install_failed
)

echo [4/4] Opening LiveClip Zero Studio...
".venv\Scripts\python.exe" -m liveclip.gui
if errorlevel 1 goto launch_failed
exit /b 0

:missing_video_tools
echo.
echo ERROR: FFmpeg and ffprobe are both required on Windows PATH.
echo See docs\QUICK_START.md for official installation and verification steps.
goto end_error

:missing_python
echo.
echo ERROR: Python 3.10+ is required. Check Python installation and PATH.
echo See https://www.python.org/downloads/windows/
goto end_error

:install_failed
echo.
echo ERROR: Python package installation failed.
echo Check your internet connection and Python version.
echo Run CHECK_SETUP_WINDOWS.bat for diagnostics.
goto end_error

:launch_failed
echo.
echo ERROR: Desktop window failed to launch. See the error text above.
echo Run CHECK_SETUP_WINDOWS.bat, then check docs\TROUBLESHOOTING.md.
goto end_error

:end_error
pause
exit /b 1
