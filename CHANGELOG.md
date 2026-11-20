# Changelog

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
