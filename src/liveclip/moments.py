"""Conservative time-aligned moment proposals from LOCAL observable signals.

A moment is an interval with accumulating evidence, not a fixed-duration slice
centered on an arbitrary maximum. All values here are normalized 0..1 signals.
This cannot identify actual races/wins/kill events without separate vision models.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

MAX_HIGHLIGHT_SECONDS = 300
LENGTH_OPTIONS = (15, 30, 45, 60, 90, 120, 180, 300)


@dataclass(frozen=True)
class Moment:
    start: float
    end: float
    peak: float
    score: float
    evidence: tuple[str, ...]
    confidence: str = "activity-evidence-only"


def _limited(values, size):
    if len(values) == 0:
        return [0.0] * size
    return [min(1.0, max(0.0, float(values[i]))) if i < len(values) and
            math.isfinite(float(values[i])) else 0.0 for i in range(size)]


def propose_moments(motion, loud, shout, cuts, *,
                    maximum_seconds: int = 60, count: int = 4,
                    min_duration: int = 3, gap_seconds: int = 4,
                    minimum_strength: float = .27) -> list[Moment]:
    """Detect *intervals*, corroborate evidence and reject weak/noisy media.

    Motion and cuts are a single visual modality, loud/shout a single audio one.
    Silent videos need sustained visual motion; a single scene cut is insufficient.
    Boundary lead-in/tail preserve context within the selected maximum.
    This is deliberately a conservative heuristic, not trained event semantics.
    """
    if maximum_seconds not in LENGTH_OPTIONS:
        raise ValueError("Choose a supported maximum clip length (15–300 seconds)")
    if not 1 <= count <= 30 or not 2 <= min_duration <= 30:
        raise ValueError("Invalid candidate or event duration budget")
    n = max(len(motion), len(loud), len(shout), len(cuts))
    if n <= 0 or n > 4 * 3600 + 1:
        return []
    m, a, h, c = [_limited(x, n) for x in (motion, loud, shout, cuts)]
    evidence = []
    magnitude = []
    for i in range(n):
        # An isolated cut (or very short one-off audio spike) is not an event.
        visual = min(1., m[i] * .85 + c[i] * .15)
        audio = min(1., a[i] * .65 + h[i] * .35)
        # No multimodal inference from correlated features alone.
        corroborated = visual >= .17 and audio >= .17
        sustained_visual = visual >= .54 and (
            (i > 0 and .85 * m[i-1] + .15 * c[i-1] >= .25) or
            (i + 1 < n and .85 * m[i+1] + .15 * c[i+1] >= .25))
        sustained_audio = audio >= .62 and (
            (i > 0 and .65 * a[i-1] + .35 * h[i-1] >= .35) or
            (i + 1 < n and .65 * a[i+1] + .35 * h[i+1] >= .35))
        strong = (corroborated and visual + audio >= .47 or
                  sustained_visual or sustained_audio)
        evidence.append(strong)
        magnitude.append(.55 * visual + .45 * audio)
    active = [i for i, is_active in enumerate(evidence) if is_active]
    if not active:
        return []
    groups = []
    current = [active[0]]
    for i in active[1:]:
        if i - current[-1] <= gap_seconds:
            current.append(i)
        else:
            groups.append(current)
            current = [i]
    groups.append(current)

    candidates: list[Moment] = []
    for group in groups:
        if len(group) < min_duration:
            continue
        left, right = group[0], group[-1] + 1
        peak = max(group, key=lambda i: magnitude[i])
        activity = sum(magnitude[i] for i in group) / len(group)
        if activity < minimum_strength or magnitude[peak] < minimum_strength + .04:
            continue
        hints = []
        for name, values in (("visual_motion", m), ("audio_surge", a),
                             ("vocal_energy", h), ("scene_transitions", c)):
            if max(values[i] for i in group) >= .23:
                hints.append(name)
        # Adaptive boundaries: never stretch a weak 12-second event into five
        # minutes of filler merely because the user chose 'up to 5 minutes'.
        lead = min(8, max(2, int(len(group) * .14)))
        tail = min(9, max(2, int(len(group) * .15)))
        start = max(0, left - lead)
        end = min(n, right + tail)
        if end - start > maximum_seconds:
            # Keep the strongest portion but retain setup before the peak.
            start = max(start, min(peak - int(maximum_seconds * .40),
                                   end - maximum_seconds))
            end = min(end, start + maximum_seconds)
        if end - start < min_duration:
            continue
        candidates.append(Moment(float(start), float(end), float(peak) + .5,
                                 round(100 * activity, 1), tuple(hints)))
    candidates.sort(key=lambda x: (-x.score, -len(x.evidence), x.start))
    selected = []
    for candidate in candidates:
        if any(max(0., min(candidate.end, old.end) - max(candidate.start, old.start)) >
               .20 * min(candidate.end - candidate.start, old.end - old.start)
               for old in selected):
            continue
        selected.append(candidate)
        if len(selected) >= count:
            break
    return sorted(selected, key=lambda x: x.start)


def candidate_window(peak: float, neighbours: list[float], *,
                     limit: int, epoch_start: float, epoch_end: float) -> tuple[float, float] | None:
    """Bound a *live* highlight to corroborating activity evidence in one epoch.

    Long clips (>60s) require multiple distinct timestamps separated in time.
    Returning None is preferable to making an arbitrary five-minute cut.
    """
    if limit not in LENGTH_OPTIONS or epoch_end <= epoch_start:
        raise ValueError("Invalid epoch or highlight duration")
    points = sorted(set(float(x) for x in [peak, *neighbours]
                        if math.isfinite(float(x)) and epoch_start <= x <= epoch_end
                        and abs(x - peak) <= limit * .62))
    if limit > 60 and (len(points) < 3 or points[-1] - points[0] < min(25., limit * .23)):
        return None
    if limit <= 60:
        start = max(epoch_start, peak - min(10., limit * .30))
        end = min(epoch_end, start + limit)
        return (start, end) if end - start >= min(5., limit) else None
    start = max(epoch_start, points[0] - 7)
    end = min(epoch_end, points[-1] + 9)
    if end - start > limit:
        start = max(start, min(peak - limit * .4, end - limit))
        end = min(end, start + limit)
    return (start, end) if end - start >= 20 else None
