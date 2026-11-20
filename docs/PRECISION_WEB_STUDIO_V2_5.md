# Precision Moments + 5-minute exports + private Web Studio — research and release gates

Status: v2.5 implementation candidate. Not a claim of trained racing-event recognition.
Audited baseline: S2zxx0zxx/Unlimited-Auto-Cut-Clipper-Tool commit 82577899ae5ba917906fd2f566440fb9e5b61614.
Constraints: zero-paid-API local-first, user's Windows Ryzen laptop, 16 GB RAM, no mandatory game models, preserved original MP4, permitted sources only.

## 1. Root cause of arbitrary cuts

- signals.py/score_signals: one-second loudness-onset, scene, motion, brightness measurements; outputs three strongest raw peaks per 30/60-second source segment. It does not understand race goals, overtake, chase, or victory.
- pipeline.py/render_highlight: a fixed length around a single peak using 40% lead and 60% trail, regardless of action start/finish.
- neon_adopt/highlights.py/rank: seven-second averaged local activity maximum, followed by fixed-duration clip. Previously fell back to the opening of a video even when there was no evidence.
- Live selection capped at 60s; local VOD at 180s; explicit single-file vertical rendering already had longer duration capacity. Need consistent up-to-five-minutes across interfaces.
- Source recording uses FFmpeg GOP/keyframe segmentation, NOT semantic events. Final selected clips require re-encoding for accurate start/end. Source https://ffmpeg.org/ffmpeg-formats.html

## 2. Research-backed architecture decisions

- Shot transition detection (PySceneDetect adaptive/content detector) identifies scene boundaries, not complete gameplay semantics: https://www.scenedetect.com/docs/latest/
- Event boundary research separates onset, ongoing action, and completion from simple shot changes: https://openaccess.thecvf.com/content/ICCV2025/papers/Jung_Online_Generic_Event_Boundary_Detection_ICCV_2025_paper.pdf
- A single sound spike or edit flash must not manufacture a highlight. Score independent modalities with temporal persistence; reject low-evidence proposals, detect sustained intervals and preserve bounded context.
- Five minutes is an UPPER LIMIT, not a forced clip duration. A 19s meaningful event should yield a shorter clip, not 281s filler.
- Game-specific race/mission outcome recognition requires authorized annotated gameplay and validated local models; no inferred accuracy or untested recognition claims.

## 3. This PR's implementation

| Component | Implemented scope | Caveat |
|---|---|---|
| Time-aligned interval finder | Conservative temporal grouping with independent evidence, variable boundaries, deduplication | Activity evidence, not semantic racing detector |
| Local candidate pipeline | Optional precision mode, no random video-start fallback, 15..300s cap | No moment may be selected |
| Live highlight pipeline | Configurable 15/30/45/60/90/120/180/300s, corroboration requirement; multi-peak evidence for long clip | Not race-state classification |
| Live recorder | Unmodified 30/60s finalized source segments, reconnect epoch isolation | Requires provider support and rights |
| Desktop GUI | Maximum duration options and precision checkbox for live/local | 16GB RAM does not guarantee speed at 4K |
| Private localhost UI | Live start/stop, local VOD processing, status, media preview, all via existing engines | No external user access or cloud render |
| Local security | Bind 127.0.0.1, per-process token, exact Host, same Origin, JSON-only authenticated writes | Additional on-device security testing pending |
| Windows one-click | START_WEB_STUDIO.vbs reuses existing .venv, fixes FFmpeg PATH in child process, opens browser | First-time prerequisites still require installation |
| Output | MP4 files retained; no automated publishing | Review scene and creator permission before posting |

## 4. Architecture in sequence

Authorized live URL -> Streamlink -> source recordings in 30/60s keyframe segments -> validated audio/visual evidence -> event-onset/active/end interval proposal -> dedup -> bounded 15..300s highlight -> same-epoch FFmpeg re-encode H264/AAC -> local preview -> human review -> file remains on disk.

For local VOD: use existing optical-flow/rms/shout/cut extractor; precision proposals bound exports to evidence. Do not create arbitrary highlight if no strong event. Existing heuristic mode stays accessible for manual experimentation, not labeled as accurate.

## 5. Follow-up stages — NOT IMPLEMENTED / NOT CERTIFIED

B1. Authorized labeled GTA/racing footage, negative examples, camera/facecam variations, lap marker and race start/end annotations.
B2. Game HUD ROI detection (speed, checkpoint, lap progress, finish/result), multi-frame trajectory tracking, camera movement rejection.
B3. Temporal action state machine: setup -> chase/overlap/crash -> resolution; distinguish outcomes from camera cuts.
B4. Optional Whisper Hindi/Hinglish transcript/speech markers and OCR, measured sync, checksum/license-verified local weights.
B5. Optional free trained event model / calibrated multimodal scorer and explanations; avoid unverified confidence claims.
B6. Smart reframing with player and HUD protected, visual preview and adjustable event boundaries; cross-platform fonts/captions.
B7. Measure annotated event precision, recall, false clips/hour, meaningful event-boundary tolerance, A/V sync, negative scene avoidance.
B8. Windows H264/AAC source/preview compatibility on Windows Media Player, browser and MX Player, 300s synthetic FFmpeg test.
B9. Real authenticated permitted YouTube/Twitch streaming, 24-hour soak, reconnect, corrupt segment handling, low-disk, force-close/restart.
B10. Real Ryzen 5/16GB CPU and disk benchmarks, update/install and repeated-launch acceptance, security review incl DNS rebinding, CSRF and file-range requests.
B11. Full durable job queue, cancel/resume, multiple streams and one-to-many publishing remain separate future features; don't silently duplicate services.
B12. Strict original clip preservation, code-license notices, source-rights gates and manual review.

## 6. User workflow

After GitHub PR merges, update project source inside existing C:\Unlimited-Auto-Cut-Clipper-Tool-main folder while retaining the Python 3.12 .venv and all previous video/output files. Double-click START_WEB_STUDIO.vbs; browser opens automatically at a private localhost address. Choose Local Shorts to test a short owned clip or Live Capture for an authorized actually-live stream. Select MAX duration (15..300), enable Precision, START and STOP + FINISH, preview the resulting file. No repeated terminal access after initial setup.

No one-click interface fixes the absence of semantic game models. Do not mark perfect race accuracy, all-device playback or continuous production as verified from Linux synthetic tests alone.
