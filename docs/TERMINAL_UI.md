# Compact terminal UI

LiveClip's optional CLI presentation is deliberately small: a single brand line,
one activity line, and real event counters. The GUI, capture engine, ranker and
renderer remain independent of terminal styling.

## Windows launcher

Double-click START_WINDOWS.bat. Its steps show verified FFmpeg/ffprobe, Python
environment and package installation states. First-run dependency downloads may
take time; the launcher does **not** invent percentages or speeds. It opens the
existing desktop studio on success. If setup fails, diagnostics remain visible.

The launcher checks FFmpeg/ffprobe by executing them instead of relying on
the 'where' command, which can be absent from a damaged Windows PATH.
CHECK_SETUP_WINDOWS.bat remains the dedicated diagnostic entry point.

## Recording and analysis CLI

Use the installed virtual environment:

    .venv\Scripts\python.exe -m liveclip doctor
    .venv\Scripts\python.exe -m liveclip record https://example.com/authorized-live
    .venv\Scripts\python.exe -m liveclip analyze C:\Videos\LiveClipZero\session

Only record media you own or are authorized to capture. Stream provider support
varies. The CLI terminal displays actual elapsed time, emitted candidate and
highlight events, and latest status. At completion, it reports the existing
MP4 files and total bytes in the session's highlights folder. These files may
include previous runs; they are not asserted as freshly created.

## Accessibility, logging and performance

- Tiny terminal (<52 columns), CI, pipes, NO_COLOR, TERM=dumb, or LIVECLIP_PLAIN=1:
  old plain event logging remains. No ANSI screen rewrites.
- LIVECLIP_VERBOSE=1: keep detailed event text visible even in interactive mode.
- Error events remain visible, and the desktop launcher preserves pip errors.
- The live screen refreshes on new events and at most once per second when idle.
- Rich is the only added UI dependency. No model, cloud API or extra media engine.
- This change does not claim automatic clip quality, unlimited hardware capacity,
  or full Windows GUI acceptance.

Developer branding in the terminal is restricted to @S2zxx0zxx.
