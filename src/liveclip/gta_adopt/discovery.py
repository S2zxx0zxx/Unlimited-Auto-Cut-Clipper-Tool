"""Read-only live YouTube discovery (no capture or access permission inferred).

Adapted from AnIntellectualBeing/GTA-Auto-Clipper find_streams.py
at a9ac2ba8b95b5a887e8ab068b8237c86bcec59a2.
MIT (c) 2026 AnIntellectualBeing. Notice in THIRD_PARTY_LICENSES/.
YouTube Data API key is supplied via environment, never stored in outputs.
"""
from __future__ import annotations
import html
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

SEARCH_URL="https://www.googleapis.com/youtube/v3/search"

def find_live(query: str, key: str, limit: int = 25) -> list[dict]:
    if not isinstance(query,str) or not 1 <= len(query.strip()) <= 150:
        raise ValueError("Search query must contain 1–150 characters")
    if not isinstance(key,str) or not key.strip():
        raise ValueError("YOUTUBE_API_KEY is missing; no public search attempted")
    if not isinstance(limit,int) or not 1<=limit<=50:
        raise ValueError("Limit must be 1..50")
    params=urlencode({"part":"snippet","eventType":"live","type":"video",
                      "q":query.strip(),"maxResults":limit,
                      "order":"viewCount","key":key.strip()})
    req=Request(f"{SEARCH_URL}?{params}",headers={"Accept":"application/json"})
    try:
        with urlopen(req,timeout=30) as response:
            data=json.load(response)
    except HTTPError as exc:
        # Never echo the credential-bearing URL or upstream body
        raise RuntimeError(f"YouTube Data API returned HTTP {exc.code}; verify quota and key") from None
    except (URLError, TimeoutError, OSError):
        # Network exceptions may contain query-string credentials, so redact details.
        raise RuntimeError("YouTube live discovery is unavailable; check network and API access") from None
    if not isinstance(data,dict):
        raise ValueError("Unexpected YouTube response")
    result=[]
    for item in data.get("items",[])[:50]:
        video_id=(item.get("id") or {}).get("videoId")
        if not isinstance(video_id,str) or len(video_id)!=11:
            continue
        info=item.get("snippet") or {}
        result.append({
            "title":html.unescape(str(info.get("title") or ""))[:300],
            "channel":str(info.get("channelTitle") or "")[:200],
            "channel_id":str(info.get("channelId") or "")[:100],
            "url":f"https://www.youtube.com/watch?v={video_id}",
            "rank_signal":"YouTube search result order, NOT live concurrent viewers",
            "gameplay_verified":False,
            "content_rights_verified":False,
        })
    return result
