"""Opt-in NeonClipping-derived backend workflows. No UI, accounts or cloud service.

Core v2.1 capture and smart segmentation are deliberately unchanged.
Source attribution: docs/NEONCLIPPING_ADOPTION.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

from . import aiparts, curation, layouts, subtitles
from .chat_hype import analyze_bucket

FFMPEG_TIMEOUT = 900
MAX_SINGLE_CLIP_SECONDS = 600
MAX_VOD_SECONDS = 4 * 3600


def _media_info(source: Path) -> dict:
    if not source.is_file():
        raise ValueError(f"Video not found: {source}")
    tool = shutil.which("ffprobe")
    if not tool:
        raise RuntimeError("ffprobe is required. Install FFmpeg and add it to PATH.")
    proc = subprocess.run([tool, "-v", "error", "-show_entries", "format=duration",
                           "-show_entries", "stream=codec_type,width,height",
                           "-of", "json", str(source)], capture_output=True, text=True, timeout=40)
    if proc.returncode:
        raise RuntimeError("ffprobe could not read the media: " + proc.stderr[-500:])
    data = json.loads(proc.stdout)
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    if not video:
        raise ValueError("A video stream is required.")
    duration = float(data.get("format", {}).get("duration") or 0)
    if not math.isfinite(duration) or duration < 0.25:
        raise ValueError("Source duration could not be measured.")
    return {"duration": duration, "width": int(video["width"]), "height": int(video["height"])}


def _box(text: str | None, width: int, height: int, label: str) -> tuple[int, int, int, int]:
    if text is None:
        return (0, 0, width, height)
    try:
        x, y, w, h = (int(s.strip()) for s in text.split(","))
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be x,y,width,height in source pixels") from None
    if min(x, y) < 0 or min(w, h) < 2 or x + w > width or y + h > height:
        raise ValueError(f"{label} box is outside the {width}x{height} source")
    return x, y, w, h


def _captions_for_clip(track: Path | None, start: float, end: float) -> str:
    if not track:
        return ""
    if not track.is_file() or track.stat().st_size > 4_000_000:
        raise ValueError("Caption track is missing or exceeds 4 MB")
    source = track.read_text(encoding="utf-8-sig")
    cues = subtitles.cues(source)
    local = [
        {"start": round(max(start, a) - start, 3),
         "end": round(min(end, b) - start, 3), "text": text}
        for a, b, text in cues if min(end, b) - max(start, a) >= .05
    ]
    if not local:
        return ""
    return subtitles.write_track(local, "srt", duration=end - start + .01, allow_overlap=True)


def verticalize(
    source: Path,
    destination: Path,
    *,
    start: float = 0,
    duration: float | None = None,
    layout: str = "blur",
    aspect: str = "vertical",
    resolution: int = 720,
    face_size: float = .32,
    cam_box: str | None = None,
    game_box: str | None = None,
    captions_file: Path | None = None,
    burn_captions: bool = False,
    fps: int = 30,
    overwrite: bool = False,
    gta_player_anchor: float | None = None,
    pan_keys_file: Path | None = None,
    track_model_file: Path | None = None,
    pop_words_file: Path | None = None,
    pop_language: str = "en",
    censor_captions: bool = False,
    credit: str = "",
) -> dict:
    """Render one bounded clip from existing source media; never delete the source."""
    source = Path(source).expanduser().resolve()
    dest = Path(destination).expanduser().resolve()
    if source == dest:
        raise ValueError("Input and output must differ.")
    if dest.exists() and not overwrite:
        raise FileExistsError(f"Output exists, pass --overwrite to replace: {dest}")
    info = _media_info(source)
    if not math.isfinite(float(start)) or start < 0 or start >= info["duration"]:
        raise ValueError("Start must be within the video.")
    if duration is None:
        duration = min(60.0, info["duration"] - start)
    if not math.isfinite(float(duration)) or not .25 <= duration <= MAX_SINGLE_CLIP_SECONDS:
        raise ValueError(f"Duration must be between .25 and {MAX_SINGLE_CLIP_SECONDS} seconds.")
    duration = min(float(duration), info["duration"] - start)
    if duration < .25:
        raise ValueError("No video remains after start.")
    if fps not in (24, 30, 60):
        raise ValueError("Supported fps values: 24, 30 or 60.")
    dest.parent.mkdir(parents=True, exist_ok=True)
    width, height, _ = layouts.output_settings({"aspect": aspect, "resolution": resolution, "fps": fps})
    mode = layouts.geometry(layout, face_size, width, height)
    if any(layer["source"] == "cam" for layer in mode["layers"]) and cam_box is None:
        raise ValueError("Selected layout requires --cam-box=x,y,w,h to avoid guessing camera position.")
    rects = [_box(cam_box, info["width"], info["height"], "Camera"),
             _box(game_box, info["width"], info["height"], "Gameplay")]
    graph = layouts.render_graph(layout, rects, face_size, width, height)
    if gta_player_anchor is not None or pan_keys_file is not None or track_model_file is not None:
        from liveclip.gta_adopt.framing import bounded, fill_filter, read_pan_keys
        if layout != "fill" or aspect != "vertical" or cam_box or game_box:
            raise ValueError("GTA pan mode requires --layout fill --aspect vertical and no manual boxes")
        if pan_keys_file is not None and track_model_file is not None:
            raise ValueError("Choose only one of --pan-keys-json and --track-player-model")
        anchor = bounded(gta_player_anchor if gta_player_anchor is not None else .38)
        keys = read_pan_keys(pan_keys_file, duration) if pan_keys_file else None
        if track_model_file is not None:
            try:
                from liveclip.gta_adopt.player_detector import track_player
                keys = track_player(source, float(start), float(duration),
                                    track_model_file.expanduser().resolve())
            except ImportError as exc:
                raise RuntimeError("Install the optional tracker: pip install -e '.[gta]'") from exc
        graph = fill_filter(width, height, anchor=anchor, keys=keys)
    srt = _captions_for_clip(captions_file, start, start + duration) if captions_file else ""
    if pop_words_file is not None and burn_captions:
        raise ValueError("Choose either standard SRT burn-in or pop-word captions, not both.")
    if burn_captions and not srt:
        raise ValueError("--burn-captions needs a valid --captions-file overlapping this clip.")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is not installed.")
    temp_output = dest.parent / (f".{dest.stem}.{uuid.uuid4().hex}.partial.mp4")
    sidecar = dest.with_suffix(".srt")
    try:
        with tempfile.TemporaryDirectory(prefix="liveclip-vertical-") as temp:
            if srt:
                Path(temp, "captions.srt").write_text(srt, encoding="utf-8")
            suffix = ",subtitles=captions.srt" if burn_captions else ""
            if pop_words_file is not None:
                from liveclip.gta_adopt.captions import load_words, ass_text
                pop_words = load_words(pop_words_file)
                pop_script = ass_text(pop_words, clip_start=start, duration=duration,
                                      width=width, height=height, language=pop_language,
                                      censor=censor_captions, credit=credit)
                Path(temp, "captions.ass").write_text(pop_script, encoding="utf-8")
                suffix = ",ass=captions.ass"
            vf = f"{graph};[base]{'fps=' + str(fps) + ',' if fps else ''}format=yuv420p{suffix}[outv]"
            cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                   "-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", str(source),
                   "-filter_complex", vf, "-map", "[outv]", "-map", "0:a?",
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                   "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                   "-movflags", "+faststart", str(temp_output)]
            proc = subprocess.run(cmd, cwd=temp, stdout=subprocess.DEVNULL,
                                  stderr=subprocess.PIPE, timeout=FFMPEG_TIMEOUT)
            if proc.returncode or not temp_output.exists() or temp_output.stat().st_size < 500:
                msg = proc.stderr.decode("utf-8", "replace")[-2000:]
                raise RuntimeError("FFmpeg vertical render failed: " + msg)
        output_info = _media_info(temp_output)
        if output_info["width"] != width or output_info["height"] != height:
            raise RuntimeError("Output resolution mismatch.")
        os.replace(temp_output, dest)
        if srt:
            sidecar.write_text(srt, encoding="utf-8")
        return {"file": str(dest), "seconds": round(output_info["duration"], 2),
                "width": width, "height": height, "layout": layout,
                "captions_sidecar": str(sidecar) if srt else None,
                "captions_burned": bool((burn_captions and srt) or pop_words_file is not None),
                "caption_engine": "gta-popup" if pop_words_file is not None else ("srt" if burn_captions else "none"),
                "gta_pan_mode": bool(gta_player_anchor is not None or pan_keys_file is not None or track_model_file is not None),
                "player_model_requested": track_model_file is not None,
                "player_tracking_applied": bool(keys) if (gta_player_anchor is not None or pan_keys_file is not None or track_model_file is not None) else False,
                "source_preserved": True}
    finally:
        temp_output.unlink(missing_ok=True)


def _read_json(path: Path):
    if not path.is_file() or path.stat().st_size > 20_000_000:
        raise ValueError("Input JSON missing or exceeds 20 MB.")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _atomic_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name("." + path.name + "." + uuid.uuid4().hex + ".partial")
    try:
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="liveclip-neon",
                                     description="Optional MIT-derived backend workflows for LiveClip Zero Smart")
    sub = parser.add_subparsers(dest="command", required=True)
    vertical = sub.add_parser("vertical", help="Render one 9:16/square/landscape clip without a web UI")
    vertical.add_argument("source", type=Path)
    vertical.add_argument("output", type=Path)
    vertical.add_argument("--start", type=float, default=0)
    vertical.add_argument("--duration", type=float)
    vertical.add_argument("--layout", choices=[x[0] for x in layouts.CATALOG], default="blur")
    vertical.add_argument("--aspect", choices=list(layouts.ASPECTS), default="vertical")
    vertical.add_argument("--resolution", type=int, choices=[720, 1080, 2160], default=720)
    vertical.add_argument("--face-size", type=float, default=.32)
    vertical.add_argument("--cam-box")
    vertical.add_argument("--game-box")
    vertical.add_argument("--captions-file", type=Path)
    vertical.add_argument("--burn-captions", action="store_true")
    vertical.add_argument("--fps", type=int, choices=[24, 30, 60], default=30)
    vertical.add_argument("--overwrite", action="store_true")
    vertical.add_argument("--gta-player-anchor", type=float, help="Opt-in third-person anchor, normally 0.38; requires fill vertical")
    vertical.add_argument("--pan-keys-json", type=Path, help="Opt-in normalized player motion keyframes, source-relative to clip")
    vertical.add_argument("--track-player-model", type=Path, help="Opt-in local YOLOX ONNX model file; no auto-download")
    vertical.add_argument("--pop-words-json", type=Path, help="Absolute word-timed source transcript, adds yellow pop captions")
    vertical.add_argument("--pop-language", choices=["en", "hinglish"], default="en")
    vertical.add_argument("--censor-captions", action="store_true", help="Optional mask sensitive words in text only")
    vertical.add_argument("--credit", default="", help="Optional editorial source credit")

    vod = sub.add_parser("vod", help="Analyze a local VOD and export top candidate clips vertically")
    vod.add_argument("source", type=Path)
    vod.add_argument("folder", type=Path)
    vod.add_argument("--count", type=int, default=3)
    vod.add_argument("--seconds", type=int, default=30)
    vod.add_argument("--profile", choices=list(curation.PROFILES), default="balanced")
    vod.add_argument("--layout", choices=[x[0] for x in layouts.CATALOG], default="blur")
    vod.add_argument("--cam-box")
    vod.add_argument("--game-box")
    vod.add_argument("--captions-file", type=Path)
    vod.add_argument("--burn-captions", action="store_true")
    vod.add_argument("--resolution", type=int, choices=[720, 1080], default=720)
    vod.add_argument("--no-motion", action="store_true")
    vod.add_argument("--smart", action="store_true", help="Optional transcript-aware scoring with local Ollama")
    vod.add_argument("--words-json", type=Path, help="Full source word transcript from the transcribe command")
    vod.add_argument("--gta-player-anchor", type=float, help="Optional GTA player anchor for --layout fill")
    vod.add_argument("--pop-captions", action="store_true", help="Use --words-json to burn per-word ASS captions")
    vod.add_argument("--pop-language", choices=["en", "hinglish"], default="en")

    asr = sub.add_parser("transcribe", help="Transcribe local source to word JSON and SRT (optional local speech model)")
    asr.add_argument("source", type=Path)
    asr.add_argument("output_base", type=Path, help="Output stem, e.g. transcript/my_video")
    asr.add_argument("--start", type=float, default=0)
    asr.add_argument("--seconds", type=float)
    asr.add_argument("--language", choices=["en", "hi", "hinglish"])
    asr.add_argument("--model", default="small", help="Explicit faster-whisper model name or local path")

    vod_url = sub.add_parser("vod-url", help="Authorized public VOD URL -> local source -> candidate shorts")
    vod_url.add_argument("url")
    vod_url.add_argument("folder", type=Path)
    vod_url.add_argument("--i-have-rights", action="store_true", help="Confirm ownership or recording permission")
    vod_url.add_argument("--count", type=int, default=3)
    vod_url.add_argument("--seconds", type=int, default=30)
    vod_url.add_argument("--profile", choices=list(curation.PROFILES), default="balanced")
    vod_url.add_argument("--max-gib", type=float, default=5.0)
    vod_url.add_argument("--no-motion", action="store_true")

    captions = sub.add_parser("captions-convert", help="Validate SRT/VTT and rewrite as SRT/VTT")
    captions.add_argument("source", type=Path)
    captions.add_argument("output", type=Path)
    captions.add_argument("--format", choices=["srt", "vtt"], default="srt")

    parts = sub.add_parser("transcript-parts", help="Prepare timestamped transcript prompts for manual review")
    parts.add_argument("words_json", type=Path)
    parts.add_argument("output", type=Path)
    parts.add_argument("--title", default="The video")
    parts.add_argument("--duration", type=float, required=True)
    parts.add_argument("--parts", type=int)
    parts.add_argument("--per-part", type=int, default=3)

    curate = sub.add_parser("curate-json", help="Select diverse candidate clips from a ranked JSON array")
    curate.add_argument("candidates_json", type=Path)
    curate.add_argument("output", type=Path)
    curate.add_argument("--count", type=int, default=5)
    curate.add_argument("--profile", choices=list(curation.PROFILES), default="balanced")

    chat = sub.add_parser("chat-score", help="Score read-only chat message counts (ten-second buckets)")
    chat.add_argument("--history", required=True, help="Comma-separated previous bucket counts")
    chat.add_argument("--current", type=int, required=True)
    chat.add_argument("--recent-30", type=int)

    chat_distinct = sub.add_parser("chat-reactions", help="Rank source-relative chat windows with spam-resistant per-user reactions")
    chat_distinct.add_argument("messages_json", type=Path)
    chat_distinct.add_argument("--window", type=int, default=30)
    chat_distinct.add_argument("--step", type=int, default=10)

    live_search = sub.add_parser("discover-live", help="Read-only YouTube live search; never confirms rights/gameplay")
    live_search.add_argument("query")
    live_search.add_argument("--max", type=int, default=25)
    return parser


def main(argv=None) -> int:
    args = _argparser().parse_args(argv)
    try:
        if args.command == "vod-url":
            from .source_download import download_public_vod
            folder = args.folder.expanduser().resolve()
            media = download_public_vod(args.url, folder / "sources",
                                        authorized=args.i_have_rights, max_gib=args.max_gib)
            child = ["vod", media["path"], str(folder / "highlights"), "--count", str(args.count),
                     "--seconds", str(args.seconds), "--profile", args.profile]
            if args.no_motion:
                child.append("--no-motion")
            return main(child)
        if args.command == "vertical":
            result = verticalize(args.source, args.output, start=args.start, duration=args.duration,
                                 layout=args.layout, aspect=args.aspect, resolution=args.resolution,
                                 face_size=args.face_size, cam_box=args.cam_box, game_box=args.game_box,
                                 captions_file=args.captions_file, burn_captions=args.burn_captions,
                                 fps=args.fps, overwrite=args.overwrite,
                                 gta_player_anchor=args.gta_player_anchor,
                                 pan_keys_file=args.pan_keys_json,
                                 track_model_file=args.track_player_model,
                                 pop_words_file=args.pop_words_json,
                                 pop_language=args.pop_language,
                                 censor_captions=args.censor_captions,
                                 credit=args.credit)
        elif args.command == "vod":
            if not 1 <= args.count <= 12 or not 10 <= args.seconds <= 180:
                raise ValueError("VOD supports 1–12 clips of 10–180 seconds each.")
            if args.pop_captions and not args.words_json:
                raise ValueError("--pop-captions requires --words-json.")
            if args.pop_captions and args.burn_captions:
                raise ValueError("Choose either --pop-captions or --burn-captions.")
            if args.gta_player_anchor is not None and args.layout != "fill":
                raise ValueError("--gta-player-anchor requires --layout fill.")
            info = _media_info(args.source)
            if info["duration"] > MAX_VOD_SECONDS:
                raise ValueError("VOD exceeds 4-hour resource safety limit in this release.")
            try:
                from .highlights import rank
            except ImportError as error:
                raise RuntimeError("Install optional VOD dependencies: pip install -e '.[neon]'") from error
            if args.smart:
                if args.words_json is None:
                    raise ValueError("--smart requires --words-json (transcribe first or import an authorized transcript).")
                words_data = _read_json(args.words_json)
                words = words_data.get("words") if isinstance(words_data, dict) else words_data
                if not isinstance(words, list) or not words or len(words) > 150_000:
                    raise ValueError("Transcript must be a nonempty word list (max 150,000).")
                from .smart import find
                chosen, engine = find(str(args.source), info["duration"], args.count, args.seconds,
                                      lambda *ignored: None, words=words, motion=not args.no_motion,
                                      profile=args.profile)
            else:
                candidates = rank(str(args.source), info["duration"], count=min(30, args.count * 4),
                                  length=args.seconds, motion_on=not args.no_motion)
                for candidate in candidates:
                    candidate["rank"] = float(candidate.get("score", 0)) / 100
                chosen = curation.select(candidates, args.count, args.profile)
                engine = "activity heuristics only"
            folder = args.folder.expanduser().resolve()
            folder.mkdir(parents=True, exist_ok=True)
            outputs = []
            for number, candidate in enumerate(chosen, 1):
                file = folder / f"highlight_{number:02}.mp4"
                clip = verticalize(args.source, file, start=float(candidate["start"]),
                                   duration=float(candidate["end"]) - float(candidate["start"]),
                                   layout=args.layout, cam_box=args.cam_box, game_box=args.game_box,
                                   captions_file=args.captions_file, burn_captions=args.burn_captions,
                                   resolution=args.resolution,
                                   gta_player_anchor=args.gta_player_anchor,
                                   pop_words_file=args.words_json if args.pop_captions else None,
                                   pop_language=args.pop_language)
                outputs.append({**candidate, "asset": clip})
            result = {"source": str(args.source), "mode": engine,
                      "outputs": outputs, "notice": "Candidate ranking, not a calibrated virality probability"}
            _atomic_json(folder / "candidates.json", result)
        elif args.command == "transcribe":
            info = _media_info(args.source)
            length = min(args.seconds if args.seconds is not None else MAX_VOD_SECONDS,
                         info["duration"] - args.start)
            if not 0 <= args.start < info["duration"] or not 0 < length <= MAX_VOD_SECONDS:
                raise ValueError("Transcription must be within source and at most four hours per request.")
            try:
                from .captions import transcribe
            except ImportError as exc:
                raise RuntimeError("Install local transcription dependencies: pip install -e '.[speech]'") from exc
            base = args.output_base.expanduser().resolve()
            base.parent.mkdir(parents=True, exist_ok=True)
            cache = base.parent / ".asr_cache"
            cache.mkdir(exist_ok=True)
            words = []
            language = args.language
            # Bounded ASR windows: process at most five minutes of audio at a time.
            # Upstream ASR emits timestamps RELATIVE to the selected window.
            end = args.start + length
            at = args.start
            while at < end - .001:
                stop = min(end, at + 300.0)
                response = transcribe(args.source.expanduser().resolve(), at, stop, cache,
                                      language=args.language, model=args.model)
                for item in response.get("words") or []:
                    start = float(item["start"]) + at
                    finish = min(end, float(item["end"]) + at)
                    if start < finish:
                        words.append({"start": round(start, 3), "end": round(finish, 3),
                                      "text": str(item["text"])})
                language = response.get("language", language)
                at = stop
            if not words:
                raise ValueError("No words detected; check the audio or import an existing subtitle track.")
            words.sort(key=lambda w: w["start"])
            out_json = base.with_suffix(".words.json")
            out_srt = base.with_suffix(".srt")
            _atomic_json(out_json, {"words": words, "language": language, "duration": info["duration"],
                                    "range_start": args.start, "range_end": end,
                                    "source": str(args.source.expanduser().resolve())})
            items = [{"start": float(w["start"]), "end": float(w["end"]), "text": str(w["text"])}
                     for w in words]
            out_srt.write_text(subtitles.write_track(items, "srt", duration=end + .1,
                                                       allow_overlap=True), encoding="utf-8")
            result = {"words": len(words), "language": language,
                      "transcript_json": str(out_json), "subtitles": str(out_srt)}
        elif args.command == "captions-convert":
            source = args.source.read_text(encoding="utf-8-sig")
            if len(source) > 4_000_000:
                raise ValueError("Caption input exceeds 4 MB")
            cues = subtitles.parse_track(source, allow_overlap=True)
            result = {"cues": len(cues), "output": str(args.output)}
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(subtitles.write_track(cues, args.format, allow_overlap=True), encoding="utf-8")
        elif args.command == "transcript-parts":
            words_data = _read_json(args.words_json)
            words = words_data.get("words") if isinstance(words_data, dict) else words_data
            if not isinstance(words, list) or not 0 < len(words) <= 150_000:
                raise ValueError("Expected a nonempty JSON array of timestamped words")
            if not math.isfinite(args.duration) or args.duration <= 0:
                raise ValueError("Duration must be positive")
            if args.parts is not None and not 1 <= args.parts <= aiparts.MAX_PARTS:
                raise ValueError("Parts must be 1–40")
            if not 1 <= args.per_part <= 10:
                raise ValueError("per-part must be 1–10")
            chunks = aiparts.split(args.title, words, args.duration, args.parts, args.per_part)
            result = {"parts": chunks, "notice": "Prompts require manual human review; no service called"}
            _atomic_json(args.output, result)
        elif args.command == "curate-json":
            clips = _read_json(args.candidates_json)
            if not isinstance(clips, list) or not 1 <= args.count <= 30:
                raise ValueError("Provide a JSON list and count 1–30")
            for c in clips:
                if not isinstance(c, dict) or not all(k in c for k in ("start", "end", "rank")):
                    raise ValueError("Each candidate needs start, end and rank")
            result = curation.select(clips, args.count, args.profile)
            _atomic_json(args.output, result)
        elif args.command == "chat-reactions":
            from liveclip.gta_adopt.chat_reactions import score_chat_windows
            messages = _read_json(args.messages_json)
            if not isinstance(messages, list) or len(messages) > 4000:
                raise ValueError("Expected no more than 4000 timestamped chat messages")
            if not 5 <= args.window <= 120 or not 5 <= args.step <= args.window:
                raise ValueError("Choose a 5–120 second window and step up to that window")
            latest = max((float(m.get("t", 0)) for m in messages if isinstance(m, dict)), default=0)
            if not math.isfinite(latest) or latest > 14400 or latest < 0:
                raise ValueError("Chat session must fit in a four-hour source timeline")
            starts = [float(t) for t in range(0, max(1, int(latest) + 1), args.step)][:120]
            result = {"windows": score_chat_windows(messages, starts, args.window),
                      "privacy": "Aggregated chat scores only; usernames and messages are not exported"}
        elif args.command == "discover-live":
            from liveclip.gta_adopt.discovery import find_live
            key = os.environ.get("YOUTUBE_API_KEY", "")
            result = {"candidates": find_live(args.query, key, args.max),
                      "warning": "Search results are NOT permission or gameplay verification"}
        elif args.command == "chat-score":
            history = [int(item.strip()) for item in args.history.split(",") if item.strip()]
            if len(history) > 30:
                history = history[-30:]
            result = vars(analyze_bucket(args.current, history, args.recent_30))
        else:
            raise ValueError("Unsupported action")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, RuntimeError, OSError, PermissionError, ImportError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        print(f"LiveClip Neon: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
