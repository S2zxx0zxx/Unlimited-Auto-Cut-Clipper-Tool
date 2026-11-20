# NeonClipping backend adoption audit

**Upstream:** https://github.com/iamajmeena/neonclipping  
**Pinned SHA:** 2632cade8e92b016314ac0e2b69b78e5f08a75d2  
**Checked:** 2026-11-20  
**LiveClip baseline:** v2.1.0  
**Change type:** Opt-in backend additions, not a replacement of current capture/GUI.

## License / provenance

NeonClipping is MIT-licensed (Copyright 2026 Ajay K Meena and contributors). The complete permission notice and warranty disclaimer are retained in THIRD_PARTY_LICENSES/NeonClipping-MIT.txt, with per-file attribution comments. The surrounding LiveClip project remains GPL-3.0-only; do not remove MIT notices. Standalone video, optional model weights, FFmpeg and other components have distinct licensing obligations. Media permissions are a separate question from open-source code permissions.

## Feature mapping, accurate as of this adoption

| Feature | NeonClipping upstream | LiveClip adopted outcome |
|---|---|---|
| Livestream recorder | Yes | Existing LiveClip recorder preserved |
| 30/60-second source segments | Alternative live recorder | Existing LiveClip segments preserved |
| Motion/audio optical flow | Yes | Optional local VOD scoring |
| Transcript + optional local Ollama | Yes | Optional transcript-aware VOD CLI; LLM reads text only |
| Vertical 9:16 and alternative aspect layouts | 11 layouts | 11 imported layout geometries + FFmpeg renderer |
| Webcam/game composition | Yes | Explicit camera/game source boxes, not auto-detected |
| Facecam detector (YuNet) | Yes | NOT integrated (model/binary rights and real QA pending) |
| SRT/VTT captions | Yes | Local caption conversion, sidecar, optional FFmpeg burn-in |
| Local Whisper ASR | Yes | Opt-in chunked local speech transcription (optional weight download) |
| Hindi/Hinglish transliteration | Yes | Imported and callable via transcription, not quality-certified |
| Fast VOD selective downloader | Yes | NOT integrated; local files only |
| YouTube timed JSON3 caption parser | Yes | Imported library; not wired for arbitrary remote URL fetch |
| AI manual transcript parts | Yes | CLI prompt-part library; human handoff required |
| Chat hype/spike | Yes | Offline scoring core; no live chat connection yet |
| Chat-triggered live clipping | Yes | NOT connected to recorder timeline |
| Creator automatic online watcher | Yes | NOT integrated |
| Native layouts / branded caption animation | Yes | Only geometry: animation/styling NOT integrated |
| Saved clip re-edit without rediscovery | Yes | NOT integrated |
| 1–5 star adaptive learning | Yes | Algorithm imported; feedback UI/storage integration pending |
| Persistent scheduler queue | Partial | NOT integrated; needs durable leasing and crash policy |
| Phone LAN remote | Yes (web) | NOT integrated; security review required |
| Native Android | No | No |
| Real social auto publishing | No | No |
| Game-specific trained kill detector | No | No |
| Verified 24h production operation | Not proven for our hardware | Not proven |

The word "imported" never means a tested, working end-to-end feature. The above excludes upstream UI and platform publishing. No part is guaranteed "viral".

## Architecture boundary

- Existing: LiveClip GUI/CLI -> Streamlink -> FFmpeg original segments -> SQLite + heuristic highlight exporter. UNCHANGED.
- Added: opt-in liveclip-neon -> MIT-derived backend library in src/liveclip/neon_adopt -> local FFmpeg.
- No background cloud service, no LAN listener, no browser extension, no new OAuth credential or automatic deletion.
- The optional VOD ranker processes audio in per-second PCM chunks (instead of reading an entire long video into memory), caps optical-flow workers at four, and must still be benchmarked against original quality.
- Raw URL downloading or fetching subtitle links from untrusted JSON is not exposed by the new CLI.
- Output files are distinct from source recordings; when a file exists, refuse overwrite unless explicitly requested.

## Install / use

Python 3.10+ and FFmpeg with ffprobe on PATH. Existing START_WINDOWS.bat and liveclip-zero commands are unchanged.

Install base:  pip install -e .

