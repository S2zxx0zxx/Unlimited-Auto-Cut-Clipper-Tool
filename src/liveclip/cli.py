"""Headless recording + smart highlights, useful for long-running local sessions.

Examples:
  python liveclip_cli.py record https://example.com/public-live --profile Gaming
  python liveclip_cli.py analyze ./Live_20261119_142000 --threshold 22
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import queue
import signal
import sys
import time

from .capture import CaptureConfig, Recorder
from .pipeline import HighlightPipeline, SmartConfig
from .signals import PROFILES
from .terminal_ui import SessionUI


def build_parser():
    parser = argparse.ArgumentParser(description='Zero-API-cost local stream capture + heuristic highlights')
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('doctor', help='Check local dependencies and environment')
    for action in ('record', 'analyze'):
        cmd = sub.add_parser(action)
        if action == 'record':
            cmd.add_argument('url', help='Authorized public livestream URL')
            cmd.add_argument('--out', type=Path, default=Path.home() / 'Videos' / 'LiveClipZero')
            cmd.add_argument('--segment-seconds', type=int, choices=[30, 60], default=30)
            cmd.add_argument('--quality', choices=['best', '720p', '480p', 'worst'], default='best')
            cmd.add_argument('--retries', type=int, default=3)
        else:
            cmd.add_argument('folder', type=Path, help='Folder with clip_000001.mp4 segments')
        cmd.add_argument('--profile', choices=list(PROFILES), default='Gaming')
        cmd.add_argument('--threshold', type=float, default=22)
        cmd.add_argument('--highlight-seconds', type=int, choices=[15, 30, 45, 60], default=30)
        cmd.add_argument('--cooldown', type=int, default=25)
        cmd.add_argument('--ocr', action='store_true', help='Use local Tesseract OCR when installed')
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.action == 'doctor':
        for name in ('python', 'ffmpeg', 'ffprobe', 'streamlink', 'tesseract'):
            path = sys.executable if name == 'python' else shutil.which(name)
            print(f'{name:12} {path or "NOT INSTALLED"}')
        return 0 if shutil.which('ffmpeg') and shutil.which('ffprobe') and shutil.which('streamlink') else 1
    smart = SmartConfig(profile=args.profile, threshold=args.threshold,
                        highlight_seconds=args.highlight_seconds,
                        cooldown_seconds=args.cooldown, ocr=args.ocr)
    try:
        smart.validate()
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    events = queue.Queue()
    recorder = Recorder(events)
    if args.action == 'record':
        try:
            recorder.start(CaptureConfig(url=args.url, seconds=args.segment_seconds,
                                         quality=args.quality, output_root=args.out,
                                         max_restarts=args.retries))
        except Exception as exc:
            print(f'Capture cannot start: {exc}', file=sys.stderr)
            return 2
        folder = recorder.session_folder
    else:
        folder = args.folder
        if not folder.is_dir() or not list(folder.glob('clip_*.mp4')):
            print('No clips in directory', file=sys.stderr)
            return 2
    assert folder is not None
    worker = HighlightPipeline(folder, smart, lambda kind, message: events.put((kind, message)))
    worker.start(already_finished=args.action == 'analyze')
    presentation = SessionUI(args.action, folder)
    presentation.start()
    stopped = False
    try:
        while recorder.active or worker.active:
            try:
                event, value = events.get(timeout=.5)
            except queue.Empty:
                presentation.refresh()
                continue
            if event in ('error','status','smart_status','candidate','highlight','log'):
                presentation.event(event, value)
            elif event == 'finished':
                worker.finish_capture()
            elif event == 'smart_finished':
                presentation.event('smart_status', 'Highlight analyzer completed.')
    except KeyboardInterrupt:
        presentation.event('status', 'Stopping and finalizing highlight analysis')
        stopped = True
        if recorder.active:
            recorder.stop()
        else:
            worker.finish_capture()
        # Keep waiting for Recorder finalization before final scan.
        while recorder.active:
            time.sleep(.2)
        worker.finish_capture()
        worker.join(timeout=180)
        if worker.active:
            worker.cancel()
    finally:
        presentation.close(interrupted=stopped)
    return 130 if stopped else 0


if __name__ == '__main__':
    raise SystemExit(main())
