"""Compact, optional terminal presentation. Recording/rendering belong to other modules.

The Windows launcher can execute this file before the project is installed. Rich is
optional at that point; the fallback never emits ANSI codes or obscures errors.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
import shutil
import sys
import time

try:
    from rich.console import Console, Group
    from rich.live import Live
    from rich.text import Text
except ImportError:  # First setup can run before pip has installed the project.
    Console = Group = Live = Text = None

ACCENT = "#71d8c4"
MUTED = "#90a2b2"
GITHUB = "@S2zxx0zxx"


def rich_terminal(stream=None) -> bool:
    """Avoid control codes in CI, redirected streams, small terminals and NO_COLOR."""
    stream = sys.stdout if stream is None else stream
    return bool(
        Console is not None
        and getattr(stream, "isatty", lambda: False)()
        and not os.environ.get("NO_COLOR")
        and not os.environ.get("LIVECLIP_PLAIN")
        and os.environ.get("TERM", "") != "dumb"
        and shutil.get_terminal_size((80, 24)).columns >= 52
    )


def _console(stream):
    return Console(file=stream, highlight=False, soft_wrap=True, color_system="auto")


def setup_line(action: str, index: str = "", label: str = "", state: str = "", *, stream=None) -> None:
    """One-line launcher output; state is asserted by the caller, never estimated."""
    stream = sys.stdout if stream is None else stream
    if action == "boot":
        if rich_terminal(stream):
            _console(stream).print(Text.assemble(("LIVECLIP", f"bold {ACCENT}"),
                ("  / zero studio", MUTED), ("    "+GITHUB, "dim")))
        else:
            print("LIVECLIP / zero studio  " + GITHUB, file=stream)
        return
    if action not in ("step", "done"):
        raise ValueError("Unknown UI action")
    if action == "done":
        label, state = "Desktop workspace", "ready"
    if state not in ("ok", "working", "failed", "ready"):
        raise ValueError("Unknown setup state")
    marker = {"ok": "+", "working": "~", "failed": "!", "ready": ">"}[state]
    suffix = {"ok": "ok", "working": "working", "failed": "failed", "ready": "opening"}[state]
    prefix = f"{index:>2}  " if action == "step" else "    "
    if rich_terminal(stream):
        color = {"ok": ACCENT, "working": "#e1b96f", "failed": "bold red", "ready": ACCENT}[state]
        _console(stream).print(Text.assemble((prefix, MUTED), (marker+" ", color),
            (label, "white"), ("  "+suffix, MUTED)))
    else:
        print(f"{prefix}{marker} {label}  {suffix}", file=stream)


def _elapsed(seconds: float) -> str:
    seconds = max(0, int(seconds))
    h, r = divmod(seconds, 3600)
    m, s = divmod(r, 60)
    return f"{h:02}:{m:02}:{s:02}" if h else f"{m:02}:{s:02}"


def _clip_message(message: object, max_length: int = 80) -> str:
    """Never render control characters from plugin-provided source messages."""
    clean = " ".join(re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", str(message)).split())
    return clean if len(clean) <= max_length else clean[:max_length-1] + "…"


class SessionUI:
    """TTY-only live summary; a pipe keeps the existing machine-readable event log."""

    def __init__(self, action: str, folder: Path, *, stream=None, clock=time.monotonic):
        self.action = action
        self.folder = Path(folder)
        self.stream = sys.stdout if stream is None else stream
        self.clock = clock
        self.started_at = clock()
        self.candidates = 0
        self.highlight_events = 0
        self.errors = 0
        self.status = "Waiting for activity"
        self._last_refresh = 0.0
        self._live = None
        self._interactive = rich_terminal(self.stream)

    def _screen(self):
        elapsed = _elapsed(self.clock() - self.started_at)
        heading = Text.assemble(("LIVECLIP", f"bold {ACCENT}"),
            ("  / " + self.action, "white"), ("     " + GITHUB, "dim"))
        activity = Text.assemble(("● ", ACCENT),
            (_clip_message(self.status, 68), MUTED))
        counts = Text.assemble(("time ", MUTED), (elapsed, "white"),
            ("   candidates ", MUTED), (str(self.candidates), "white"),
            ("   highlight events ", MUTED), (str(self.highlight_events), "white"))
        return Group(heading, activity, counts)

    def start(self) -> None:
        if self._interactive:
            self._live = Live(self._screen(), console=_console(self.stream),
                              refresh_per_second=2, auto_refresh=False, transient=True)
            self._live.start(refresh=True)
        else:
            print("Session:", self.folder, file=self.stream, flush=True)

    def refresh(self, *, force: bool = False) -> None:
        if self._live is None:
            return
        now = self.clock()
        if force or now - self._last_refresh >= 1:
            self._live.update(self._screen(), refresh=True)
            self._last_refresh = now

    def event(self, kind: str, message: object) -> None:
        if kind == "candidate":
            self.candidates += 1
        elif kind == "highlight":
            self.highlight_events += 1
        elif kind == "error":
            self.errors += 1
        if kind != "log":
            self.status = f"{kind}: {_clip_message(message, 66)}"
        if self._live is None:
            print(f"[{kind}] {message}", file=self.stream, flush=True)
        elif kind == "error" or os.environ.get("LIVECLIP_VERBOSE") == "1":
            # Detailed failures remain permanently visible when Live exits.
            self._live.console.print(Text(f"[{kind}] {message}",
                style="red" if kind == "error" else MUTED))
        self.refresh(force=True)

    def close(self, *, interrupted: bool = False) -> None:
        if self._live is None:
            return
        self._live.stop()
        self._live = None
        # The folder may contain earlier runs: explicitly label disk inventory.
        clips = list((self.folder / "highlights").glob("highlight_*.mp4"))
        bytes_total = 0
        for clip in clips:
            try:
                bytes_total += clip.stat().st_size
            except OSError:
                pass
        result = "interrupted" if interrupted else ("finished with errors" if self.errors else "finished")
        self._interactive = False
        _console(self.stream).print(Text.assemble(("LIVECLIP", f"bold {ACCENT}"),
            ("  / " + result, "white")))
        _console(self.stream).print(
            f"elapsed {_elapsed(self.clock()-self.started_at)}  ·  "
            f"output files {len(clips)}  ·  output size {bytes_total / (1024 * 1024):.1f} MiB"
        )
        _console(self.stream).print("Output: " + str(self.folder))


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in ("boot", "step", "done"):
        print("Usage: terminal_ui.py boot | step INDEX LABEL STATE | done", file=sys.stderr)
        return 2
    try:
        if args[0] == "step":
            if len(args) != 4:
                raise ValueError("step requires INDEX LABEL STATE")
            setup_line("step", args[1], args[2], args[3])
        elif len(args) == 1:
            setup_line(args[0])
        else:
            raise ValueError("Unexpected setup arguments")
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
