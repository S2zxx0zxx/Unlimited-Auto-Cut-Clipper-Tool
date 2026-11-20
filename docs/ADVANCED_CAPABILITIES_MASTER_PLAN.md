# LiveClip Zero Smart — Advanced Capabilities Master Blueprint

**Plan ID:** LC-ADV-2026-11-20-v1 · **Research cut:** 2026-11-20 · **Status:** RESEARCHED / NOT IMPLEMENTED · **Repository baseline:** main `8a3db1c3f1357c50f387ab344d207f70d4dd2f26`, v2.1.0

> This is a durable implementation contract, not a claim that planned features work. No application source code is changed in this planning PR. The release baseline already has Streamlink → FFmpeg local recording, 30/60-second source segments, deterministic heuristic signals, candidate exports, SQLite journal, Tkinter UI and CLI. All remote-site, OS-specific and 24-hour acceptance evidence remains outstanding.

## 1. Non-negotiable project invariants

1. **Zero paid-service requirement:** core processing, storage and model inference must run locally. User-provided CPU/GPU, disk space, bandwidth and time are not free or infinite; report real resource usage. Optional third-party hosting or publication services cannot be mandatory.
2. **Rights-first capture and publishing:** only user-owned or otherwise authorized content. Record provenance/permission per source; never bypass DRM, private access, user consent, API quotas, CAPTCHA or anti-abuse controls. No default mass publishing.
3. **Capture survives AI failures:** isolate capture, feature extraction, scoring, rendering and publishing behind durable queues; failure of downstream AI must not corrupt or stop source recording.
4. **Source preservation:** immutable source video, monotonically ordered session segment IDs, reconnect epochs and timebases; no automatic deletion without explicit retention policy and backup confirmation.
5. **Truthful outputs:** rank candidate moments, not guaranteed viral clips. Store model version, score components, threshold, timestamp alignment and why each candidate was selected.
6. **Privacy by design:** local inference by default; minimized logs, redaction of signed source URLs and OAuth secrets, encrypted tokens in OS credential stores, optional model downloads and no silent telemetry.
7. **No silent degradation:** if models, GPU, OCR or network fail, emit an explicit state and fall back only to a disclosed supported mode. Never label a fallback as semantic AI.
8. **A capability is DONE only after:** tests, documentation, security review, measured acceptance criteria, real device/provider verification where applicable, CI and user-visible UX. No 'complete' based solely on implementation.

## 2. Intended pipeline / system boundaries

```text
Authorized source URL / local input
  -> SourceAdapter + permission/URL validation
  -> CaptureSupervisor [Streamlink, FFmpeg, reconnect epoch, disk guard]
  -> Durable Segments [immutable, sha256, duration, PTS, status]
  -> AnalyzerQueue [bounded jobs; resource budget; resume]
       |-> Audio/VAD/ASR/speech reactions
       |-> Visual motion/cuts/OCR/object/face/subject tracking
       |-> GameAdapter (per-game HUD, kill feed, win screen, scoreboard)
       |-> Optional semantic classifiers
  -> EvidenceFeatures [timecoded, versioned, provenance]
  -> Ranker [multi-signal scores, calibration, overlap/cooldown, diversity]
  -> ReviewQueue [candidate/keep/reject/edit]
  -> MediaPipeline [trim, 9:16 crop track, captions, loudness, QC]
  -> ExportLibrary [MP4, preview, VTT/SRT, manifest, rights metadata]
  -> PublishingQueue [manual approve -> OAuth platform adapters -> receipts]
```

Suggested Python package boundaries (proposal, **not present in repo**):

