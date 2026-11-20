# LiveClip Zero Studio — Quick Start

**Version:** 2.4.0 · **Audience:** new users without Python/video-editing experience

The app is a local desktop program. It is **not** an Android APK, browser extension, online service or one-file Windows EXE. Installing source requires Python and FFmpeg/ffprobe. You do **not** need an API key or paid account for local clips.

## Windows 10/11 — guided setup

### A. Install prerequisites once

1. Install a supported Python **3.10+** release from https://www.python.org/downloads/windows/. Select the installer's **Add Python to PATH** option (when offered).
2. Install a Windows FFmpeg distribution (with **ffmpeg.exe** and **ffprobe.exe**) using an official link at https://ffmpeg.org/download.html. Add its \`bin\` directory to the Windows PATH.
3. Open **Command Prompt** and verify:

    py -3 --version
    ffmpeg -version
    ffprobe -version

A missing or unrecognized command means the prerequisites need repair. You may need to open a **new** terminal window after updating PATH.

### B. Open the desktop studio

1. Download ZIP: https://github.com/S2zxx0zxx/Unlimited-Auto-Cut-Clipper-Tool/archive/refs/heads/main.zip
2. Right-click ZIP → **Extract All**. Use a local writable folder such as \`C:\LiveClipStudio\`. Do not run scripts while files are still inside the ZIP archive.
3. Double-click \`START_WINDOWS.bat\`. The first run creates a \`.venv\` directory and downloads **free local media-analysis dependencies**. It may take longer the first time; no payment is required.
4. The **LiveClip Zero Studio** desktop window opens. Open **Local Shorts Studio** if it is not the selected tab.
5. If the launcher fails, double-click \`CHECK_SETUP_WINDOWS.bat\` and see [Troubleshooting](TROUBLESHOOTING.md). No administrator access is needed for the standard Python virtual environment, assuming the folder is writable.

### C. First result without any external video

1. Select **Local Shorts Studio**.
2. Click **Generate demo video**. This creates a tiny **synthetic** 36-second example using FFmpeg, without downloading real game footage.
3. The app sets **1 highlight / 15 seconds** after the demo finishes.
4. Click **CREATE HIGHLIGHT SHORTS**.
5. Use **Open last results**. Expect a generated MP4 plus \`candidates.json\` if the activity ranker selected a candidate.
6. Open the MP4, check playback, correct aspect ratio and audio. If no highlight was selected, the app will explicitly report that result; it is not a crash or quality certification.

### D. First result from your own recorded video

1. Click **Browse video** and select a locally stored MP4, MKV, MOV or WebM that you own or are licensed to reuse.
2. Pick **1/3/5 highlights**, **15/30/60 seconds**, **Balanced/Action/Dialogue** and **Blur/Fill**.
3. Choose an output folder, press **CREATE HIGHLIGHT SHORTS**, then **Open last results**.
4. A new dated results folder is created per run. Original input file remains intact.
5. Review every candidate before posting publicly.

The analysis is heuristic. A continuous quiet or extremely short video may produce zero selected clips. GPU is **not required** for the default CPU-compatible workflow, but faster hardware helps.

## Live source test

After local-file processing works, you can test a **public livestream you own or are authorized to record**:

1. Open **Live + Smart**.
2. Paste a supported authorized public stream URL; choose 30-second source segments, Gaming profile, 720p, threshold 22 and OCR OFF for the first test.
3. Start recording for a short controlled test, then choose **STOP + FINISH**.
4. Open the session folder. Find \`clip_*.mp4\` source recordings. Generated highlight exports appear in \`highlights/\`.
5. Ensure the test is playable and the source remains untouched. Actual provider support depends on Streamlink plugins, availability and account restrictions.

There is **no verified claim** that all sites and streams work. Private/DRM-protected streams and unauthorized copying are excluded.

## macOS and Linux

1. Install Python 3.10+, FFmpeg with ffprobe, and a functional Tkinter system package.
2. Extract the project and open a terminal **inside the project folder**.
3. Run:

    sh start_mac_linux.sh

4. The script creates \`.venv\`, installs the default free local video-analysis extras and opens the desktop application.
5. On headless servers without a desktop display, use the CLI instead:

    .venv/bin/python -m liveclip doctor
    .venv/bin/liveclip-studio --help

**Platform note:** Mac/Linux launcher and Tkinter rendering require actual device acceptance; only the GitHub Linux CI synthetic suite was previously exercised.

## Advanced CLI, only when needed

Windows PowerShell (inside the project folder):

    .\.venv\Scripts\liveclip-studio.exe --help
    .\.venv\Scripts\liveclip-studio.exe vod "C:\Videos\gameplay.mp4" "C:\Videos\shorts" --count 3 --seconds 30
    .\.venv\Scripts\liveclip-studio.exe vertical "C:\Videos\gameplay.mp4" "C:\Videos\short.mp4" --layout fill --duration 30

Optional features may require separately installed speech-recognition models, a local ONNX model, a private platform API key or FFmpeg compiled with subtitle support. The application does not bundle model weights or provider account permissions.

## How to collect a useful support report

Double-click \`CHECK_SETUP_WINDOWS.bat\`, copy the output (but **redact URLs, API keys, personal names and local private path details**), and report: OS version, Python version, FFmpeg version, command attempted, exact error, and whether the demo video rendered.

See [Troubleshooting](TROUBLESHOOTING.md) and the [source repository](https://github.com/S2zxx0zxx/Unlimited-Auto-Cut-Clipper-Tool).
