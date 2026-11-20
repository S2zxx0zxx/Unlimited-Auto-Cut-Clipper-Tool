"""GTA-oriented framing controls; safety-hardened MIT adaptation.

Derived concepts: gameplay_crop_offset, pick_player, smooth_path and pan curve
from AnIntellectualBeing/GTA-Auto-Clipper @ a9ac2ba8b95b5a887e8ab068b8237c86bcec59a2
Copyright (c) 2026 AnIntellectualBeing; MIT notice in
THIRD_PARTY_LICENSES/GTA-Auto-Clipper-MIT.txt.
Player tracking is an optional heuristic, NOT game-event recognition.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import median
from typing import Sequence


def bounded(value: float, low: float = 0.0, high: float = 1.0) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("Non-finite position")
    return max(low, min(high, value))


def gameplay_crop_offset(frame_width: int, frame_height: int, player_x: float | None = None) -> float:
    """Offset 0..1 aligning the gameplay crop to desired horizontal subject pixel."""
    if frame_width <= 0 or frame_height <= 0:
        raise ValueError("Frame width and height must be positive")
    crop_width = frame_height * 9.0 / 16.0
    available = frame_width - crop_width
    if available <= 0:
        return .5
    anchor = (frame_width * .38) if player_x is None else float(player_x)
    return bounded((anchor - crop_width / 2) / available)


def choose_crop_offset(frame_width: int, frame_height: int,
                       face_samples: Sequence[Sequence[tuple[float, float, float, float]]],
                       anchor: float = .38) -> float:
    """Favor player position; move away from a STABLE edge facecam only.

    In-game faces should not trigger a camera pan. Without enough evidence keep
    the chosen player anchor. Caller decides whether this heuristic applies.
    """
    anchor = bounded(anchor)
    base = gameplay_crop_offset(frame_width, frame_height, frame_width * anchor)
    if frame_width <= 0 or frame_height <= 0 or not face_samples:
        return base
    plausible = []
    for sample in face_samples:
        candidates = [box for box in sample if len(box) == 4
                      and 0 < box[2] < frame_width * .12
                      and 0 < box[3] < frame_height * .22
                      and (box[1] + box[3] * .5 < frame_height * .25
                           or box[1] + box[3] * .5 > frame_height * .75)]
        if len(candidates) == 1:
            plausible.append(candidates[0])
    if len(plausible) < max(3, math.ceil(len(face_samples) * .6)):
        return base
    midx = median([b[0] + b[2] * .5 for b in plausible])
    midy = median([b[1] + b[3] * .5 for b in plausible])
    if any(abs(b[0] + b[2] * .5 - midx) > frame_width * .04
           or abs(b[1] + b[3] * .5 - midy) > frame_height * .06 for b in plausible):
        return base
    crop_width = frame_height * 9 / 16
    available = frame_width - crop_width
    if available <= 0:
        return .5
    half_cam = 1.5 * median([b[2] for b in plausible])
    cam_l, cam_r = midx - half_cam, midx + half_cam
    left, right = available * base, available * base + crop_width
    if cam_r <= left or cam_l >= right:
        return base
    new_x = cam_r if midx < frame_width * anchor else cam_l - crop_width
    return bounded(new_x / available)


def pick_player(people: Sequence[Sequence[float]], width: int, height: int,
                previous_x: float | None = None) -> float | None:
    """Return likely third-person player center, normalized; not a certainty."""
    if width <= 0 or height <= 0:
        raise ValueError("Invalid frame dimensions")
    best, best_cost = None, None
    for person in people:
        if len(person) < 5:
            continue
        x, y, w, h, score = (float(z) for z in person[:5])
        if not all(map(math.isfinite, (x, y, w, h, score))) or w <= 0 or h < height * .12:
            continue
        cx, cy = (x + w / 2) / width, (y + h / 2) / height
        if not .12 <= cx <= .88:
            continue
        cost = abs(cx - .45) * 1.2 + abs(cy - .6) * .6 - h / height * 1.5
        if previous_x is not None:
            cost += abs(cx - bounded(previous_x)) * 1.5
        if best_cost is None or cost < best_cost:
            best, best_cost = cx, cost
    return best


def smooth_path(times: Sequence[float], positions: Sequence[float | None],
                default: float = .5, max_speed: float = .12) -> list[float]:
    """Median suppresses spurious detections; speed caps avoid camera jumps."""
    if len(times) != len(positions) or not times:
        raise ValueError("Need equal nonempty frame times and positions")
    if not 0 < max_speed <= 1:
        raise ValueError("max_speed must be within (0,1]")
    ts = [float(t) for t in times]
    if not all(map(math.isfinite, ts)) or any(b <= a for a, b in zip(ts, ts[1:])):
        raise ValueError("Times must be finite and strictly increasing")
    filled, last = [], None
    for item in positions:
        if item is not None:
            last = bounded(item)
        filled.append(last)
    first = next((x for x in filled if x is not None), bounded(default))
    filled = [first if x is None else x for x in filled]
    med = [float(median(filled[max(0, i-1):min(len(filled), i+2)]))
           for i in range(len(filled))]
    output = [med[0]]
    for i in range(1, len(med)):
        step = max_speed * (ts[i] - ts[i-1])
        output.append(bounded(output[-1] + max(-step, min(step, med[i] - output[-1]))))
    return output


def read_pan_keys(path: Path, duration: float, *, max_points: int = 96) -> list[tuple[float, float]]:
    """Read explicitly provided normalized positions; fail closed on malformed path."""
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Invalid duration")
    if not path.is_file() or path.stat().st_size > 50_000:
        raise ValueError("Pan JSON missing or too large")
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("pan_keys")
    if not isinstance(data, list) or not 2 <= len(data) <= max_points:
        raise ValueError("Expected 2..96 [seconds, normalized_x] points")
    times, positions = [], []
    for row in data:
        if not isinstance(row, (tuple, list)) or len(row) != 2:
            raise ValueError("Expected [seconds, normalized_x] pairs")
        t, x = float(row[0]), bounded(row[1])
        if not math.isfinite(t) or not 0 <= t <= duration:
            raise ValueError("Pan timestamp outside clip")
        times.append(t); positions.append(x)
    return list(zip(times, smooth_path(times, positions)))


def pan_x_expr(keys: Sequence[tuple[float, float]], output_width: int) -> str:
    """Escaped expression for FFmpeg crop x based on linear temporal interpolation."""
    if not keys or len(keys) > 96 or output_width <= 0:
        raise ValueError("Provide 1..96 pan keyframes and output width")
    def x_at(p: float) -> str:
        return f"(iw*{bounded(p):.5f}-{output_width / 2:.2f})"
    expr = x_at(keys[-1][1])
    for (start, p0), (end, p1) in reversed(list(zip(keys, keys[1:]))):
        if end <= start:
            raise ValueError("Pan keyframes must be increasing")
        interpolated = f"({x_at(p0)}+({x_at(p1)}-{x_at(p0)})*(t-{start:.3f})/{end-start:.3f})"
        expr = f"if(lt(t\\,{end:.3f})\\,{interpolated}\\,{expr})"
    return f"max(0\\,min(iw-{output_width}\\,{expr}))"


def fill_filter(width: int, height: int, anchor: float = .5,
                keys: Sequence[tuple[float, float]] | None = None) -> str:
    """Return FFmpeg video filter graph producing [base] for vertical gameplay."""
    if width <= 0 or height <= 0 or width % 2 or height % 2:
        raise ValueError("Output dimensions must be positive and even")
    x = pan_x_expr(keys, width) if keys else f"max(0\\,min(iw-{width}\\,iw*{bounded(anchor):.5f}-{width / 2:.2f}))"
    return (f"[0:v]setpts=PTS-STARTPTS,scale={width}:{height}:force_original_aspect_ratio=increase:"
            f"force_divisible_by=2,crop={width}:{height}:'{x}':(ih-{height})/2,setsar=1[base]")