```text
src/liveclip/
  core/{config,contracts,events,types,clock,errors}.py
  sources/{registry,streamlink_adapter,local_file}.py
  capture/{supervisor,segmenter,recovery,resource_guard}.py
  storage/{sqlite,repository,migrations,artifacts}.py
  jobs/{scheduler,lease,worker,limits}.py
  analysis/{audio,visual,ocr,asr,models,game_adapters}.py
  ranking/{features,scoring,calibration,selection}.py
  editing/{timeline,reframe,subtitles,render,quality_check}.py
  publishing/{base,oauth,youtube,instagram,facebook,receipts}.py
  interfaces/{cli,desktop,local_api}.py
  observability/{logging,metrics,health}.py
  security/{url_policy,rights,token_store}.py
tests/{unit,integration,fixtures,e2e,benchmarks,security}/
docs/{ADR,acceptance,migration,operations,licenses}/
```

Do **not** perform a blind all-at-once refactor. Extract modules behind adapters incrementally; preserve existing CLI, GUI and serialized session compatibility. Migrate SQLite under versioned transactions with rollback, backups and compatibility tests.

## 3. Workstreams: specification, proposed tech, acceptance

### LC-01 — Real provider capture and media timing [P0 / unverified]
**Goal:** reliable authorized YouTube/Twitch/public-supported livestream capture.
- Confirm supported URLs against current Streamlink plugins; enforce HTTPS and a bounded allowlist for network capture, DNS/IP checks against private/loopback/link-local addresses, redirect validation, and never accept arbitrary auth cookies from web UI.
- Add adapter capability discovery, stream quality fallback, failed authorization diagnostics, reconnect backoff/jitter and explicit connection epochs.
- FFmpeg `ffprobe` validation; handle corrupt/truncated segments, keyframe-imprecise 30/60s boundaries, timestamp discontinuities, audio/video drift, HLS/DASH edge cases and shutdown finalization.
- QA with authorized live sources: 30m per site/quality, reconnect network loss, end-of-live, signal interrupt, slow disk, insufficient space, crash/restart, and no valid finalized segments lost. Keep reproducible provider/version matrix; never claim universal support.

### LC-02 — Semantic audio/video intelligence [P0 / not implemented]
**Goal:** identify meaningful candidate events, not just loudness or motion.
- Build timecoded feature store: VAD, ASR text, speech emphasis, laughter/cheering candidates, event OCR, temporal image embeddings, scene boundaries; investigate small CPU-friendly ONNX models before larger GPU models.
- Separate model runtime from capture, configure processing budget and deterministic fallback. Batch consecutive finalized segments, and preserve lookbehind/lookahead to avoid cut-off reactions.
- Define per-event class, confidence (calibrated only against data), evidence, precision/recall and 'unknown' abstention; no unsupported emotion reading or fabricated narrative.
- Benchmark on licensed manually labelled positive/negative streams, diverse languages, silence, games and noisy commentary. Report precision, recall, F1 and inference time against heuristic baseline, not unmeasured 'AI accuracy'.
- Candidate tools: OpenCV (Apache-2.0), ONNX Runtime (MIT), PySceneDetect (BSD-3-Clause), optional ASR from faster-whisper (MIT); inspect *each model's weights license separately*.

### LC-03 — Game-specific adapter architecture [P0 / not implemented]
**Goal:** event classes for explicitly selected games, e.g. victory/defeat, killfeed, multi-kill, round-end, objective/score change, clutch.
- Define plugin contract `GameAdapter.detect(context)->List[EventEvidence]` with game name/version, HUD geometry, resolution/aspect calibration, OCR vocabularies, templates, temporal smoothing and negative-class filters.
- Adapter registry plus 'Generic gaming' heuristic fallback; never advertise one universal recognizer. Add screen regions-of-interest, optional game menu setup, multi-language support and UI version drift tests.
- Keep per-game golden test sets and adversarial overlays (subtitles, spectating, spectator feed, fake victory screens). Begin with ONE game selected by available rights/test footage; expand only after measured acceptance.
- Annotation options: self-hosted CVAT Community (MIT) or Label Studio (Apache-2.0); label every moment with event timestamps, reviewer agreement and recording permission.

