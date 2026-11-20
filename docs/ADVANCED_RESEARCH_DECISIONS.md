# Advanced Capability Research & Decision Register

**Review date:** 2026-11-20 · **Decision maturity:** design candidates only · **Status:** RESEARCHED, no new runtime implementation

This file records verified platform/library facts, design choices, discarded shortcuts and questions which MUST be checked again before implementation. The local-first GPL-3.0 project is not a paid infrastructure product and cannot assume all model weights or external binaries have the same licenses as their host libraries.

## R-01: Stream capture — Streamlink + FFmpeg, not 'any URL works'

**Evidence:** Streamlink maintains a plugin-based list of supported services including YouTube and Twitch; real provider access varies with URL, account, region, DRM, stream availability and current plugin compatibility.
- https://streamlink.github.io/latest/
- https://streamlink.github.io/latest/cli/plugins/twitch.html
**Decision:** retain Streamlink adapter with explicit supported source diagnostics, TLS/source validation and controlled FFmpeg child processes. Use owned or authorized test streams.
**Rejected:** promise arbitrary links, bypass login/DRM, unbounded simultaneous capture.
**Unverified:** this repository's end-to-end real provider capture on Windows/macOS/Linux.

## R-02: Visual stack — deterministic media path first, model inference optional

**Evidence:** OpenCV is Apache-2.0; PySceneDetect BSD-3-Clause; ONNX Runtime MIT.
- https://github.com/opencv/opencv
- https://github.com/Breakthrough/PySceneDetect
- https://github.com/microsoft/onnxruntime/blob/main/LICENSE
**Decision:** scene detection + image/video ROI candidates without AI model first; then optional versioned ONNX inference for trained subject/event models. Must measure CPU-only throughput, memory and clip quality.
**Rejected:** introduce a GPU-required monolith or download unvetted model weights automatically.
**Licensing note:** permissive runtime license does NOT automatically license a third-party ONNX model file.

## R-03: Gaming event recognition — adapters + ground truth, not a universal magic model

**Evidence:** CVAT Community and Label Studio offer self-hosted dataset annotation workflows.
- https://github.com/cvat-ai/cvat
- https://github.com/HumanSignal/label-studio
**Decision:** one game at a time; events: victory/defeat, killfeed, multi-kill, round end and objective/score changes; game-version HUD signatures, OCR, temporal verification and hard negatives. Keep generic fallback.
**Rejected:** claim a universal cross-game kill/headshot detector trained without data.
**Gate:** authorized labelled dataset, independent human review and event-level precision/recall.

## R-04: 9:16 smart reframing — smooth tracked virtual camera

**Evidence:** MediaPipe vision tasks and open-source prototypes demonstrate face/object/scene-based cropping approaches. Upstream examples are *research references*, not audited production dependencies.
- https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision
- https://github.com/idopinto/ai-video-reframing
- https://github.com/delvilo/wide2short
**Decision:** deterministic center-crop fallback; candidate face/HUD region detection; tracker smoothing, scene resets, gameplay+facecam layouts, manual subject lock and side-by-side preview. Input aspect ratio may be 16:9, 4:3, 21:9, etc.
**Rejected:** crop every frame independently (causes jitter); cropping away critical gameplay HUD; assuming all model licenses permit commercial redistribution.
**Gate:** annotated subject-retention, HUD visibility, jitter and manual-correction metrics on held-out clips.

## R-05: Model licensing — do not treat 'open-source' as unrestricted

**Evidence:** Ultralytics publicly documents AGPL-3.0 and Enterprise licensing, while FFmpeg binary obligations depend on how it is built and distributed.
- https://www.ultralytics.com/license
- https://ffmpeg.org/legal.html
**Decision:** model registry tracks source, weights SHA-256, license, intended use, restrictions, notice, model size and supported hardware. Require written license assessment before bundling any weights or external binaries.
**Rejected:** silent import and bundling of Ultralytics weights or a GPL-enabled FFmpeg binary without attribution/compliance work.

## R-06: ASR/captions — local, editable, language measured

**Evidence:** faster-whisper implements Whisper inference through CTranslate2 and supports word timestamps; WhisperX adds timing/alignment/diarization options with additional dependencies/licensing.
- https://github.com/SYSTRAN/faster-whisper
- https://github.com/m-bain/whisperX
**Decision:** modular ASR adapter CPU-first, transcription to editable SRT/VTT; optional alignment and translation after ground-truth evaluation on mixed Hindi/English, slang and other supported languages. Do not imply word confidence or perfect bilingual accuracy.
**Rejected:** default paid cloud speech API, inference without local capacity controls, silently rewriting low-confidence slang.

## R-07: YouTube publishing — OAuth, compliance and current quota

**Evidence:** YouTube Data API `videos.insert` and the Quota Calculator were revised in 2026; current docs show a separate upload quota bucket and new accounting. API policy governs project registration, verification/audit and applicable upload restrictions.
- https://developers.google.com/youtube/data/reference/rest/v3/videos/insert
- https://developers.google.com/youtube/data/determine_quota_cost
- https://developers.google.com/youtube/data/revision_history
- https://developers.google.com/youtube/terms/developer-policies
**Decision:** query/check actual project quota at implementation and test on explicitly authorized channels. Manual approve + publish status receipts + idempotency and privacy controls.
**Rejected:** hardcode historical 1600-unit estimate, promise 100 uploads are always available/allowed, OAuth token or browser-session scraping, duplicate mass posting.
**Unverified:** the user's project/channel eligibility, audit state and actual upload quota.

