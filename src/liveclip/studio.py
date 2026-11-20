"""First-party local video onboarding and rendering controls.

This module is a thin, UI-safe orchestration layer over LiveClip's existing
VOD ranker and portrait renderer. The underlying media engines are shared by
CLI and desktop; no second clipping algorithm is introduced.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
import shutil
import subprocess
from threading import Thread
from tkinter import filedialog, messagebox, ttk
import tkinter as tk
from uuid import uuid4


def make_vod_args(source: Path, folder: Path, *, count: int = 3,
                  seconds: int = 30, profile: str = "balanced",
                  layout: str = "blur", precision: bool = False) -> list[str]:
    """Validate and prepare a deterministic existing-engine request."""
    from .neon_adopt.curation import PROFILES
    from .moments import LENGTH_OPTIONS
    if count not in (1, 3, 5) or seconds not in LENGTH_OPTIONS:
        raise ValueError("Choose 1, 3 or 5 clips and a length up to 300 seconds.")
    if profile not in PROFILES:
        raise ValueError("Unknown analysis profile.")
    if layout not in ("blur", "fill"):
        raise ValueError("Choose blurred background or fullscreen crop.")
    path = Path(source).expanduser().resolve()
    target = Path(folder).expanduser().resolve()
    if not path.is_file() or path.suffix.lower() not in {".mp4", ".mkv", ".mov", ".webm"}:
        raise ValueError("Choose an existing MP4, MKV, MOV or WebM video file.")
    if target == path or path in target.parents:
        raise ValueError("Output folder cannot be the input video.")
    args = ["vod", str(path), str(target), "--count", str(count),
            "--seconds", str(seconds), "--profile", profile, "--layout", layout]
    if precision:
        args.append("--precision")
    return args


def demo_ffmpeg_args(destination: Path) -> list[str]:
    """Synthetic 36-second, small test video with entirely original signal data."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg missing. Install FFmpeg (with ffprobe) first.")
    return [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
            "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=12:duration=36",
            "-f", "lavfi", "-i", "sine=frequency=700:sample_rate=16000:duration=36",
            "-shortest", "-c:v", "mpeg4", "-q:v", "5", "-c:a", "aac",
            str(destination)]


