"""Chat-velocity scoring without copying NeonClipping's network or deletion code.

Derived from the MIT-licensed live_session.py spike/hype rules in
iamajmeena/neonclipping @ 2632cade8e92b016314ac0e2b69b78e5f08a75d2.
Inputs are trusted timestamped message COUNTS, not user messages.
"""

from dataclasses import dataclass
from math import isfinite
from statistics import mean, pstdev

BUCKET_SECONDS = 10
HISTORY_BUCKETS = 30
MIN_NONEMPTY_HISTORY = 6
MIN_SPIKE_MESSAGES = 8
SPIKE_SIGMA = 2.5
SPIKE_RATIO = 2.5


@dataclass(frozen=True)
class HypeResult:
    current: int
    usual: float
    is_spike: bool
    score: int
    label: str
    sufficient_history: bool


def is_spike(count: int, history: list[int]) -> bool:
    if not isinstance(count, int) or count < 0:
        raise ValueError("count must be a non-negative integer")
    if any(not isinstance(x, int) or x < 0 for x in history):
        raise ValueError("history values must be non-negative integers")
    if sum(bool(x) for x in history) < MIN_NONEMPTY_HISTORY:
        return False
    mu = mean(history)
    sigma = pstdev(history) or 1.0
    return count >= MIN_SPIKE_MESSAGES and count > mu + SPIKE_SIGMA * sigma and count >= SPIKE_RATIO * max(mu, 1.0)


def hype_percent(messages_last_30s: int, baseline_per_bucket: float, history_buckets: int = 30) -> int:
    if not isinstance(messages_last_30s, int) or messages_last_30s < 0:
        raise ValueError("messages_last_30s must be a non-negative integer")
    if not isfinite(baseline_per_bucket) or baseline_per_bucket < 0 or history_buckets < 0:
        raise ValueError("invalid baseline")
    if history_buckets < 3:
        return max(0, min(100, round(100 * messages_last_30s / 150)))
    usual_30 = max(3 * baseline_per_bucket, 6)
    return max(0, min(100, round(100 * messages_last_30s / (4 * usual_30))))


def classify_hype(score: int) -> str:
    if score < 25:
        return "quiet"
    if score < 50:
        return "building"
    if score < 80:
        return "hot"
    return "peak"


def analyze_bucket(count: int, history: list[int], recent_30: int | None = None) -> HypeResult:
    recent = count if recent_30 is None else recent_30
    usual = mean(history[-HISTORY_BUCKETS:]) if history else 0
    score = hype_percent(recent, usual, len(history))
    ready = sum(bool(x) for x in history[-HISTORY_BUCKETS:]) >= MIN_NONEMPTY_HISTORY
    return HypeResult(count, round(usual, 3), is_spike(count, history[-HISTORY_BUCKETS:]), score,
                      classify_hype(score), ready)