### LC-04 — 9:16 reframing / subject tracking / media editor [P0 / not implemented]
**Goal:** 1080×1920-ready vertical exports with subject kept in frame, not blindly center cropped.
- Layer A: fixed center crop + letterbox fallback and safe-area template for stream UI.
- Layer B: face/object/active-player/HUD saliency detection sampled at adaptive cadence; track identities/boxes across frames; smooth virtual camera path with velocity/acceleration limits and shot-change resets.
- Layer C: scene-aware mode for gameplay + facecam split composition; manual keyframes/subject lock; preserve killfeed/scoreboard legibility and captions safe areas.
- Rendering: FFmpeg trim/crop/scale/pad/overlay/loudnorm where appropriate, H.264/AAC outputs, timestamp-correct audio; hardware encode opt-in and validated software fallback.
- QC: crop-boundary overflow, subject retention (define benchmark target before build), hallucinated tracker boxes, jitter score, text clipping, VFR and 16:9/4:3/ultrawide inputs. Don't select YOLO library/weights until AGPL/commercial implications are resolved.

### LC-05 — Local subtitles, speech transcription, translation [P1 / not implemented]
**Goal:** editable burned-in subtitles and downloadable SRT/VTT with truthful language/word timing.
- Audio extract -> VAD -> local ASR (CPU first, GPU optional) -> word alignment -> human correction -> SRT/VTT -> font-safe styled captions -> FFmpeg render.
- Mixed Hindi/English gaming slang, profanity handling, per-language templates, silence suppression, special characters, Unicode shaping, line length and safe areas. Translation is a separate optional *model*, never assumed native ASR ability.
- Candidate: faster-whisper for transcriptions/word timestamps; WhisperX as optional alignment/diarization with its own model/dependency rights; local translation model only after language-pair evaluation.
- Test WER/CER on user-approved ground truth, word-boundary alignment, subtitle overflow, blank/silent audio and sync on retimed segments. Flag low-confidence words for review.

### LC-06 — Advanced ranking, deduplication and learning [P0 / not implemented]
**Goal:** useful, diverse shortlist with evidence-backed scores.
- Preserve current heuristic baseline as fallback. Add candidate fusion (game events + semantic transcript + reaction + scene + audio); early vs late event context, overlap graph, near-duplicate perceptual hash/audio fingerprint, per-session top-K and threshold.
- Provide rationale and confidence bands only after calibration; allow user Keep/Reject, trim adjustment and tag feedback to update local thresholds. **No hidden model retraining or unreviewed publication.**
- Evaluate precision@5, recall of labelled priority events, diversity, missed-event rate, false-positive rate, duplicate ratio and ranking reproducibility. Use same held-out source set for every release.

### LC-07 — Multi-stream production manager [P1 / not implemented]
**Goal:** multiple authorized streams controlled from one dashboard without claiming infinite concurrency.
- Durable per-stream state machine, job lease, per-stream process isolation, priority and max concurrency; separate capture CPU budget from inference and export queues. Pause/continue jobs individually.
- SQLite WAL sufficient for a single-host initial deployment; implement a storage abstraction before any remote coordinator. Process-local queue is not durable; introduce leased jobs and retries with idempotency keys.
- Dashboard: source cards, health/reconnect state, recording bytes, segment lag, GPU/CPU/disk pressure, failed jobs, filter/search, per-stream settings and alerts.
- QA: two then N simultaneous sources under measured hardware, cancellation isolation, crash recovery, no duplicate exports, disk-full behavior, lock contention and clear throughput ceilings.

