"""LiveClip Zero: stream capture and automatic segment creation.

All processing and output are local. Uses Streamlink + FFmpeg; no paid APIs.
Only capture streams that you own or are authorized to record.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import queue
import ipaddress
import re
import shutil
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit


MIN_FREE_BYTES = 1024 * 1024 * 1024  # 1 GiB free-space guard


def validate_url(raw: str) -> str:
    url = raw.strip()
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError("A valid public http(s) livestream URL is required.")
    if any(ord(char) < 32 for char in url):
        raise ValueError("Control characters are not allowed in URL.")
    try:
        address = ipaddress.ip_address(parts.hostname.strip('[]'))
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValueError("Private, loopback and reserved IP addresses are not allowed.")
    if parts.username or parts.password:
        raise ValueError("Do not put usernames or passwords in the URL.")
    if parts.hostname.lower().rstrip(".") in ("localhost", "localhost.localdomain") or parts.hostname.lower().endswith(".localhost"):
        raise ValueError("Localhost URLs are not supported by this desktop app.")
    return url


def ffmpeg_executable() -> str:
    # Use a full system FFmpeg build. Some minimal bundled builds do not
    # support reliable MP4 segmentation and can crash with this muxer.
    path = shutil.which("ffmpeg")
    if path:
        return path
    raise RuntimeError("FFmpeg is missing. Install FFmpeg (see README) and restart.")


def command_for_segments(ffmpeg: str, seconds: int, first_number: int, folder: Path) -> list[str]:
    return [
        ffmpeg, "-hide_banner", "-loglevel", "warning", "-nostdin",
        "-fflags", "+genpts", "-i", "pipe:0",
        "-map", "0:v:0", "-map", "0:a?",
        "-c", "copy", "-avoid_negative_ts", "make_zero",
        "-f", "segment", "-segment_time", str(seconds),
        "-reset_timestamps", "1", "-segment_start_number", str(first_number),
        "-segment_format", "mp4", str(folder / "clip_%06d.mp4")
    ]


def next_clip_number(folder: Path) -> int:
    nums = []
    for item in folder.glob("clip_*.mp4"):
        match = re.fullmatch(r"clip_(\d{6})\.mp4", item.name)
        if match:
            nums.append(int(match.group(1)))
    return max(nums, default=0) + 1


@dataclass(frozen=True)
class CaptureConfig:
    url: str
    seconds: int
    output_root: Path
    quality: str = "best"
    max_restarts: int = 3

    def validate(self) -> None:
        validate_url(self.url)
        if self.seconds not in (30, 60):
            raise ValueError("Clip length must be 30 or 60 seconds.")
        if self.quality not in ("best", "720p", "480p", "worst"):
            raise ValueError("Invalid quality option.")
        if self.max_restarts < 0 or self.max_restarts > 20:
            raise ValueError("Invalid retry limit.")


class Recorder:
    def __init__(self, events: queue.Queue):
        self.events = events
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._streamlink: subprocess.Popen | None = None
        self._ffmpeg: subprocess.Popen | None = None
        self.session_folder: Path | None = None
        self.active = False
        self._lock = threading.Lock()

    def send(self, kind: str, message: str):
        self.events.put((kind, message))

    def start(self, config: CaptureConfig):
        config.validate()
        if self.active:
            raise RuntimeError("A recording is already running.")
        root = config.output_root.expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(root).free < MIN_FREE_BYTES:
            raise RuntimeError("Less than 1 GiB disk space available. Free space first.")
        folder = root / datetime.now().strftime("Live_%Y%m%d_%H%M%S")
        folder.mkdir(exist_ok=False)
        self.session_folder = folder
        self._stop.clear()
        self.active = True
        self._thread = threading.Thread(target=self._run, args=(config,), daemon=True)
        self._thread.start()
        self.send("folder", str(folder))

    def stop(self):
        self._stop.set()
        self.send("status", "Stopping and finalizing current clip…")
        with self._lock:
            upstream = self._streamlink
        if upstream and upstream.poll() is None:
            try:
                upstream.terminate()
            except OSError:
                pass

    def _read_stderr(self, process: subprocess.Popen, label: str):
        if process.stderr is None:
            return
        try:
            for raw in iter(process.stderr.readline, b""):
                line = raw.decode("utf-8", errors="replace").strip()
                if line:
                    self.send("log", f"[{label}] {line[-300:]}")
        except (OSError, ValueError):
            pass

    def _run_once(self, config: CaptureConfig, ffmpeg_path: str):
        folder = self.session_folder
        assert folder is not None
        # Streamlink may be installed into the same Python venv used by this app.
        script = Path(sys.executable).parent / ("streamlink.exe" if sys.platform == "win32" else "streamlink")
        streamlink_exec = str(script) if script.exists() else shutil.which("streamlink")
        if not streamlink_exec:
            raise RuntimeError("Streamlink is missing. Launch via START_WINDOWS.bat or start_mac_linux.sh.")
        upstream_args = [
            streamlink_exec, "--stdout", "--ffmpeg-ffmpeg", ffmpeg_path,
            "--retry-streams", "3", "--retry-max", "5",
            validate_url(config.url), config.quality
        ]
        first = next_clip_number(folder)
        downstream_args = command_for_segments(ffmpeg_path, config.seconds, first, folder)
        self.send("status", "Connecting to livestream…")
        upstream = subprocess.Popen(
            upstream_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0
        )
        downstream = None
        stderr_readers = []
        with self._lock:
            self._streamlink = upstream
        try:
            downstream = subprocess.Popen(
                downstream_args, stdin=upstream.stdout,
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
            )
            # Critical: close this FD in the parent so FFmpeg can detect EOF.
            if upstream.stdout:
                upstream.stdout.close()
            with self._lock:
                self._ffmpeg = downstream
            for child, label in ((upstream, "Streamlink"), (downstream, "FFmpeg")):
                reader = threading.Thread(target=self._read_stderr, args=(child, label), daemon=True)
                reader.start()
                stderr_readers.append(reader)
            self.send("status", "Recording live stream. Clips save automatically.")
            while not self._stop.is_set():
                if downstream.poll() is not None or upstream.poll() is not None:
                    break
                if shutil.disk_usage(folder).free < MIN_FREE_BYTES:
                    self.send("error", "Disk space below 1 GiB. Recording stopped for safety.")
                    self._stop.set()
                    break
                time.sleep(0.75)
        finally:
            # Stop producer first; consumer then sees EOF and closes MP4 files.
            if upstream.poll() is None:
                upstream.terminate()
            try:
                upstream.wait(timeout=5)
            except subprocess.TimeoutExpired:
                upstream.kill()
                upstream.wait()
            if downstream is not None:
                try:
                    downstream.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    downstream.terminate()
                    try:
                        downstream.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        downstream.kill()
                        downstream.wait()
            for reader in stderr_readers:
                reader.join(timeout=2)
            for child in (upstream, downstream):
                if child is not None and child.stderr is not None:
                    child.stderr.close()
            with self._lock:
                self._streamlink = None
                self._ffmpeg = None
        return (upstream.returncode, downstream.returncode if downstream else None)

    def _run(self, config: CaptureConfig):
        try:
            ffmpeg_path = ffmpeg_executable()
            for attempt in range(config.max_restarts + 1):
                if self._stop.is_set():
                    break
                if attempt > 0:
                    delay = min(5 * attempt, 15)
                    self.send("status", f"Reconnect {attempt}/{config.max_restarts} in {delay}s…")
                    if self._stop.wait(delay):
                        break
                if attempt > 0 and self.session_folder is not None:
                    # Mark a timeline break: never stitch highlights across outages.
                    index = next_clip_number(self.session_folder)
                    (self.session_folder / f"gap_before_{index:06d}.marker").touch()
                    self.send("log", f"Reconnect gap marked before clip {index}")
                self.send("log", f"Recording attempt {attempt + 1}")
                codes = self._run_once(config, ffmpeg_path)
                self.send("log", f"Stream ended: Streamlink={codes[0]}, FFmpeg={codes[1]}")
                if self._stop.is_set():
                    break
            if not self._stop.is_set():
                self.send("error", "Stream ended, is inaccessible, or reconnects exhausted. Check logs.")
            self.send("status", "Stopped. Saved clips are in the session folder.")
        except Exception as exc:
            self.send("error", f"Capture failed: {exc}")
        finally:
            self.active = False
            self.send("finished", "")
