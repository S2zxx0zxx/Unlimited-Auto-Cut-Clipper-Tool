#!/bin/sh
set -eu
cd "$(dirname "$0")"
echo "LiveClip Zero Studio — desktop launcher"
command -v ffmpeg >/dev/null || { echo 'FFmpeg missing; see docs/QUICK_START.md'; exit 1; }
command -v ffprobe >/dev/null || { echo 'ffprobe missing; see docs/QUICK_START.md'; exit 1; }
command -v python3 >/dev/null || { echo 'Python 3.10+ required'; exit 1; }
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
.venv/bin/python -c 'import sys; assert sys.version_info >= (3,10), "Python 3.10+ required"'
if ! .venv/bin/python -c 'import liveclip,numpy,cv2,streamlink; assert liveclip.__version__=="2.4.0"' >/dev/null 2>&1; then
  .venv/bin/python -m pip install --disable-pip-version-check -e '.[neon]'
fi
.venv/bin/python -m liveclip.gui
