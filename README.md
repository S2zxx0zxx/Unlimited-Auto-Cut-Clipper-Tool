# Unlimited Auto Cut Clipper Tool

**LiveClip Zero Smart — v2.2.0** · Open-source · Local-first · No paid AI/cloud API

Record a **supported, authorized public livestream** into continuous source segments and automatically rank **candidate highlights** using reproducible audio/video heuristics. Review, keep or reject the generated MP4s. A local Tkinter GUI and headless CLI are included.

> **Accuracy disclosure:** This is not a trained AI highlight model. Loud sounds, fast motion and OCR keywords can produce false positives; a truly funny, skillful or viral moment cannot be guaranteed. No DRM bypass, private stream capture, YouTube upload, copyrighted-content licensing or monetization guarantee is included.

## Features

- Live URL → Streamlink → FFmpeg → incremental **30/60-second original clips**.
- Audio surge/onset, motion, scene-cut and brightness-flash scoring; optional Tesseract OCR.
- **Gaming, Sports, Reaction, Podcast, Balanced** profiles; threshold and cooldown controls.
- Exports **15/30/45/60-second** highlight candidates, thumbnails, JSONL and CSV reports.
- Review UI: Keep/Reject labels without deleting source or exports.
- SQLite WAL journal, reconnect gap markers, resumable analysis, atomic export and low-storage guard.
- Local operation, optional OCR, no API keys. Runs while PC stays on.

## Get started

### Windows GUI

1. Install **Python 3.10+** and **FFmpeg with ffprobe**. Ensure both are available in PATH.
2. Download or clone this repo. Double-click `START_WINDOWS.bat` (first run installs Streamlink via `pip`).
3. Paste an authorized public livestream URL, choose Gaming/Balanced, duration and output folder, then click **START LIVE + SMART**.
4. Find source clips in `Live_*/clip_*.mp4` and chosen exports in `Live_*/highlights/`. Use the Review tab.

### macOS/Linux GUI

Install Python 3.10+, FFmpeg/ffprobe and your platform's Tkinter support, then run `sh start_mac_linux.sh`.

### CLI / headless

```sh
python -m venv .venv
. .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
liveclip-zero doctor
liveclip-zero record 'https://example.org/your-authorized-live' --segment-seconds 30 --profile Gaming --threshold 22
liveclip-zero analyze '/path/to/Live_20261119_121500' --profile Sports --highlight-seconds 30
liveclip-zero-gui
```

Press **Ctrl+C** to stop capture gracefully. On Windows use `START_WINDOWS.bat` for easiest GUI setup. Supported URLs depend on Streamlink plugins and platform restrictions; inaccessible/private/DRM-protected streams are not supported.

## How it works

```text
Approved live URL ─► Streamlink subprocess ─► FFmpeg segment muxer ─► clip_*.mp4
                                                           │
                                    finalized-only analysis worker
                                                           │
                       audio/video features + optional local OCR
                                                           │
                                  score threshold + cooldown
                                                           │
                           SQLite candidate journal / recovery
                                                           │
                         bounded FFmpeg highlight export
                                                           │
                            MP4 + JPG + CSV/JSONL + Review
```

The ranking number **0–100 is a heuristic score, not a probability**. Keyframe-aligned segmentation may not yield exact 30/60-second source durations. Each highlight export transcodes to H.264/AAC for reasonable playback compatibility.

### Local data and resource boundaries

Sources and outputs stay in your specified folder, without automatic deletion. URLs are not intentionally written to session metadata, but command-line history and external tools may retain URLs. Do not capture copyrighted third-party streams without permission. Disk space, bandwidth, CPU and host uptime are practical limits, so “unlimited” refers to **no hardcoded clip-count cap**, not infinite capacity.

## Verify

```sh
python -m compileall -q src tests
python -m unittest discover -s tests -p 'test_*.py' -v
```

Tests generate **synthetic locally-created media**; FFmpeg and ffprobe are needed for the video integration suite. GitHub Actions configuration is provided, but a passing remote run must be checked separately. See [Architecture](docs/ARCHITECTURE.md), [Security](docs/SECURITY.md), [Development](docs/DEVELOPMENT.md) and [Test evidence](docs/TEST_RESULTS.md).

## GTA Auto Clipper — unique third-repository backend enhancements (v2.3)

