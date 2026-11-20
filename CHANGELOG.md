# Changelog

## 2.5.0 — 2026-11-20
- Add private loopback browser Studio with live Start/Stop, local VOD, preview, and one-click terminal-free Windows launcher.
- Support 15–300s maximum highlight windows in live and local workflows without making 300 seconds of arbitrary filler.
- Add opt-in conservative activity-event proposal and independent audio/video confirmation to suppress random-looking cuts; preserve existing algorithms and author notices.
- Add explicit limitations for game-specific race recognition, timeline proof, replay acceptance, and provider/OS tests.
- Add synthetic 300-second FFmpeg multi-segment render, localhost-security and false-positive regression tests.


## 2.4.0 — 2026-11-20
- Make LiveClip Zero Studio the primary first-party desktop product identity; preserve repository source/license attribution.
- Add a Local Shorts Studio tab, existing-video highlight export, and fully local synthetic demo generation.
- Enable optional offline VOD analysis through the one-click desktop launchers; provide a Windows environment check.
- Add a stable `liveclip-studio` CLI entry point; keep existing commands as backward-compatible aliases.
- Rework onboarding and troubleshooting around real user workflows, installation prerequisites and transparent verification limits.
- Keep third-party copyright/permission notices intact; no Git history rewrite or false authorship claims.


## 2.3.0 — 2026-11-20
- Audit all 57 tracked files in GTA Auto Clipper pinned at a9ac2ba8; record canonical de-dup decisions and outstanding third-party dependencies.
- Add optional GTA third-person player-centred vertical cropping and validated smoothed temporal keyframe pan to existing Neon vertical FFmpeg renderer.
- Add opt-in local ONNX person detector requiring user-supplied YOLOX weights; no background model download or performance claim.
- Add optional word-timed yellow pop ASS captions, text-only sensitive word masking and safe transcript escaping.
- Add unique-viewer spam-resistant chat-reaction signals and read-only YouTube live discovery (not automatic recording or verified viewer counts).
- Preserve existing livestream recorder, GUI, MP4 segments and SQLite; original MIT license and per-file provenance retained; synthetic unit/render tests added.
- Live chat synchronization, real model accuracy, source rights and official publishing remain release-gated.


## 2.2.0 — 2026-11-20
- Adopt selected MIT-licensed NeonClipping backend components with full notice and upstream commit provenance.
- Add opt-in CLI for vertical FFmpeg layout rendering, subtitle sidecars/burn-in, local VOD candidate ranking, read-only chat hype scoring and prompt chunking.
- Add opt-in local faster-whisper ASR, transcript-aware Ollama scoring, rights-confirmed public VOD importer and safety bounds.
- Preserve existing recorder/GUI, immutable source clips and SQLite journal; import does not imply full NeonClipping feature parity.
- Add synthetic FFmpeg and optional OpenCV/NumPy backend tests; update exact pending-feature ledger and source audit.


## 2.1.0 — 2026-11-19
- Package layout (`src/liveclip/`) and installable CLI/GUI entry points.
- Dependency doctor diagnostics and documentation reorganization.
- IP-literal and control-character URL input hardening.
- SQLite busy timeout, synthetic regression tests and Linux Actions workflow.
- Inject a fake Streamlink executable in CI media tests independent of installed CLI.
- Preserve v2.0 recording, multi-signal heuristics, OCR option, review, reports and restart recovery.

## 2.0.0 — 2026-11-19
- First local Smart Highlight Detector candidate build with GUI, headless CLI and synthetic offline tests.
