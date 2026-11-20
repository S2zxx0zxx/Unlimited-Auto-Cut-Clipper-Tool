"""Single-position per-word yellow pop captions in ASS.

Adapted from GTA-Auto-Clipper clip.py:write_ass,
AnIntellectualBeing @ a9ac2ba8b95b5a887e8ab068b8237c86bcec59a2
Copyright (c) 2026 AnIntellectualBeing; MIT notice:
THIRD_PARTY_LICENSES/GTA-Auto-Clipper-MIT.txt.

Local subtitles are not a guarantee of platform reach.
"""
from __future__ import annotations
import math
import re
from pathlib import Path

# Platform-neutral, optional user-controlled censoring; audio is never modified.
SENSITIVE_WORDS = frozenset({
    "fuck", "fucking", "fucked", "shit", "bullshit", "bitch", "asshole",
    "chutiya", "madarchod", "bhenchod", "behenchod", "gandu", "bsdk",
})

def _esc(text: str) -> str:
    """Never interpret transcript text as ASS override commands."""
    text = str(text).replace("\\", "＼").replace("{", "(").replace("}", ")")
    return " ".join(ch for ch in text if ch.isprintable()).strip()[:100]


def mask_word(text: str) -> str:
    core = re.sub(r"[^\w]", "", str(text).casefold())
    if core in SENSITIVE_WORDS:
        return str(text)[:1] + "*" * max(2, len(str(text)) - 1)
    return str(text)


def _stamp(seconds: float) -> str:
    centiseconds = max(0, int(round(seconds * 100)))
    hh, left = divmod(centiseconds, 360000)
    mm, left = divmod(left, 6000)
    ss, cs = divmod(left, 100)
    return f"{hh}:{mm:02}:{ss:02}.{cs:02}"


def _normalized_words(words: list[dict], clip_start: float, duration: float, censor: bool) -> list[tuple[float,float,str]]:
    end = clip_start + duration
    out = []
    for raw in words:
        if not isinstance(raw, dict):
            raise ValueError("Each caption word must be an object")
        try:
            a,b = float(raw["start"]),float(raw["end"])
            txt = str(raw["text"])
        except (KeyError,ValueError,TypeError) as exc:
            raise ValueError("Invalid caption word") from exc
        if not math.isfinite(a) or not math.isfinite(b) or b <= a:
            raise ValueError("Caption word times must be finite and increasing")
        if b <= clip_start or a >= end:
            continue
        cleaned = _esc(mask_word(txt) if censor else txt).upper()
        if not cleaned:
            continue
        begin = max(0,a - clip_start)
        finish = min(duration,b - clip_start)
        if finish - begin >= .03:
            out.append((begin,finish,cleaned))
    out.sort(key=lambda x:(x[0],x[1]))
    return out[:20000]


def ass_text(words: list[dict], *, clip_start: float = 0., duration: float,
             width: int = 720, height: int = 1280, language: str = "en",
             censor: bool = False, credit: str = "") -> str:
    """Return self-contained ASS content. No overlapping caption events.

    Word timestamps are SOURCE-absolute, consistent with transcribe .words.json.
    Supports English and Romanized Hinglish text. Missing/uncertain transcripts
    must be reviewed before use; no speech is inferred.
    """
    if not 0 < duration <= 3600 or not math.isfinite(duration):
        raise ValueError("Invalid clip duration")
    if width <= 0 or height <= 0 or width % 2 or height % 2:
        raise ValueError("Invalid output size")
    if language not in ("en", "hinglish"):
        raise ValueError("Only en and hinglish are supported for pop captions")
    items = _normalized_words(words, clip_start, duration, censor)
    fontsize = int(width * .072)
    margin = int(height * .24)
    text = (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {width}\nPlayResY: {height}\nWrapStyle: 2\n"
        "ScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n"
        f"Style: Word,DejaVu Sans,{fontsize},&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,3,1,2,24,24,{margin},1\n"
        f"Style: Credit,DejaVu Sans,{max(18, int(width*.034))},&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,0,0,1,2,0,7,24,24,24,1\n\n"
        "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
    )
    groups, group = [], []
    for word in items:
        if group:
            previous = group[-1]
            length = sum(len(w[2]) + 1 for w in group) + len(word[2])
            if word[0] - previous[1] > .6 or len(group) >= 3 or length > 18 or re.search(r"[.!?]$",previous[2]):
                groups.append(group)
                group = []
        group.append(word)
    if group:
        groups.append(group)
    events, end_previous = [], 0.
    for gi,phrase in enumerate(groups):
        phrase_end = min(duration, phrase[-1][1] + .3)
        if gi+1 < len(groups):
            phrase_end = min(phrase_end,groups[gi+1][0][0])
        for i,(start,stop,word) in enumerate(phrase):
            t0=max(start,end_previous)
            t1=phrase[i+1][0] if i+1 < len(phrase) else phrase_end
            t1=min(duration, t1)
            if t1-t0 < .025:
                continue
            parts=[]
            for j,(_,_,part) in enumerate(phrase):
                if j < i:
                    parts.append(r"{\alpha&H00&\c&HFFFFFF&\fscx100\fscy100}"+part)
                elif j == i:
                    parts.append(r"{\alpha&H00&\c&H00FFFF&\fscx118\fscy118\t(0,110,\fscx100\fscy100)}"+part)
                else:
                    parts.append(r"{\alpha&HFF&\fscx100\fscy100}"+part)
            chars=sum(len(t[2]) for t in phrase)+len(phrase)-1
            adaptive=max(int(fontsize*.65), min(fontsize, int(width/(.83*max(chars,1)))))
            events.append(f"Dialogue: 0,{_stamp(t0)},{_stamp(t1)},Word,,0,0,0,,{{\\fs{adaptive}}}{' '.join(parts)}")
            end_previous=t1
    if credit:
        safe_credit=_esc(credit)[:100]
        if safe_credit:
            events.append(f"Dialogue: 1,0:00:00.00,{_stamp(min(duration,4))},Credit,,0,0,0,,via {safe_credit}")
    return text + "\n".join(events) + "\n"


def load_words(path: Path, limit_bytes: int = 10_000_000) -> list[dict]:
    import json
    if not path.is_file() or path.stat().st_size > limit_bytes:
        raise ValueError("Word transcript missing or too large")
    data=json.loads(path.read_text(encoding="utf-8-sig"))
    data=data.get("words") if isinstance(data,dict) else data
    if not isinstance(data,list) or len(data)>20000:
        raise ValueError("Expected up to 20,000 word objects")
    return data
