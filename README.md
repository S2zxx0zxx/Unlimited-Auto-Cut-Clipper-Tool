# LiveClip Zero Studio

**Version 2.4.0 · Unlimited Auto Cut Clipper Tool · Open source · Local-first**

A desktop video workspace for **recording authorized livestreams**, finding highlight candidates, and turning your own videos into vertical clips. No paid AI service, cloud account, or video upload is required for the basic workflows.

**Start here:** [Windows quick start](docs/QUICK_START.md) · [Mac/Linux setup](docs/QUICK_START.md#macos-and-linux) · [Troubleshooting](docs/TROUBLESHOOTING.md)

## New in 2.5 — Private localhost Studio and precision moments

**Existing users on Windows:** once updated to this source version, keep your existing Python 3.12 environment (`.venv`), FFmpeg 9.1 installation and saved recordings. Double-click **START_WEB_STUDIO.vbs** in the project folder. Your private localhost browser tab opens automatically. You do **not** need to open CMD for every recording. No paid AI or cloud service is involved.

**First-time install:** install Python 3.10+ with functional Tk/Tcl and FFmpeg/ffprobe; run **START_WINDOWS.bat** once to create the local `.venv`. Thereafter the web launcher reuses it.

The browser workspace lets you:
- Paste your **own or authorized live URL**, choose 30/60s source segmentation, up to **300-second highlight maximum**, then click **START LIVE + SMART** and **STOP + FINISH**.
- Paste a local recorded video path (in Windows File Explorer, **Shift+right-click → Copy as path**), choose 1/3/5 clips, activity profile and layout, then generate up-to-5-minute highlight candidates.
- Use **Precision mode** to group corroborated activity into time intervals and decline weak/no-evidence moments instead of forcing random cuts. **Max duration is a cap, not a guarantee.**
- Monitor progress and preview saved MP4s in the browser with local HTTP range playback; your files stay on your laptop.

The web service binds **only to 127.0.0.1** with a random port and per-launch token. It does not expose a public site, forward media to a paid API, or post to social platforms. Closing the browser tab does not necessarily stop the local server or active capture; press **STOP + FINISH** first. If you need a visible diagnostic terminal, run START_WEB_STUDIO_DEBUG.bat.

Technical note: current detector understands audio spikes, visual activity, transitions and sustained evidence. It **does not guarantee** race start/finish, chase resolution, wins, jokes, or viral quality without validated game-specific models. Review the first and last frames; if no clear event is present, Precision mode may rightly produce **zero** clips. The existing 30/60-second recorder segments remain separate from the variable-length final outputs. See [Research, acceptance and open gates](docs/PRECISION_WEB_STUDIO_V2_5.md).

## Get your first result (Windows)

1. Install [Python 3.10+](https://www.python.org/downloads/windows/) and [FFmpeg + ffprobe](https://ffmpeg.org/download.html). They must be available in your Windows PATH. You only need to install these once.
2. [Download the latest repository ZIP](https://github.com/S2zxx0zxx/Unlimited-Auto-Cut-Clipper-Tool/archive/refs/heads/main.zip) and extract it to a folder such as \`C:\LiveClipStudio\`.
3. Double-click **\`START_WINDOWS.bat\`**. On the first run, it installs the free recording and video-analysis Python dependencies into a private \`.venv\` folder.
4. In the desktop app, choose **Local Shorts Studio → Generate demo video**. When generation finishes, press **CREATE HIGHLIGHT SHORTS**.
5. Open the generated output folder. You should see playable MP4 highlight(s) and a \`candidates.json\` manifest. The original demo remains untouched.

Want to use your own video instead? Choose an MP4/MKV/MOV/WebM file and select **1 / 3 / 5 highlights**, **15 / 30 / 60 seconds**, **Balanced / Action / Dialogue**, and **Blurred background / Fullscreen crop**. The Studio creates a fresh output folder for every job.

> **Quality limits:** "highlights" are ranked candidates based on activity and available evidence. Not every source produces highlights, and a candidate score is not a calibrated virality prediction. Review clips before publishing.

## What the desktop app can do

| Tab | What you get |
|---|---|
| **Local Shorts Studio** | Select local video, generate sample video, create portrait highlight candidates, open output |
| **Live + Smart** | Record an allowed public live source into 30/60-second source segments, analyze finalized media, export highlight MP4s |
| **Analyze existing folder** | Resume an existing recording session without re-scoring previously indexed segments |
| **Review highlights** | Open generated clips and mark Keep or Reject without deleting your original recordings |

**Live highlight profiles:** Gaming, Sports, Reaction, Podcast, Balanced. Controls include detection threshold, highlight duration, overlap cooldown and optional Tesseract OCR. Exported live sessions include MP4s, thumbnails, CSV/JSONL and a resumable SQLite state journal.

All video processing happens on your computer. Internet is needed to access livestreams, public VODs and first-time dependency/model downloads; basic local rendering does not require a paid cloud API.

## Optional advanced workflows

The **\`liveclip-studio\`** command is available after installation. It uses the same video engines as the desktop app. Open a command prompt in the project folder, activate the virtual environment, and run:

\`\`\`powershell
# Windows PowerShell in the extracted project folder
.\.venv\Scripts\liveclip-studio.exe --help

# Generate up to 3 clips from a local file
.\.venv\Scripts\liveclip-studio.exe vod gameplay.mp4 highlights --count 3 --seconds 30 --profile action

# Make a fullscreen vertical short from a local video
.\.venv\Scripts\liveclip-studio.exe vertical gameplay.mp4 portrait.mp4 --layout fill --start 10 --duration 30

# Optional third-person GTA-focused framing, without claiming trained game understanding
.\.venv\Scripts\liveclip-studio.exe vertical gameplay.mp4 gta-portrait.mp4 --layout fill --gta-player-anchor 0.38 --duration 30

# Convert subtitles to WebVTT
.\.venv\Scripts\liveclip-studio.exe captions-convert captions.srt captions.vtt --format vtt
\`\`\`

Additional opt-in functions include 11 framing/layout options, manual camera/game regions, source-preserving local VOD ranking, transcript-guided scoring with optional Ollama, word-level captions with optional local speech transcription, timed pop-word animations, chat-score analysis of supplied message records, and read-only YouTube live discovery with your own API key. Some need extra dependencies, model files, API access or human review, and **are not certified as fully automatic workflows**.

For advanced features, run \`.\.venv\Scripts\python.exe -m pip install -e ".[all]"\` on Windows (after checking local disk/RAM and model download sizes). Do not run this unless you need those optional capabilities. No third-party service credentials are bundled.

## Live capture workflow

You may capture only streams you own or are authorized to record. Provider support depends on the service and current Streamlink compatibility, and is **not guaranteed** for private, paid, restricted or DRM-protected material.

1. Open **Live + Smart**; paste the authorized public livestream URL.
2. Choose **30 or 60 seconds** for source segments, stream quality, output folder and detection settings.
3. Click **START LIVE + SMART** and leave your computer on.
4. Stop using **STOP + FINISH**, then allow final analysis to finish.
5. Find \`clip_*.mp4\` in the session folder and \`highlight_*.mp4\` in its \`highlights/\` subfolder.

Source recordings are retained by default. "Unlimited" means **no arbitrary software clip-count cap**, not unlimited CPU, storage, upload quotas or uptime.


### Terminal interface

The Windows launcher and headless \`liveclip-zero\` recording/analyze commands
have a compact terminal presentation. It shows actual setup states, recent
activity and observed event counts without estimating fake progress. The existing
desktop GUI and media engines are unchanged. Use \`NO_COLOR=1\` or
\`LIVECLIP_PLAIN=1\` for plain output, and \`LIVECLIP_VERBOSE=1\` for
detailed interactive logs. See [Compact terminal UI](docs/TERMINAL_UI.md).

## Diagnose and verify

- Windows: double-click \`CHECK_SETUP_WINDOWS.bat\` to report versions and missing tools.
- CLI: \`.\.venv\Scripts\python.exe -m liveclip doctor\`
- Automated tests: \`.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v\`
- Linux/macOS: \`sh start_mac_linux.sh\` after installing Python, FFmpeg/ffprobe and Tkinter.

**Latest certified scope:** Linux GitHub CI's synthetic media and unit tests. Real Windows/macOS GUI acceptance, actual YouTube/Twitch capture, local model accuracy, large-scale concurrency and 24-hour soak tests remain unverified. See the [Development guide](docs/DEVELOPMENT.md) and [Engineering roadmap](docs/ADVANCED_EXECUTION_LEDGER.md).

## Project organization

\`\`\`text
src/liveclip/
  gui.py              Desktop recording, review and local Shorts Studio entry
  studio.py           First-party guided local-video workflow and demo
  capture.py          Livestream capture and reconnection
  pipeline.py         Durable local segment/highlight journal
  signals.py          Activity and visual/audio features
  cli.py              Recording and health-check commands
  neon_adopt/         Optional media/transcription/ranking engine modules
  gta_adopt/          Optional gameplay framing, tracking and caption modules
tests/                Synthetic test and regression suite
docs/                 Setup, security, architecture, testing and release plans
THIRD_PARTY_LICENSES/  Required copyright and permission notices
\`\`\`

The \`src/\` paths are developer implementation details; no multiple redundant recorder engines or account services are required for the standard desktop experience.

## License and project trust

The application repository uses **GPL-3.0-only**. It incorporates selected permissively licensed open-source components; their author copyright and permission notices are preserved in [THIRD_PARTY_LICENSES](THIRD_PARTY_LICENSES) and source headers. Such required notices and Git history are not rewritten to misrepresent authorship. The license of the software is not permission to copy or republish another creator's video.

Contributions and bug reports: [CONTRIBUTING.md](CONTRIBUTING.md). Security handling: [docs/SECURITY.md](docs/SECURITY.md). Past changes: [CHANGELOG.md](CHANGELOG.md).