class LocalShortsStudio:
    """A single local-file workflow, deliberately independent of live recording."""

    def __init__(self, notebook: ttk.Notebook, root: tk.Tk,
                 can_start, log_callback):
        self.root = root
        self.can_start = can_start
        self.log_callback = log_callback
        self.frame = ttk.Frame(notebook, padding=13)
        notebook.add(self.frame, text="Local Shorts Studio")
        self.source = tk.StringVar(master=root, value="")
        self.destination = tk.StringVar(master=root, value=str(
            Path.home() / "Videos" / "LiveClipZero" / "Shorts"))
        self.count = tk.StringVar(master=root, value="3")
        self.seconds = tk.StringVar(master=root, value="30")
        self.profile = tk.StringVar(master=root, value="balanced")
        self.layout = tk.StringVar(master=root, value="blur")
        self.precision = tk.BooleanVar(master=root, value=True)
        self.status = tk.StringVar(master=root, value="Choose a video or generate a demo, then create shorts.")
        self.last_folder: Path | None = None
        self._busy = False
        self._events: Queue = Queue()
        self._ui()

    def is_busy(self) -> bool:
        return self._busy

    def _ui(self):
        ttk.Label(self.frame, text="LOCAL SHORTS STUDIO",
                  style="Title.TLabel").pack(anchor="w", pady=(0, 6))
        ttk.Label(self.frame, text="Turn a video you own into 9:16 highlight candidates. "
                  "Your source video stays untouched.", style="Hint.TLabel").pack(anchor="w")
        ttk.Label(self.frame, text="1  Choose an input video", style="TLabel").pack(anchor="w", pady=(14, 5))
        source = ttk.Frame(self.frame)
        source.pack(fill="x")
        ttk.Entry(source, textvariable=self.source).pack(side="left", fill="x", expand=True)
        ttk.Button(source, text="Browse video", command=self.browse_source).pack(side="left", padx=(8, 0))
        ttk.Label(self.frame, text="2  Choose where the generated clips should go").pack(anchor="w", pady=(12, 5))
        folder = ttk.Frame(self.frame)
        folder.pack(fill="x")
        ttk.Entry(folder, textvariable=self.destination).pack(side="left", fill="x", expand=True)
        ttk.Button(folder, text="Browse folder", command=self.browse_destination).pack(side="left", padx=(8, 0))
        options = ttk.Frame(self.frame)
        options.pack(fill="x", pady=(14, 4))
        settings = [
            ("Highlights", self.count, ["1", "3", "5"]),
            ("Max duration", self.seconds, ["15", "30", "45", "60", "90", "120", "180", "300"]),
            ("Find moments", self.profile, ["balanced", "action", "dialogue"]),
            ("Vertical style", self.layout, ["blur", "fill"]),
        ]
        for i, (name, state, items) in enumerate(settings):
            ttk.Label(options, text=name).grid(row=0, column=i, sticky="w", padx=(0, 12))
            ttk.Combobox(options, textvariable=state, values=items, state="readonly",
                         width=15).grid(row=1, column=i, sticky="w", padx=(0, 12), pady=(5, 3))
        ttk.Checkbutton(self.frame, text="Precision moments: require sustained activity; no random filler (recommended)",
                        variable=self.precision).pack(anchor="w", pady=(8, 3))
        ttk.Label(self.frame, text="Max duration is a ceiling; meaningful moments may be shorter.",
                  style="Hint.TLabel").pack(anchor="w")
        ttk.Label(self.frame, text="blur = preserve full gameplay with blurred background  •  "
                  "fill = crop to fill the vertical frame",
                  style="Hint.TLabel").pack(anchor="w", pady=(5, 12))
        actions = ttk.Frame(self.frame)
        actions.pack(fill="x")
        self.create_button = ttk.Button(actions, text="CREATE HIGHLIGHT SHORTS",
                                        command=self.create)
        self.create_button.pack(side="left")
        self.demo_button = ttk.Button(actions, text="Generate demo video",
                                      command=self.generate_demo)
        self.demo_button.pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Open last results", command=self.open_results).pack(side="left", padx=(8, 0))
        ttk.Label(self.frame, textvariable=self.status,
                  style="Hint.TLabel", wraplength=740).pack(anchor="w", pady=(15, 4))
        ttk.Label(self.frame, text="Demo video is generated locally with FFmpeg. "
                  "It does not use real game footage, and no live-stream access is required.",
                  style="Hint.TLabel", wraplength=740).pack(anchor="w", pady=(5, 0))

    def browse_source(self):
        value = filedialog.askopenfilename(title="Choose your video",
                                            filetypes=[("Video", "*.mp4 *.mkv *.mov *.webm"),
                                                       ("All files", "*.*")])
        if value:
            self.source.set(value)

    def browse_destination(self):
        value = filedialog.askdirectory(title="Choose destination for finished shorts")
        if value:
            self.destination.set(value)

    def _start(self, fn) -> bool:
        if self._busy:
            messagebox.showinfo("Already working", "Finish the current Studio task first.")
            return False
        if not self.can_start():
            messagebox.showwarning("Recorder active",
                "Finish the live capture or session analysis before starting a new Studio job.")
            return False
        self._busy = True
        self.status.set("Working locally... your original video is preserved.")
        self.create_button.configure(state="disabled")
        self.demo_button.configure(state="disabled")
        Thread(target=self._work, args=(fn,), daemon=True).start()
        self.root.after(150, self._poll)
        return True

    def _work(self, fn):
        try:
            result = fn()
            self._events.put(("done", result))
        except Exception as exc:
            self._events.put(("error", str(exc)))

    def _poll(self):
        try:
            kind, payload = self._events.get_nowait()
        except Empty:
            if self._busy:
                self.root.after(150, self._poll)
            return
        self._busy = False
        self.create_button.configure(state="normal")
        self.demo_button.configure(state="normal")
        if kind == "error":
            self.status.set("Could not finish — " + payload[:400])
            self.log_callback("Studio error: " + payload[:500])
            messagebox.showerror("Studio job failed", payload)
            return
        self.status.set(payload["message"])
        self.last_folder = payload["folder"]
        if "demo" in payload:
            self.source.set(str(payload["demo"]))
            self.count.set("1")
            self.seconds.set("15")
            self.precision.set(False)  # Only the synthetic demo explicitly uses legacy test candidate ranking
        self.log_callback(payload["message"])

    def _run_vod(self, args: list[str], folder: Path):
        from .neon_adopt.cli import main
        result = main(args)
        if result != 0:
            raise RuntimeError("Local VOD processing failed. Check the console for the detailed error; "
                               "verify that optional analysis dependencies are installed.")
        clips = sorted(folder.glob("highlight_*.mp4"))
        if not clips:
            return {"folder": folder, "message": (
                "No strong event found: no arbitrary clips exported. "
                "Try a longer active video or turn off precision for a manual review-only sample.")}
        return {"folder": folder, "message": f"Created {len(clips)} highlight MP4(s) in {folder}"}

    def create(self):
        try:
            root = Path(self.destination.get()).expanduser().resolve()
            folder = root / ("Shorts_" + datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:6])
            args = make_vod_args(Path(self.source.get()), folder, count=int(self.count.get()),
                                 seconds=int(self.seconds.get()), profile=self.profile.get(),
                                 layout=self.layout.get(), precision=self.precision.get())
            if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
                raise RuntimeError("FFmpeg and ffprobe must both be on your PATH.")
        except (OSError, ValueError, RuntimeError) as exc:
            messagebox.showerror("Check video settings", str(exc))
            return
        self._start(lambda: self._run_vod(args, folder))

    def generate_demo(self):
        try:
            base = Path(self.destination.get()).expanduser().resolve()
            demo_dir = base / ("Demo_" + datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:6])
            target = demo_dir / "demo_gameplay.mp4"
            cmd = demo_ffmpeg_args(target)
        except (ValueError, RuntimeError, OSError) as exc:
            messagebox.showerror("Demo prerequisites", str(exc))
            return
        def worker():
            demo_dir.mkdir(parents=True, exist_ok=False)
            proc = subprocess.run(cmd, capture_output=True, timeout=120)
            if proc.returncode or not target.is_file() or target.stat().st_size < 1000:
                raise RuntimeError("Local demo generation failed: " +
                                   proc.stderr.decode("utf-8", "replace")[-1000:])
            return {"folder": demo_dir, "demo": target,
                    "message": "Demo video created. Now press CREATE HIGHLIGHT SHORTS "
                               "(1 highlight / 15 seconds has been preselected)."}
        self._start(worker)

    def open_results(self):
        from .gui import open_path
        if self.last_folder and self.last_folder.is_dir():
            open_path(self.last_folder)
        else:
            messagebox.showinfo("No result yet", "Create a demo or some clips first.")