### LC-08 — Platform publishing adapters [P1 / not implemented]
**Goal:** export and optionally publish approved original/authorized content to YouTube, Instagram and Facebook without unsafe shortcuts.
- `PublishRequest` is created only for an asset with rights record + manual approval. Human-editable caption/title/tags, thumbnail, privacy and per-platform rendition.
- Official API + OAuth only. Credential storage in OS keyring; least scopes, revocation, token refresh, retries with idempotency/status reconciliation, quota/rate ceilings and platform-specific error taxonomy.
- YouTube: follow current `videos.insert` policies, API project verification/audit, dynamically checked upload quota and publish privacy. Note that 2026 quota documentation has changed; never hardcode legacy 1600-unit upload cost or assume unlimited uploads.
- Instagram: compatible professional-account flow and permissions; verify current Meta Graph API container/media publishing limits and reachable media hosting requirements at implementation. Facebook: supported Page publishing/reels endpoint and access review, not personal-profile hacks.
- Export-first flow is mandatory fallback when no authorized API route exists. Test draft/private/unlisted publishing where allowed, cancellation, duplicate prevention, OAuth expiration and platform error recovery. Do not equate upload success with reach/monetization.

### LC-09 — Native desktop packaging [P1 / unverified]
**Goal:** verified downloadable Windows/macOS/Linux binaries.
- Package on each OS independently (PyInstaller does not cross-compile), track FFmpeg/Streamlink/Tesseract discovery and redistribution notices. Do not silently bundle GPL-affecting dependencies.
- Windows .exe / installer, macOS signed/notarized pathway assessment (signing fees may conflict with true zero-budget distribution), Linux AppImage/packaging feasibility; install/uninstall, config migration and update channel.
- Matrix smoke tests: clean machine, no Python, non-admin install, offline launch, Unicode paths, Smart/Basic fallback, antivirus/SmartScreen warnings, sleep/wake and app crash.

### LC-10 — Browser extension and Android client [P2 / not implemented]
**Goal:** client interfaces, not duplicate full server/AI implementation without necessity.
- Chrome Manifest V3 extension: user gesture + tabCapture/offscreen document for permitted tab capture, or a thin controller for localhost desktop engine. A service worker is not a 24h autonomous daemon; explain tab closure and user-interaction constraints.
- Android: first scope a **companion/review/control app** for the local PC engine; native on-device export possible with Jetpack Media3 Transformer. Device capture requires compliant permissions, foreground notifications and platform-specific review. No background bypass.
- Pairing must be explicit, with ephemeral tokens, localhost-only by default, origin protection, QR pairing if remote is later enabled; no unauthenticated LAN-wide control port.
- Test permission prompts, browser restart, process lifecycle, app backgrounding, device thermal/low-memory, upload network changes and device-specific codecs.

### LC-11 — Always-on resilience/performance/zero-budget efficiency [P0 / unverified]
**Goal:** measurable stable processing with honest capacity limits.
- Bounded work queues, CPU/GPU inference semaphores, batch ASR, low-res proxy frames, incremental hashing, avoid recomputing unchanged segments, prefer stream-copy for source, lazy encoding, enable hardware acceleration only if tested.
- Implement configurable disk budgets, soft/hard warnings, retention export/backup rules, user-owned output folders and crash-consistent manifests. Never auto-remove originals by default.
- Metrics: captured minutes, segments missing, segment finalize lag, analysis backlog duration, p50/p95 analysis time, render time, fps, CPU/RAM/GPU, disk written/hour, reconnect attempts, errors/100h, rights-check failures.
- Acceptance: 24h soak on stated hardware + network, forced power/process kill, restart and resume, low disk, slow IO, corrupt file, fallback models, orphan processes and reprocessing idempotency. Publish actual observed figures, not guaranteed SLA.

