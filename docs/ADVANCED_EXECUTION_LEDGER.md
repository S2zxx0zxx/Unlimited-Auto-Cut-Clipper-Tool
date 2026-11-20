# Advanced Implementation Ledger — LiveClip Zero Smart

**Ledger:** LC-ADV-2026-11-20-v1 · **Baseline:** main `8a3db1c3` · **Scope:** 13 tracked workstreams / **120 granular tasks**

**Status key:** `TODO` = not implemented; `IN_PROGRESS` = active PR; `BLOCKED` = prerequisite missing; `IMPLEMENTED_UNVERIFIED` = code exists but acceptance not proven; `VERIFIED` = acceptance evidence linked; `N/A` = intentionally rejected with ADR. All tasks below are initially TODO, **not complete**. Work must be updated when code and evidence exist.

| ID | Requirement / required action | Status | Evidence / PR |
|---|---|---|---|
| **LC-00** | **Baseline & invariants** | **PLANNED** | See master plan |
| LC-00.01 | Re-fetch latest main commit and record version, existing features, and CI evidence | TODO | — |
| LC-00.02 | Freeze v2.1 synthetic benchmark fixtures and output checksums | TODO | — |
| LC-00.03 | Record outstanding real-provider/OS/24h gaps as UNVERIFIED | TODO | — |
| LC-00.04 | Define compatibility contract for old CLI, GUI and session folders | TODO | — |
| LC-00.05 | Inventory secrets, media-source trust boundaries and licensing | TODO | — |
| LC-00.06 | Write migration/rollback strategy before any major package refactor | TODO | — |
| LC-00.07 | Record target hardware specs and approved test footage rather than assuming them | TODO | — |
| LC-00.08 | Measure baseline CPU, RAM, disk/hour, output integrity and queue lag | TODO | — |
| **LC-01** | **Provider capture reliability** | **PLANNED** | See master plan |
| LC-01.01 | Write Streamlink provider adapter and capability-discovery contract | TODO | — |
| LC-01.02 | Implement URL scheme/host allowlist, redirects and IP-address policy with tests | TODO | — |
| LC-01.03 | Add provider error taxonomy: offline, geo, unauthorized, plugin failure and DRM | TODO | — |
| LC-01.04 | Add reconnection backoff, epochs and no-cross-gap export assertion | TODO | — |
| LC-01.05 | Probe every finalized clip and validate duration, A/V timebase and codecs | TODO | — |
| LC-01.06 | Test source end, stream quality changes and missing audio/video streams | TODO | — |
| LC-01.07 | Test graceful Ctrl+C, forced-kill/restart and corrupt segment recovery | TODO | — |
| LC-01.08 | Run authorized YouTube live acceptance with logged versions and playback proof | TODO | — |
| LC-01.09 | Run authorized Twitch live acceptance with logged versions and playback proof | TODO | — |
| LC-01.10 | Capture low-disk, slow-I/O and network-flap result matrix | TODO | — |
| **LC-02** | **Semantic intelligence** | **PLANNED** | See master plan |
| LC-02.01 | Define time-aligned event/evidence schema and strict model API | TODO | — |
| LC-02.02 | Add local VAD and speech/silence classification behind feature flag | TODO | — |
| LC-02.03 | Add transcript features (context, intent, speaker emphasis) with confidences | TODO | — |
| LC-02.04 | Add temporal visual embeddings/scene understanding as optional local model | TODO | — |
| LC-02.05 | Add laughter/cheer/reaction candidate feature with false-positive controls | TODO | — |
| LC-02.06 | Implement safe model-download hashes, license and hardware profile checks | TODO | — |
| LC-02.07 | Build explicit heuristic fallback and missing-model UX | TODO | — |
| LC-02.08 | Benchmark precision/recall/F1 per event class on held-out labelled footage | TODO | — |
| LC-02.09 | Document model cards, data provenance, hardware throughput and failure cases | TODO | — |
| **LC-03** | **Gaming adapters** | **PLANNED** | See master plan |
| LC-03.01 | Define GameAdapter interface with version, ROI and game metadata | TODO | — |
| LC-03.02 | Specify event label taxonomy: kill, multi-kill, victory, defeat, round-end, objective | TODO | — |
| LC-03.03 | Select first supported game only from authorized labelled footage | TODO | — |
| LC-03.04 | Build annotation guidelines and inter-reviewer disagreement workflow | TODO | — |
| LC-03.05 | Develop per-game HUD/killfeed/scoreboard OCR and template detection | TODO | — |
| LC-03.06 | Add temporal tracking to reduce fake overlay and spectator-view triggers | TODO | — |
| LC-03.07 | Test resolution, localization, game updates and UI layout changes | TODO | — |
| LC-03.08 | Ship adapter-level benchmark and compare with generic Gaming profile | TODO | — |
| LC-03.09 | Expand to second game only after first game measured release gate | TODO | — |
| **LC-04** | **Vertical editing/reframing** | **PLANNED** | See master plan |
| LC-04.01 | Add timeline recipe contract for 9:16, 16:9, 1:1 and safe areas | TODO | — |
| LC-04.02 | Implement deterministic center crop, blur/pad and game HUD-preserving fallback | TODO | — |
| LC-04.03 | Evaluate tracker/model license and choose compliant face/object detector | TODO | — |
| LC-04.04 | Compute subject saliency and identity tracking with confidence boundaries | TODO | — |
| LC-04.05 | Apply temporally smoothed virtual-camera path and shot-change reset | TODO | — |
| LC-04.06 | Provide facecam/gameplay split-screen layout and manual subject lock | TODO | — |
| LC-04.07 | Add crop preview, keyframe edit and manual override UI | TODO | — |
| LC-04.08 | Render H.264/AAC and optional verified hardware-encode path | TODO | — |
| LC-04.09 | Measure subject retention, HUD readability, crop jitter and video/audio sync | TODO | — |
| **LC-05** | **ASR/subtitles/translation** | **PLANNED** | See master plan |
| LC-05.01 | Define transcript segments/words and language fields in SQLite schema | TODO | — |
| LC-05.02 | Add CPU-first faster-whisper adapter with selectable model size | TODO | — |
| LC-05.03 | Integrate VAD, silence suppression and confidence warnings | TODO | — |
| LC-05.04 | Produce editable transcript and word-aligned SRT and WebVTT exports | TODO | — |
| LC-05.05 | Add subtitle styles with 9:16 safe-area checks and font licensing | TODO | — |
| LC-05.06 | Handle Hindi/Hinglish/English mixed speech, slang and Unicode shaping | TODO | — |
| LC-05.07 | Make translation optional with model/license and language-specific evaluation | TODO | — |
| LC-05.08 | Render burned-in subtitles with audio/video timestamp alignment | TODO | — |
| LC-05.09 | Measure WER/CER, word timing error and subtitle overflow from ground truth | TODO | — |
| **LC-06** | **Ranking and curation** | **PLANNED** | See master plan |
| LC-06.01 | Preserve existing heuristic score as baseline and fallback | TODO | — |
| LC-06.02 | Create multi-signal ranker incorporating semantic and game evidence | TODO | — |
| LC-06.03 | Add dynamic event context window and pre/post-roll per event class | TODO | — |
| LC-06.04 | Build cross-segment overlap graph and perceptual/audio deduplication | TODO | — |
| LC-06.05 | Build top-K diversity and per-session quality controls | TODO | — |
| LC-06.06 | Add evidence explanations and do not call raw score a probability | TODO | — |
| LC-06.07 | Capture Keep/Reject/trim feedback without silent automatic retraining | TODO | — |
| LC-06.08 | Measure precision@K, false positives, missed events and duplicate rate | TODO | — |
| LC-06.09 | Verify deterministic resume, reproducibility and user-rejected candidate behavior | TODO | — |
| **LC-07** | **Multi-stream dashboard** | **PLANNED** | See master plan |
| LC-07.01 | Define per-stream lifecycle, limits, idempotency and job priority | TODO | — |
| LC-07.02 | Move background jobs to persisted SQLite job records and leases | TODO | — |
| LC-07.03 | Implement per-stream capture isolation and independent cancellation | TODO | — |
| LC-07.04 | Add bounded workers for capture, ASR, inference and rendering | TODO | — |
| LC-07.05 | Implement progress/queue/CPU/memory/disk charts from local metrics | TODO | — |
| LC-07.06 | Add source-specific profile, output path and review queue | TODO | — |
| LC-07.07 | Test 2 authorized simultaneous streams on stated hardware | TODO | — |
| LC-07.08 | Measure hardware-constrained upper bound, blocking and queue fair scheduling | TODO | — |
| LC-07.09 | Test crash, restart, lock contention, orphan jobs and disk pressure | TODO | — |
| **LC-08** | **Publishing** | **PLANNED** | See master plan |
| LC-08.01 | Define publish asset contract with permission evidence and human approval | TODO | — |
| LC-08.02 | Add OAuth token vault in OS keychain with minimal scopes and revocation | TODO | — |
| LC-08.03 | Implement YouTube upload adapter using official API and audit requirements | TODO | — |
| LC-08.04 | Verify up-to-date YouTube upload quota & privacy constraints at implementation | TODO | — |
| LC-08.05 | Implement Instagram supported professional account publishing flow | TODO | — |
| LC-08.06 | Verify media hosting reachability and account publish limits for Meta | TODO | — |
| LC-08.07 | Implement Facebook Page/Reels publishing via supported endpoint | TODO | — |
| LC-08.08 | Add platform-specific captions, thumbnails, ratios and policy validation | TODO | — |
| LC-08.09 | Add publish-state reconciler, deduplication, retry/backoff and receipts | TODO | — |
| LC-08.10 | Test no-approval/no-rights refusal and expired/invalid permissions | TODO | — |
| LC-08.11 | Test draft/private where supported; reject prohibited mass-upload shortcuts | TODO | — |
| **LC-09** | **Desktop packaging** | **PLANNED** | See master plan |
| LC-09.01 | Create per-OS package recipe and lock deterministic dependency versions | TODO | — |
| LC-09.02 | Produce Windows standalone installer with FFmpeg/Streamlink discovery | TODO | — |
| LC-09.03 | Document executable signing and SmartScreen warnings/constraints | TODO | — |
| LC-09.04 | Produce macOS bundle on macOS runner and notarization feasibility check | TODO | — |
| LC-09.05 | Produce Linux distribution artifact and executable permissions | TODO | — |
| LC-09.06 | Add OS-matrix tests for GUI launch, basic capture and export | TODO | — |
| LC-09.07 | Check external binary redistribution and GPL/LGPL license notices | TODO | — |
| LC-09.08 | Test non-ASCII paths, unattended app crash and clean uninstall | TODO | — |
| LC-09.09 | Publish checksums, versioned release notes and rollback artifacts | TODO | — |
| **LC-10** | **Chrome/Android surfaces** | **PLANNED** | See master plan |
| LC-10.01 | Decide companion/controller vs on-device processing in architecture ADR | TODO | — |
| LC-10.02 | Define secured localhost-only API with explicit pairing and origin checks | TODO | — |
| LC-10.03 | Create Chrome MV3 UI, permissions audit and user-gesture capture lifecycle | TODO | — |
| LC-10.04 | Test tabCapture/offscreen behavior, navigation, tab close and browser restart | TODO | — |
| LC-10.05 | Build Android companion in Kotlin with file review and local connection | TODO | — |
| LC-10.06 | Evaluate native device export through Jetpack Media3 Transformer | TODO | — |
| LC-10.07 | Implement Android foreground capture only if permission/UX gates pass | TODO | — |
| LC-10.08 | Test Android thermal/memory/battery and permission revocation | TODO | — |
| LC-10.09 | Prove no publicly accessible control server or secret leakage | TODO | — |
| **LC-11** | **Performance and reliability** | **PLANNED** | See master plan |
| LC-11.01 | Implement configurable CPU/GPU worker count and backpressure | TODO | — |
| LC-11.02 | Implement disk soft/hard quotas and never-delete-source default | TODO | — |
| LC-11.03 | Cache low-resolution frame features and avoid duplicate inference | TODO | — |
| LC-11.04 | Add resource monitor and per-stage p50/p95 latency histograms | TODO | — |
| LC-11.05 | Add pause/resume and safe cancellation of rendering jobs | TODO | — |
| LC-11.06 | Perform 24-hour authorized soak test under documented hardware | TODO | — |
| LC-11.07 | Inject crash, power/network loss, disk-full and model timeout | TODO | — |
| LC-11.08 | Verify data integrity, no duplicate jobs, no orphan processes after restart | TODO | — |
| LC-11.09 | Publish sustainable streams/host and storage growth measurements | TODO | — |
| **LC-12** | **Security/legal/release** | **PLANNED** | See master plan |
| LC-12.01 | Threat model SSRF/DNS rebinding, media parsing, tokens, exports and local API | TODO | — |
| LC-12.02 | Add dependency pinning, automated vulnerability report and SBOM | TODO | — |
| LC-12.03 | Inventory ML model weights, licenses and redistribution evidence | TODO | — |
| LC-12.04 | Review FFmpeg build license and bundled external components | TODO | — |
| LC-12.05 | Implement source rights record, allowed destinations and revocation handling | TODO | — |
| LC-12.06 | Document content privacy, capture consent and logs/secrets redaction | TODO | — |
| LC-12.07 | Add accessibility/keyboard/navigation acceptance for desktop interfaces | TODO | — |
| LC-12.08 | Create test matrix for real provider, OS, AI quality and publishing | TODO | — |
| LC-12.09 | Require evidence URLs before marking tasks verified/complete | TODO | — |
| LC-12.10 | Build release rollback checklist and versioned signoff manifest | TODO | — |

