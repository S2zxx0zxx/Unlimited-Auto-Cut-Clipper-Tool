"""Explicit opt-in VOD import from supported public URL; no credentials or DRM bypass.

Inspired by NeonClipping MIT standalone.py at commit
2632cade8e92b016314ac0e2b69b78e5f08a75d2.
This implementation has no server endpoints and never deletes input media.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import urlsplit


ALLOWED_HOSTS = frozenset({
    "youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be",
    "twitch.tv", "www.twitch.tv", "clips.twitch.tv",
    "kick.com", "www.kick.com",
})


def validate_vod_url(raw: str) -> str:
    if not isinstance(raw, str) or len(raw) > 2000:
        raise ValueError("Provide a supported public VOD URL (max 2000 characters).")
    url = raw.strip()
    try:
        target = urlsplit(url)
        host = target.hostname
        port = target.port
    except ValueError:
        raise ValueError("Invalid URL.") from None
    if (target.scheme != "https" or not host or host.lower() not in ALLOWED_HOSTS
            or target.username or target.password or port not in (None, 443)):
        raise ValueError("Only public HTTPS YouTube/Twitch/Kick URLs are accepted.")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("IP-literal URLs are not allowed.")
    if any(ch in url for ch in ("\n", "\r", "\x00")):
        raise ValueError("Invalid URL characters.")
    return url


def download_public_vod(url: str, directory: Path, *, authorized: bool = False,
                        max_gib: float = 5.0, max_seconds: float = 4 * 3600) -> dict:
    """Download a public VOD only with explicit permission and local resource limits.

    yt-dlp follows provider-supplied media redirects; do not expose this as a
    remotely reachable API without independent SSRF and DNS rebinding controls.
    """
    if not authorized:
        raise PermissionError("Explicit rights confirmation is required (--i-have-rights).")
    url = validate_vod_url(url)
    if not math.isfinite(max_gib) or not 0.25 <= max_gib <= 20:
        raise ValueError("max_gib must be between 0.25 and 20.")
    if not 0 < max_seconds <= 4 * 3600:
        raise ValueError("max_seconds must be within four hours.")
    try:
        import yt_dlp
    except ImportError as exc:
        raise RuntimeError("Install the optional VOD downloader: pip install -e '.[download]'") from exc

    directory = Path(directory).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(directory).free < (max_gib + .5) * (1024 ** 3):
        raise RuntimeError("Insufficient free disk for selected download budget.")
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "noplaylist": True,
                           "skip_download": True, "socket_timeout": 20,
                           "retries": 2, "extractor_retries": 1}) as downloader:
        info = downloader.extract_info(url, download=False)
    if not isinstance(info, dict) or info.get("is_live") or info.get("live_status") in ("is_live", "is_upcoming"):
        raise ValueError("This is live/upcoming or unsupported; use LiveClip live capture instead.")
    duration = float(info.get("duration") or 0)
    if not math.isfinite(duration) or not 0 < duration <= max_seconds:
        raise ValueError("VOD duration missing or exceeds the chosen safety limit.")
    stem = hashlib.sha256(url.encode("utf-8")).hexdigest()[:18]
    target = directory / f"vod_{stem}.mp4"
    if target.is_file() and target.stat().st_size > 4096:
        return {"path": str(target), "cached": True, "duration": duration,
                "provider": urlsplit(url).hostname, "original_preserved": True}
    template = str(directory / (f"vod_{stem}.%(ext)s"))
    options = {
        "quiet": True, "no_warnings": True, "noplaylist": True,
        "format": "best[height<=720][ext=mp4]/bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]",
        "merge_output_format": "mp4", "outtmpl": template,
        "socket_timeout": 20, "retries": 2, "fragment_retries": 2,
        "extractor_retries": 1, "max_filesize": int(max_gib * 1024 ** 3),
        "overwrites": False, "restrictfilenames": True,
    }
    with yt_dlp.YoutubeDL(options) as downloader:
        outcome = downloader.download([url])
        if outcome:
            raise RuntimeError("The provider download failed or was unavailable.")
    candidates = sorted(directory.glob(f"vod_{stem}.*"))
    media = next((p for p in candidates if p.suffix.lower() in (".mp4", ".mkv", ".webm")), None)
    if media is None:
        raise RuntimeError("No supported output media was produced.")
    if media.stat().st_size > max_gib * 1024 ** 3:
        raise RuntimeError("Downloaded file exceeded the selected storage limit; review manually.")
    if media != target:
        # Preserve the downloaded container; FFmpeg accepts MKV/WebM directly.
        target = media
    return {"path": str(target), "cached": False, "duration": duration,
            "provider": urlsplit(url).hostname, "original_preserved": True,
            "notice": "Public VOD captured with user-supplied rights assertion"}
