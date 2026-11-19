#!/bin/sh
set -eu
cd "$(dirname "$0")"
command -v ffmpeg >/dev/null || { echo 'FFmpeg missing'; exit 1; }
command -v ffprobe >/dev/null || { echo 'ffprobe missing'; exit 1; }
if [ ! -x .venv/bin/python ]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install -e .
.venv/bin/python -m liveclip.gui
