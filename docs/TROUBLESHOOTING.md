# Troubleshooting — LiveClip Zero Studio

| Symptom | Likely issue / safe fix |
|---|---|
| \`ffmpeg\` or \`ffprobe\` not recognized | Install both binaries and add the FFmpeg \`bin\` folder to PATH; reopen Command Prompt |
| Python missing or version too old | Install Python 3.10+ and use \`py -3 --version\`; then launch again |
| Window closes after double-click | Run \`CHECK_SETUP_WINDOWS.bat\`; errors remain visible until key press |
| \`pip install -e ".[neon]"\` fails | Ensure Python is supported, internet is available on first run and writable folder/disk; don't download arbitrary dependency ZIPs |
| Tkinter fails to launch | Install the Tk support for your platform and run from a graphical desktop session |
| No local highlight candidates | Try a longer, more active source, shorter clip length or lower threshold for live modes; scores are heuristics |
| Video still landscape or poor crop | Select \`fill\` for full-frame crop or \`blur\` to preserve all source content; inspect the resulting MP4 |
| Portrait render takes time | FFmpeg uses local CPU. 1080/2160 resolutions and long videos cost more; try 720p first |
| Subtitle burn-in fails | Install FFmpeg with libass/subtitles filter or use SRT sidecar without burn |
| Speech transcription not working | Optional \`.[speech]\` dependency and model weights are required; model download needs explicit action |
| ONNX player tracking won't launch | Supply a compatible trusted ONNX model and install \`.[gta]\`; this path is not production-qualified |
| Livestream recorder produces no clips | Verify the public authorized stream is live, the URL is supported and the selected quality exists; check logs for provider errors |
| \`streamlink\` missing in doctor | Relaunch \`START_WINDOWS.bat\` to initialize the local environment; run doctor inside \`.venv\` |
| Keep/Reject changes not visible | Review the same session folder and refresh the list; exported MP4 files are never deleted by rejecting |
| No output after Ctrl+C | Recording finalization and rendering can require extra processing; inspect session folder and errors; avoid repeated forced termination |
| Disk space low | Change output folder to a drive with sufficient space; raw source segments accumulate by design and are not auto-deleted |

## Start/Stop controls missing on smaller laptop screens

The Start and Stop buttons belong on the **Live + Smart** tab immediately below
the output folder. If you are on an older download where the buttons fall below
the large Notebook, update `src/liveclip/gui.py` from the current verified
repository release. Do **not** reinstall Python, FFmpeg or the local .venv for
this presentation-only issue. Never start capture merely by pasting the URL:
click **START LIVE + SMART** when the source is live and you are authorized
to record it. Click **STOP + FINISH** to finalize.

## Diagnosis (Windows)

Double-click \`CHECK_SETUP_WINDOWS.bat\`, or run the following in the extracted project folder:

    .\.venv\Scripts\python.exe -m liveclip doctor
    .\.venv\Scripts\python.exe -m compileall -q src tests
    .\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v

Test results are conditional on your environment. If the optional OCR test skips due to no Tesseract, it does not mean OCR was tested successfully. Real provider, Windows/macOS native GUI and 24-hour soak are separate acceptance requirements.

## Protect your data

Never share account cookies, OAuth tokens, API keys, provider-signed URLs or unredacted private recordings in public GitHub issues. Do not disable Windows security protections to install a ZIP or executable from an unknown source.

For problems with dependencies, use official project download sites and the pinned requirements in \`pyproject.toml\`; optional model weights are not bundled by default. Do not process or republish third-party footage without rights.
