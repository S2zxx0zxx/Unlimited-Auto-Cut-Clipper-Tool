"""Offline, synthetic-media tests. No copyrighted material or internet required."""
from __future__ import annotations

import json
import math
from pathlib import Path
import random
import shutil
import sqlite3
import subprocess
import tempfile
import time
import unittest
import wave

from liveclip.pipeline import HighlightPipeline, SessionDB, SmartConfig
from liveclip.signals import analyze_segment, score_signals, probe_video
from liveclip.capture import CaptureConfig, next_clip_number, validate_url


def synthesize(folder: Path, seconds: int = 26, fps: int = 5):
    """20s of low activity, followed by a strong 3s burst, then low activity."""
    randomizer = random.Random(5)
    width, height = 160, 90
    source = folder / 'test.rgb'
    with source.open('wb') as f:
        for n in range(seconds * fps):
            t = n / fps
            if 10 <= t < 13:
                frame = bytes(randomizer.randint(0, 255) for _ in range(width * height * 3))
            else:
                color = (15, 20, 28)
                frame = bytes(color) * (width * height)
            f.write(frame)
    sample_rate = 8000
    wav = folder / 'test.wav'
    with wave.open(str(wav), 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        from array import array
        samples = array('h')
        for n in range(seconds * sample_rate):
            t = n / sample_rate
            amplitude = .7 if 10 <= t < 13 else .012
            samples.append(int(amplitude * math.sin(2 * math.pi * 350 * t) * 30000))
        f.writeframes(samples.tobytes())
    video = folder / 'synth.mp4'
    args = [shutil.which('ffmpeg') or 'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
            '-f', 'rawvideo', '-pixel_format', 'rgb24', '-video_size', f'{width}x{height}',
            '-framerate', str(fps), '-i', str(source), '-i', str(wav),
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '25', '-g', str(fps * 10),
            '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '64k', str(video)]
    subprocess.run(args, check=True, capture_output=True, timeout=50)
    for source_file in (source, wav):
        source_file.unlink()
    # Split on keyframes; one 10s burst window and a following segment for post-roll.
    subprocess.run([shutil.which('ffmpeg') or 'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                    '-i', str(video), '-map', '0:v:0', '-map', '0:a:0', '-c', 'copy',
                    '-f', 'segment', '-segment_time', '10', '-reset_timestamps', '1',
                    str(folder / 'clip_%06d.mp4')], check=True, capture_output=True, timeout=40)
    return video


class TestSignals(unittest.TestCase):
    def test_profile_and_novelty(self):
        audio = [-50] * 9 + [-7, -8] + [-50] * 5
        motion = [.01] * 9 + [.65, .5] + [.01] * 5
        cuts = [.0] * 9 + [.7, .65] + [.0] * 5
        flashes = [.01] * 9 + [.5, .3] + [.01] * 5
        scored = score_signals(audio, motion, cuts, flashes, 'Gaming')
        self.assertGreater(scored[9]['score'], 50)
        self.assertLess(scored[4]['score'], 5)
        self.assertIn('audio_surge', scored[9]['reasons'])

    def test_no_audio_support(self):
        scored = score_signals([], [.01, .8, .01], [0, .7, 0], [0, .5, 0], 'Gaming')
        self.assertGreater(scored[1]['score'], 30)

    def test_capture_validation(self):
        cfg = CaptureConfig('https://twitch.tv/a', 30, Path('/tmp'))
        cfg.validate()
        for url in ['file:///some/local', 'https://user:pass@host/t', 'http://localhost:5000']:
            with self.assertRaises(ValueError):
                validate_url(url)
        with self.assertRaises(ValueError):
            SmartConfig(profile='invalid').validate()


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg needed')
class TestPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='liveclip_smart_test_')
        cls.folder = Path(cls.temp.name)
        cls.video = synthesize(cls.folder)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_media_signals_and_export_recovery(self):
        clips = sorted(self.folder.glob('clip_*.mp4'))
        self.assertGreaterEqual(len(clips), 2)
        info, peaks = analyze_segment(clips[1], 'Gaming', False)
        self.assertGreater(info.seconds, 2)
        self.assertTrue(peaks)
        self.assertGreater(max(p.score for p in peaks), 25)
        self.assertLess(next_clip_number(self.folder), 10)
        events = []
        pipeline = HighlightPipeline(self.folder, SmartConfig(profile='Gaming', threshold=22,
                                       highlight_seconds=15, cooldown_seconds=12),
                                     lambda event, message: events.append((event, message)))
        pipeline.start(already_finished=True)
        pipeline.join(timeout=90)
        self.assertFalse(pipeline.active, 'pipeline failed to stop')
        self.assertFalse([x for x in events if x[0]=='error'], events)
        produced = sorted((self.folder / 'highlights').glob('highlight_*.mp4'))
        self.assertTrue(produced, events)
        duration = probe_video(produced[0]).seconds
        self.assertGreater(duration, 3)
        self.assertLessEqual(duration, 15.5)
        lines = (self.folder / 'highlights.jsonl').read_text().splitlines()
        self.assertTrue(lines)
        meta = json.loads(lines[0])
        self.assertIn('reasons', meta)
        self.assertIn('score', meta)
        # Rerun: should neither duplicate output nor events.
        pipeline2 = HighlightPipeline(self.folder, SmartConfig(profile='Gaming', threshold=22,
                                         highlight_seconds=15, cooldown_seconds=12))
        pipeline2.start(already_finished=True)
        pipeline2.join(timeout=30)
        self.assertEqual(len(produced), len(list((self.folder/'highlights').glob('highlight_*.mp4'))))
        self.assertEqual(len(lines), len((self.folder/'highlights.jsonl').read_text().splitlines()))


if __name__ == '__main__':
    unittest.main(verbosity=2)
