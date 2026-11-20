# GTA Auto Clipper — pinned upstream audit and no-duplicate adoption register

**Audited source:** https://github.com/AnIntellectualBeing/GTA-Auto-Clipper at commit `a9ac2ba8b95b5a887e8ab068b8237c86bcec59a2` (2026-11-20)
**Downstream:** LiveClip Zero Smart v2.2 baseline `81413c8a3abbdbcdbf0865da5901a4b03bc635d5`
**Inventory:** 57 tracked blob files, full GitHub tree not truncated.
**Scope:** video analytics/backend. Every upstream path is accounted for below; static images, PDF, paid guide and site assets are inventoried **without claiming full visual/PDF semantic inspection**. Key Python runtime, tests, license and workflow docs were inspected. No upstream UI is ported.

## Dedup-first technical decisions

| System | Existing LiveClip + Neon | GTA source value | Integration rule |
|---|---|---|---|
| Stream capture and chunks | LiveClip has reconnect epochs, MP4 segments, SQLite and source preservation | Another standalone TS recorder, with cleanup | KEEP existing engine, never copy a second recorder |
| Media ranker | LiveClip multi-signal; Neon optional VOD optical flow/audio | Chat-first plus audio/speech reaction phrase detection | ADD identity-aware reaction evidence only; preserve baseline and existing Neon profiles |
| Live chat | Neon counts message spikes; no live reader in LiveClip | Per-user dedup, reaction bursts, TLS Twitch/YouTube API collectors | ADD spam-aware offline scoring; authenticated network collector remains gated |
| Vertical export | Neon 11 layout geometry and FFmpeg export | Third-person anchor, smoothed temporal player pan, persistent facecam avoidance | EXTEND same `liveclip-neon vertical` renderer; no parallel editor |
| Captions | Neon SRT/VTT + Whisper + styled captions modules | One-line per-word yellow pop ASS animation, profanity text mask | ADD optional caption style to existing FFmpeg path, no new ASR model |
| Auto facecam | Neon has YuNet candidate source; no downstream deployed model | YuNet/static facecam in same 320x320 detector | DO NOT copy duplicate face model; use single future detector adapter |
| Source discovery | User URL and opt-in VOD import | Live YouTube Data API search | ADD read-only candidate finder; **not** implied gameplay or content rights |
| Person tracker | None in downstream, Neon layouts are manual | OpenCV+YOLOX-S ONNX CPU detector and temporal smoothing | ADD optional **local model-path** inference, no hidden download/weights bundle |
| Publishing | Not implemented; official OAuth plan | Zernio vendor client + unattended publishing | NO direct merge into core; assess vendor costs/rights/idempotency separately |
| Security | LiveClip source URL, local file guards, no auto deletion | Creator confirmation, dry-run, test outputs | Preserve user approval/capture provenance and fail-closed publication gates |

## Source tree file-by-file disposition (57 blobs)

