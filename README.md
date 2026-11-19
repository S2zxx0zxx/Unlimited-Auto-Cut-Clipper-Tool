# Unlimited Auto Cut Clipper Tool

**LiveClip Zero Smart — v2.1.0** · Open-source · Local-first · No paid AI/cloud API

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

## Licensing

GPL-3.0-only — see the repository `LICENSE`. Third-party software (FFmpeg, Streamlink, Python, Tesseract) retains its own separate license and distribution obligations.
