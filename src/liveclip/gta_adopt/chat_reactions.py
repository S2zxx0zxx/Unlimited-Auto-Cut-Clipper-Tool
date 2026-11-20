"""Identity-aware read-only chat-reaction scoring for existing LiveClip chat pipeline.

Adapted from AnIntellectualBeing/GTA-Auto-Clipper live_chat.py,
pinned @ a9ac2ba8b95b5a887e8ab068b8237c86bcec59a2.
MIT (c) 2026 AnIntellectualBeing. See THIRD_PARTY_LICENSES/GTA-Auto-Clipper-MIT.txt.
Unlike existing aggregate chat_hype, distinct chatters and reaction vocabulary
reduce repeated message spam; **no new network collector** is created.
"""
from __future__ import annotations
import math
import re
from statistics import median

REACTION=re.compile(
    r"\b(?:lol|lmao|rofl|wtf|omg|no way|clip it|insane|crazy|rip|bruh|"
    r"that was close|what just happened|holy (?:shit|crap)|lul|kekw|"
    r"pog|poggers|monkas|omegalul)\b|😂|🤣|💀|😱|😮",re.I
)


def reaction_match(message: str) -> bool:
    return bool(REACTION.search(str(message or "")[:400]))


def score_chat_windows(messages: list[dict], starts: list[float], clip_seconds: float,
                       *, max_messages: int = 50000, max_windows: int = 2000) -> list[dict]:
    """Return 0..4 relative activity score per window; not 'virality probability'.

    Chat times t are source-relative seconds, not wall clock. Identity information
    is only processed in memory and never included in the result.
    """
    if (not 0 < clip_seconds <= 600 or not math.isfinite(clip_seconds)
            or not 0 < len(starts) <= max_windows or len(messages) > max_messages):
        raise ValueError("Invalid chat analysis size/window")
    valid=[]
    for row in messages:
        if not isinstance(row,dict):
            continue
        try: t=float(row.get("t",-1))
        except (ValueError,TypeError): continue
        if not math.isfinite(t) or t<0: continue
        valid.append((t,str(row.get("user") or "unknown")[:150].casefold(),
                      " ".join(str(row.get("text") or "")[:400].casefold().split())))
    valid.sort()
    result=[]
    for start in starts:
        if not math.isfinite(float(start)) or start<0:
            raise ValueError("Starts must be non-negative and finite")
        left, right=float(start),float(start)+clip_seconds
        selected=[row for row in valid if left <= row[0] < right]
        by_user: dict[str,set[str]]={}
        buckets:dict[int, tuple[set[str],set[str]]]={}
        for t,user,body in selected:
            by_user.setdefault(user,set()).add(body)
            idx=int((t-left)//5)
            users,reactions=buckets.setdefault(idx,(set(),set()))
            users.add(user)
            if reaction_match(body):
                reactions.add(user)
        peak_idx, peak=(max(buckets.items(),key=lambda kv:len(kv[1][0])+2*len(kv[1][1]))
                       if buckets else (0,(set(),set())))
        result.append({
            "start":round(left,3),"messages":len(selected),
            "chatters":len(by_user),
            "reactions":sum(any(reaction_match(m) for m in bodies) for bodies in by_user.values()),
            "distinct_lines":sum(len(texts) for texts in by_user.values()),
            "peak_t":round(left+peak_idx*5+2.5,3),
            "peak_chatters":len(peak[0])
        })
    counts=[min(r["distinct_lines"],r["chatters"]*3) for r in result]
    med=median(counts)
    mad=max(1.,median([abs(x-med) for x in counts]))
    for row,activity in zip(result,counts):
        burst=max(0,(activity-med)/mad)
        participation=min(row["chatters"],16)/16
        reactions=min(row["reactions"],5)/5
        row["signal"]=round(min(4.,min(2.5,burst*.55)+participation*.75+reactions*1.25),3)
    return result