The pinned MIT source is [AnIntellectualBeing/GTA-Auto-Clipper](https://github.com/AnIntellectualBeing/GTA-Auto-Clipper) at a9ac2ba8. [The 57-file audit and deduplication decisions](docs/GTA_AUTO_CLIPPER_AUDIT.md) explain what is new, existing, intentionally excluded, or still pending. The [MIT license and author notice](THIRD_PARTY_LICENSES/GTA-Auto-Clipper-MIT.txt) are preserved. No new GUI or recorder replaces LiveClip/Neon.

New opt-in features extend the **same** liveclip-neon commands:

    # Player-centred GTA framing (no trained player recognizer required)
    liveclip-neon vertical owned.mp4 gta-short.mp4 --layout fill --gta-player-anchor 0.38 --start 10 --duration 30

    # Use pre-reviewed clip-relative [seconds, x_fraction] points for a smooth pan
    liveclip-neon vertical owned.mp4 tracked.mp4 --layout fill --pan-keys-json keyframes.json --duration 30

    # Optional local YOLOX-S person tracker (no model weights auto-downloaded)
    pip install -e '.[gta]'
    liveclip-neon vertical owned.mp4 onnx-short.mp4 --layout fill --track-player-model /trusted/yolox-model.onnx

    # Existing absolute-time Whisper words -> one-line word-by-word yellow pop subtitles
    liveclip-neon vertical owned.mp4 captions.mp4 --layout fill --pop-words-json transcript.words.json --pop-language en

    # Apply GTA crop and pop captions to clips selected from a local VOD
    liveclip-neon vod owned.mp4 highlights --layout fill --gta-player-anchor 0.38 --words-json transcript.words.json --pop-captions

    # Distinct-chatter/reaction scoring from pre-aligned chat timestamps (offline)
    liveclip-neon chat-reactions messages.json --window 30 --step 10

    # Read-only live discovery; requires YOUR YouTube Data API key
    liveclip-neon discover-live "GTA 6 gameplay" --max 10

Notes: a tracking model file and its weights license must be verified separately. Chat times must be relative to the matching source and reconnection epoch, not arbitrary wall-clock timestamps. YouTube discovery never implies gameplay is visually confirmed or recording/posting is permitted. These are heuristics and optional styling options; not semantic game-event recognition. Every original source clip is preserved.

## Future capability roadmap (research and planning only)

The next-phase build is tracked in the [Advanced Capabilities Master Plan](docs/ADVANCED_CAPABILITIES_MASTER_PLAN.md), the [120-task Execution Ledger](docs/ADVANCED_EXECUTION_LEDGER.md), and the [Research & Architecture Decision Register](docs/ADVANCED_RESEARCH_DECISIONS.md). These are **planned features, not currently shipped**: real-provider reliability, semantic/game-specific event recognition, subject-aware vertical reframing, subtitles/translation, calibrated ranking, multi-stream control, official platform publishing, desktop installers, Chrome/Android clients, 24-hour resilience and release/security certification. Each requires verified acceptance evidence before being marked complete.

## Optional NeonClipping backend (MIT-attributed, no UI replacement)

An opt-in "liveclip-neon" CLI adds local VOD candidate ranking, transcript-aware (optional Ollama) scoring, vertical layout renders, SRT/VTT captions, chunked local speech recognition, transcript prompt splitting, read-only chat hype scoring, and rights-confirmed public VOD URL import. The existing live recorder and GUI are unchanged. This is **not full NeonClipping parity**; automatic facecam detection, live-chat-triggered capture, creator monitoring, saved-edit UI, and social publishing remain pending.

Install only the required extras:

    pip install -e '.[neon]'      # NumPy/OpenCV for VOD ranking
    pip install -e '.[speech]'    # Optional faster-whisper ASR
    pip install -e '.[download]'  # Optional yt-dlp VOD import
    liveclip-neon --help

See [adopted feature matrix, license and examples](docs/NEONCLIPPING_ADOPTION.md). Imported MIT copyright/permission notice is at [THIRD_PARTY_LICENSES/NeonClipping-MIT.txt](THIRD_PARTY_LICENSES/NeonClipping-MIT.txt). Never assume a candidate score predicts virality or that third-party media is licensed for reposting.

## Licensing

GPL-3.0-only — see the repository `LICENSE`. Third-party software (FFmpeg, Streamlink, Python, Tesseract) retains its own separate license and distribution obligations.
