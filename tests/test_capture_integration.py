"""End-to-end local simulation: fake Streamlink stdout -> real FFmpeg -> analyzer.
No internet, DRM, or third-party content is used. Real provider coverage is not asserted.
"""
from __future__ import annotations

import os
from pathlib import Path
import queue
import shutil
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

import liveclip.capture as liveclip_core
from liveclip.capture import CaptureConfig, Recorder
from liveclip.pipeline import HighlightPipeline, SmartConfig
from test_smart import synthesize


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
class CaptureIntegrationTest(unittest.TestCase):
    def test_capture_pipeline(self):
        with tempfile.TemporaryDirectory(prefix='liveclip_pipeline_integration_') as temp:
            root = Path(temp)
            src = synthesize(root)
            ts = root / 'stream.ts'
            subprocess.run([shutil.which('ffmpeg'), '-hide_banner', '-loglevel', 'error', '-y',
                            '-i', str(src), '-c:v', 'copy', '-c:a', 'copy', '-f', 'mpegts', str(ts)],
                           check=True, capture_output=True, timeout=30)
            binary = root / ('fake_streamlink.bat' if os.name == 'nt' else 'fake_streamlink')
            if os.name == 'nt':
                self.skipTest('The fake Streamlink fixture here targets POSIX; Windows GUI is untested')
            binary.write_text('#!/usr/bin/env python3\nimport os,sys,shutil\nwith open(os.environ["LOCAL_FAKE_TS"],"rb") as f:\n shutil.copyfileobj(f,sys.stdout.buffer)\n')
            binary.chmod(0o755)
            events = queue.Queue()
            rec = Recorder(events)
            # Record subprocesses inherit PATH and LOCAL_FAKE_TS.
            with patch.dict(os.environ, {'LOCAL_FAKE_TS': str(ts)}), \
                 patch.object(liveclip_core, 'streamlink_executable', return_value=str(binary)):
                rec.start(CaptureConfig('https://example.com/authorized-live', 30, root / 'output', max_restarts=0))
                assert rec.session_folder
                pipeline = HighlightPipeline(rec.session_folder,
                    SmartConfig(profile='Gaming', threshold=15, highlight_seconds=15,
                                cooldown_seconds=12),
                    lambda kind, value: events.put((kind, value)))
                pipeline.start()
                finished = False
                errors = []
                until = time.monotonic() + 45
                while time.monotonic() < until and (rec.active or pipeline.active):
                    try:
                        kind, value = events.get(timeout=.25)
                    except queue.Empty:
                        continue
                    if kind=='finished':
                        finished=True
                        pipeline.finish_capture()
                    elif kind=='error':
                        errors.append(value)
                if not finished and not rec.active:
                    pipeline.finish_capture()
                pipeline.join(timeout=30)
                self.assertFalse(rec.active, 'Recorder hung')
                self.assertFalse(pipeline.active, 'Smart analyzer hung')
                # A finite fake livestream may issue the routine 'stream ended' status.
                self.assertFalse([e for e in errors if 'failed:' in e.lower()], errors)
                clips = list(rec.session_folder.glob('clip_*.mp4'))
                highlights = list((rec.session_folder / 'highlights').glob('highlight_*.mp4'))
                self.assertTrue(clips, 'No source segments created')
                self.assertTrue(highlights, 'No highlights created')
                print(f'PASS simulated Streamlink: {len(clips)} source segments; {len(highlights)} local highlights')


if __name__=='__main__':
    unittest.main(verbosity=2)