### LC-12 — Security, governance and release certification [P0 / not implemented as comprehensive gate]
**Goal:** secure, licensed, reversible and reproducible release train.
- Threat model: malicious URLs and DNS rebinding, corrupt FFmpeg media payloads, command injection, archive traversal, SQLite corruption, sensitive URL/token logging, third-party model supply-chain risk, local API CSRF, publication abuse and copyright/privacy rights.
- Dependency lockfiles, SBOM and license audit (FFmpeg LGPL/GPL configuration matters; YOLO/weights licenses may be AGPL), malware-safe model download hashes, CI dependency/security checks and update policy.
- Test pyramid: unit; synthetic pipeline integration; real provider/device permission matrix; 24h soak; human-labelled precision/recall benchmarks; adversarial media; cross-version migrations; packaging; publish sandbox; accessibility; rollback.
- Documentation: source provenance, platform support matrix, known limits, troubleshooting, consent, data retention, developer process, model cards, test evidence and release notes.
- Gate ownership: release is **Blocked** until required evidence links and acceptance fields in the Execution Ledger are checked. Review every workstream after each PR.

## 4. Data model / contracts to implement incrementally

- `StreamSession`: id, source_adapter, normalized origin (avoid saving signed URL), permission_id, started/ended_at, capture_status, epoch_id, hardware_budget.
- `Segment`: session_id, sequence, epoch_id, local_path, content_sha256, container, codec, duration_ms, source_pts_start/end, finalized_at, validation_state.
- `AnalysisJob`: idempotency_key, kind, owner_session, input_hashes, model_id/version, priority, attempt, lease_expires, state, error_code, resource_cost.
- `EvidenceEvent`: time_start/end, signal_kind, event_class, evidence_json, value, model_version, source_segment_ids, timebase, confidence_type.
- `Candidate`: time window, score components, ranking version, detection profile, overlap_group, review status, user edits, source fingerprints.
- `RenderedAsset`: source IDs, timeline recipe, target platform/aspect/codec, checksum, file path, QC results, artifact generation status.
- `RightsRecord`: source_owner/rights_basis, permission evidence reference, allowed destinations, capture/publish scope, expiry/revocation.
- `PublishJob`: asset_id, account_key_ref (not token), platform, approval_actor/time, privacy, request fingerprint, remote id, retry state, errors, receipts.

Schema versioning is mandatory. File paths and media blobs remain outside SQLite; SQLite stores references and metadata. For optional remote coordination, do not open a non-authenticated server; separate this as a later ADR.

## 5. Dependency-aware implementation order

- **Gate A: Baseline freeze** — status matrix, repeat existing tests, source fixtures, environment/version capture, defects and security audit. No feature changes until regression baseline and backups are defined.
- **Gate B: Capture + durable jobs** — LC-01, LC-11 minimum and LC-12 base controls. Capture/recovery must be stable before adding expensive inference.
- **Gate C: Dataset/evaluation harness** — labelled authorized footage, repeatable positive/negative fixtures, reviewer labels and acceptance thresholds (LC-02/03/06).
- **Gate D: Smart Intelligence** — LC-02 speech/video semantics, LC-03 first game adapter, LC-06 ranking/feedback. Report measured precision/recall before expansion.
- **Gate E: Shorts editor** — LC-04 9:16 subject tracking, LC-05 captions/transcription, export QC and accessible manual overrides.
- **Gate F: Production workstation** — LC-07 multistream and LC-09 installers; Windows-first acceptance if user's workstation is Windows, then macOS/Linux.
- **Gate G: Publishing** — LC-08 rights-first OAuth and manual-approval workflows; platform-by-platform external audit.
- **Gate H: Companion surfaces** — LC-10 Chrome/Android, starting with controller/review clients rather than duplicating heavy inference.
- **Gate I: Final certification** — LC-11 soak, LC-12 security/compliance, measured release matrix and regression/rollback. Any failing required gate => NOT RELEASED.

**Definition of Done per PR:** problem statement, exact source/feature touchpoints, design ADR, threat model delta, success/failure telemetry, deterministic tests, real environment evidence if relevant, docs, dependency/license check, rollback notes and linked ledger items. The assistant cannot assume a user's GPU, OS, provider privileges or rights; capture these as explicit evidence during the respective gates.

## 6. Evaluation targets (proposals — NOT current results)

