"""Local-only, deterministic highlight detection. No cloud, model, or paid API.

Signals are intentionally *heuristics*, not semantic understanding. All timestamps
are measured on finalized media segments. Untrusted media is decoded only by FFmpeg.
"""
from __future__ import annotations

from array import array
from dataclasses import asdict, dataclass
import json
import math
import re
import shutil
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Callable

VIDEO_WIDTH = 160
VIDEO_HEIGHT = 90
FRAME_BYTES = VIDEO_WIDTH * VIDEO_HEIGHT
VIDEO_FPS = 2
AUDIO_RATE = 8000
FFMPEG_TIMEOUT = 120
MAX_SEGMENT_DURATION = 120  # live recorder uses 30/60s; cap untrusted offline files

PROFILES = {
    # audio surge, onset, movement, scene cuts, flash
    "Balanced": (.32, .23, .23, .14, .08),
    "Gaming": (.26, .22, .30, .12, .10),
    "Sports": (.31, .24, .21, .14, .10),
    "Reaction": (.39, .30, .14, .10, .07),
    "Podcast": (.45, .35, .10, .06, .04),
}
KEYWORD_RE = re.compile(r"\b(?:VICTORY|WINNER|HEADSHOT|ELIMINAT(?:ED|ION)|GAME\s+OVER|LEVEL\s+UP|ROUND\s+WON|CHICKEN\s+DINNER|MATCH\s+WON|ACE|GOAL)\b", re.I)


@dataclass
class MediaInfo:
    seconds: float
    audio: bool
    video: bool


@dataclass
class Peak:
    at: float
    score: float
    reasons: list[str]
    signals: dict[str, float]
    ocr_matches: list[str]


def _run(command: list[str], timeout: int = FFMPEG_TIMEOUT, stdin: bytes | None = None) -> bytes:
    proc = subprocess.run(command, input=stdin, capture_output=True, timeout=timeout, check=False)
    if proc.returncode:
        raise RuntimeError(f"Media process failed: {proc.stderr.decode('utf-8', 'replace')[-500:]}")
    return proc.stdout


def _exe(name: str) -> str:
    binary = shutil.which(name)
    if not binary:
        raise RuntimeError(f"{name} executable was not found in PATH")
    return binary


def probe_video(file: Path) -> MediaInfo:
    if not file.is_file() or file.stat().st_size < 100:
        raise ValueError(f"Not a complete media file: {file}")
    raw = _run([_exe('ffprobe'), '-v', 'error', '-show_entries', 'format=duration:stream=codec_type,duration',
                '-of', 'json', str(file)], timeout=25)
    data = json.loads(raw)
    streams = data.get('streams', [])
    raw_duration = (data.get('format') or {}).get('duration')
    try:
        seconds = float(raw_duration)
    except (ValueError, TypeError):
        seconds = max((float(s.get('duration', 0)) for s in streams if s.get('duration')), default=0)
    if not (0 < seconds <= MAX_SEGMENT_DURATION) or not math.isfinite(seconds):
        raise ValueError(f"Segment duration must be >0 and <= {MAX_SEGMENT_DURATION}s (got {seconds})")
    video = any(s.get('codec_type') == 'video' for s in streams)
    audio = any(s.get('codec_type') == 'audio' for s in streams)
    if not video:
        raise ValueError('Segment has no video stream')
    return MediaInfo(seconds, audio, video)


def audio_levels(file: Path, duration: float) -> list[float]:
    """RMS dBFS in 1-second buckets. -90 for silence. No audio => [] (handled upstream)."""
    raw = _run([_exe('ffmpeg'), '-hide_banner', '-loglevel', 'error', '-nostdin',
                '-i', str(file), '-vn', '-map', '0:a:0', '-ac', '1', '-ar', str(AUDIO_RATE),
                '-t', str(min(duration, MAX_SEGMENT_DURATION)), '-f', 's16le', 'pipe:1'])
    out = []
    for idx in range(0, len(raw), AUDIO_RATE * 2):
        block = array('h')
        block.frombytes(raw[idx:idx + AUDIO_RATE * 2 - ((len(raw[idx:idx + AUDIO_RATE * 2])) % 2)])
        if sys.byteorder != 'little':
            block.byteswap()
        if not block:
            continue
        mean_square = sum(sample * sample for sample in block) / len(block)
        out.append(max(-90.0, 10 * math.log10(max(mean_square, 1) / (32768**2))))
    return out