| Source path | Bytes | Decision | Reason |
|---|---:|---|---|
| `.gitignore` | 201 | EXISTING | Existing LiveClip ignore policy preserved; secret/media rules audited |
| `AGENTS.md` | 1667 | PROCESS REFERENCE | Editorial-rights & no-secret work instructions, not runtime code |
| `AI_WORKFLOW.md` | 2977 | PROCESS REFERENCE | Optional orchestration design, no agent automation copied |
| `GTA-CLIPPING-PROMPT.txt` | 3328 | PROCESS REFERENCE | Prompt workflow not a reusable software engine |
| `LICENSE` | 1076 | ADOPTED | Third-party MIT license copied verbatim to THIRD_PARTY_LICENSES |
| `README.md` | 8927 | RESEARCH | Feature/limit claims mapped; upstream runtime not treated as proven downstream |
| `clip.py` | 39149 | PARTIAL | Player-centered crops, framing and pop ASS captions selectively reimplemented; original recorder kept |
| `docs/MULTI-AGENT.md` | 3730 | PROCESS REFERENCE | Roles and veto patterns; platform upload cap claims not independently authoritative |
| `docs/RAZORPAY-SETUP.md` | 2507 | OUT OF SCOPE | Paid guide commerce, not video clipping engine |
| `find_streams.py` | 3013 | ADAPTED | YouTube read-only search with API key only; no auto-record/permission inference |
| `live_chat.py` | 11617 | PARTIAL | Distinct-user spam-resistant chat scoring ported; network collectors gated |
| `models/ATTRIBUTION.md` | 402 | LICENSE REVIEW | OpenCV Zoo YuNet and YOLOX-S model origins noted; weights license review separate |
| `models/face_detection_yunet_2023mar.onnx` | 232589 | EXISTING REFERENCE | YuNet binary already referenced upstream NeonClipping; do not duplicate/distribute |
| `player_track.py` | 6540 | PARTIAL | Local tracker and smoothing ported; no automatic model download; real model acceptance pending |
| `publish.py` | 684 | GATED | Alias for third-party publisher; no duplicate upload integration |
| `requirements.txt` | 69 | ADAPTED | Extra dependency groups rather than replacing pinned environment |
| `site/404.html` | 511 | OUT OF SCOPE | Marketing site UI/scripts/assets, not requested backend |
| `site/_headers` | 595 | OUT OF SCOPE | Marketing site security headers, not local app |
| `site/_redirects` | 58 | OUT OF SCOPE | Website routing, not clipping engine |
| `site/app.js` | 2987 | OUT OF SCOPE | Marketing site UI/scripts/assets, not requested backend |
| `site/automation.css` | 2260 | OUT OF SCOPE | Marketing site UI/scripts/assets, not requested backend |
| `site/download-ready.css` | 1714 | OUT OF SCOPE | Marketing site UI/scripts/assets, not requested backend |
| `site/download-ready.html` | 2281 | OUT OF SCOPE | Marketing site UI/scripts/assets, not requested backend |
| `site/functions/_lib/razorpay.mjs` | 1963 | OUT OF SCOPE | Payment integration is not clipping logic |
| `site/functions/_lib/verticalclipper.mjs` | 641 | OUT OF SCOPE | Paid delivery helpers |
| `site/functions/api/config.js` | 381 | OUT OF SCOPE | Payment/paid content delivery backend, not local clipper |
| `site/functions/api/create-order.js` | 1289 | OUT OF SCOPE | Payment/paid content delivery backend, not local clipper |
| `site/functions/api/download.js` | 1194 | OUT OF SCOPE | Payment/paid content delivery backend, not local clipper |
| `site/functions/api/verify-payment.js` | 1868 | OUT OF SCOPE | Payment/paid content delivery backend, not local clipper |
| `site/functions/api/verticalclipper/config.js` | 420 | OUT OF SCOPE | Payment/paid content delivery backend, not local clipper |
| `site/functions/api/verticalclipper/create-order.js` | 1522 | OUT OF SCOPE | Payment/paid content delivery backend, not local clipper |
| `site/functions/api/verticalclipper/download.js` | 1348 | OUT OF SCOPE | Payment/paid content delivery backend, not local clipper |
| `site/functions/api/verticalclipper/verify-payment.js` | 2129 | OUT OF SCOPE | Payment/paid content delivery backend, not local clipper |
| `site/guide-download.js` | 1591 | OUT OF SCOPE | Marketing site UI/scripts/assets, not requested backend |
| `site/images/ATTRIBUTION.md` | 465 | OUT OF SCOPE | Graphic/marketing/media asset, no reusable algorithm; independent image rights |
| `site/images/Jason_and_Lucia_01.webp` | 105900 | OUT OF SCOPE | Graphic/marketing/media asset, no reusable algorithm; independent image rights |
| `site/images/Vice_City_01.webp` | 107308 | OUT OF SCOPE | Graphic/marketing/media asset, no reusable algorithm; independent image rights |
| `site/images/Vice_City_10.webp` | 199676 | OUT OF SCOPE | Graphic/marketing/media asset, no reusable algorithm; independent image rights |
| `site/images/verticalclipper-sample-01.gif` | 2200323 | OUT OF SCOPE | Graphic/marketing/media asset, no reusable algorithm; independent image rights |
| `site/images/verticalclipper-sample-02.gif` | 1742711 | OUT OF SCOPE | Graphic/marketing/media asset, no reusable algorithm; independent image rights |
| `site/images/verticalclipper-sample-03.gif` | 1530800 | OUT OF SCOPE | Graphic/marketing/media asset, no reusable algorithm; independent image rights |
| `site/images/verticalclipper-sample.gif` | 2051750 | OUT OF SCOPE | Graphic/marketing/media asset, no reusable algorithm; independent image rights |
| `site/index.html` | 14299 | OUT OF SCOPE | UI explicitly excluded by user |
| `site/package.json` | 187 | OUT OF SCOPE | Marketing site runtime |
| `site/privacy.html` | 2039 | OUT OF SCOPE | Marketing site UI/scripts/assets, not requested backend |
| `site/refunds.html` | 1802 | OUT OF SCOPE | Marketing site UI/scripts/assets, not requested backend |
| `site/styles.css` | 11534 | OUT OF SCOPE | Marketing site UI/scripts/assets, not requested backend |
| `site/terms.html` | 2406 | OUT OF SCOPE | Marketing site UI/scripts/assets, not requested backend |
| `site/verticalclipper.css` | 7547 | OUT OF SCOPE | Marketing site UI/scripts/assets, not requested backend |
| `site/verticalclipper.js` | 2530 | OUT OF SCOPE | Marketing site UI/scripts/assets, not requested backend |
| `site/verticalclipper/index.html` | 12942 | OUT OF SCOPE | Paid guide/marketing UI excluded |
| `tests/__init__.py` | 0 | NOT NEEDED | No unique runtime algorithm |
| `tests/site/razorpay.test.mjs` | 4362 | OUT OF SCOPE | Site/payment validation, not app acceptance |
| `tests/test_clipper.py` | 9090 | TEST REFERENCE | Adapted framing/caption behavior tested in LiveClip's own suite |
| `tests/test_live_chat.py` | 1601 | TEST REFERENCE | Anti-spam scoring and collector-fallback cases inform LiveClip tests |
| `tests/test_publisher.py` | 1307 | GATED | Zernio publishing tests do not prove account permission |
| `zernio_publish.py` | 7719 | GATED | Third-party publishing, API pricing/credentials and quota; rights/approval review required |