Choose numeric acceptance thresholds *after* collecting a representative labelled baseline. At a minimum:
- Capture: timecode continuity, source-segment completeness, reconnect gap correctness and valid playback.
- Intelligence: per-class precision/recall/F1 and comparison to v2.1 heuristic baseline; human reviewer disagreement captured.
- Reframing: % of time priority subject or crucial game HUD stays in safe area, crop-jitter rate, manual correction rate.
- ASR: WER/CER per language and subtitle timing drift distributions.
- Rankings: precision@K, duplicate rate, proportion of approved highlights, missed-event rate.
- Operations: per-stream CPU/RAM/GPU, disk GB/h, analysis queue delay, recovery time and 24h error totals.
- Publishing: request-to-receipt traceability, correct privacy, zero duplicates in failure/retry tests and scoped auth.

**No throughput/accuracy/virality number is promised in advance.**

## 7. Cost, copyright and dependency decisions

- Core remains **free-to-use software**, not zero hardware cost. Paid ASR/cloud APIs, shared GPU servers, commercial embedding models and paid signing are not default requirements.
- Prefer OpenCV (Apache-2.0), ONNX Runtime (MIT), faster-whisper (MIT) and PySceneDetect (BSD-3-Clause) as *candidates*; exact dependency/model versions and model-weight license must be reviewed and pinned.
- Ultralytics software and weights have AGPL/commercial licensing constraints; no automatic adoption into this GPL-3.0 project without documented compatibility/redistribution assessment.
- FFmpeg distribution compliance depends on the *built binary and configuration*, not just the upstream project name.
- YouTube's official monetization guidance warns about reused and mass-produced content; clips remain original/authorized and must add authentic value where required.
- Mobile app storefront accounts, signing/certificates, hardware purchase and cloud upload/media hosting can carry fees; no zero-budget guarantee for those distribution paths.

## 8. Research references and review cadence

This is a **research-to-design** artifact; links below require revalidation at implementation because APIs evolve:
- Streamlink: https://streamlink.github.io/latest/
- OpenCV license: https://github.com/opencv/opencv
- ONNX Runtime license: https://github.com/microsoft/onnxruntime/blob/main/LICENSE
- PySceneDetect: https://github.com/Breakthrough/PySceneDetect
- faster-whisper: https://github.com/SYSTRAN/faster-whisper
- WhisperX alignment: https://github.com/m-bain/whisperX
- CVAT Community: https://github.com/cvat-ai/cvat
- Ultralytics licensing: https://www.ultralytics.com/license
- FFmpeg legal: https://ffmpeg.org/legal.html
- Chrome tab capture: https://developer.chrome.com/docs/extensions/reference/api/tabCapture
- Android editing: https://developer.android.com/media/implement/editing-app
- PyInstaller: https://pyinstaller.org/en/stable/
- YouTube quota: https://developers.google.com/youtube/data/determine_quota_cost
- YouTube upload: https://developers.google.com/youtube/data/reference/rest/v3/videos/insert
- YouTube developer policies: https://developers.google.com/youtube/terms/developer-policies
- YouTube monetization: https://support.google.com/youtube/answer/1311392
- Instagram platform: https://developers.facebook.com/docs/instagram-platform/
- Facebook Page videos: https://developers.facebook.com/docs/graph-api/reference/page/videos/

See [Execution Ledger](ADVANCED_EXECUTION_LEDGER.md) for granular trackable tasks and completion gates, and [Research Decision Register](ADVANCED_RESEARCH_DECISIONS.md) for rejected approaches and version-sensitive verification notes.

## 9. Preservation / memory contract

**Canonical project memory is this versioned GitHub documentation, not a presumed chat-memory write.** Before starting any next capability: re-fetch latest `main`, reconcile ledger status, read linked ADRs and existing tests, implement in a feature branch/PR, update the ledger with evidence, verify CI and report blockers. Never silently mark unimplemented or unverified work complete.