## Required work package rules

1. Re-check latest `main` and this ledger **before each work package**. Create a new branch and one bounded PR per releasable feature or independent fix.
2. Each PR links exact task IDs, ADR, test commands/results, known limitations, licensing/security checks and rollback plan.
3. Do **not** switch TODO to VERIFIED merely because code is merged. A separate measured acceptance artifact must be linked.
4. Critical P0 failures block related dependent work. Do not silently skip tasks or mark entire stream complete while lower rows are TODO/BLOCKED.
5. After every PR, reconcile task statuses, update high-level feature matrix and record the then-current commit SHA.
6. Research sources and external API rules must be rechecked at execution, not inferred unchanged from this plan.
7. Keep raw private/user footage, OAuth access tokens and provider credentials **out** of public GitHub. Use synthetic fixtures, anonymized reports and secrets scanning.
8. Every user-facing status should distinguish **implemented**, **tested on synthetic fixtures**, **tested on real authorized stream**, and **release certified**.

## Release gate evidence template

```text
Task ID(s): LC-xx.yy
Feature branch / PR / merge SHA:
Build/artifact/version:
Baseline and target platform/hardware:
Synthetic test / output artifact:
Real authorized test / provider + timestamp:
Quality metrics vs previous release:
Resource budget / measured CPU, memory, GB/hour, p95:
Security/rights/licensing checks:
Known failure/limitations:
Rollback tested:
Reviewer signoff:
Status transition + timestamp:
```

## No-assumption blockers to resolve at implementation time

- Actual Windows/macOS/Linux hardware CPU/GPU/RAM and available disk.
- Creator-owned or explicitly permitted livestreams; recorded permission scope.
- First game/game version, resolution/layout, languages and labelled events.
- Supported platform account class and granted official OAuth scopes.
- Platform API review/audit/quotas and technical ability to host publisher-accessible upload media.
- Compatible model weights licenses, download sizes and runtime benchmarks.
- Whether macOS distribution signing/notarization or Play Store publication costs are acceptable.

## Frozen baseline evidence (already exists, not part of new TODO tasks)

- `src/liveclip/` exists, core features declared in README/architecture; this does **not** prove live provider acceptance.
- Linux CI for baseline main `8a3db1c3` passed project installation, compile and offline synthetic tests (GitHub Actions run 44482917018).
- Missing verified evidence: real YouTube/Twitch capture, Windows/macOS GUI, 24h soak, human-labelled precision/recall, installer distribution, official API publishing.

**Source of truth:** [Master Plan](ADVANCED_CAPABILITIES_MASTER_PLAN.md) + this ledger + [Research Decisions](ADVANCED_RESEARCH_DECISIONS.md). Do not depend on any claimed assistant memory write.