## Implemented in this PR (acceptance to be validated in CI)

- `gta_adopt/framing.py`: MIT-credited gameplay anchor, facecam-offset evidence heuristic, validated smoothing and FFmpeg temporal keyframe pan; explicit opt-in.
- `gta_adopt/player_detector.py`: optional ONNX CPU person detector from local user-supplied model; no automatic downloads. GPU and real GTA accuracy not measured.
- `gta_adopt/captions.py`: timed, non-overlapping ASS yellow spoken-word animation; same caption position and optional text-only profanity mask; treats transcript as text, not ASS instructions.
- `gta_adopt/chat_reactions.py`: distinct-user capped/reaction burst rank; no network chat login/credential handling added.
- `gta_adopt/discovery.py`: explicit read-only YouTube live search using `YOUTUBE_API_KEY`; not live-concurrent-viewer ranking and **not** recording permission.
- `neon_adopt/cli.py`: extends existing `liveclip-neon vertical` with --gta-player-anchor, --pan-keys-json, --track-player-model, --pop-words-json, plus chat-reactions and discover-live; preserves all earlier CLI verbs.
- Third-party MIT notice retained as `THIRD_PARTY_LICENSES/GTA-Auto-Clipper-MIT.txt`.

## Unimplemented / intentionally gated

1. **Live chat collector → session timebase → finalized segment → automatic chat-triggered exports.** Upstream timestamps derived from last-modified file time, which is not proof of exact transport PTS or reconnect epoch; do not silently copy it.
2. **Automatic facecam inference** still unintegrated into the existing renderer. Neon and GTA both use YuNet; one audited model layer should supersede both, not duplicate.
3. **YOLOX model download and real player detection** requires independently verified model checksum/license, CPU/RAM acceptance, GTA test fixtures; new tracker is code-only opt-in pending model acceptance.
4. **Animated pop-caption aesthetics on real footage** require multiple languages, font coverage, spoken-word sync, safe areas and libass support verification.
5. **Zernio publisher** is a third-party service (API, credential, pricing, consent and quota risks). Not a zero-budget guaranteed official YouTube/Meta publisher; never assume allowed without account review.
6. **YouTube search/chat API** requires an authorized API project/key; quota costs and current policy require verification. Discovery never triggers recording or posting.
7. **Multi-stream sender/veto automation** and scheduled publishing require existing durable job manager, rights records, license provenance and manual approval; not provided by importing code.
8. **Source rights and privacy**: direct creator permission or self-owned footage, no DRM/auth bypass, user control over recordings. Copyright notice for source code does not license any gameplay/video/audio.
9. **Distribution**: no new UI, Chrome/Android binary, bundled proprietary model, signing or platform integration in this PR.
10. **Quality**: heuristic AI candidate rank ≠ reliable game-event recognition; no precision/recall, real livestream soak or platform upload success asserted here.

## Acceptance and regression protocol

- Must preserve existing `liveclip-zero` recorder, GUI, reconnect epoch logic and SQLite. Only new explicit opt-in flags affect FFmpeg output.
- CI: package install; compile; all existing tests; new pure unit tests for player anchor, smoothing, anti-spam chat and ASS events; synthetic FFmpeg 720x1280 static/motion crop and caption burn.
- Model integration acceptance is **blocked** pending actual trusted ONNX weights and authorized example gameplay. Real YouTube API/search likewise unverified without an API project.
- Security: no arbitrary network address from browser, no silent secret logging, no auto-deletion, no auto-posting, no dynamic code evaluation, model download is opt-in manual and source text escaped before ASS.
- Release gate must record measured CPU/RAM, correction/false-positive rates, actual frame crop tests, simulated network loss and 24h video test before claiming complete product parity.

## Maintainable source-of-truth rule

Prior integrations: LiveClip base (v2.1), NeonClipping MIT (v2.2), GTA Auto Clipper MIT (v2.3 candidate).
For each newly proposed upstream repo: pin its SHA, inventory every tracked file, compare features against current `main` and this register, identify exactly **one authoritative implementation per capability**, retain license/notice, add a bounded adapter and tests, update master ledger, and gate merge on the latest CI. Prefer the better demonstrated implementation, not the largest codebase or an unverified "power" claim.

Never mark a pending capability VERIFIED solely because this adoption PR merges.