## R-08: Instagram and Facebook publishing — official platform/account-aware adapters

**Evidence:** Meta documents professional-account Instagram publication concepts, content-publishing limits, and Page video publishing via Graph API; permissions and endpoints evolve.
- https://developers.facebook.com/docs/instagram-platform/
- https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/v21.0/
- https://developers.facebook.com/docs/graph-api/reference/page/videos/
**Decision:** verify current Meta API version, account type, app review, scopes, upload-media URL expectations and per-account limits at implementation. Publish only after owner consent.
**Rejected:** unsupported private-account automation, anti-bot circumvention, unreviewed batches.
**Unverified:** Instagram/Facebook publishing permissions for any specific account and whether zero-cost media serving is available.

## R-09: Browser extension — user gesture required

**Evidence:** Chrome MV3 tabCapture only starts after user action; service-worker/offscreen-document pattern exists, but capture ends when tab/media stream ends.
- https://developer.chrome.com/docs/extensions/reference/api/tabCapture
- https://developer.chrome.com/docs/extensions/how-to/web-platform/screen-capture
**Decision:** extension first as local desktop controller or explicitly user-started tab capture. Never claim headless 24/7 service from Chrome extension.
**Rejected:** hidden recording without consent, bypassing permission prompts.

## R-10: Android — companion first, full native capture only if justified

**Evidence:** Jetpack Media3 Transformer supports local editing and export. Foreground capture/processing has Android permissions and lifecycle restrictions.
- https://developer.android.com/media/implement/editing-app
- https://developer.android.com/media/media3/transformer/transformations
- https://developer.android.com/reference/android/content/pm/ServiceInfo
**Decision:** Android review/control companion first. Evaluate on-device clip trim/export with Media3 separately. Require explicit user consent for capture and realistic battery/thermal targets.
**Rejected:** running Python desktop capture unchanged on Android, hidden unlimited background recording.

## R-11: Desktop installers — OS-specific build/test

**Evidence:** PyInstaller docs say it is *not* a cross-compiler. Packaging an .exe on Linux is not a substitute for a tested Windows build.
- https://pyinstaller.org/en/stable/
**Decision:** per-OS CI jobs and real-device smoke; verify packaging dependencies, external binaries, malware scanner false positives and signature requirements. A packaged binary is not the same as an audited installer.
**Rejected:** label a ZIP of Python source 'Windows executable' or assume free macOS signing/notarization.

## R-12: Content rights, anti-spam and long-run operations

**Evidence:** YouTube's monetization policy specifically distinguishes original/authentic content from reused or mass-produced repetitive content, even where copyright permission might be separate.
- https://support.google.com/youtube/answer/1311392
**Decision:** explicit rights metadata, human editorial review, original contributions where needed, policy-respecting publication, storage budgets, 24h tests, actual measured performance and transparent failure states.
**Rejected:** 'unlimited videos' = infinite hardware or automatic platform approval; guaranteed virality; indiscriminate reposting.

## Architecture decision backlog (all OPEN)

| ADR ID | Choice requiring evidence | Proposed default | Decision gate |
|---|---|---|---|
| ADR-001 | Canonical timebase and reconnect epoch mapping | monotonic segment order + PTS | capture integration |
| ADR-002 | SQLite schemas and durable job leasing | single-host SQLite WAL | crash recovery |
| ADR-003 | Model pack formats and dependency pinning | ONNX optional / CPU-first | license/perf benchmarks |
| ADR-004 | First game adapter | selected licensed footage | labelled dataset available |
| ADR-005 | Caption/translation engines | faster-whisper + optional translator | language WER, compute |
| ADR-006 | Crop camera path/tracker | scene-aware smooth virtual camera | annotated retention |
| ADR-007 | Platform publishing media relay | no cloud by default | official Meta access + privacy |
| ADR-008 | UI architecture | existing Tkinter evolving + local API | portability/usability |
| ADR-009 | Windows/macOS/Linux packaging | native build per OS | clean-device acceptance |
| ADR-010 | Browser extension relationship | companion control + opt-in capture | user gesture tests |
| ADR-011 | Android relationship | companion/review first | Android lifecycle tests |
| ADR-012 | Budget/retention and media backup | user-visible quotas, no auto deletion | 24h soak |
| ADR-013 | Version/feature availability truthfulness | separate code/test/provider/ship flags | release report |
| ADR-014 | License and content-rights provenance | lockfiles + SBOM + rights record | independent audit |

## Research sufficiency and outstanding evidence

This document is a source-backed plan, not exhaustive empirical validation. External docs confirm *feasibility of components*, not their integration into this application. The following still require experiments: representative licensed footage, exact computer specs, resource load, OS behaviors, YouTube/Twitch provider tests, gaming precision, model rights, platform accounts/scopes/quotas, native media packaging, Chrome/Android consent behavior and release economics.

Each ADR must record actual decision, rejected alternatives, benchmark results, source/version and decision owner before respective feature PR merges.

**Do not silently infer the user's hardware, publication rights, API approvals, or model quality.**