Install optional VOD video scoring:  pip install -e '.[neon]'

Install optional speech-to-text:  pip install -e '.[speech]'

Install all local extras:  pip install -e '.[all]'

New CLI: liveclip-neon --help

### Video conversion

Make a vertical short from an authorized local source:

    liveclip-neon vertical video.mp4 short.mp4 --start 120 --duration 45 --layout blur

11 supported layouts: stack, bottom, blur, fill, game, pip_tl, pip_tr, pip_bl, pip_br, circle, side.
For camera layouts, the source camera rectangle MUST be supplied. No guessed facecam location:

    liveclip-neon vertical video.mp4 short.mp4 --layout stack --cam-box 1200,40,650,400 --game-box 0,0,1920,1080

The default output is 720x1280. Option --resolution 1080 makes 1080x1920. The source path and output path must differ.

### Clip ranking and short rendering

    liveclip-neon vod video.mp4 output_clips --count 3 --seconds 30 --profile balanced

Requires optional [neon] extras. The ranker is heuristic, not trained gameplay event recognition.

### Captions / transcript

    liveclip-neon captions-convert source.srt converted.vtt --format vtt

    liveclip-neon vertical video.mp4 short.mp4 --captions-file captions.srt --burn-captions

Burn-in requires an FFmpeg binary built with libass support; otherwise use SRT sidecars.

    liveclip-neon transcribe video.mp4 transcript --language hi --model small

Transcription is explicitly opt-in and may download model weights. It processes up to four hours in 300-second bounded windows and writes .words.json and .srt.

    liveclip-neon vod video.mp4 ai_clips --count 3 --seconds 30 --smart --words-json transcript.words.json

Optional transcript scoring may use a local Ollama text model if installed, with non-LLM fallback. This does not recognize visual gameplay events.

Manual-review transcript prompts require a JSON ARRAY of word objects; the transcribe command outputs an object containing the array under the "words" field. Extract it before calling transcript-parts. Workflow auto-chaining remains pending.

    liveclip-neon transcript-parts words_array.json prompts.json --duration 5400 --title "Authorized stream"

### Chat hype without network access

    liveclip-neon chat-score --history 2,2,2,2,2,2,2,2,2,2 --current 50 --recent-30 80

This analyzes aggregate counts only; it does not connect to Twitch or YouTube chat and does not create a highlight automatically.

## QA evidence and release gates

- GitHub Actions Linux runs existing tests and new synthetic FFmpeg tests for vertical output, source preservation, caption conversion, geometry, chat-scoring and curation.
- Separate smoke tests exercise optional NumPy/OpenCV VOD ranker and smart module import.
- CI passing does not establish quality on real provider streams, Windows/macOS native GUIs, accuracy on Hindi speech, model license reviews, 24-hour endurance or API publishing.
- Re-run tests for each adapted dependency/runtime. Keep a measured CPU/RAM/disk-throughput and precision-vs-recall report.
- Never copy upstream automatic source cleanup into LiveClip; existing user source clips must stay intact.
- LAN phone access cannot be enabled until authenticated local API, CSRF/origin protection and review.
- Social platform mass publishing and bypass of quotas/DRM/auth access are out of scope.

## Follow-up integration tasks that remain NOT DONE

1. Secure live chat ingestion, stream timeline/epoch mapping and chat-spike triggered clip creation.
2. YuNet facecam detector with model license audit, source frame validation and manual override.
3. Caption animation/style rendering, transcript editor and saved-clip batch re-rendering.
4. Durable job scheduling, creator watch, live-status detection and bounded concurrent streams.
5. Fast source VOD download + official platform caption fetching with URL policy and permission evidence.
6. Safety-reviewed local phone controller, no globally open control endpoint.
7. Real provider/OS acceptance and hard-soak benchmarking; per-game semantic accuracy study.
8. Source-inclusive build/installer and platform publishing with manual approval.
9. Integrate imported learning/curation feedback into existing SQLite metadata with explicit user choice.

Canonical full future requirements are in docs/ADVANCED_CAPABILITIES_MASTER_PLAN.md and the 120-task docs/ADVANCED_EXECUTION_LEDGER.md. Each new workstream must update the ledger only with measurable evidence; no undocumented completion flags.