def video_levels(file: Path, duration: float) -> tuple[list[float], list[float], list[float]]:
    """Motion (frame MAD), scene-cut strength, brightness-jump strength per second."""
    raw = _run([_exe('ffmpeg'), '-hide_banner', '-loglevel', 'error', '-nostdin',
                '-i', str(file), '-an', '-t', str(min(duration, MAX_SEGMENT_DURATION)),
                '-vf', f'fps={VIDEO_FPS},scale={VIDEO_WIDTH}:{VIDEO_HEIGHT},format=gray',
                '-f', 'rawvideo', 'pipe:1'])
    n = len(raw) // FRAME_BYTES
    bucket_count = max(1, math.ceil(duration))
    motion = [[] for _ in range(bucket_count)]
    cuts = [[] for _ in range(bucket_count)]
    flashes = [[] for _ in range(bucket_count)]
    previous = None
    previous_brightness = None
    # memoryview avoids duplicating the raw video buffer; ~2MB/min @ 160x90/2fps.
    view = memoryview(raw)
    for j in range(n):
        frame = view[j * FRAME_BYTES:(j + 1) * FRAME_BYTES]
        brightness = sum(frame) / (FRAME_BYTES * 255)
        bucket = min(bucket_count - 1, j // VIDEO_FPS)
        if previous is not None:
            distance = sum(abs(a - b) for a, b in zip(frame, previous)) / (FRAME_BYTES * 255)
            motion[bucket].append(distance)
            cuts[bucket].append(distance if distance > .24 else 0.0)
            flashes[bucket].append(abs(brightness - previous_brightness))
        previous, previous_brightness = frame, brightness
    return ([max(x, default=0) for x in motion],
            [max(x, default=0) for x in cuts],
            [max(x, default=0) for x in flashes])


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def score_signals(audio: list[float], motion: list[float], cuts: list[float],
                  flashes: list[float], profile: str) -> list[dict[str, object]]:
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile: {profile}")
    count = max(len(audio), len(motion), len(cuts), len(flashes))
    if not count:
        return []
    active_audio = [x for x in audio if x > -75]
    audio_baseline = statistics.median(active_audio) if active_audio else -90
    motion_baseline = statistics.median(motion) if motion else 0
    weights = PROFILES[profile]
    out = []
    for i in range(count):
        db = audio[min(i, len(audio) - 1)] if audio else -90
        prev = audio[max(0, i - 1)] if audio and i else db
        active = db > -70 and bool(audio)
        surge = clamp((db - audio_baseline - 2) / 15) if active else 0
        onset = clamp((db - prev - 3) / 15) if active else 0
        current_motion = motion[i] if i < len(motion) else 0
        movement = clamp((current_motion - motion_baseline - .025) / .16)
        scene = clamp(((cuts[i] if i < len(cuts) else 0) - .21) / .35)
        flash = clamp(((flashes[i] if i < len(flashes) else 0) - .10) / .35)
        values = (surge, onset, movement, scene, flash)
        # For silent / video-only sources, redistribute audio weights to video.
        adjusted = weights
        if not active_audio:
            video_sum = sum(weights[2:])
            adjusted = (0, 0, *(v / video_sum for v in weights[2:]))
        score = 100 * sum(a * b for a, b in zip(values, adjusted))
        reasons = [name for name, value in zip(
            ('audio_surge', 'audio_onset', 'rapid_motion', 'scene_change', 'brightness_flash'), values
        ) if value >= .45]
        out.append({'at': i + .5, 'score': round(score, 1), 'reasons': reasons,
                    'signals': {k: round(v, 3) for k, v in zip(
                        ('audio_surge', 'audio_onset', 'motion', 'scene', 'flash'), values)}})
    return out


def ocr_keywords(file: Path, at: float) -> list[str]:
    """Optional Tesseract local OCR; bounded to one frame per candidate."""
    if not shutil.which('tesseract'):
        return []
    try:
        png = _run([_exe('ffmpeg'), '-hide_banner', '-loglevel', 'error', '-nostdin',
                    '-ss', str(max(0.0, at)), '-i', str(file), '-frames:v', '1',
                    '-vf', 'scale=960:-2', '-f', 'image2pipe', '-vcodec', 'png', 'pipe:1'], timeout=20)
        raw = _run([_exe('tesseract'), 'stdin', 'stdout', '--psm', '11'], timeout=15, stdin=png)
        return sorted(set(m.group(0).upper() for m in KEYWORD_RE.finditer(raw.decode('utf-8', 'replace'))))[:5]
    except (RuntimeError, subprocess.TimeoutExpired, OSError):
        return []


def analyze_segment(file: Path, profile: str = 'Gaming',
                    ocr: bool = False, max_peaks: int = 3, min_separation: int = 8) -> tuple[MediaInfo, list[Peak]]:
    info = probe_video(file)
    a = audio_levels(file, info.seconds) if info.audio else []
    motion, cuts, flashes = video_levels(file, info.seconds)
    seconds = score_signals(a, motion, cuts, flashes, profile)
    # Cheap visual/audio analysis runs on all seconds. Optional OCR also samples
    # the time axis so static victory banners are not missed when they appear
    # without a loud audio event or big scene change.
    if ocr and shutil.which('tesseract'):
        times: set[float] = set()
        for point in sorted(seconds, key=lambda p: p['score'], reverse=True)[:max_peaks + 1]:
            times.add(float(point['at']))
        times.update(float(t) for t in range(2, math.ceil(info.seconds), 5))
        for at in sorted(times):
            matches = ocr_keywords(file, at)
            if matches:
                bucket = max(0, min(len(seconds) - 1, int(at)))
                point = seconds[bucket]
                # OCR-only events should qualify even when audio is quiet.
                point['score'] = min(100.0, max(point['score'], 36) + 15)
                point['reasons'] = list(dict.fromkeys([*point['reasons'], 'screen_text']))
                point['ocr_matches'] = list(dict.fromkeys([*point.get('ocr_matches', []), *matches]))
    selected: list[dict] = []
    for point in sorted(seconds, key=lambda p: p['score'], reverse=True):
        if len(selected) >= max_peaks:
            break
        if all(abs(point['at'] - p['at']) >= min_separation for p in selected):
            selected.append(point)
    peaks = [Peak(float(p['at']), float(round(p['score'], 1)),
                  list(p['reasons']), dict(p['signals']), list(p.get('ocr_matches', [])))
             for p in sorted(selected, key=lambda p: p['at'])]
    return info, peaks
