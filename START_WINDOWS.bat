@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title LiveClip Zero Studio
echo.
echo LIVECLIP / zero studio  @S2zxx0zxx
echo.

rem Call FFmpeg directly instead of relying on the Windows 'where' command.
ffmpeg -version >nul 2>nul
if errorlevel 1 goto missing_video_tools
ffprobe -version >nul 2>nul
if errorlevel 1 goto missing_video_tools
call :note 01 "Video tools" ok

if not exist ".venv\Scripts\python.exe" (
    py -3 --version >nul 2>nul
    if not errorlevel 1 (
        py -3 -m venv ".venv"
    ) else (
        python -m venv ".venv"
    )
    if errorlevel 1 goto missing_python
)
".venv\Scripts\python.exe" -c "import sys; assert sys.version_info >= (3,10), 'Python 3.10+ required'"
if errorlevel 1 goto missing_python
call :note 02 "Python environment" ok

".venv\Scripts\python.exe" -c "import liveclip,numpy,cv2,streamlink,rich; assert liveclip.__version__=='2.4.0'" >nul 2>nul
if errorlevel 1 (
    call :note 03 "Local dependencies" working
    ".venv\Scripts\python.exe" -m pip install --quiet --progress-bar off --disable-pip-version-check -e ".[neon]"
    if errorlevel 1 goto install_failed
)
call :note 03 "Local dependencies" ok
".venv\Scripts\python.exe" "src\liveclip\terminal_ui.py" done
".venv\Scripts\python.exe" -m liveclip.gui
if errorlevel 1 goto launch_failed
exit /b 0

:note
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "src\liveclip\terminal_ui.py" step "%~1" "%~2" "%~3"
) else (
    echo %~1  + %~2  %~3
)
exit /b 0

:missing_video_tools
echo.
echo ERROR: FFmpeg and ffprobe must be executable from this terminal.
echo Check their bin directory in PATH, then see docs\QUICK_START.md.
goto end_error

:missing_python
echo.
echo ERROR: Python 3.10+ is required. Check installation and PATH.
echo See https://www.python.org/downloads/windows/
goto end_error

:install_failed
echo.
echo ERROR: Local Python package installation failed. Read pip errors above.
echo Run CHECK_SETUP_WINDOWS.bat and see docs\TROUBLESHOOTING.md.
goto end_error

:launch_failed
echo.
echo ERROR: Desktop window failed to launch. Read the error above.
echo Run CHECK_SETUP_WINDOWS.bat and see docs\TROUBLESHOOTING.md.
goto end_error

:end_error
pause
exit /b 1
